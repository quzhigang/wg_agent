"""
灾损评估工具
提供洪水灾害损失评估功能
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)


class AssessFloodDamageTool(BaseTool):
    """洪水灾损评估工具"""
    
    @property
    def name(self) -> str:
        return "assess_flood_damage"
    
    @property
    def description(self) -> str:
        return "评估洪水造成的人口、农业、经济损失"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DAMAGE_ASSESS
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="inundation_area",
                type="object",
                description="淹没范围数据（GeoJSON或面积）",
                required=False
            ),
            ToolParameter(
                name="water_depth",
                type="float",
                description="平均淹没水深(米)",
                required=False
            ),
            ToolParameter(
                name="duration_hours",
                type="integer",
                description="淹没持续时间(小时)",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行灾损评估"""
        inundation_area = kwargs.get('inundation_area')
        water_depth = kwargs.get('water_depth', 1.5)
        duration_hours = kwargs.get('duration_hours', 24)
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/damage/assess"
            
            params = {
                "water_depth": water_depth,
                "duration_hours": duration_hours
            }
            if inundation_area:
                params["inundation_area"] = inundation_area
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(success=True, data=data)
            
        except Exception as e:
            logger.error(f"灾损评估失败: {e}")
            return self._get_mock_result(water_depth, duration_hours)
    
    def _get_mock_result(self, water_depth: float, duration_hours: int) -> ToolResult:
        """返回模拟结果"""
        mock_data = {
            "assessment_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "inundation_summary": {
                "total_area_km2": 85.6,
                "max_depth_m": water_depth * 2,
                "avg_depth_m": water_depth,
                "duration_hours": duration_hours
            },
            "population_impact": {
                "affected_population": 25800,
                "evacuated_population": 18500,
                "affected_households": 8600,
                "villages_affected": 32
            },
            "agricultural_loss": {
                "crop_area_affected_ha": 4500,
                "crop_loss_million_yuan": 125.5,
                "livestock_affected": 3200,
                "aquaculture_loss_million_yuan": 18.6
            },
            "infrastructure_damage": {
                "roads_damaged_km": 45.2,
                "bridges_damaged": 8,
                "power_facilities_affected": 15,
                "water_facilities_affected": 12
            },
            "economic_loss": {
                "direct_loss_million_yuan": 856.5,
                "indirect_loss_million_yuan": 285.2,
                "total_loss_million_yuan": 1141.7
            },
            "risk_level": "high"
        }
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


class GetVulnerabilityDataTool(BaseTool):
    """获取脆弱性数据工具"""
    
    @property
    def name(self) -> str:
        return "get_vulnerability_data"
    
    @property
    def description(self) -> str:
        return "获取区域的洪水脆弱性数据，包括人口、土地利用等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DAMAGE_ASSESS
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="region_name",
                type="string",
                description="区域名称",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取脆弱性数据"""
        region_name = kwargs.get('region_name')
        
        # 返回模拟数据
        mock_data = {
            "region": region_name or "卫辉市",
            "population_density_per_km2": 580,
            "land_use": {
                "residential_percent": 15,
                "agricultural_percent": 60,
                "industrial_percent": 10,
                "other_percent": 15
            },
            "critical_facilities": {
                "hospitals": 3,
                "schools": 25,
                "power_stations": 2,
                "water_plants": 1
            },
            "historical_losses": [
                {"year": 2021, "loss_million_yuan": 2850},
                {"year": 2016, "loss_million_yuan": 580}
            ]
        }
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


# 注册工具
def register_damage_assess_tools():
    """注册灾损评估工具"""
    register_tool(AssessFloodDamageTool())
    register_tool(GetVulnerabilityDataTool())
    logger.info("灾损评估工具注册完成")


# 模块加载时自动注册
register_damage_assess_tools()
