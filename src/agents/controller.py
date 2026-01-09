"""
Controller - 结果合成控制器
负责整合执行结果、生成最终响应、处理输出格式化
"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import settings
from ..config.logging_config import get_logger
from ..config.llm_prompt_logger import log_llm_call
from .state import AgentState, OutputType

logger = get_logger(__name__)


# 响应生成提示词
RESPONSE_GENERATION_PROMPT = """你是卫共流域数字孪生系统的智能助手，负责生成最终响应。

## 用户原始问题
{user_message}

## 用户意图
{intent}

## 执行计划
{plan_summary}

## 执行结果
{execution_results}

## 检索到的相关知识
{retrieved_documents}

## 输出要求
1. 根据执行结果，生成清晰、准确、专业的回答
2. 如果有数据查询结果，请整理成易于理解的格式
3. 如果执行过程中有错误，请适当说明并给出建议
4. 回答应该简洁明了，重点突出

请生成最终回答:
"""

# Web页面生成决策提示词
WEB_PAGE_DECISION_PROMPT = """根据以下信息，决定是否需要生成Web页面展示结果。

## 用户问题
{user_message}

## 执行结果
{execution_results}

## 判断标准
需要生成Web页面的情况:
1. 查询结果包含时序数据（如水位、雨量、流量变化）
2. 需要展示图表（趋势图、柱状图、饼图等）
3. 数据量较大，需要表格展示
4. 包含地理信息需要地图展示

不需要Web页面的情况:
1. 简单的文字回答
2. 单个数值查询
3. 知识问答类问题

请返回JSON格式:
{{
    "need_web_page": true/false,
    "page_type": "chart/table/map/dashboard/none",
    "reason": "判断理由"
}}
"""


class Controller:
    """结果合成控制器"""
    
    def __init__(self):
        """初始化控制器"""
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_model_name,
            temperature=0.7
        )
        
        # 响应生成链
        self.response_prompt = ChatPromptTemplate.from_template(RESPONSE_GENERATION_PROMPT)
        self.response_chain = self.response_prompt | self.llm
        
        logger.info("Controller初始化完成")
    
    async def synthesize_response(self, state: AgentState) -> Dict[str, Any]:
        """
        合成最终响应
        
        Args:
            state: 当前智能体状态
            
        Returns:
            包含最终响应的状态更新
        """
        logger.info("开始合成最终响应...")
        
        try:
            # 格式化执行结果
            execution_summary = self._format_execution_results(
                state.get('execution_results', [])
            )
            
            # 格式化计划摘要
            plan_summary = self._format_plan_summary(state.get('plan', []))
            
            # 格式化检索文档
            docs_summary = self._format_documents(
                state.get('retrieved_documents', [])
            )
            
            # 检查是否需要生成Web页面
            output_type = state.get('output_type', 'text')
            
            if output_type == OutputType.WEB_PAGE.value or await self._should_generate_web_page(state):
                # 需要生成Web页面
                response = await self._generate_web_page_response(state, execution_summary)
                return {
                    "output_type": OutputType.WEB_PAGE.value,
                    "final_response": response['text_response'],
                    "generated_page_url": response.get('page_url'),
                    "next_action": "end"
                }
            
            # 准备上下文变量
            context_vars = {
                "user_message": state.get('user_message', ''),
                "intent": state.get('intent', 'unknown'),
                "plan_summary": plan_summary or "无执行计划",
                "execution_results": execution_summary or "无执行结果",
                "retrieved_documents": docs_summary or "无相关知识"
            }
            
            # 生成文本响应
            response = await self.response_chain.ainvoke(context_vars)
            
            # 记录LLM调用日志
            full_prompt = RESPONSE_GENERATION_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="响应合成",
                module_name="Controller.synthesize_response",
                prompt_template_name="RESPONSE_GENERATION_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=response.content
            )
            
            logger.info("响应合成完成")
            
            return {
                "output_type": OutputType.TEXT.value,
                "final_response": response.content,
                "next_action": "end"
            }
            
        except Exception as e:
            logger.error(f"响应合成失败: {e}")
            return {
                "output_type": OutputType.TEXT.value,
                "final_response": f"抱歉，处理您的请求时遇到了问题: {str(e)}",
                "error": str(e),
                "next_action": "end"
            }
    
    async def _should_generate_web_page(self, state: AgentState) -> bool:
        """
        判断是否需要生成Web页面
        
        Args:
            state: 当前状态
            
        Returns:
            是否需要生成Web页面
        """
        execution_results = state.get('execution_results', [])
        
        # 快速判断：如果结果中包含大量数据，可能需要Web页面
        for result in execution_results:
            output = result.get('output')
            if isinstance(output, (list, dict)):
                # 如果是列表且长度超过10，或包含时序数据关键字
                if isinstance(output, list) and len(output) > 10:
                    return True
                if isinstance(output, dict):
                    # 检查是否包含图表相关的数据结构
                    if any(key in output for key in ['data', 'series', 'values', 'time_series']):
                        return True
        
        return False
    
    async def _generate_web_page_response(
        self, 
        state: AgentState,
        execution_summary: str
    ) -> Dict[str, Any]:
        """
        生成Web页面响应
        
        Args:
            state: 当前状态
            execution_summary: 执行结果摘要
            
        Returns:
            包含文本响应和页面URL的字典
        """
        logger.info("准备生成Web页面...")
        
        try:
            from ..output.page_generator import generate_report_page
            
            # 整合所有执行结果数据
            combined_data = {}
            results = state.get('execution_results', [])
            for result in results:
                if result.get('success'):
                    output = result.get('output')
                    if isinstance(output, dict):
                        combined_data.update(output)
            
            # 确定报告类型 (简单逻辑，可扩展)
            report_type = "generic"
            intent = state.get('intent', '')
            if '洪水' in intent or '预报' in intent:
                report_type = 'flood_forecast'
            elif '预案' in intent:
                report_type = 'emergency_plan'
            
            # 生成页面
            page_url = await generate_report_page(
                report_type=report_type,
                data=combined_data,
                title=f"{intent}报告"
            )
            
            # 使用LLM生成针对用户问题的智能文字回复
            docs_summary = self._format_documents(
                state.get('retrieved_documents', [])
            )
            plan_summary = self._format_plan_summary(state.get('plan', []))
            
            try:
                # 准备上下文变量
                web_context_vars = {
                    "user_message": state.get('user_message', ''),
                    "intent": state.get('intent', 'unknown'),
                    "plan_summary": plan_summary or "无执行计划",
                    "execution_results": execution_summary or "无执行结果",
                    "retrieved_documents": docs_summary or "无相关知识"
                }
                
                llm_response = await self.response_chain.ainvoke(web_context_vars)
                text_response = llm_response.content
                
                # 记录LLM调用日志
                full_prompt = RESPONSE_GENERATION_PROMPT.format(**web_context_vars)
                log_llm_call(
                    step_name="Web页面响应合成",
                    module_name="Controller._generate_web_page_response",
                    prompt_template_name="RESPONSE_GENERATION_PROMPT",
                    context_variables=web_context_vars,
                    full_prompt=full_prompt,
                    response=text_response
                )
                
                logger.info("LLM生成文字回复成功")
            except Exception as llm_error:
                logger.warning(f"LLM生成文字回复失败，使用默认模板: {llm_error}")
                text_response = f"""根据您的查询，我已为您生成了详细报告。

{execution_summary}

您可以点击右侧查看完整报告。"""
            
            return {
                "text_response": text_response,
                "page_url": page_url
            }
            
        except Exception as e:
            logger.error(f"生成Web页面失败: {e}")
            return {
                "text_response": f"{execution_summary}\n\n(Web页面生成失败: {e})",
                "page_url": None
            }
    
    async def handle_error_response(self, state: AgentState) -> Dict[str, Any]:
        """
        处理错误情况的响应
        
        Args:
            state: 当前状态
            
        Returns:
            错误响应
        """
        error = state.get('error', '未知错误')
        user_message = state.get('user_message', '')
        
        logger.warning(f"生成错误响应: {error}")
        
        # 根据错误类型生成友好的响应
        error_responses = {
            "意图分析失败": "抱歉，我没能理解您的问题，请尝试用更清晰的方式描述您的需求。",
            "工具执行失败": "抱歉，在处理您的请求时遇到了技术问题，请稍后再试。",
            "超时": "抱歉，请求处理超时，可能是因为数据量较大或网络问题，请稍后再试。"
        }
        
        # 匹配错误类型
        response = None
        for key, msg in error_responses.items():
            if key in error:
                response = msg
                break
        
        if not response:
            response = f"抱歉，处理您的请求时遇到了问题。错误信息: {error}"
        
        return {
            "output_type": OutputType.TEXT.value,
            "final_response": response,
            "next_action": "end"
        }
    
    async def format_streaming_response(
        self, 
        state: AgentState
    ) -> Dict[str, Any]:
        """
        格式化流式响应数据
        
        用于WebSocket或SSE实时推送
        
        Args:
            state: 当前状态
            
        Returns:
            流式响应数据
        """
        return {
            "type": "progress",
            "data": {
                "current_step": state.get('current_step_index', 0),
                "total_steps": len(state.get('plan', [])),
                "status": state.get('next_action', 'processing'),
                "message": self._get_progress_message(state)
            }
        }
    
    def _get_progress_message(self, state: AgentState) -> str:
        """获取进度消息"""
        action = state.get('next_action', '')
        
        if action == 'plan':
            return "正在分析您的问题..."
        elif action == 'execute':
            step_index = state.get('current_step_index', 0)
            plan = state.get('plan', [])
            if step_index < len(plan):
                return f"正在执行: {plan[step_index].get('description', '处理中...')}"
            return "正在执行任务..."
        elif action == 'respond':
            return "正在生成回复..."
        elif action == 'wait_async':
            return "正在等待后台任务完成..."
        elif action == 'end':
            return "处理完成"
        
        return "处理中..."
    
    def _format_execution_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化执行结果"""
        if not results:
            return ""
        
        formatted = []
        for r in results:
            step_id = r.get('step_id', '?')
            success = r.get('success', False)
            output = r.get('output', '')
            error = r.get('error')
            
            if success:
                # 格式化输出
                if isinstance(output, dict):
                    output_str = self._format_dict_output(output)
                elif isinstance(output, list):
                    output_str = self._format_list_output(output)
                else:
                    output_str = str(output)
                formatted.append(f"步骤{step_id}: {output_str}")
            else:
                formatted.append(f"步骤{step_id}: 执行失败 - {error}")
        
        return "\n\n".join(formatted)
    
    def _format_dict_output(self, data: Dict[str, Any], max_items: int = 20) -> str:
        """格式化字典输出"""
        items = list(data.items())[:max_items]
        lines = [f"  - {k}: {v}" for k, v in items]
        if len(data) > max_items:
            lines.append(f"  ... 共{len(data)}项")
        return "\n".join(lines)
    
    def _format_list_output(self, data: List[Any], max_items: int = 10) -> str:
        """格式化列表输出"""
        items = data[:max_items]
        lines = [f"  {i+1}. {item}" for i, item in enumerate(items)]
        if len(data) > max_items:
            lines.append(f"  ... 共{len(data)}项")
        return "\n".join(lines)
    
    def _format_plan_summary(self, plan: List[Dict[str, Any]]) -> str:
        """格式化计划摘要"""
        if not plan:
            return ""
        
        steps = []
        for step in plan:
            step_id = step.get('step_id', '?')
            description = step.get('description', '')
            status = step.get('status', 'pending')
            steps.append(f"{step_id}. {description} [{status}]")
        
        return "\n".join(steps)
    
    def _format_documents(self, documents: List[Dict[str, Any]]) -> str:
        """格式化文档摘要"""
        if not documents:
            return ""

        formatted = []
        for i, doc in enumerate(documents[:5], 1):
            content = doc.get('content', '')[:2000]
            metadata = doc.get('metadata', {})
            # 优先使用source(网络搜索)，其次doc_name(知识库)
            source = metadata.get('source') or metadata.get('doc_name') or '未知来源'
            title = metadata.get('title', '')
            if title:
                formatted.append(f"[{i}] {source} - {title}\n{content}")
            else:
                formatted.append(f"[{i}] {source}\n{content}")

        return "\n\n".join(formatted)


# 创建全局Controller实例
_controller_instance: Optional[Controller] = None


def get_controller() -> Controller:
    """获取Controller单例"""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = Controller()
    return _controller_instance


async def controller_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph节点函数 - 控制节点
    
    合成最终响应
    """
    controller = get_controller()
    
    # 检查是否有错误需要处理
    if state.get('error') and not state.get('execution_results'):
        return await controller.handle_error_response(state)
    
    # 合成响应
    return await controller.synthesize_response(state)
