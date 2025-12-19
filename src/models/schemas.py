"""
Pydantic数据模型定义
用于API请求/响应和内部数据传输
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
from pydantic import BaseModel, Field
from uuid import uuid4


# ===========================================
# 枚举类型
# ===========================================

class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OutputType(str, Enum):
    """输出类型"""
    TEXT = "text"  # 简单文本
    WEB_PAGE = "web_page"  # Web页面（包含图表）


class PageType(str, Enum):
    """页面类型"""
    CHART = "chart"  # 图表数据页面
    FORECAST = "forecast"  # 预报结果页面
    PRINCIPLE = "principle"  # 原理说明页面
    CUSTOM = "custom"  # 自定义页面


# ===========================================
# 基础模型
# ===========================================

class BaseSchema(BaseModel):
    """基础模型"""
    class Config:
        from_attributes = True
        populate_by_name = True


# ===========================================
# 会话相关模型
# ===========================================

class ConversationCreate(BaseSchema):
    """创建会话请求"""
    user_id: Optional[str] = None
    title: Optional[str] = None


class ConversationResponse(BaseSchema):
    """会话响应"""
    id: str
    user_id: Optional[str] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    summary: Optional[str] = None


class MessageCreate(BaseSchema):
    """创建消息请求"""
    content: str
    role: MessageRole = MessageRole.USER


class MessageResponse(BaseSchema):
    """消息响应"""
    id: int
    conversation_id: str
    role: MessageRole
    content: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


# ===========================================
# 聊天相关模型
# ===========================================

class ChatRequest(BaseSchema):
    """聊天请求"""
    message: str
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    stream: bool = False  # 是否流式输出


class ChatResponse(BaseSchema):
    """聊天响应"""
    conversation_id: str
    message_id: int
    content: str
    output_type: OutputType
    page_url: Optional[str] = None  # Web页面URL（如果输出类型是web_page）
    execution_steps: List[Dict[str, Any]] = []  # 执行步骤记录


class StreamChunk(BaseSchema):
    """流式响应块"""
    type: Literal["step", "content", "page", "done", "error"]
    data: Any


# ===========================================
# 任务规划相关模型
# ===========================================

class TaskStep(BaseSchema):
    """任务步骤"""
    step_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    step_number: int
    description: str
    tool_name: Optional[str] = None
    tool_params: Optional[Dict[str, Any]] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskPlan(BaseSchema):
    """任务计划"""
    plan_id: str = Field(default_factory=lambda: str(uuid4()))
    user_intent: str
    is_workflow_match: bool = False
    workflow_name: Optional[str] = None
    steps: List[TaskStep] = []
    current_step: int = 0
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ===========================================
# 工具相关模型
# ===========================================

class ToolParameter(BaseSchema):
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[Any]] = None


class ToolDefinition(BaseSchema):
    """工具定义"""
    name: str
    description: str
    category: str  # 工具分类：basin_info, monitoring_data, flood_control, hydro_model, disaster_assess
    parameters: List[ToolParameter] = []
    returns: str = "Any"
    is_async: bool = False  # 是否为异步工具


class ToolCallRequest(BaseSchema):
    """工具调用请求"""
    tool_name: str
    parameters: Dict[str, Any] = {}


class ToolCallResult(BaseSchema):
    """工具调用结果"""
    tool_name: str
    status: Literal["success", "failed"]
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: int = 0


# ===========================================
# 异步任务相关模型
# ===========================================

class AsyncTaskCreate(BaseSchema):
    """创建异步任务"""
    task_type: str
    input_params: Dict[str, Any] = {}
    conversation_id: Optional[str] = None


class AsyncTaskResponse(BaseSchema):
    """异步任务响应"""
    id: str
    task_type: str
    status: TaskStatus
    input_params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ===========================================
# Web页面生成相关模型
# ===========================================

class PageGenerationRequest(BaseSchema):
    """页面生成请求"""
    page_type: PageType
    data: Dict[str, Any]
    template_name: Optional[str] = None


class PageGenerationResponse(BaseSchema):
    """页面生成响应"""
    page_id: str
    page_type: PageType
    file_path: str
    url: str
    is_cached: bool = False


# ===========================================
# RAG相关模型
# ===========================================

class KnowledgeQuery(BaseSchema):
    """知识查询请求"""
    query: str
    top_k: int = 5
    threshold: float = 0.7


class KnowledgeResult(BaseSchema):
    """知识查询结果"""
    content: str
    source: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


# ===========================================
# 工作流相关模型
# ===========================================

class WorkflowDefinition(BaseSchema):
    """工作流定义"""
    name: str
    description: str
    trigger_patterns: List[str]  # 触发模式（用于匹配用户意图）
    steps: List[Dict[str, Any]]


class WorkflowMatch(BaseSchema):
    """工作流匹配结果"""
    matched: bool
    workflow_name: Optional[str] = None
    confidence: float = 0.0
    extracted_params: Dict[str, Any] = {}


# ===========================================
# Agent状态模型
# ===========================================

class AgentState(BaseSchema):
    """智能体状态（用于LangGraph）"""
    conversation_id: str
    user_input: str
    messages: List[Dict[str, Any]] = []
    current_plan: Optional[TaskPlan] = None
    execution_results: List[Dict[str, Any]] = []
    final_output: Optional[str] = None
    output_type: OutputType = OutputType.TEXT
    page_url: Optional[str] = None
    error: Optional[str] = None
    step_logs: List[Dict[str, Any]] = []  # 执行步骤日志


# ===========================================
# API响应包装
# ===========================================

class APIResponse(BaseSchema):
    """通用API响应"""
    success: bool
    message: str = ""
    data: Optional[Any] = None
    error: Optional[str] = None
