"""
工作流基类定义

支持两种执行模式：
1. 批量执行模式（execute）：一次性执行所有步骤，适用于简单工作流
2. 单步执行模式（execute_step）：每次执行一个步骤，支持流式进度显示

单步执行模式为后续扩展提供基础：
- 步骤重试：检测到错误后重新执行当前步骤
- 替代方案：主工具失败时切换到 fallback_tools
- 回滚机制：错误时逆序执行已完成步骤的回滚操作
- 条件跳转：根据步骤结果动态修改计划或跳过步骤
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class WorkflowStatus(str, Enum):
    """工作流状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    """步骤执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class WorkflowStep(BaseModel):
    """工作流步骤定义"""
    step_id: int = Field(..., description="步骤ID")
    name: str = Field(..., description="步骤名称")
    description: str = Field(default="", description="步骤描述")
    tool_name: Optional[str] = Field(default=None, description="工具名称")
    tool_args_template: Optional[Dict[str, Any]] = Field(default=None, description="工具参数模板")
    depends_on: List[int] = Field(default_factory=list, description="依赖的步骤ID")
    is_async: bool = Field(default=False, description="是否异步执行")
    output_key: Optional[str] = Field(default=None, description="输出结果的key")
    # 扩展字段：为后续错误处理和回滚机制预留
    fallback_tools: List[str] = Field(default_factory=list, description="替代工具列表")
    retry_count: int = Field(default=0, description="重试次数")
    skip_on_error: bool = Field(default=False, description="错误时是否跳过")
    rollback_tool: Optional[str] = Field(default=None, description="回滚工具")
    rollback_args: Optional[Dict[str, Any]] = Field(default=None, description="回滚参数")


class WorkflowDefinition(BaseModel):
    """工作流定义"""
    name: str = Field(..., description="工作流名称")
    description: str = Field(..., description="工作流描述")
    trigger_intents: List[str] = Field(default_factory=list, description="触发意图列表")
    trigger_keywords: List[str] = Field(default_factory=list, description="触发关键词列表")
    steps: List[WorkflowStep] = Field(..., description="工作流步骤")
    output_type: str = Field(default="text", description="输出类型")
    estimated_time_seconds: int = Field(default=30, description="预估执行时间")


class BaseWorkflow(ABC):
    """工作流基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工作流名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工作流描述"""
        pass
    
    @property
    def trigger_intents(self) -> List[str]:
        """触发意图"""
        return []
    
    @property
    def trigger_keywords(self) -> List[str]:
        """触发关键词"""
        return []
    
    @property
    @abstractmethod
    def steps(self) -> List[WorkflowStep]:
        """工作流步骤"""
        pass
    
    @property
    def output_type(self) -> str:
        """输出类型"""
        return "text"
    
    def get_definition(self) -> WorkflowDefinition:
        """获取工作流定义"""
        return WorkflowDefinition(
            name=self.name,
            description=self.description,
            trigger_intents=self.trigger_intents,
            trigger_keywords=self.trigger_keywords,
            steps=self.steps,
            output_type=self.output_type
        )
    
    def match(self, intent: str, user_message: str) -> bool:
        """
        检查是否匹配此工作流
        
        Args:
            intent: 用户意图
            user_message: 用户消息
            
        Returns:
            是否匹配
        """
        # 检查意图匹配
        if intent in self.trigger_intents:
            return True
        
        # 检查关键词匹配
        for keyword in self.trigger_keywords:
            if keyword in user_message:
                return True
        
        return False
    
    def build_plan(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        根据参数构建执行计划
        
        Args:
            params: 从用户消息中提取的参数
            
        Returns:
            执行计划（序列化的步骤列表）
        """
        plan = []
        for step in self.steps:
            step_dict = step.model_dump()
            
            # 填充工具参数
            if step.tool_args_template:
                tool_args = {}
                for key, value_template in step.tool_args_template.items():
                    if isinstance(value_template, str) and value_template.startswith('$'):
                        # 从params中获取值
                        param_key = value_template[1:]
                        tool_args[key] = params.get(param_key, value_template)
                    else:
                        tool_args[key] = value_template
                step_dict['tool_args'] = tool_args
            
            plan.append(step_dict)
        
        return plan
    
    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工作流（批量模式）

        Args:
            state: 智能体状态

        Returns:
            更新后的状态
        """
        pass

    @property
    def supports_step_execution(self) -> bool:
        """
        是否支持单步执行模式

        子类可以重写此属性来启用单步执行模式。
        默认为 False，使用批量执行模式（execute方法）。
        """
        return False

    def get_plan_steps(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取工作流的执行计划步骤列表

        用于在流式响应中先发送计划，让前端显示步骤列表。

        Args:
            state: 智能体状态

        Returns:
            步骤列表，每个步骤包含 step_id, name, description, tool_name 等信息
        """
        plan_steps = []
        for step in self.steps:
            plan_steps.append({
                'step_id': step.step_id,
                'name': step.name,  # 简短名称，用于显示
                'description': step.description,  # 详细描述
                'tool_name': step.tool_name
            })
        return plan_steps

    async def prepare_execution(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备执行工作流（初始化阶段）

        在单步执行模式下，此方法在第一步执行前调用，用于：
        - 解析用户消息中的参数
        - 初始化工作流上下文
        - 准备执行所需的数据

        Args:
            state: 智能体状态

        Returns:
            更新后的状态，包含 workflow_context 等初始化数据
        """
        # 默认实现：返回空的工作流上下文
        return {
            'workflow_context': {},
            'workflow_status': WorkflowStatus.RUNNING.value
        }

    async def execute_step(self, state: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """
        执行单个步骤（单步执行模式）

        Args:
            state: 智能体状态，包含：
                - workflow_context: 工作流上下文（步骤间数据传递）
                - execution_results: 已执行步骤的结果列表
                - current_step_index: 当前步骤索引
            step_index: 要执行的步骤索引（从0开始）

        Returns:
            步骤执行结果，包含：
                - step_result: 当前步骤的执行结果
                - workflow_context: 更新后的工作流上下文
                - step_completed: 步骤是否完成
                - workflow_completed: 工作流是否全部完成
                - error: 错误信息（如果有）
        """
        # 默认实现：抛出未实现异常
        # 子类需要重写此方法以支持单步执行
        raise NotImplementedError(
            f"工作流 {self.name} 未实现 execute_step 方法。"
            f"请重写此方法或将 supports_step_execution 设为 False。"
        )

    async def finalize_execution(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        完成工作流执行（收尾阶段）

        在单步执行模式下，所有步骤执行完成后调用，用于：
        - 汇总执行结果
        - 生成最终输出（如Web页面）
        - 清理临时数据

        Args:
            state: 智能体状态

        Returns:
            最终状态，包含 final_response, output_type, generated_page_url 等
        """
        # 默认实现：返回基本的完成状态
        return {
            'workflow_status': WorkflowStatus.COMPLETED.value,
            'next_action': 'respond'
        }

