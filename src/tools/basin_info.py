"""
流域基本信息工具
提供流域概况、河流信息、水利设施等基础数据查询
"""

from typing import Dict, Any, List, Optional
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)


class GetBasinInfoTool(BaseTool):
    """获取流域概况工具"""
    
    @property
    def name(self) -> str:
        return "get_basin_info"
    
    @property
    def description(self) -> str:
        return "获取卫共流域的基本概况信息，包括流域面积、河流长度、主要特征等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="info_type",
                type="string",
                description="信息类型: overview(概况), geography(地理), climate(气候), hydrology(水文)",
                required=False,
                default="overview",
                enum=["overview", "geography", "climate", "hydrology"]
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取流域信息"""
        info_type = kwargs.get('info_type', 'overview')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/info"
            
            params = {'type': info_type}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data.get('data', data)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"获取流域信息HTTP错误: {e}")
            return self._get_mock_data(info_type)
        except Exception as e:
            logger.error(f"获取流域信息失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_data(self, info_type: str) -> ToolResult:
        """返回模拟数据"""
        mock_data = {
            "overview": {
                "basin_name": "卫共流域",
                "location": "河南省北部",
                "total_area_km2": 15600,
                "main_rivers": ["卫河", "共渠", "淇河"],
                "administrative_divisions": ["新乡市", "鹤壁市", "安阳市", "濮阳市"],
                "population_million": 12.5,
                "description": "卫共流域位于河南省北部，是海河流域的重要组成部分，流域面积约15600平方公里。"
            },
            "geography": {
                "terrain": "西高东低，地势由太行山向华北平原过渡",
                "elevation_range": "50-1500米",
                "soil_types": ["黄土", "褐土", "潮土"],
                "land_use": {
                    "farmland_percent": 65,
                    "forest_percent": 15,
                    "urban_percent": 12,
                    "water_percent": 8
                }
            },
            "climate": {
                "climate_type": "温带大陆性季风气候",
                "annual_precipitation_mm": 580,
                "precipitation_distribution": "60%-70%集中在7-8月",
                "annual_temperature_c": 14.2,
                "frost_free_days": 200
            },
            "hydrology": {
                "main_river": "卫河",
                "river_length_km": 283,
                "multi_year_avg_flow_m3s": 35.6,
                "annual_runoff_billion_m3": 8.5,
                "flood_season": "7月-9月",
                "major_floods": ["1963年", "1996年", "2021年"]
            }
        }
        
        result = mock_data.get(info_type, mock_data["overview"])
        return ToolResult(success=True, data=result, metadata={"is_mock": True})


class GetRiverInfoTool(BaseTool):
    """获取河流信息工具"""
    
    @property
    def name(self) -> str:
        return "get_river_info"
    
    @property
    def description(self) -> str:
        return "获取流域内河流的详细信息，包括河流长度、流域面积、主要支流等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="river_name",
                type="string",
                description="河流名称",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取河流信息"""
        river_name = kwargs.get('river_name')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/rivers"
            
            params = {}
            if river_name:
                params['name'] = river_name
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data.get('data', data)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"获取河流信息HTTP错误: {e}")
            return self._get_mock_data(river_name)
        except Exception as e:
            logger.error(f"获取河流信息失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_data(self, river_name: str) -> ToolResult:
        """返回模拟数据"""
        mock_rivers = [
            {
                "river_name": "卫河",
                "river_code": "HAI-WEI",
                "length_km": 283,
                "basin_area_km2": 8560,
                "source": "太行山东麓",
                "outlet": "汇入漳卫河",
                "main_tributaries": ["淇河", "共渠", "汤河"],
                "warning_sections": ["卫辉", "浚县", "道口"],
                "description": "卫河是海河水系南运河的支流，发源于太行山东麓，流经新乡、鹤壁、安阳等地。"
            },
            {
                "river_name": "淇河",
                "river_code": "HAI-QI",
                "length_km": 165,
                "basin_area_km2": 2380,
                "source": "山西省陵川县",
                "outlet": "汇入卫河",
                "main_tributaries": ["淅河", "沧河"],
                "description": "淇河发源于山西省陵川县，流经河南省林州市、鹤壁市，在淇县注入卫河。"
            },
            {
                "river_name": "共渠",
                "river_code": "HAI-GQ",
                "length_km": 85,
                "basin_area_km2": 1250,
                "source": "辉县市",
                "outlet": "汇入卫河",
                "description": "共渠是卫河的重要支流，主要承担排涝和灌溉功能。"
            }
        ]
        
        if river_name:
            result = [r for r in mock_rivers if river_name in r['river_name']]
        else:
            result = mock_rivers
        
        return ToolResult(success=True, data=result, metadata={"is_mock": True})


class GetWaterProjectsTool(BaseTool):
    """获取水利工程信息工具"""
    
    @property
    def name(self) -> str:
        return "get_water_projects"
    
    @property
    def description(self) -> str:
        return "获取流域内水利工程信息，包括水库、闸坝、蓄滞洪区等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="project_type",
                type="string",
                description="工程类型: reservoir(水库), sluice(水闸), dam(堤坝), detention(蓄滞洪区)",
                required=False,
                enum=["reservoir", "sluice", "dam", "detention"]
            ),
            ToolParameter(
                name="project_name",
                type="string",
                description="工程名称",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取水利工程信息"""
        project_type = kwargs.get('project_type')
        project_name = kwargs.get('project_name')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/projects"
            
            params = {}
            if project_type:
                params['type'] = project_type
            if project_name:
                params['name'] = project_name
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data.get('data', data)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"获取水利工程信息HTTP错误: {e}")
            return self._get_mock_data(project_type)
        except Exception as e:
            logger.error(f"获取水利工程信息失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_data(self, project_type: str) -> ToolResult:
        """返回模拟数据"""
        mock_projects = {
            "reservoir": [
                {
                    "name": "良相水库",
                    "type": "reservoir",
                    "location": "辉县市",
                    "total_capacity_million_m3": 1580,
                    "flood_control_capacity_million_m3": 850,
                    "normal_level_m": 130.0,
                    "flood_limit_level_m": 128.0,
                    "design_flood_level_m": 132.5,
                    "built_year": 1958
                },
                {
                    "name": "石门水库",
                    "type": "reservoir",
                    "location": "林州市",
                    "total_capacity_million_m3": 2350,
                    "flood_control_capacity_million_m3": 1200,
                    "normal_level_m": 185.0,
                    "flood_limit_level_m": 182.0,
                    "built_year": 1966
                }
            ],
            "sluice": [
                {
                    "name": "卫辉枢纽",
                    "type": "sluice",
                    "location": "卫辉市",
                    "design_flow_m3s": 1500,
                    "gates_count": 12,
                    "function": "防洪、灌溉、航运"
                }
            ],
            "detention": [
                {
                    "name": "良相蓄滞洪区",
                    "type": "detention",
                    "location": "辉县市-卫辉市",
                    "design_capacity_million_m3": 3500,
                    "area_km2": 120,
                    "population_thousand": 15,
                    "activation_condition": "卫辉站水位超82.0m"
                }
            ]
        }
        
        if project_type:
            result = mock_projects.get(project_type, [])
        else:
            result = []
            for projects in mock_projects.values():
                result.extend(projects)
        
        return ToolResult(success=True, data=result, metadata={"is_mock": True})


class GetAdministrativeDivisionsTool(BaseTool):
    """获取行政区划信息工具"""
    
    @property
    def name(self) -> str:
        return "get_administrative_divisions"
    
    @property
    def description(self) -> str:
        return "获取流域涉及的行政区划信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="city_name",
                type="string",
                description="城市名称",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取行政区划信息"""
        city_name = kwargs.get('city_name')
        
        # 直接返回模拟数据
        return self._get_mock_data(city_name)
    
    def _get_mock_data(self, city_name: str) -> ToolResult:
        """返回模拟数据"""
        mock_divisions = [
            {
                "city": "新乡市",
                "counties": ["辉县市", "卫辉市", "获嘉县", "原阳县"],
                "basin_area_km2": 5200,
                "population_million": 4.5,
                "main_rivers": ["卫河", "共渠"]
            },
            {
                "city": "鹤壁市",
                "counties": ["淇县", "浚县", "淇滨区"],
                "basin_area_km2": 3800,
                "population_million": 1.6,
                "main_rivers": ["淇河", "卫河"]
            },
            {
                "city": "安阳市",
                "counties": ["林州市", "安阳县", "滑县"],
                "basin_area_km2": 4200,
                "population_million": 3.8,
                "main_rivers": ["淇河", "洹河"]
            },
            {
                "city": "濮阳市",
                "counties": ["濮阳县", "清丰县"],
                "basin_area_km2": 2400,
                "population_million": 2.6,
                "main_rivers": ["卫河"]
            }
        ]
        
        if city_name:
            result = [d for d in mock_divisions if city_name in d['city']]
        else:
            result = mock_divisions
        
        return ToolResult(success=True, data=result, metadata={"is_mock": True})


# 注册工具
def register_basin_info_tools():
    """注册流域基本信息工具"""
    register_tool(GetBasinInfoTool())
    register_tool(GetRiverInfoTool())
    register_tool(GetWaterProjectsTool())
    register_tool(GetAdministrativeDivisionsTool())
    logger.info("流域基本信息工具注册完成")


# 模块加载时自动注册
register_basin_info_tools()
