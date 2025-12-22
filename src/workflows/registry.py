"""
工作流注册表
管理所有预定义工作流的注册、匹配和执行
"""

from typing import Dict, Any, Optional, List, Type

from ..config.logging_config import get_logger
from .base import BaseWorkflow, WorkflowDefinition

logger = get_logger(__name__)


class WorkflowRegistry:
    """
    工作流注册表
    
    单例模式，管理所有工作流的注册和匹配
    """
    
    _instance: Optional['WorkflowRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._workflows: Dict[str, BaseWorkflow] = {}
        self._initialized = True
        
        logger.info("工作流注册表初始化完成")
    
    def register(self, workflow: BaseWorkflow) -> None:
        """
        注册工作流
        
        Args:
            workflow: 工作流实例
        """
        name = workflow.name
        
        if name in self._workflows:
            logger.warning(f"工作流 {name} 已存在，将被覆盖")
        
        self._workflows[name] = workflow
        logger.info(f"注册工作流: {name}")
    
    def unregister(self, name: str) -> bool:
        """
        注销工作流
        
        Args:
            name: 工作流名称
            
        Returns:
            是否成功注销
        """
        if name in self._workflows:
            self._workflows.pop(name)
            logger.info(f"注销工作流: {name}")
            return True
        return False
    
    def get_workflow(self, name: str) -> Optional[BaseWorkflow]:
        """
        获取工作流实例
        
        Args:
            name: 工作流名称
            
        Returns:
            工作流实例或None
        """
        return self._workflows.get(name)
    
    def has_workflow(self, name: str) -> bool:
        """检查工作流是否存在"""
        return name in self._workflows
    
    def match_workflow(self, intent: str, user_message: str) -> Optional[BaseWorkflow]:
        """
        根据意图和用户消息匹配工作流
        
        Args:
            intent: 用户意图
            user_message: 用户消息
            
        Returns:
            匹配的工作流或None
        """
        for workflow in self._workflows.values():
            if workflow.match(intent, user_message):
                logger.info(f"匹配到工作流: {workflow.name}")
                return workflow
        
        logger.debug("未匹配到任何工作流")
        return None
    
    def list_workflows(self) -> List[str]:
        """
        列出所有工作流名称
        
        Returns:
            工作流名称列表
        """
        return list(self._workflows.keys())
    
    def get_all_definitions(self) -> List[WorkflowDefinition]:
        """
        获取所有工作流定义
        
        Returns:
            工作流定义列表
        """
        return [wf.get_definition() for wf in self._workflows.values()]
    
    def get_workflows_description(self) -> str:
        """
        获取工作流描述文本（用于提示词）
        
        Returns:
            格式化的工作流描述
        """
        descriptions = []
        for i, workflow in enumerate(self._workflows.values(), 1):
            definition = workflow.get_definition()
            desc = f"{i}. {definition.name}: {definition.description}"
            if definition.trigger_keywords:
                desc += f" (关键词: {', '.join(definition.trigger_keywords[:3])})"
            descriptions.append(desc)
        
        return "\n".join(descriptions)
    
    def clear(self) -> None:
        """清空所有工作流"""
        self._workflows.clear()
        logger.info("工作流注册表已清空")


# 全局注册表实例
_registry: Optional[WorkflowRegistry] = None


def get_workflow_registry() -> WorkflowRegistry:
    """获取工作流注册表单例"""
    global _registry
    if _registry is None:
        _registry = WorkflowRegistry()
    return _registry


def register_workflow(workflow: BaseWorkflow) -> BaseWorkflow:
    """
    注册工作流的便捷函数
    
    Args:
        workflow: 工作流实例
        
    Returns:
        工作流实例
    """
    registry = get_workflow_registry()
    registry.register(workflow)
    return workflow


def init_default_workflows():
    """
    初始化默认工作流
    
    加载所有内置工作流
    """
    logger.info("初始化默认工作流...")
    
    # 导入工作流模块，触发自动注册
    try:
        from . import get_autoforecast_result
        from . import get_history_autoforecast_result
        from . import flood_autoforecast_getresult
        from . import get_manualforecast_result
        logger.info("默认工作流加载完成")
    except ImportError as e:
        logger.warning(f"部分工作流模块加载失败: {e}")
