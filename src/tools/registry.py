"""
工具注册表
管理所有可用工具的注册、发现和调用
"""

from typing import Dict, Any, Optional, List, Type, Callable
from functools import wraps

from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolResult, ToolDefinition

logger = get_logger(__name__)


class ToolRegistry:
    """
    工具注册表
    
    单例模式，管理所有工具的注册和调用
    """
    
    _instance: Optional['ToolRegistry'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._tools: Dict[str, BaseTool] = {}
        self._tool_functions: Dict[str, Callable] = {}
        self._categories: Dict[ToolCategory, List[str]] = {
            category: [] for category in ToolCategory
        }
        self._initialized = True
        
        logger.info("工具注册表初始化完成")
    
    def register(self, tool: BaseTool) -> None:
        """
        注册工具
        
        Args:
            tool: 工具实例
        """
        name = tool.name
        
        if name in self._tools:
            logger.warning(f"工具 {name} 已存在，将被覆盖")
        
        self._tools[name] = tool
        self._tool_functions[name] = tool.__call__
        
        # 按类别归类
        category = tool.category
        if name not in self._categories[category]:
            self._categories[category].append(name)
    
    def register_function(
        self, 
        name: str, 
        func: Callable,
        description: str = "",
        category: ToolCategory = ToolCategory.BASIN_INFO
    ) -> None:
        """
        注册函数作为工具
        
        Args:
            name: 工具名称
            func: 工具函数
            description: 工具描述
            category: 工具类别
        """
        self._tool_functions[name] = func
        
        if name not in self._categories[category]:
            self._categories[category].append(name)
        
        logger.info(f"注册函数工具: {name}")
    
    def unregister(self, name: str) -> bool:
        """
        注销工具
        
        Args:
            name: 工具名称
            
        Returns:
            是否成功注销
        """
        if name in self._tools:
            tool = self._tools.pop(name)
            category = tool.category
            if name in self._categories[category]:
                self._categories[category].remove(name)
            logger.info(f"注销工具: {name}")
            return True
        
        if name in self._tool_functions:
            self._tool_functions.pop(name)
            for cat_tools in self._categories.values():
                if name in cat_tools:
                    cat_tools.remove(name)
            return True
        
        return False
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        获取工具实例
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例或None
        """
        return self._tools.get(name)
    
    def get_tool_function(self, name: str) -> Optional[Callable]:
        """
        获取工具函数
        
        Args:
            name: 工具名称
            
        Returns:
            工具函数或None
        """
        return self._tool_functions.get(name)
    
    def has_tool(self, name: str) -> bool:
        """检查工具是否存在"""
        return name in self._tools or name in self._tool_functions
    
    async def execute(self, name: str, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            执行结果
        """
        if name in self._tools:
            tool = self._tools[name]
            return await tool(**kwargs)
        
        if name in self._tool_functions:
            func = self._tool_functions[name]
            try:
                import asyncio
                if asyncio.iscoroutinefunction(func):
                    result = await func(**kwargs)
                else:
                    result = func(**kwargs)
                
                # 如果返回的不是ToolResult，包装一下
                if isinstance(result, ToolResult):
                    return result
                return ToolResult(success=True, data=result)
            except Exception as e:
                logger.error(f"工具 {name} 执行失败: {e}")
                return ToolResult(success=False, error=str(e))
        
        return ToolResult(
            success=False,
            error=f"工具不存在: {name}"
        )
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """
        列出工具
        
        Args:
            category: 可选的类别过滤
            
        Returns:
            工具名称列表
        """
        if category:
            return self._categories.get(category, [])
        return list(self._tools.keys()) + list(
            k for k in self._tool_functions.keys() 
            if k not in self._tools
        )
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        按类别获取工具
        
        Args:
            category: 工具类别
            
        Returns:
            工具列表
        """
        names = self._categories.get(category, [])
        return [self._tools[name] for name in names if name in self._tools]
    
    def get_all_definitions(self) -> List[ToolDefinition]:
        """
        获取所有工具定义
        
        Returns:
            工具定义列表
        """
        return [tool.get_definition() for tool in self._tools.values()]
    
    def get_tools_description(self, category: Optional[ToolCategory] = None) -> str:
        """
        获取工具描述文本（用于提示词）
        
        Args:
            category: 可选的类别过滤
            
        Returns:
            格式化的工具描述
        """
        tools = self._tools.values()
        if category:
            tools = [t for t in tools if t.category == category]
        
        descriptions = []
        for i, tool in enumerate(tools, 1):
            descriptions.append(f"{i}. {tool.get_prompt_description()}")
        
        return "\n".join(descriptions)
    
    def get_tool_names_and_descriptions(self) -> Dict[str, str]:
        """
        获取工具名称和描述的映射
        
        Returns:
            {工具名称: 描述}
        """
        return {
            name: tool.description 
            for name, tool in self._tools.items()
        }
    
    def clear(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        self._tool_functions.clear()
        for category in self._categories:
            self._categories[category] = []
        logger.info("工具注册表已清空")


# 全局注册表实例
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """获取工具注册表单例"""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: BaseTool) -> BaseTool:
    """
    注册工具的便捷函数
    
    Args:
        tool: 工具实例
        
    Returns:
        工具实例
    """
    registry = get_tool_registry()
    registry.register(tool)
    return tool


def tool(
    name: Optional[str] = None,
    description: str = "",
    category: ToolCategory = ToolCategory.BASIN_INFO
):
    """
    工具装饰器
    
    用于将普通函数注册为工具
    
    Args:
        name: 工具名称（默认使用函数名）
        description: 工具描述
        category: 工具类别
        
    Example:
        @tool(name="query_water_level", description="查询水位")
        async def query_water_level(station_id: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or ""
        
        @wraps(func)
        async def wrapper(**kwargs):
            return await func(**kwargs)
        
        # 注册到注册表
        registry = get_tool_registry()
        registry.register_function(tool_name, wrapper, tool_desc, category)
        
        return wrapper
    
    return decorator


async def execute_tool(name: str, **kwargs) -> ToolResult:
    """
    执行工具的便捷函数
    
    Args:
        name: 工具名称
        **kwargs: 工具参数
        
    Returns:
        执行结果
    """
    registry = get_tool_registry()
    return await registry.execute(name, **kwargs)


def init_default_tools():
    """
    初始化默认工具
    
    加载所有内置工具
    """
    logger.info("初始化默认工具...")
    
    # 导入11类工具模块，触发自动注册
    # 基础信息、监测数据、模型方案、降雨处理、洪水模型、洪灾损失、其他辅助业务、模型新建及参数设置
    try:
        from . import auth                  # 用户认证工具
        from . import basin_info            # 基础信息接口工具
        from . import hydro_monitor         # 监测数据接口工具
        from . import modelplan_control     # 模型方案管理工具
        from . import rain_control          # 降雨处理工具
        from . import damage_assess         # 洪灾损失评估工具  
        from . import flood_otherbusiness   # 防洪其他辅助业务工具  
        from . import hydromodel_set        # 水利专业模型-方案新建计算及参数设置
        from . import hydromodel_baseinfo   # 水利专业模型-获取与专业模型相关的基础信息        
        from . import hydromodel_parget     # 水利专业模型-获取专业模型参数及边界条件信息        
        from . import hydromodel_resultget  # 水利专业模型-获取专业模型方案及结果信息接口
        logger.info("默认工具加载完成")
    except ImportError as e:
        logger.warning(f"部分工具模块加载失败: {e}")
    
    # 注册RAG知识库搜索工具
    try:
        from ..rag import search_knowledge
        registry = get_tool_registry()
        registry.register_function(
            name="search_knowledge",
            func=search_knowledge,
            description="搜索知识库，查询流域相关的背景知识、专业知识等信息",
            category=ToolCategory.BASIN_INFO
        )
        logger.info("RAG知识库搜索工具注册完成")
    except ImportError as e:
        logger.warning(f"RAG知识库搜索工具注册失败: {e}")
