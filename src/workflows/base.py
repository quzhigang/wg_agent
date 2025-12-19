"""
工作流基类定义
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
        执行工作流
        
        Args:
            state: 智能体状态
            
        Returns:
            更新后的状态
        """
        pass
