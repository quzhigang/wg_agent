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


# 需要过滤的工具列表（这些工具的结果不传递给响应合成LLM）
EXCLUDE_TOOLS_FROM_RESPONSE = [
    "login",           # 登录工具，返回token等敏感信息
    "get_auth_token",  # 认证工具
]

# 需要过滤的敏感字段
SENSITIVE_FIELDS = ["token", "password", "api_key", "secret"]


# 响应生成提示词
RESPONSE_GENERATION_PROMPT = """你是卫共流域数字孪生系统的智能助手，负责生成最终响应。

## 最近对话历史
{chat_history}

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
1. 结合对话历史理解用户问题的完整含义（如用户说"小南海呢？"，需结合历史知道是在问流域面积）
2. 根据执行结果，生成清晰、准确、专业的回答
3. 如果有数据查询结果，请整理成易于理解的格式
4. 如果执行过程中有错误，请适当说明并给出建议
5. 回答应该简洁明了，直接切中主题。
6. 【重要】如果使用了检索到的知识，必须在回答末尾添加"参考来源"部分。直接复制上面每条知识的"来源引用格式"字段内容作为来源链接，不要修改或简化！

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
        # 思考模式配置（用于Qwen3等模型，非流式调用需设置为false）
        extra_body = {"enable_thinking": settings.llm_enable_thinking}

        # 结果合成LLM
        synthesis_cfg = settings.get_synthesis_config()
        self.llm = ChatOpenAI(
            api_key=synthesis_cfg["api_key"],
            base_url=synthesis_cfg["api_base"],
            model=synthesis_cfg["model"],
            temperature=synthesis_cfg["temperature"],
            model_kwargs={"extra_body": extra_body}
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
            # 格式化执行结果（传入plan用于过滤内部工具）
            execution_summary = self._format_execution_results(
                state.get('execution_results', []),
                state.get('plan', [])
            )

            # 格式化计划摘要
            plan_summary = self._format_plan_summary(state.get('plan', []))

            # 格式化检索文档
            docs_summary = self._format_documents(
                state.get('retrieved_documents', [])
            )

            # 格式化聊天历史（限制最近2轮对话）
            chat_history_str = self._format_chat_history(state.get('chat_history', []))

            # 检查工作流是否已经生成了页面URL
            workflow_page_url = state.get('generated_page_url')
            if workflow_page_url:
                logger.info(f"工作流已生成页面URL: {workflow_page_url}")
                # 生成文字回复
                text_response = await self._generate_text_response_for_workflow(state, execution_summary)
                return {
                    "output_type": OutputType.WEB_PAGE.value,
                    "final_response": text_response,
                    "generated_page_url": workflow_page_url,
                    "page_generating": False,
                    "next_action": "end"
                }

            # 检查是否需要生成Web页面
            output_type = state.get('output_type', 'text')

            if output_type == OutputType.WEB_PAGE.value or await self._should_generate_web_page(state):
                # 需要生成Web页面（异步模式）
                response = await self._generate_web_page_response(state, execution_summary)
                return {
                    "output_type": OutputType.WEB_PAGE.value,
                    "final_response": response['text_response'],
                    "generated_page_url": response.get('page_url'),
                    "page_task_id": response.get('page_task_id'),
                    "page_generating": response.get('page_generating', False),
                    "next_action": "end"
                }

            # 准备上下文变量
            context_vars = {
                "chat_history": chat_history_str or "无",
                "user_message": state.get('user_message', ''),
                "intent": state.get('intent', 'unknown'),
                "plan_summary": plan_summary or "无执行计划",
                "execution_results": execution_summary or "无执行结果",
                "retrieved_documents": docs_summary or "无相关知识"
            }

            # 生成文本响应
            import time
            _start = time.time()
            response = await self.response_chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = RESPONSE_GENERATION_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="响应合成",
                module_name="Controller.synthesize_response",
                prompt_template_name="RESPONSE_GENERATION_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=response.content,
                elapsed_time=_elapsed
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
        生成Web页面响应（异步模式）

        页面生成由独立的异步智能体执行，不阻塞主对话流程。
        返回任务ID，前端通过轮询或WebSocket获取页面URL。

        Args:
            state: 当前状态
            execution_summary: 执行结果摘要

        Returns:
            包含文本响应和页面任务ID的字典
        """
        logger.info("准备异步生成Web页面...")

        # 先生成文字回复（不阻塞）
        text_response = None
        results = state.get('execution_results', [])

        # 检查最后一步是否已经是LLM生成的文字总结
        if results:
            last_result = results[-1]
            last_output = last_result.get('output')
            if last_result.get('success') and isinstance(last_output, str) and len(last_output) > 20:
                text_response = last_output
                logger.info("复用执行步骤中的LLM总结，跳过重复生成")

        if not text_response:
            # 需要LLM生成文字回复
            docs_summary = self._format_documents(state.get('retrieved_documents', []))
            plan_summary = self._format_plan_summary(state.get('plan', []))

            try:
                chat_history_str = self._format_chat_history(state.get('chat_history', []))
                web_context_vars = {
                    "chat_history": chat_history_str or "无",
                    "user_message": state.get('user_message', ''),
                    "intent": state.get('intent', 'unknown'),
                    "plan_summary": plan_summary or "无执行计划",
                    "execution_results": execution_summary or "无执行结果",
                    "retrieved_documents": docs_summary or "无相关知识"
                }

                import time
                _start = time.time()
                llm_response = await self.response_chain.ainvoke(web_context_vars)
                _elapsed = time.time() - _start
                text_response = llm_response.content

                full_prompt = RESPONSE_GENERATION_PROMPT.format(**web_context_vars)
                log_llm_call(
                    step_name="Web页面响应合成",
                    module_name="Controller._generate_web_page_response",
                    prompt_template_name="RESPONSE_GENERATION_PROMPT",
                    context_variables=web_context_vars,
                    full_prompt=full_prompt,
                    response=text_response,
                    elapsed_time=_elapsed
                )
                logger.info("LLM生成文字回复成功")
            except Exception as llm_error:
                logger.warning(f"LLM生成文字回复失败，使用默认模板: {llm_error}")
                text_response = f"""根据您的查询，系统正在为您生成详细报告。

{execution_summary}

报告生成中，请稍候..."""

        # 异步提交页面生成任务
        try:
            from ..output.async_page_agent import get_async_page_agent

            # 整合所有执行结果数据
            combined_data = {}
            for result in results:
                if result.get('success'):
                    output = result.get('output')
                    if isinstance(output, dict):
                        combined_data.update(output)

            # 确定报告类型
            report_type = "generic"
            intent = state.get('intent', '')
            if '洪水' in intent or '预报' in intent:
                report_type = 'flood_forecast'
            elif '预案' in intent:
                report_type = 'emergency_plan'

            # 提交异步任务
            async_agent = get_async_page_agent()
            task_id = async_agent.submit_task(
                conversation_id=state.get('conversation_id', ''),
                report_type=report_type,
                data=combined_data,
                title=f"{intent}报告",
                execution_summary=execution_summary
            )

            logger.info(f"页面生成任务已提交: {task_id}")

            return {
                "text_response": text_response,
                "page_url": None,  # 页面URL稍后通过任务状态获取
                "page_task_id": task_id,
                "page_generating": True
            }

        except Exception as e:
            logger.error(f"提交页面生成任务失败: {e}")
            return {
                "text_response": text_response,
                "page_url": None,
                "page_task_id": None,
                "page_generating": False,
                "page_error": str(e)
            }

    async def _generate_text_response_for_workflow(
        self,
        state: AgentState,
        execution_summary: str
    ) -> str:
        """
        为工作流生成文字回复

        当工作流已经生成了页面URL时，只需要生成文字回复。

        Args:
            state: 当前状态
            execution_summary: 执行结果摘要

        Returns:
            文字回复
        """
        # 检查工作流结果中是否有提取的数据
        extracted_result = state.get('extracted_result', {})
        forecast_target = state.get('forecast_target', {})

        logger.info(f"生成工作流文字回复 - extracted_result存在: {bool(extracted_result)}, forecast_target: {forecast_target}")

        # 如果有提取的结果，基于结果生成回复
        if extracted_result:
            target_name = forecast_target.get('name', '目标')
            target_type = forecast_target.get('type', 'basin')
            summary = extracted_result.get('summary', '')
            data = extracted_result.get('data', {})

            logger.info(f"提取结果 - summary: {summary}, data存在: {bool(data)}, data有message: {data.get('message') if data else None}")

            # 构建格式化的文字回复
            if data and not data.get('message'):
                # 有有效数据，生成格式化回复
                result = self._format_forecast_response(target_name, target_type, summary, data)
                logger.info(f"生成的文字回复: {result[:100]}...")
                return result
            elif data.get('message'):
                # 有错误消息
                return data.get('message')

        # 使用LLM生成回复
        logger.info("extracted_result为空或无有效数据，使用LLM生成回复")
        try:
            chat_history_str = self._format_chat_history(state.get('chat_history', []))
            docs_summary = self._format_documents(state.get('retrieved_documents', []))

            context_vars = {
                "chat_history": chat_history_str or "无",
                "user_message": state.get('user_message', ''),
                "intent": state.get('intent', 'unknown'),
                "plan_summary": "工作流执行完成",
                "execution_results": execution_summary or "无执行结果",
                "retrieved_documents": docs_summary or "无相关知识"
            }

            import time
            _start = time.time()
            response = await self.response_chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            full_prompt = RESPONSE_GENERATION_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="工作流响应合成",
                module_name="Controller._generate_text_response_for_workflow",
                prompt_template_name="RESPONSE_GENERATION_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=response.content,
                elapsed_time=_elapsed
            )

            return response.content

        except Exception as e:
            logger.warning(f"LLM生成回复失败: {e}")
            return f"已完成查询，详细结果请查看右侧报告页面。"

    def _format_forecast_response(
        self,
        target_name: str,
        target_type: str,
        summary: str,
        data: Dict[str, Any]
    ) -> str:
        """
        格式化预报结果为文字回复

        Args:
            target_name: 目标名称（如水库名、站点名）
            target_type: 目标类型（reservoir/station/detention_basin/basin/multiple）
            summary: 摘要信息
            data: 预报数据

        Returns:
            格式化的文字回复
        """
        lines = [f"**{summary}**\n"]

        # 多对象查询结果（支持 targets 和 results 两种格式）
        if target_type == 'multiple':
            items = data.get('targets') or data.get('results') or []
            if items:
                for result_item in items:
                    item_data = result_item.get('data', {})
                    # 兼容两种格式：直接的 name/type 或嵌套的 target.name/target.type
                    item_name = result_item.get('name') or result_item.get('target', {}).get('name', '未知对象')
                    item_type = result_item.get('type') or result_item.get('target', {}).get('type', 'basin')

                    # 检查是否有错误消息
                    if item_data.get('message'):
                        lines.append(f"\n⚠️ **{item_name}**：{item_data.get('message')}")
                        continue

                    # 根据类型格式化单个对象的结果
                    single_lines = self._format_single_target_response(item_name, item_type, item_data)
                    lines.extend(single_lines)

                lines.append("\n💡 *详细信息和过程曲线请查看左侧报告页面。*")
                return "\n".join(lines)

        if target_type == 'reservoir':
            # 水库预报结果格式化
            lines.append(f"📊 **{target_name}预报数据：**\n")

            # 入库流量信息
            inflow_peak = data.get('Max_InQ') or data.get('inflow_peak') or data.get('入库洪峰流量')
            inflow_peak_time = data.get('MaxInQ_Time') or data.get('inflow_peak_time') or data.get('入库洪峰时间')
            if inflow_peak is not None:
                lines.append(f"- **入库洪峰流量**：{inflow_peak} m³/s")
                if inflow_peak_time:
                    lines.append(f"- **入库洪峰时间**：{inflow_peak_time}")

            # 出库流量信息
            outflow_peak = data.get('Max_OutQ') or data.get('outflow_peak') or data.get('出库洪峰流量')
            outflow_peak_time = data.get('MaxOutQ_Time') or data.get('outflow_peak_time') or data.get('出库洪峰时间')
            if outflow_peak is not None:
                lines.append(f"- **出库洪峰流量**：{outflow_peak} m³/s")
                if outflow_peak_time:
                    lines.append(f"- **出库洪峰时间**：{outflow_peak_time}")

            # 水位信息
            max_level = data.get('Max_Level') or data.get('max_water_level') or data.get('最高水位')
            max_level_time = data.get('MaxLevel_Time') or data.get('max_water_level_time') or data.get('最高水位时间')
            if max_level is not None:
                lines.append(f"- **最高水位**：{max_level} m")
                if max_level_time:
                    lines.append(f"- **最高水位时间**：{max_level_time}")

            # 蓄水量信息
            max_storage = data.get('Max_Volumn') or data.get('max_storage') or data.get('最大蓄水量')
            if max_storage is not None:
                lines.append(f"- **最大蓄水量**：{max_storage} 万m³")

            # 总入库量和总出库量
            total_inflow = data.get('Total_InVolumn') or data.get('总入库量')
            total_outflow = data.get('Total_OutVolumn') or data.get('总出库量')
            if total_inflow is not None:
                lines.append(f"- **总入库量**：{total_inflow} 万m³")
            if total_outflow is not None:
                lines.append(f"- **总出库量**：{total_outflow} 万m³")

            # 预报结束时状态
            end_level = data.get('EndTime_Level') or data.get('预报结束水位')
            end_storage = data.get('EndTime_Volumn') or data.get('预报结束蓄水量')
            if end_level is not None or end_storage is not None:
                lines.append(f"\n📈 **预报结束时状态：**")
                if end_level is not None:
                    lines.append(f"- **水位**：{end_level} m")
                if end_storage is not None:
                    lines.append(f"- **蓄水量**：{end_storage} 万m³")

        elif target_type == 'station':
            # 站点预报结果格式化
            lines.append(f"📊 **{target_name}预报数据：**\n")

            # 根据API返回的字段名获取数据
            # API字段: Max_Qischarge, MaxQ_AtTime, Max_Level, Total_Flood, Stcd, SectionName
            peak_flow = data.get('Max_Qischarge') or data.get('peak_flow') or data.get('洪峰流量')
            peak_time = data.get('MaxQ_AtTime') or data.get('peak_time') or data.get('洪峰时间')
            peak_level = data.get('Max_Level') or data.get('peak_level') or data.get('洪峰水位')
            total_flood = data.get('Total_Flood') or data.get('总过洪量')
            stcd = data.get('Stcd')
            section_name = data.get('SectionName')

            if section_name:
                lines.append(f"- **断面名称**：{section_name}")
            if stcd:
                lines.append(f"- **站点编码**：{stcd}")
            if peak_flow is not None:
                lines.append(f"- **洪峰流量**：{peak_flow} m³/s")
            if peak_time:
                lines.append(f"- **洪峰到达时间**：{peak_time}")
            if peak_level is not None:
                lines.append(f"- **最高水位**：{peak_level} m")
            if total_flood is not None:
                lines.append(f"- **总过洪量**：{total_flood} 万m³")

        elif target_type == 'detention_basin':
            # 蓄滞洪区预报结果格式化
            lines.append(f"📊 **{target_name}预报数据：**\n")

            # 显示所有非时序数据字段
            skip_keys = {'message', 'InQ_Dic', 'OutQ_Dic', 'Level_Dic', 'Volumn_Dic',
                        'YHDOutQ_Dic', 'XHDOutQ_Dic'}
            for key, value in data.items():
                if key not in skip_keys and not isinstance(value, dict):
                    lines.append(f"- **{key}**：{value}")

        else:
            # 全流域或其他类型
            lines.append(f"📊 **预报数据：**\n")

            # 处理水库结果
            reservoir_result = data.get('reservoir_result', {})
            if reservoir_result:
                for res_name, res_data in reservoir_result.items():
                    lines.append(f"\n🏞️ **{res_name}：**")
                    if isinstance(res_data, dict):
                        max_level = res_data.get('Max_Level')
                        max_inq = res_data.get('Max_InQ')
                        max_outq = res_data.get('Max_OutQ')
                        if max_level is not None:
                            lines.append(f"- 最高水位：{max_level} m")
                        if max_inq is not None:
                            lines.append(f"- 入库洪峰：{max_inq} m³/s")
                        if max_outq is not None:
                            lines.append(f"- 出库洪峰：{max_outq} m³/s")

            # 处理站点结果
            station_result = data.get('station_result', data.get('stations', []))
            if station_result:
                if isinstance(station_result, list):
                    for sta in station_result:
                        sta_name = sta.get('name', '未知站点')
                        lines.append(f"\n📍 **{sta_name}：**")
                        peak_flow = sta.get('peak_flow') or sta.get('洪峰流量')
                        peak_level = sta.get('peak_level') or sta.get('洪峰水位')
                        if peak_flow is not None:
                            lines.append(f"- 洪峰流量：{peak_flow} m³/s")
                        if peak_level is not None:
                            lines.append(f"- 洪峰水位：{peak_level} m")

        lines.append("\n💡 *详细信息和过程曲线请查看左侧报告页面。*")

        return "\n".join(lines)

    def _format_single_target_response(
        self,
        target_name: str,
        target_type: str,
        data: Dict[str, Any]
    ) -> List[str]:
        """
        格式化单个对象的预报结果

        Args:
            target_name: 目标名称
            target_type: 目标类型
            data: 预报数据

        Returns:
            格式化的文字行列表
        """
        lines = []

        if target_type == 'reservoir':
            lines.append(f"\n🏞️ **{target_name}：**")
            # 入库流量信息
            inflow_peak = data.get('Max_InQ') or data.get('inflow_peak')
            inflow_peak_time = data.get('MaxInQ_Time') or data.get('inflow_peak_time')
            if inflow_peak is not None:
                lines.append(f"- 入库洪峰流量：{inflow_peak} m³/s")
                if inflow_peak_time:
                    lines.append(f"- 入库洪峰时间：{inflow_peak_time}")
            # 出库流量信息
            outflow_peak = data.get('Max_OutQ') or data.get('outflow_peak')
            if outflow_peak is not None:
                lines.append(f"- 出库洪峰流量：{outflow_peak} m³/s")
            # 水位信息
            max_level = data.get('Max_Level') or data.get('max_water_level')
            max_level_time = data.get('MaxLevel_Time')
            if max_level is not None:
                lines.append(f"- 最高水位：{max_level} m")
                if max_level_time:
                    lines.append(f"- 最高水位时间：{max_level_time}")

        elif target_type == 'station':
            lines.append(f"\n📍 **{target_name}：**")
            # 站点预报结果
            peak_flow = data.get('Max_Qischarge') or data.get('peak_flow')
            peak_time = data.get('MaxQ_AtTime') or data.get('peak_time')
            peak_level = data.get('Max_Level') or data.get('peak_level')
            total_flood = data.get('Total_Flood')
            if peak_flow is not None:
                lines.append(f"- 洪峰流量：{peak_flow} m³/s")
            if peak_time:
                lines.append(f"- 洪峰到达时间：{peak_time}")
            if peak_level is not None:
                lines.append(f"- 最高水位：{peak_level} m")
            if total_flood is not None:
                lines.append(f"- 总过洪量：{total_flood} 万m³")

        elif target_type == 'detention_basin':
            lines.append(f"\n🌊 **{target_name}：**")
            # 蓄滞洪区预报结果
            state_val = data.get('Xzhq_State') or data.get('状态')
            if state_val:
                lines.append(f"- 状态：{state_val}")
            max_inflow = data.get('Max_InQ')
            if max_inflow is not None:
                lines.append(f"- 最大进洪流量：{max_inflow} m³/s")
            total_inflow = data.get('Total_InVolumn')
            if total_inflow is not None:
                lines.append(f"- 总进洪量：{total_inflow} 万m³")

        elif target_type == 'gate':
            lines.append(f"\n🚧 **{target_name}：**")
            # 闸站预报结果（类似站点）
            peak_flow = data.get('Max_Qischarge') or data.get('peak_flow')
            peak_level = data.get('Max_Level') or data.get('peak_level')
            if peak_flow is not None:
                lines.append(f"- 洪峰流量：{peak_flow} m³/s")
            if peak_level is not None:
                lines.append(f"- 最高水位：{peak_level} m")

        else:
            lines.append(f"\n📊 **{target_name}：**")
            # 通用格式化
            for key, value in data.items():
                if not isinstance(value, (dict, list)) and key not in ['message']:
                    lines.append(f"- {key}：{value}")

        return lines

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
    
    def _format_execution_results(self, results: List[Dict[str, Any]], plan: List[Dict[str, Any]] = None) -> str:
        """格式化执行结果，过滤内部工具和敏感信息"""
        if not results:
            return ""

        # 构建 step_id -> tool_name 映射
        tool_map = {}
        if plan:
            for step in plan:
                tool_map[step.get('step_id')] = step.get('tool_name', '')

        formatted = []
        for r in results:
            step_id = r.get('step_id', '?')
            tool_name = tool_map.get(step_id, '')

            # 过滤：跳过内部工具的结果
            if tool_name in EXCLUDE_TOOLS_FROM_RESPONSE:
                logger.debug(f"过滤步骤{step_id}的结果（工具: {tool_name}）")
                continue

            success = r.get('success', False)
            output = r.get('output', '')
            error = r.get('error')

            if success:
                # 格式化输出
                if isinstance(output, dict):
                    # 过滤敏感字段
                    filtered_output = self._filter_sensitive_fields(output)
                    output_str = self._format_dict_output(filtered_output)
                elif isinstance(output, list):
                    output_str = self._format_list_output(output)
                else:
                    output_str = str(output)
                formatted.append(f"步骤{step_id}: {output_str}")
            else:
                formatted.append(f"步骤{step_id}: 执行失败 - {error}")

        return "\n\n".join(formatted)

    def _filter_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤字典中的敏感字段"""
        filtered = {}
        for key, value in data.items():
            # 检查是否为敏感字段
            if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                continue
            # 递归处理嵌套字典
            if isinstance(value, dict):
                filtered[key] = self._filter_sensitive_fields(value)
            else:
                filtered[key] = value
        return filtered
    
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

    def _format_chat_history(self, chat_history: List[Dict[str, str]], max_turns: int = 2) -> str:
        """格式化聊天历史，限制最近N轮对话"""
        if not chat_history:
            return ""

        # 最近N轮对话（每轮包含user和assistant各一条）
        recent = chat_history[-max_turns * 2:]
        formatted = []
        for msg in recent:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            # 限制每条消息长度，避免过长
            if len(content) > 200:
                content = content[:200] + "..."
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)
    
    def _format_documents(self, documents: List[Dict[str, Any]]) -> str:
        """格式化文档摘要，包含来源信息供LLM引用"""
        if not documents:
            return ""

        formatted = []
        for i, doc in enumerate(documents[:5], 1):
            # 不截断内容，保留完整的知识库检索结果
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})

            # 获取来源信息
            source_url = metadata.get('source', '')  # 网络搜索URL
            doc_name = metadata.get('doc_name', '')  # 知识库文档名
            category = metadata.get('category', '')  # 知识库类别
            title = metadata.get('title', '')

            # 构建来源标识
            if source_url and source_url.startswith('http'):
                # 网络搜索结果
                source_label = f"网络来源: {title or source_url}"
                source_ref = f"[{title or '网络链接'}]({source_url})"
            else:
                # 知识库文档 - 生成完整URL
                kb_id = category or 'unknown'
                display_name = doc_name or kb_id
                source_label = f"知识库: {kb_id}, 文档: {doc_name}"
                if doc_name:
                    # 使用完整URL确保链接正确
                    source_ref = f"[{display_name}](http://localhost:8000/knowledge/kb-doc/{kb_id}/{doc_name})"
                else:
                    source_ref = f"知识库-{kb_id}"

            formatted.append(f"[{i}] 来源: {source_label}\n来源引用格式: {source_ref}\n内容: {content}")

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
