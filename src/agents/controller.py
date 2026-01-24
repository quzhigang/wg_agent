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
from ..output.template_match_service import get_template_match_service
from ..output.page_generator import get_page_generator
from ..output.dynamic_template_service import get_dynamic_template_service
from ..output.dynamic_page_generator import get_dynamic_page_generator
from ..utils.conversation_context_collector import create_collector_from_state

logger = get_logger(__name__)


# 需要过滤的工具列表（这些工具的结果不传递给响应合成LLM）
EXCLUDE_TOOLS_FROM_RESPONSE = [
    "login",           # 登录工具，返回token等敏感信息
    "get_auth_token",  # 认证工具
]

# 需要过滤的敏感字段
SENSITIVE_FIELDS = ["token", "password", "api_key", "secret"]

# 需要轻量化处理的工具列表（这些工具返回大量时序数据，需要截取部分值）
# 轻量化处理：对于时序数据字典，只保留前几个值作为示例
LIGHTWEIGHT_TOOLS = [
    "get_tjdata_result",           # 获取预报方案结果，包含大量时序数据
    "get_history_autoforcast_res", # 获取历史自动预报结果，包含大量时序数据
]


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
3. 回答应该简洁明了，直接切中主题，突出关键数据和结论
4. 如果执行过程中有错误，请适当说明并给出建议
5. 【重要】如果使用了检索到的知识，必须在回答末尾添加"参考来源"部分。直接复制上面每条知识的"来源引用格式"字段内容作为来源链接，不要修改或简化！

## 格式禁止
- 【禁止】不要使用Markdown表格格式（如 | 列1 | 列2 | 这种格式）
- 【禁止】不要罗列大量数据项，表格和详细数据应在左侧报告页面中展示
- 【建议】使用简洁的文字描述或短列表（如"- 项目: 值"）来呈现关键信息
- 【建议】如果数据较多，只提取最关键的2-3个指标进行说明，并提示用户查看左侧报告页面获取完整信息

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
    
    def prepare_response_context(self, state: AgentState) -> Dict[str, Any]:
        """
        准备响应上下文数据

        Args:
            state: 当前智能体状态

        Returns:
            包含所有上下文数据的字典
        """
        # 格式化执行结果（传入plan用于过滤内部工具）
        execution_summary = self._format_execution_results(
            state.get('execution_results', []),
            state.get('plan', [])
        )

        # 格式化计划摘要（传入执行结果以推断步骤状态）
        plan_summary = self._format_plan_summary(
            state.get('plan', []),
            state.get('execution_results', [])
        )

        # 格式化检索文档
        docs_summary = self._format_documents(
            state.get('retrieved_documents', [])
        )

        # 格式化聊天历史（限制最近2轮对话）
        chat_history_str = self._format_chat_history(state.get('chat_history', []))

        # 整合所有执行结果数据（用于模板数据准备）
        results = state.get('execution_results', [])
        combined_data = {}
        for result in results:
            if result.get('success'):
                output = result.get('output') or result.get('result')
                if isinstance(output, dict):
                    combined_data.update(output)

        return {
            "execution_summary": execution_summary,
            "plan_summary": plan_summary,
            "docs_summary": docs_summary,
            "chat_history_str": chat_history_str,
            "combined_data": combined_data,
            "results": results
        }

    async def generate_text_only(self, state: AgentState, context: Dict[str, Any]) -> str:
        """
        仅生成文字回复（独立方法，用于并行执行）

        Args:
            state: 当前智能体状态
            context: 预先准备的上下文数据

        Returns:
            文字回复内容
        """
        # 检查是否有可复用的文字回复
        results = context.get('results', [])
        if results:
            last_result = results[-1]
            last_output = last_result.get('output')
            if last_result.get('success') and isinstance(last_output, str) and len(last_output) > 20:
                logger.info("复用执行步骤中的LLM总结，跳过重复生成")
                return last_output

        # 准备上下文变量
        context_vars = {
            "chat_history": context.get('chat_history_str') or "无",
            "user_message": state.get('user_message', ''),
            "intent": state.get('intent', 'unknown'),
            "plan_summary": context.get('plan_summary') or "无执行计划",
            "execution_results": context.get('execution_summary') or "无执行结果",
            "retrieved_documents": context.get('docs_summary') or "无相关知识"
        }

        try:
            import time
            _start = time.time()
            response = await self.response_chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = RESPONSE_GENERATION_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="文字响应生成",
                module_name="Controller.generate_text_only",
                prompt_template_name="RESPONSE_GENERATION_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=response.content,
                elapsed_time=_elapsed
            )

            logger.info("LLM生成文字回复成功")
            return response.content

        except Exception as e:
            logger.warning(f"LLM生成文字回复失败: {e}")
            return f"根据您的查询，系统已完成处理。\n\n{context.get('execution_summary', '')}"

    async def generate_page_only(self, state: AgentState, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        仅生成页面（独立方法，用于并行执行）

        Args:
            state: 当前智能体状态
            context: 预先准备的上下文数据

        Returns:
            包含页面URL或错误信息的字典
        """
        try:
            results = context.get('results', [])
            combined_data = context.get('combined_data', {})
            execution_summary = context.get('execution_summary', '')

            sub_intent = state.get('business_sub_intent', '')
            user_message = state.get('user_message', '')

            template_match_service = get_template_match_service()
            matched_template = await template_match_service.match_template(
                user_message=user_message,
                sub_intent=sub_intent,
                execution_results=results,
                execution_summary=execution_summary
            )

            # 如果匹配到模板且置信度足够高，使用模板生成页面
            if matched_template and matched_template.get('confidence', 0) >= 0.7:
                logger.info(f"匹配到模板: {matched_template.get('display_name')}, 置信度: {matched_template.get('confidence')}")

                # 检查是否为动态模板且有HTML内容（直接复用）
                if matched_template.get('is_dynamic') and matched_template.get('html_content'):
                    logger.info(f"复用动态模板HTML内容: {matched_template.get('display_name')}")

                    page_generator = get_page_generator()
                    page_url = await page_generator.save_html_content(
                        html_content=matched_template['html_content'],
                        title=matched_template.get('page_title') or self._generate_page_title(state)
                    )

                    template_match_service.increment_use_count(matched_template.get('id'), success=True)
                    logger.info(f"动态模板复用成功: {page_url}")

                    return {
                        "page_url": page_url,
                        "template_used": matched_template.get('display_name'),
                        "template_reused": True,
                        "success": True
                    }

                # 预定义模板：使用模板生成页面
                template_data = self._prepare_template_data(state, combined_data, matched_template)

                page_generator = get_page_generator()
                page_url = await page_generator.generate_page_with_template(
                    template_info=matched_template,
                    data=template_data,
                    title=self._generate_page_title(state)
                )

                template_match_service.increment_use_count(matched_template.get('id'), success=True)
                logger.info(f"使用模板生成页面成功: {page_url}")

                return {
                    "page_url": page_url,
                    "template_used": matched_template.get('display_name'),
                    "success": True
                }

            # 未匹配到模板，使用动态生成
            logger.info("未匹配到预定义模板，使用 DynamicPageGenerator 动态生成页面")

            # 创建上下文收集器
            collector = create_collector_from_state(state)

            # 获取生成器实例
            generator = get_dynamic_page_generator()

            # 生成页面
            page_url = await generator.generate(
                conversation_context=collector.to_frontend_format()
            )

            return {
                "page_url": page_url,
                "template_used": "dynamic_generated",
                "success": True
            }

        except Exception as e:
            logger.error(f"页面生成失败: {e}")
            return {
                "page_url": None,
                "success": False,
                "error": str(e)
            }

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
            # 准备上下文数据
            context = self.prepare_response_context(state)
            execution_summary = context['execution_summary']

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

            # 使用短路求值：如果 output_type 已经是 web_page，就不需要调用 _should_generate_web_page
            if output_type == OutputType.WEB_PAGE.value:
                need_web_page = True
            else:
                need_web_page = await self._should_generate_web_page(state)

            if need_web_page:
                # 需要生成Web页面 - 返回标记，让 graph 并行处理
                # 将需要的状态字段添加到返回值中，供 generate_page_only 使用
                return {
                    "output_type": OutputType.WEB_PAGE.value,
                    "need_parallel_generation": True,
                    "response_context": context,
                    "next_action": "parallel_generate",
                    # 传递 generate_page_only 需要的状态字段
                    "business_sub_intent": state.get('business_sub_intent', ''),
                    "user_message": state.get('user_message', ''),
                    "forecast_target": state.get('forecast_target', {}),
                    "extracted_result": state.get('extracted_result', {}),
                    "workflow_context": state.get('workflow_context', {}),
                    "intent": state.get('intent', ''),
                    # 传递方案ID（所有工作流统一输出为 plan_id）
                    "plan_id": state.get('plan_id'),
                }

            # 不需要页面，只生成文字回复
            text_response = await self.generate_text_only(state, context)

            logger.info("响应合成完成（纯文字）")

            return {
                "output_type": OutputType.TEXT.value,
                "final_response": text_response,
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

        基于内容语义判断，而非简单的数据结构判断。

        生成页面的条件（满足任一）：
        1. 包含时序数据（过程曲线）
        2. 包含需要图表展示的多维数据
        3. 包含地理坐标/地图数据
        4. 包含图片/文件路径
        5. 数据量大（列表>5条表格数据）
        6. 包含预报/预测结果

        不生成页面的条件：
        1. 单个数值结果（水位、流量等）
        2. 简单的是/否判断
        3. 短文本描述
        4. 纯文本知识库检索结果

        Args:
            state: 当前状态

        Returns:
            是否需要生成Web页面
        """
        # 1. 检查执行结果（意图3：BUSINESS）
        execution_results = state.get('execution_results', [])
        for result in execution_results:
            output = result.get('output') or result.get('result')
            if self._check_need_web_page(output):
                logger.debug(f"检测到需要Web页面展示的数据（来自执行结果）")
                return True

        # 2. 检查知识库检索结果（意图2：KNOWLEDGE）
        # 知识库检索结果通常是纯文本，不需要页面展示
        # 但如果检索到的内容包含结构化数据（如表格、图片路径等），则需要页面
        retrieved_documents = state.get('retrieved_documents', [])
        if retrieved_documents:
            # 检查检索结果数量：如果检索到大量文档（>5条），可能需要页面展示
            if len(retrieved_documents) > 5:
                logger.debug(f"检索到大量文档（{len(retrieved_documents)}条），建议页面展示")
                return True

            # 检查文档内容是否包含需要页面展示的数据
            for doc in retrieved_documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})

                # 检查是否包含图片
                if metadata.get('has_images') or self._content_has_images(content):
                    logger.debug("检索文档包含图片，需要页面展示")
                    return True

                # 检查是否包含表格数据（Markdown表格格式）
                if self._content_has_table(content):
                    logger.debug("检索文档包含表格，需要页面展示")
                    return True

        return False

    def _content_has_images(self, content: str) -> bool:
        """检查文本内容是否包含图片引用"""
        if not content:
            return False
        # 检查Markdown图片语法或图片路径
        image_patterns = ['![', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp']
        content_lower = content.lower()
        return any(pattern in content_lower for pattern in image_patterns)

    def _content_has_table(self, content: str) -> bool:
        """检查文本内容是否包含表格"""
        if not content:
            return False
        # 检查Markdown表格语法（至少3行包含|分隔符）
        lines = content.split('\n')
        table_lines = [line for line in lines if '|' in line and line.strip().startswith('|')]
        return len(table_lines) >= 3

    def _check_need_web_page(self, data: Any, depth: int = 0) -> bool:
        """
        递归检查数据是否需要Web页面展示

        Args:
            data: 要检查的数据
            depth: 递归深度，防止无限递归

        Returns:
            是否需要Web页面
        """
        if depth > 5:  # 防止过深递归
            return False

        # 1. 空值或简单类型 - 不需要页面
        if data is None:
            return False
        if isinstance(data, bool):
            return False
        if isinstance(data, (int, float)):
            return False
        if isinstance(data, str):
            # 检查是否包含图片路径
            if self._is_image_path(data):
                return True
            # 短文本不需要页面
            return False

        # 2. 列表类型
        if isinstance(data, list):
            if len(data) == 0:
                return False
            # 表格数据：列表中的元素是字典，且长度>5
            if len(data) > 5 and isinstance(data[0], dict):
                return True
            # 时序数据：检查是否包含时间字段
            if len(data) > 3 and isinstance(data[0], dict):
                if self._has_time_series_fields(data[0]):
                    return True
            # 递归检查列表元素
            for item in data[:10]:  # 只检查前10个元素
                if self._check_need_web_page(item, depth + 1):
                    return True
            return False

        # 3. 字典类型
        if isinstance(data, dict):
            # 检查是否包含需要图表展示的关键字段
            if self._has_chart_data_fields(data):
                return True
            # 检查是否包含地图数据
            if self._has_map_data_fields(data):
                return True
            # 检查是否包含预报/预测数据
            if self._has_forecast_fields(data):
                return True
            # 检查是否包含图片
            if self._has_image_fields(data):
                return True
            # 检查是否包含时序数据字典
            if self._has_timeseries_dict_values(data):
                return True
            # 递归检查字典值
            for key, value in data.items():
                if self._check_need_web_page(value, depth + 1):
                    return True
            return False

        return False

    def _has_time_series_fields(self, data: dict) -> bool:
        """检查是否包含时序数据字段"""
        time_fields = {'time', 'datetime', 'date', 'timestamp', 'tm', 'dt',
                       '时间', '日期', 'TM', 'DATETIME'}
        value_fields = {'value', 'values', 'z', 'q', 'p', 'water_level', 'flow',
                        'rainfall', '水位', '流量', '雨量', 'Z', 'Q', 'P'}

        keys_lower = {str(k).lower() for k in data.keys()}
        keys_original = set(str(k) for k in data.keys())
        all_keys = keys_lower | keys_original

        has_time = bool(time_fields & all_keys)
        has_value = bool(value_fields & all_keys)

        return has_time and has_value

    def _has_chart_data_fields(self, data: dict) -> bool:
        """检查是否包含图表数据字段"""
        chart_fields = {'series', 'datasets', 'chart_data', 'xaxis', 'yaxis',
                        'categories', 'legend', 'echarts', 'chart'}
        keys_lower = {str(k).lower() for k in data.keys()}
        return bool(chart_fields & keys_lower)

    def _has_map_data_fields(self, data: dict) -> bool:
        """检查是否包含地图数据字段"""
        map_fields = {'lat', 'lng', 'latitude', 'longitude', 'coordinates',
                      'coord', 'latlng', 'geo', 'geometry',
                      '经度', '纬度', 'lgtd', 'lttd'}
        keys_lower = {str(k).lower() for k in data.keys()}
        return bool(map_fields & keys_lower)

    def _has_forecast_fields(self, data: dict) -> bool:
        """检查是否包含预报/预测数据字段"""
        forecast_fields = {'forecast', 'prediction', 'predicted', 'forecast_data',
                          'forecast_result', 'predict_result', '预报', '预测',
                          'future', 'expected', 'projected',
                          # 水文预报特有字段
                          'max_inq', 'max_outq', 'max_level', 'max_qischarge',
                          'inq_dic', 'outq_dic', 'level_dic', 'q_dic', 'z_dic'}
        keys_lower = {str(k).lower() for k in data.keys()}
        return bool(forecast_fields & keys_lower)

    def _has_image_fields(self, data: dict) -> bool:
        """检查是否包含图片字段"""
        image_fields = {'image', 'img', 'picture', 'photo', 'image_url',
                        'img_url', 'thumbnail', '图片', '图像'}
        keys_lower = {str(k).lower() for k in data.keys()}
        if image_fields & keys_lower:
            return True

        # 检查值是否为图片路径
        for value in data.values():
            if isinstance(value, str) and self._is_image_path(value):
                return True
        return False

    def _has_timeseries_dict_values(self, data: dict) -> bool:
        """检查字典值中是否包含时序数据字典（如 InQ_Dic, Level_Dic 等）"""
        timeseries_key_patterns = {'_dic', 'dic_', 'series', 'history', 'process'}
        for key, value in data.items():
            key_lower = str(key).lower()
            # 检查键名是否符合时序数据模式
            if any(pattern in key_lower for pattern in timeseries_key_patterns):
                if isinstance(value, dict) and len(value) > 3:
                    return True
        return False

    def _is_image_path(self, path: str) -> bool:
        """检查是否为图片路径"""
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp'}
        path_lower = path.lower()
        return any(path_lower.endswith(ext) for ext in image_extensions)

    def _prepare_template_data(
        self,
        state: AgentState,
        combined_data: Dict[str, Any],
        template_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        准备模板所需的数据

        根据模板类型和执行结果，构建符合模板要求的数据结构。
        包含预定义模板所需的关键参数（planCode, token, stcd 等）。

        Args:
            state: 当前状态
            combined_data: 合并后的执行结果数据
            template_info: 模板信息

        Returns:
            模板数据字典
        """
        template_name = template_info.get('name', '')
        forecast_target = state.get('forecast_target', {})
        extracted_result = state.get('extracted_result', {})
        workflow_context = state.get('workflow_context', {})

        # 基础数据
        data = {
            "user_message": state.get('user_message', ''),
            "intent": state.get('intent', ''),
            "sub_intent": state.get('business_sub_intent', ''),
        }

        # 从 workflow_context 中提取关键参数（用于预定义模板）
        # workflow_context 可能有多种结构：
        # 1. ctx 结构: {'auth_token': ..., 'results': {...}, 'context_data': {'steps': {...}}}
        # 2. context_data 结构: {'inputs': {}, 'steps': {...}, 'state': {}}
        steps_data = {}
        if isinstance(workflow_context, dict):
            # 尝试从 context_data.steps 获取（ctx 结构）
            if 'context_data' in workflow_context:
                steps_data = workflow_context.get('context_data', {}).get('steps', {})
            # 尝试直接从 steps 获取（context_data 结构）
            elif 'steps' in workflow_context:
                steps_data = workflow_context.get('steps', {})

            # 如果 steps_data 为空，尝试从 results 中提取 token
            if not steps_data.get('login') and 'results' in workflow_context:
                results = workflow_context.get('results', {})
                if results.get('auth_token'):
                    data['token'] = results['auth_token']

        # 提取 token
        login_data = steps_data.get('login', {})
        if login_data.get('token'):
            data['token'] = login_data['token']

        # 提取 planCode（所有工作流统一输出为 plan_id）
        plan_id = state.get('plan_id')
        logger.info(f"提取 planCode: plan_id={plan_id}")
        if plan_id:
            data['planCode'] = plan_id
        else:
            # 回退：尝试从 steps_data 中获取
            forecast_step = steps_data.get('forecast', {})
            if forecast_step.get('planCode'):
                data['planCode'] = forecast_step['planCode']

        # 根据模板类型准备数据
        if template_name in ['res_flood_forecast', 'res_flood_resultshow']:
            # 水库洪水预报模板
            target_name = forecast_target.get('name', '盘石头水库')
            data["reservoirName"] = target_name
            data["reservoir_name"] = target_name

            # 从 extracted_result 或 combined_data 获取水库预报数据
            if extracted_result and extracted_result.get('data'):
                reservoir_data = extracted_result.get('data', {})
            else:
                # 尝试从 combined_data 中提取
                reservoir_result = combined_data.get('reservoir_result', {})
                reservoir_data = reservoir_result.get(target_name, {})

            data["data"] = reservoir_data
            data["reservoir_result"] = reservoir_data
            data["result_desc"] = extracted_result.get('summary', '') or combined_data.get('result_desc', '')

            # 提取 stcd
            if reservoir_data.get('Stcd'):
                data['stcd'] = reservoir_data['Stcd']

            # 降雨数据
            data["rain_data"] = combined_data.get('rain_data', [])

        elif template_name == 'station_flood_forecast':
            # 站点洪水预报模板
            target_name = forecast_target.get('name', '')
            data["station_name"] = target_name

            if extracted_result and extracted_result.get('data'):
                data["station_result"] = extracted_result.get('data', {})
            else:
                data["station_result"] = combined_data.get('station_result', {})

            data["result_desc"] = extracted_result.get('summary', '')

        elif template_name == 'detention_basin_forecast':
            # 蓄滞洪区预报模板
            target_name = forecast_target.get('name', '')
            data["detention_name"] = target_name

            if extracted_result and extracted_result.get('data'):
                data["detention_result"] = extracted_result.get('data', {})
            else:
                data["detention_result"] = combined_data.get('detention_result', {})

            data["result_desc"] = extracted_result.get('summary', '')

        else:
            # 通用模板：直接传递合并数据
            data.update(combined_data)
            if extracted_result:
                data["extracted_result"] = extracted_result

        return data

    def _generate_page_title(self, state: AgentState) -> str:
        """
        生成页面标题

        Args:
            state: 当前状态

        Returns:
            页面标题
        """
        forecast_target = state.get('forecast_target', {})
        target_name = forecast_target.get('name', '')
        intent = state.get('intent', '')
        sub_intent = state.get('business_sub_intent', '')

        if target_name:
            if 'forecast' in sub_intent or '预报' in intent:
                return f"{target_name}洪水预报结果"
            else:
                return f"{target_name}查询结果"

        if intent:
            return f"{intent}报告"

        return "查询结果报告"

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
        """
        格式化执行结果，过滤内部工具和敏感信息

        兼容两种执行模式：
        - 批量执行模式：结果字段为 'output'
        - 单步执行模式：结果字段为 'result'
        """
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
            tool_name = tool_map.get(step_id, '') or r.get('tool_name', '')

            # 过滤：跳过内部工具的结果
            if tool_name in EXCLUDE_TOOLS_FROM_RESPONSE:
                logger.debug(f"过滤步骤{step_id}的结果（工具: {tool_name}）")
                continue

            success = r.get('success', False)
            # 兼容两种字段名：'output'（批量模式）和 'result'（单步模式）
            output = r.get('output') or r.get('result') or r.get('data', '')
            error = r.get('error')

            if success:
                # 检查是否需要轻量化处理
                # 对于所有包含大量时序数据的结果都进行轻量化处理
                need_lightweight = tool_name in LIGHTWEIGHT_TOOLS

                # 格式化输出
                if isinstance(output, dict):
                    # 过滤敏感字段
                    filtered_output = self._filter_sensitive_fields(output)
                    # 对所有字典类型的输出进行轻量化处理（不仅仅是特定工具）
                    # 这样可以避免大量时序数据导致的性能问题
                    filtered_output = self._lightweight_timeseries_data(filtered_output)
                    output_str = self._format_dict_output(filtered_output)
                elif isinstance(output, list):
                    output_str = self._format_list_output(output)
                elif output:
                    output_str = str(output)
                else:
                    # 如果没有输出内容，显示步骤名称
                    step_name = r.get('step_name', '')
                    output_str = f"完成 - {step_name}" if step_name else "完成"
                formatted.append(f"步骤{step_id}: {output_str}")
            else:
                formatted.append(f"步骤{step_id}: 执行失败 - {error}")

        return "\n\n".join(formatted)

    def _lightweight_timeseries_data(self, data: Dict[str, Any], max_timeseries_items: int = 3) -> Dict[str, Any]:
        """
        轻量化处理时序数据字典

        对于包含大量时序数据的字典（如 {'2026-01-21 08:00': 100, '2026-01-21 09:00': 150, ...}），
        只保留前几个值作为示例，避免传递给LLM的数据过大。

        Args:
            data: 原始数据字典
            max_timeseries_items: 时序数据最多保留的项数

        Returns:
            轻量化处理后的字典
        """
        if not isinstance(data, dict):
            return data

        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                # 检查是否为时序数据字典（键看起来像时间戳或日期）
                if self._is_timeseries_dict(value):
                    # 截取前几个值
                    items = list(value.items())
                    if len(items) > max_timeseries_items:
                        truncated = dict(items[:max_timeseries_items])
                        truncated['...'] = f"(共{len(items)}条时序数据，已截取前{max_timeseries_items}条)"
                        result[key] = truncated
                    else:
                        result[key] = value
                else:
                    # 递归处理嵌套字典
                    result[key] = self._lightweight_timeseries_data(value, max_timeseries_items)
            elif isinstance(value, list) and len(value) > 20:
                # 对于过长的列表，也进行截取
                result[key] = value[:5] + [f"...(共{len(value)}项)"]
            else:
                result[key] = value

        return result

    def _is_timeseries_dict(self, data: Dict[str, Any]) -> bool:
        """
        判断字典是否为时序数据字典

        时序数据字典的特征：
        - 键是时间格式的字符串（如 '2026-01-21 08:00:00'）
        - 值是数值类型
        """
        if not data or len(data) < 5:
            return False

        # 检查前几个键是否符合时间格式
        sample_keys = list(data.keys())[:3]
        time_pattern_count = 0

        for key in sample_keys:
            if isinstance(key, str):
                # 检查是否包含日期时间特征
                if any(sep in key for sep in ['-', '/', ':']) and any(c.isdigit() for c in key):
                    time_pattern_count += 1

        # 如果大部分键符合时间格式，认为是时序数据
        return time_pattern_count >= 2

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
    
    def _format_plan_summary(self, plan: List[Dict[str, Any]], execution_results: List[Dict[str, Any]] = None) -> str:
        """
        格式化计划摘要

        Args:
            plan: 执行计划步骤列表
            execution_results: 执行结果列表（用于推断步骤状态）

        Returns:
            格式化的计划摘要字符串
        """
        if not plan:
            return ""

        # 构建 step_id -> 执行结果 的映射
        result_map = {}
        if execution_results:
            for r in execution_results:
                step_id = r.get('step_id')
                if step_id is not None:
                    result_map[step_id] = r

        steps = []
        for step in plan:
            step_id = step.get('step_id', '?')
            description = step.get('description', '') or step.get('name', '')

            # 优先使用步骤自带的状态，否则从执行结果推断
            status = step.get('status')
            if not status and step_id in result_map:
                result = result_map[step_id]
                if result.get('success'):
                    status = 'completed'
                else:
                    status = 'failed'
            elif not status:
                status = 'pending'

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
