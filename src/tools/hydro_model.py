"""
水利专业模型工具
提供水文模型、水动力模型等专业计算功能
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)


class RunHydrologicalModelTool(BaseTool):
    """运行水文模型工具"""
    
    @property
    def name(self) -> str:
        return "run_hydrological_model"
    
    @property
    def description(self) -> str:
        return "运行水文模型进行产汇流计算"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="model_type",
                type="string",
                description="模型类型: xaj(新安江), tank(水箱), api(API模型)",
                required=False,
                default="xaj",
                enum=["xaj", "tank", "api"]
            ),
            ToolParameter(
                name="start_time",
                type="string",
                description="计算开始时间",
                required=False
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="计算结束时间",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水文模型"""
        model_type = kwargs.get('model_type', 'xaj')
        
        try:
            url = settings.wg_model_server_url
            params = {
                "method": "RunHydrologicalModel",
                "model_type": model_type
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"model_type": model_type}
            )
            
        except Exception as e:
            logger.error(f"水文模型运行失败: {e}")
            return self._get_mock_result(model_type)
    
    def _get_mock_result(self, model_type: str) -> ToolResult:
        """返回模拟结果"""
        import uuid
        return ToolResult(
            success=True,
            data={
                "task_id": str(uuid.uuid4()),
                "model_type": model_type,
                "status": "submitted",
                "message": "水文模型计算任务已提交"
            },
            metadata={"is_mock": True, "is_async_task": True}
        )


class RunHydrodynamicModelTool(BaseTool):
    """运行水动力模型工具"""
    
    @property
    def name(self) -> str:
        return "run_hydrodynamic_model"
    
    @property
    def description(self) -> str:
        return "运行一维/二维水动力模型进行洪水演进计算"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def timeout_seconds(self) -> int:
        return 600  # 10分钟
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="model_type",
                type="string",
                description="模型类型: mike11(一维), mike21(二维)",
                required=False,
                default="mike11",
                enum=["mike11", "mike21"]
            ),
            ToolParameter(
                name="boundary_conditions",
                type="object",
                description="边界条件",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水动力模型"""
        model_type = kwargs.get('model_type', 'mike11')
        
        try:
            url = settings.wg_model_server_url
            params = {
                "method": "RunHydrodynamicModel",
                "model_type": model_type
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(success=True, data=data)
            
        except Exception as e:
            logger.error(f"水动力模型运行失败: {e}")
            return self._get_mock_result(model_type)
    
    def _get_mock_result(self, model_type: str) -> ToolResult:
        """返回模拟结果"""
        import uuid
        return ToolResult(
            success=True,
            data={
                "task_id": str(uuid.uuid4()),
                "model_type": model_type,
                "status": "submitted",
                "message": "水动力模型计算任务已提交",
                "estimated_time_minutes": 15
            },
            metadata={"is_mock": True, "is_async_task": True}
        )


class GetModelResultTool(BaseTool):
    """获取模型计算结果工具"""
    
    @property
    def name(self) -> str:
        return "get_model_result"
    
    @property
    def description(self) -> str:
        return "获取水利模型的计算结果"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="task_id",
                type="string",
                description="模型计算任务ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取模型结果"""
        task_id = kwargs.get('task_id')
        
        try:
            url = settings.wg_model_server_url
            params = {
                "method": "GetModelResult",
                "task_id": task_id
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(success=True, data=data)
            
        except Exception as e:
            logger.error(f"获取模型结果失败: {e}")
            return self._get_mock_result()
    
    def _get_mock_result(self) -> ToolResult:
        """返回模拟结果"""
        mock_data = {
            "status": "completed",
            "result": {
                "sections": [
                    {"name": "卫辉断面", "max_level": 79.85, "max_flow": 1250.5},
                    {"name": "浚县断面", "max_level": 45.65, "max_flow": 1180.2}
                ],
                "inundation_area_km2": 25.6,
                "max_depth_m": 3.2
            }
        }
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


# 注册工具
def register_hydro_model_tools():
    """注册水利专业模型工具"""
    register_tool(RunHydrologicalModelTool())
    register_tool(RunHydrodynamicModelTool())
    register_tool(GetModelResultTool())
    logger.info("水利专业模型工具注册完成")


# 模块加载时自动注册
register_hydro_model_tools()
