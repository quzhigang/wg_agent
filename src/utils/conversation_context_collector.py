"""
对话上下文收集器

收集整个对话过程中的工具调用、参数、结果，用于动态页面生成。
与 WorkflowContext 的区别：
- WorkflowContext: 工作流执行期间的数据传递，用于步骤间参数引用
- ConversationContextCollector: 对话级别的完整记录，用于页面生成和调试
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from copy import deepcopy

from ..config.logging_config import get_logger

logger = get_logger(__name__)


# 敏感字段列表，导出时需要过滤
SENSITIVE_FIELDS = [
    "token", "password", "secret", "api_key", "authorization",
    "access_token", "refresh_token", "credential"
]


@dataclass
class ToolCallRecord:
    """工具调用记录"""
    tool_name: str
    step_id: int
    step_description: str
    input_params: Dict[str, Any]
    output_result: Any
    success: bool
    execution_time_ms: int
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    error_message: Optional[str] = None


@dataclass
class IntentResult:
    """意图识别结果"""
    intent_category: str  # chat/knowledge/business
    business_sub_intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    target_kbs: List[str] = field(default_factory=list)
    rewritten_query: Optional[str] = None
    confidence: float = 0.0


@dataclass
class PlanStepRecord:
    """执行计划步骤记录"""
    step_id: int
    description: str
    tool_name: Optional[str] = None
    tool_args: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[int] = field(default_factory=list)


@dataclass
class ConversationContext:
    """对话上下文数据结构"""
    conversation_id: str
    user_message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    # 意图识别结果
    intent: Optional[IntentResult] = None

    # 执行计划
    plan: List[PlanStepRecord] = field(default_factory=list)

    # 工具调用记录
    tool_calls: List[ToolCallRecord] = field(default_factory=list)

    # 检索到的文档
    retrieved_documents: List[Dict[str, Any]] = field(default_factory=list)

    # 工作流信息
    matched_workflow: Optional[str] = None
    workflow_params: Dict[str, Any] = field(default_factory=dict)

    # 工作流提取的业务数据（如洪水预报结果）
    extracted_result: Optional[Dict[str, Any]] = None
    forecast_target: Optional[Dict[str, Any]] = None

    # 最终结果
    final_response: Optional[str] = None
    output_type: str = "text"  # text/web_page


class ConversationContextCollector:
    """
    对话上下文收集器

    负责收集整个对话过程中的所有信息，包括：
    1. 用户输入和意图识别结果
    2. 执行计划
    3. 工具调用记录（参数、结果、耗时）
    4. 检索到的文档
    5. 最终响应

    使用示例：
    ```python
    collector = ConversationContextCollector(
        conversation_id="conv_123",
        user_message="盘石头水库洪水预报"
    )

    # 记录意图识别结果
    collector.set_intent_result(
        intent_category="business",
        business_sub_intent="flood_forecast",
        entities={"object": "盘石头水库", "object_type": "reservoir"}
    )

    # 记录执行计划
    collector.set_plan(plan_steps)

    # 记录工具调用
    collector.record_tool_call(
        tool_name="login",
        step_id=1,
        step_description="登录认证",
        input_params={"account": "admin"},
        output_result={"token": "xxx"},
        success=True,
        execution_time_ms=150
    )

    # 导出为前端格式
    frontend_data = collector.to_frontend_format()
    ```
    """

    def __init__(self, conversation_id: str, user_message: str):
        """
        初始化收集器

        Args:
            conversation_id: 会话ID
            user_message: 用户原始消息
        """
        self._context = ConversationContext(
            conversation_id=conversation_id,
            user_message=user_message
        )
        logger.debug(f"创建对话上下文收集器: {conversation_id}")

    def set_intent_result(
        self,
        intent_category: str,
        business_sub_intent: Optional[str] = None,
        entities: Optional[Dict[str, Any]] = None,
        target_kbs: Optional[List[str]] = None,
        rewritten_query: Optional[str] = None,
        confidence: float = 0.0
    ):
        """
        记录意图识别结果

        Args:
            intent_category: 意图大类 (chat/knowledge/business)
            business_sub_intent: 业务子意图
            entities: 提取的实体
            target_kbs: 目标知识库列表
            rewritten_query: 重写后的查询
            confidence: 置信度
        """
        self._context.intent = IntentResult(
            intent_category=intent_category,
            business_sub_intent=business_sub_intent,
            entities=entities or {},
            target_kbs=target_kbs or [],
            rewritten_query=rewritten_query,
            confidence=confidence
        )
        logger.debug(f"记录意图识别结果: {intent_category}/{business_sub_intent}")

    def set_plan(self, plan_steps: List[Dict[str, Any]]):
        """
        记录执行计划

        Args:
            plan_steps: 执行计划步骤列表（序列化的PlanStep）
        """
        self._context.plan = [
            PlanStepRecord(
                step_id=step.get("step_id", 0),
                description=step.get("description", ""),
                tool_name=step.get("tool_name"),
                tool_args=step.get("tool_args", {}),
                dependencies=step.get("dependencies", [])
            )
            for step in plan_steps
        ]
        logger.debug(f"记录执行计划: {len(plan_steps)} 个步骤")

    def record_tool_call(
        self,
        tool_name: str,
        step_id: int,
        step_description: str,
        input_params: Dict[str, Any],
        output_result: Any,
        success: bool,
        execution_time_ms: int,
        error_message: Optional[str] = None
    ):
        """
        记录工具调用

        Args:
            tool_name: 工具名称
            step_id: 步骤ID
            step_description: 步骤描述
            input_params: 输入参数
            output_result: 输出结果
            success: 是否成功
            execution_time_ms: 执行耗时（毫秒）
            error_message: 错误信息（如果失败）
        """
        record = ToolCallRecord(
            tool_name=tool_name,
            step_id=step_id,
            step_description=step_description,
            input_params=deepcopy(input_params),
            output_result=deepcopy(output_result),
            success=success,
            execution_time_ms=execution_time_ms,
            error_message=error_message
        )
        self._context.tool_calls.append(record)
        logger.debug(f"记录工具调用: {tool_name} (step {step_id}), 成功={success}, 耗时={execution_time_ms}ms")

    def set_retrieved_documents(self, documents: List[Dict[str, Any]]):
        """
        记录检索到的文档

        Args:
            documents: 检索到的文档列表
        """
        self._context.retrieved_documents = deepcopy(documents)
        logger.debug(f"记录检索文档: {len(documents)} 个")

    def set_workflow_info(
        self,
        matched_workflow: Optional[str] = None,
        workflow_params: Optional[Dict[str, Any]] = None
    ):
        """
        记录工作流信息

        Args:
            matched_workflow: 匹配的工作流名称
            workflow_params: 工作流参数
        """
        self._context.matched_workflow = matched_workflow
        self._context.workflow_params = workflow_params or {}
        logger.debug(f"记录工作流信息: {matched_workflow}")

    def set_extracted_result(self, extracted_result: Dict[str, Any]):
        """
        记录工作流提取的业务数据

        Args:
            extracted_result: 工作流提取的结果数据（如洪水预报结果）
        """
        self._context.extracted_result = deepcopy(extracted_result)
        logger.debug(f"记录工作流提取结果: {list(extracted_result.keys()) if extracted_result else None}")

    def set_forecast_target(self, forecast_target: Dict[str, Any]):
        """
        记录预报目标信息

        Args:
            forecast_target: 预报目标信息（水库/流域/站点等）
        """
        self._context.forecast_target = deepcopy(forecast_target)
        logger.debug(f"记录预报目标: {forecast_target.get('name') if forecast_target else None}")

    def set_final_response(self, response: str, output_type: str = "text"):
        """
        记录最终响应

        Args:
            response: 最终响应内容
            output_type: 输出类型 (text/web_page)
        """
        self._context.final_response = response
        self._context.output_type = output_type

    def get_tool_call_by_name(self, tool_name: str) -> Optional[ToolCallRecord]:
        """
        根据工具名称获取工具调用记录

        Args:
            tool_name: 工具名称

        Returns:
            工具调用记录，不存在则返回 None
        """
        for record in self._context.tool_calls:
            if record.tool_name == tool_name:
                return record
        return None

    def get_tool_call_by_step(self, step_id: int) -> Optional[ToolCallRecord]:
        """
        根据步骤ID获取工具调用记录

        Args:
            step_id: 步骤ID

        Returns:
            工具调用记录，不存在则返回 None
        """
        for record in self._context.tool_calls:
            if record.step_id == step_id:
                return record
        return None

    def get_successful_tool_calls(self) -> List[ToolCallRecord]:
        """获取所有成功的工具调用"""
        return [r for r in self._context.tool_calls if r.success]

    def to_dict(self) -> Dict[str, Any]:
        """
        导出为字典（包含所有数据）

        Returns:
            完整的上下文数据字典
        """
        return asdict(self._context)

    def to_frontend_format(self, filter_sensitive: bool = True) -> Dict[str, Any]:
        """
        导出为前端可用格式

        过滤敏感信息，并将数据结构转换为前端友好的格式。

        Args:
            filter_sensitive: 是否过滤敏感信息

        Returns:
            前端可用的上下文数据
        """
        data = self.to_dict()

        if filter_sensitive:
            data = self._filter_sensitive_data(data)

        # 转换为前端友好的格式
        frontend_data = {
            "meta": {
                "conversation_id": data["conversation_id"],
                "user_message": data["user_message"],
                "timestamp": data["timestamp"],
                "output_type": data["output_type"]
            },
            "intent": data.get("intent"),
            "execution": {
                "plan": data.get("plan", []),
                "tool_calls": data.get("tool_calls", []),
                "workflow": {
                    "name": data.get("matched_workflow"),
                    "params": data.get("workflow_params", {})
                }
            },
            "retrieval": {
                "documents": data.get("retrieved_documents", [])
            },
            # 工作流提取的业务数据（核心数据，用于页面渲染）
            "workflow_result": {
                "extracted_result": data.get("extracted_result"),
                "forecast_target": data.get("forecast_target")
            },
            "response": data.get("final_response")
        }

        return frontend_data

    def _filter_sensitive_data(self, data: Any) -> Any:
        """
        递归过滤敏感数据

        Args:
            data: 要过滤的数据

        Returns:
            过滤后的数据
        """
        if isinstance(data, dict):
            filtered = {}
            for key, value in data.items():
                # 检查键名是否包含敏感字段
                key_lower = key.lower()
                is_sensitive = any(sf in key_lower for sf in SENSITIVE_FIELDS)

                if is_sensitive:
                    # 敏感字段用占位符替换
                    filtered[key] = "[FILTERED]"
                else:
                    filtered[key] = self._filter_sensitive_data(value)
            return filtered
        elif isinstance(data, list):
            return [self._filter_sensitive_data(item) for item in data]
        else:
            return data

    def merge_from_workflow_context(self, workflow_context: Dict[str, Any]):
        """
        从 WorkflowContext 合并数据

        将 WorkflowContext 中的步骤执行结果合并到工具调用记录中。
        支持两种格式：
        1. 旧格式: { "steps": { "step_name": result, ... } }
        2. 新格式: { "results": { "extracted_result": {...}, ... }, "context_data": { "steps": {...} } }

        Args:
            workflow_context: WorkflowContext.to_dict() 的结果
        """
        if not workflow_context:
            return

        # 尝试从 context_data.steps 获取步骤数据（新格式）
        context_data = workflow_context.get("context_data", {})
        if isinstance(context_data, dict):
            steps = context_data.get("steps", {})
        else:
            steps = {}

        # 如果没有 context_data.steps，尝试从顶层 steps 获取（旧格式）
        if not steps:
            steps = workflow_context.get("steps", {})

        for step_name, step_result in steps.items():
            # 检查是否已有该步骤的记录
            existing = None
            for record in self._context.tool_calls:
                if record.tool_name == step_name:
                    existing = record
                    break

            if not existing:
                # 创建新记录
                self.record_tool_call(
                    tool_name=step_name,
                    step_id=0,  # 从 workflow_context 合并的没有 step_id
                    step_description=f"工作流步骤: {step_name}",
                    input_params={},
                    output_result=step_result,
                    success=True,
                    execution_time_ms=0
                )

        # 如果 workflow_context 中有 results.extracted_result，也设置到 context 中
        results = workflow_context.get("results", {})
        if results and isinstance(results, dict):
            extracted_result = results.get("extracted_result")
            if extracted_result and not self._context.extracted_result:
                self._context.extracted_result = deepcopy(extracted_result)
                logger.debug(f"从 workflow_context.results 合并了 extracted_result")

        # 如果有 forecast_target，也设置
        forecast_target = workflow_context.get("forecast_target")
        if forecast_target and not self._context.forecast_target:
            self._context.forecast_target = deepcopy(forecast_target)
            logger.debug(f"从 workflow_context 合并了 forecast_target")

        logger.debug(f"从 WorkflowContext 合并了 {len(steps)} 个步骤")

    def merge_from_execution_results(self, execution_results: List[Dict[str, Any]], plan: List[Dict[str, Any]]):
        """
        从执行结果列表合并数据

        Args:
            execution_results: ExecutionResult 列表（序列化后）
            plan: 执行计划步骤列表
        """
        # 创建步骤ID到计划步骤的映射
        plan_map = {step.get("step_id"): step for step in plan}

        for result in execution_results:
            step_id = result.get("step_id", 0)
            plan_step = plan_map.get(step_id, {})

            # 兼容两种字段名：'output' (ExecutionResult格式) 和 'result' (工作流步骤格式)
            output_result = result.get("output") or result.get("result")

            # 优先使用执行结果中的 tool_name，其次使用计划中的
            tool_name = result.get("tool_name") or plan_step.get("tool_name", "unknown")
            # 优先使用执行结果中的 step_name，其次使用计划中的 description
            step_description = result.get("step_name") or plan_step.get("description", "")

            self.record_tool_call(
                tool_name=tool_name,
                step_id=step_id,
                step_description=step_description,
                input_params=plan_step.get("tool_args", {}),
                output_result=output_result,
                success=result.get("success", False),
                execution_time_ms=result.get("execution_time_ms", 0),
                error_message=result.get("error")
            )

        logger.debug(f"从执行结果合并了 {len(execution_results)} 个记录")

    def __repr__(self) -> str:
        return (
            f"ConversationContextCollector("
            f"conversation_id={self._context.conversation_id}, "
            f"tool_calls={len(self._context.tool_calls)}, "
            f"intent={self._context.intent.intent_category if self._context.intent else None})"
        )


def create_collector_from_state(state: Dict[str, Any]) -> ConversationContextCollector:
    """
    从智能体状态创建对话上下文收集器

    Args:
        state: 智能体状态字典

    Returns:
        初始化并填充数据的 ConversationContextCollector 实例
    """
    collector = ConversationContextCollector(
        conversation_id=state.get("conversation_id", ""),
        user_message=state.get("user_message", "")
    )

    # 设置意图识别结果
    if state.get("intent_category"):
        collector.set_intent_result(
            intent_category=state.get("intent_category", ""),
            business_sub_intent=state.get("business_sub_intent"),
            entities=state.get("entities", {}),
            target_kbs=state.get("target_kbs", []),
            rewritten_query=state.get("rewritten_query"),
            confidence=state.get("intent_confidence", 0.0)
        )

    # 设置执行计划
    if state.get("plan"):
        collector.set_plan(state.get("plan", []))

    # 设置工作流信息
    if state.get("matched_workflow"):
        collector.set_workflow_info(
            matched_workflow=state.get("matched_workflow"),
            workflow_params=state.get("workflow_params", {})
        )

    # 从执行结果合并工具调用记录
    if state.get("execution_results"):
        collector.merge_from_execution_results(
            execution_results=state.get("execution_results", []),
            plan=state.get("plan", [])
        )

    # 设置检索文档
    if state.get("retrieved_documents"):
        collector.set_retrieved_documents(state.get("retrieved_documents", []))

    # 从 workflow_context 合并（如果有）
    if state.get("workflow_context"):
        collector.merge_from_workflow_context(state.get("workflow_context"))

    # 合并工作流提取的结果数据（extracted_result）
    # 这是工作流最终提取的业务数据，如洪水预报结果
    if state.get("extracted_result"):
        collector.set_extracted_result(state.get("extracted_result"))

    # 合并预报目标信息
    if state.get("forecast_target"):
        collector.set_forecast_target(state.get("forecast_target"))

    return collector
