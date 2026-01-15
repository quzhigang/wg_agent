"""
工具基类定义
所有工具都应继承此基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class ToolCategory(str, Enum):
    """工具类别"""
    BASIN_INFO = "basin_info"  # 流域基本信息
    HYDRO_MONITOR = "hydro_monitor"  # 水雨情监测数据
    FLOOD_CONTROL = "flood_control"  # 防洪业务
    HYDRO_MODEL = "hydro_model"  # 水利专业模型
    DAMAGE_ASSESS = "damage_assess"  # 灾损评估
    KNOWLEDGE = "knowledge"  # 知识库
    OUTPUT = "output"  # 输出工具


class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型: string, integer, float, boolean, array, object")
    description: str = Field(..., description="参数描述")
    required: bool = Field(default=True, description="是否必需")
    default: Any = Field(default=None, description="默认值")
    enum: Optional[List[str]] = Field(default=None, description="枚举值列表")


class ToolResult(BaseModel):
    """工具执行结果"""
    success: bool = Field(..., description="是否成功")
    data: Any = Field(default=None, description="返回数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    execution_time_ms: Optional[int] = Field(default=None, description="执行耗时(毫秒)")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="附加元数据")


class ToolDefinition(BaseModel):
    """工具定义"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    category: ToolCategory = Field(..., description="工具类别")
    parameters: List[ToolParameter] = Field(default_factory=list, description="参数列表")
    returns: str = Field(default="", description="返回值描述")
    is_async: bool = Field(default=False, description="是否为异步工具")
    requires_auth: bool = Field(default=False, description="是否需要认证")
    timeout_seconds: int = Field(default=30, description="超时时间(秒)")


class BaseTool(ABC):
    """
    工具基类
    
    所有工具都应继承此类并实现execute方法
    """
    
    def __init__(self):
        """初始化工具"""
        self._definition: Optional[ToolDefinition] = None
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """工具类别"""
        pass
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """工具参数列表"""
        return []
    
    @property
    def is_async(self) -> bool:
        """是否为异步工具"""
        return False
    
    @property
    def timeout_seconds(self) -> int:
        """超时时间"""
        return 30
    
    def get_definition(self) -> ToolDefinition:
        """获取工具定义"""
        if self._definition is None:
            self._definition = ToolDefinition(
                name=self.name,
                description=self.description,
                category=self.category,
                parameters=self.parameters,
                is_async=self.is_async,
                timeout_seconds=self.timeout_seconds
            )
        return self._definition
    
    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证参数
        
        Args:
            params: 输入参数
            
        Returns:
            (是否有效, 错误信息)
        """
        for param in self.parameters:
            if param.required and param.name not in params:
                return False, f"缺少必需参数: {param.name}"
            
            if param.name in params:
                value = params[param.name]

                # 非必需参数值为None时跳过类型校验
                if not param.required and value is None:
                    continue

                # 类型检查与自动转换
                if param.type == "string":
                    if value is None:
                        return False, f"参数 {param.name} 不能为空"
                    if not isinstance(value, str):
                        # 尝试自动转换为字符串
                        params[param.name] = str(value)
                elif param.type == "integer" and not isinstance(value, int):
                    return False, f"参数 {param.name} 应为整数类型"
                elif param.type == "float" and not isinstance(value, (int, float)):
                    return False, f"参数 {param.name} 应为浮点数类型"
                elif param.type == "boolean" and not isinstance(value, bool):
                    return False, f"参数 {param.name} 应为布尔类型"
                elif param.type == "array" and not isinstance(value, list):
                    return False, f"参数 {param.name} 应为数组类型"
                elif param.type == "object" and not isinstance(value, dict):
                    return False, f"参数 {param.name} 应为对象类型"
                
                # 枚举值检查
                if param.enum and value not in param.enum:
                    return False, f"参数 {param.name} 的值必须是: {param.enum}"
        
        return True, None
    
    def fill_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """填充默认值"""
        filled = params.copy()
        for param in self.parameters:
            if param.name not in filled and param.default is not None:
                filled[param.name] = param.default
        return filled
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            执行结果
        """
        pass
    
    async def __call__(self, **kwargs) -> ToolResult:
        """
        调用工具
        
        提供参数验证和日志记录
        """
        import time
        
        logger.debug(f"执行工具: {self.name}")
        start_time = time.time()
        
        try:
            # 验证参数
            valid, error = self.validate_params(kwargs)
            if not valid:
                return ToolResult(
                    success=False,
                    error=error
                )
            
            # 填充默认值
            params = self.fill_defaults(kwargs)
            
            # 执行工具
            result = await self.execute(**params)
            
            # 记录执行时间
            execution_time = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time
            
            logger.debug(f"工具 {self.name} 执行完成，耗时 {execution_time}ms")
            
            return result
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"工具 {self.name} 执行失败: {e}")
            
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    def to_langchain_tool(self):
        """
        转换为LangChain工具格式
        
        Returns:
            LangChain工具
        """
        from langchain_core.tools import StructuredTool
        
        # 构建参数schema
        param_schema = {}
        for param in self.parameters:
            param_schema[param.name] = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                param_schema[param.name]["enum"] = param.enum
        
        return StructuredTool.from_function(
            func=self._sync_execute,
            name=self.name,
            description=self.description,
            args_schema=None,  # 可以定义Pydantic模型
            coroutine=self.execute
        )
    
    def _sync_execute(self, **kwargs):
        """同步执行包装"""
        import asyncio
        return asyncio.run(self.execute(**kwargs))
    
    def get_prompt_description(self) -> str:
        """
        获取用于提示词的工具描述
        
        Returns:
            格式化的工具描述
        """
        params_desc = []
        for param in self.parameters:
            required = "(必需)" if param.required else "(可选)"
            params_desc.append(f"  - {param.name} [{param.type}] {required}: {param.description}")
        
        params_str = "\n".join(params_desc) if params_desc else "  无参数"
        
        return f"""工具名称: {self.name}
描述: {self.description}
类别: {self.category.value}
参数:
{params_str}
"""
