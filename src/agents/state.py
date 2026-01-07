"""
智能体状态定义
定义LangGraph状态图的状态结构
"""

from typing import List, Dict, Any, Optional, Annotated
from typing_extensions import TypedDict
from enum import Enum
from pydantic import BaseModel, Field
from operator import add


class StepStatus(str, Enum):
    """步骤执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class OutputType(str, Enum):
    """输出类型"""
    TEXT = "text"
    WEB_PAGE = "web_page"


class IntentCategory(str, Enum):
    """意图大类"""
    CHAT = "chat"                    # 第1类：一般对话、闲聊
    KNOWLEDGE = "knowledge"          # 第2类：固有知识查询
    BUSINESS = "business"            # 第3类：业务相关


class BusinessSubIntent(str, Enum):
    """业务子意图（第3类细分）"""
    DATA_QUERY = "data_query"              # 监测数据查询
    FLOOD_FORECAST = "flood_forecast"      # 洪水预报
    FLOOD_SIMULATION = "flood_simulation"  # 洪水预演
    EMERGENCY_PLAN = "emergency_plan"      # 预案生成
    DAMAGE_ASSESSMENT = "damage_assessment"  # 灾损评估
    OTHER = "other"                        # 其他业务


class PlanStep(BaseModel):
    """执行计划步骤"""
    step_id: int = Field(..., description="步骤ID")
    description: str = Field(..., description="步骤描述")
    tool_name: Optional[str] = Field(None, description="需要调用的工具名称")
    tool_args: Optional[Dict[str, Any]] = Field(None, description="工具参数")
    dependencies: List[int] = Field(default_factory=list, description="依赖的步骤ID列表")
    status: StepStatus = Field(default=StepStatus.PENDING, description="执行状态")
    is_async: bool = Field(default=False, description="是否为异步任务")
    retry_count: int = Field(default=0, description="重试次数")


class ExecutionResult(BaseModel):
    """步骤执行结果"""
    step_id: int = Field(..., description="步骤ID")
    success: bool = Field(..., description="是否成功")
    output: Any = Field(None, description="输出结果")
    error: Optional[str] = Field(None, description="错误信息")
    execution_time_ms: Optional[int] = Field(None, description="执行耗时(毫秒)")


class AgentState(TypedDict):
    """
    LangGraph智能体状态

    使用TypedDict定义状态结构，支持状态更新和持久化
    """
    # 会话信息
    conversation_id: str
    user_id: Optional[str]

    # 用户输入
    user_message: str

    # 上下文信息
    chat_history: List[Dict[str, str]]
    context_summary: Optional[str]

    # 意图识别结果 - 新增三大类分类
    intent_category: Optional[str]  # IntentCategory: chat/knowledge/business
    business_sub_intent: Optional[str]  # BusinessSubIntent: 业务子意图
    intent: Optional[str]  # 保留原字段兼容
    intent_confidence: Optional[float]
    target_kbs: Optional[List[str]]  # 目标知识库列表（用于knowledge场景）

    # 快速对话相关
    is_quick_chat: Optional[bool]
    direct_response: Optional[str]

    # 工作流匹配
    matched_workflow: Optional[str]
    workflow_params: Optional[Dict[str, Any]]
    workflow_from_template: Optional[bool]  # 是否来自模板匹配

    # 执行计划
    plan: List[Dict[str, Any]]  # List[PlanStep] 序列化后的形式
    current_step_index: int

    # 执行结果 - 使用Annotated支持结果累积
    execution_results: Annotated[List[Dict[str, Any]], add]  # List[ExecutionResult]

    # RAG相关
    retrieved_documents: List[Dict[str, Any]]
    retrieval_source: Optional[str]  # 检索来源: "rag" 或 "mcp_websearch"

    # 最终输出
    output_type: str  # OutputType
    final_response: Optional[str]
    generated_page_url: Optional[str]

    # 异步任务
    async_task_ids: List[str]
    pending_async_results: Dict[str, Any]

    # 错误处理
    error: Optional[str]
    should_retry: bool

    # 流程控制
    next_action: Optional[str]  # 下一步动作: "plan", "execute", "respond", "wait_async", "end"


def create_initial_state(
    conversation_id: str,
    user_message: str,
    user_id: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    context_summary: Optional[str] = None
) -> AgentState:
    """
    创建初始智能体状态
    
    Args:
        conversation_id: 会话ID
        user_message: 用户消息
        user_id: 用户ID
        chat_history: 聊天历史
        context_summary: 上下文摘要
        
    Returns:
        初始化的AgentState
    """
    return AgentState(
        # 会话信息
        conversation_id=conversation_id,
        user_id=user_id,

        # 用户输入
        user_message=user_message,

        # 上下文信息
        chat_history=chat_history or [],
        context_summary=context_summary,

        # 意图识别结果
        intent_category=None,
        business_sub_intent=None,
        intent=None,
        intent_confidence=None,
        target_kbs=None,

        # 快速对话相关
        is_quick_chat=None,
        direct_response=None,

        # 工作流匹配
        matched_workflow=None,
        workflow_params=None,
        workflow_from_template=None,

        # 执行计划
        plan=[],
        current_step_index=0,

        # 执行结果
        execution_results=[],

        # RAG相关
        retrieved_documents=[],
        retrieval_source=None,

        # 最终输出
        output_type=OutputType.TEXT.value,
        final_response=None,
        generated_page_url=None,

        # 异步任务
        async_task_ids=[],
        pending_async_results={},

        # 错误处理
        error=None,
        should_retry=False,

        # 流程控制
        next_action="plan"
    )


def serialize_plan_step(step: PlanStep) -> Dict[str, Any]:
    """序列化PlanStep为字典"""
    return step.model_dump()


def deserialize_plan_step(data: Dict[str, Any]) -> PlanStep:
    """从字典反序列化PlanStep"""
    return PlanStep(**data)


def serialize_execution_result(result: ExecutionResult) -> Dict[str, Any]:
    """序列化ExecutionResult为字典"""
    return result.model_dump()


def deserialize_execution_result(data: Dict[str, Any]) -> ExecutionResult:
    """从字典反序列化ExecutionResult"""
    return ExecutionResult(**data)
