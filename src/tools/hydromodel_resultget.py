"""
水利专业模型-获取专业模型方案及结果数据相关工具
提供模型方案信息查询、调度计划获取、各类结果数据获取、风险预警信息、历史预报方案管理、场次洪水管理等功能
所有接口基于 Model_Ser.ashx.cs 处理，接口地址统一为：http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx
"""

from typing import Dict, Any, List, Optional
import json
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)

# 模型服务基础URL
MODEL_SERVER_URL = "http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx"


class GetModelsTool(BaseTool):
    """获取已有所有模型方案信息工具"""
    
    @property
    def name(self) -> str:
        return "get_models"
    
    @property
    def description(self) -> str:
        return "获取已有所有模型方案信息，包括方案名称、描述、业务模型编码、起止时间、状态、进度等12个属性"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="model_instance",
                type="string",
                description="模型实例名称字符串，默认为'wg_mike11'",
                required=False,
                default="wg_mike11"
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取所有模型方案信息"""
        model_instance = kwargs.get('model_instance', 'wg_mike11')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_models",
                "request_pars": model_instance
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"model_instance": model_instance, "request_type": "get_models"}
            )
            
        except Exception as e:
            logger.error(f"获取模型方案信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"model_instance": model_instance, "request_type": "get_models"}
            )


class GetDispatchPlanTool(BaseTool):
    """获取方案主要控制闸站的简短调度指令工具"""
    
    @property
    def name(self) -> str:
        return "get_dispatch_plan"
    
    @property
    def description(self) -> str:
        return "获取方案主要控制闸站的简短调度指令，包含水库、河道闸站、蓄滞洪区3种类型的各控制闸站的调度信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取调度指令"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_dispatch_plan",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_dispatch_plan"}
            )
            
        except Exception as e:
            logger.error(f"获取调度指令失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_dispatch_plan"}
            )


class GetTjdataResultTool(BaseTool):
    """获取方案的结果数据工具"""
    
    @property
    def name(self) -> str:
        return "get_tjdata_result"
    
    @property
    def description(self) -> str:
        return "获取方案的结果数据，包含水库、河道断面、蓄滞洪区的洪水计算结果以及结果概述、河道风险，此外还可能包含调度方案结果"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取方案结果数据"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_tjdata_result",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_tjdata_result"}
            )
            
        except Exception as e:
            logger.error(f"获取方案结果数据失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_tjdata_result"}
            )


class GetGisgcPolygonResultTool(BaseTool):
    """获取方案某时刻河道水面GIS面要素结果工具"""
    
    @property
    def name(self) -> str:
        return "get_gisgc_polygon_result"
    
    @property
    def description(self) -> str:
        return "获取方案某时刻河道水面GIS面要素结果，为geojson格式的带Z值的三维水面要素，用于在三维场景中绘制三维水面"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="now_time",
                type="string",
                description="时间字符串，如'2021/07/20 08:00:00'",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取GIS面要素结果"""
        plan_code = kwargs.get('plan_code')
        now_time = kwargs.get('now_time')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, now_time])
            params = {
                "request_type": "get_gisgc_polygon_result",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "now_time": now_time, "request_type": "get_gisgc_polygon_result"}
            )
            
        except Exception as e:
            logger.error(f"获取GIS面要素结果失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_gisgc_polygon_result"}
            )


class GetSamplelineDataResultTool(BaseTool):
    """获取方案的GIS过程线全过程属性结果工具"""
    
    @property
    def name(self) -> str:
        return "get_sampleline_data_result"
    
    @property
    def description(self) -> str:
        return "获取方案的GIS过程线的全过程属性结果，用于在地图区分色动态渲染过程结果，如流量、流速等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="gis_restype",
                type="string",
                description="结果数据类型: 'Waterlevel'(水位), 'Speed'(流速), 'Waterh'(水深), 'Discharge'(流量)",
                required=True,
                enum=["Waterlevel", "Speed", "Waterh", "Discharge"]
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取GIS过程线属性结果"""
        plan_code = kwargs.get('plan_code')
        gis_restype = kwargs.get('gis_restype')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, gis_restype])
            params = {
                "request_type": "get_sampleline_data_result",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "gis_restype": gis_restype, "request_type": "get_sampleline_data_result"}
            )
            
        except Exception as e:
            logger.error(f"获取GIS过程线属性结果失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_sampleline_data_result"}
            )


class GetGistjResultTool(BaseTool):
    """获取方案的GIS统计线结果工具"""
    
    @property
    def name(self) -> str:
        return "get_gistj_result"
    
    @property
    def description(self) -> str:
        return "获取方案的GIS统计线结果，为geojson格式的河道分段线要素，用于在地图区分色渲染全过程最大流量、流速等分布结果"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取GIS统计线结果"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_gistj_result",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_gistj_result"}
            )
            
        except Exception as e:
            logger.error(f"获取GIS统计线结果失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_gistj_result"}
            )


class GetGistjPolygonResultTool(BaseTool):
    """获取方案的GIS统计面结果(淹没面)工具"""
    
    @property
    def name(self) -> str:
        return "get_gistj_polygon_result"
    
    @property
    def description(self) -> str:
        return "获取方案的GIS统计面结果(淹没面)，为geojson格式的二维面要素，用于在地图中分水渲染淹没区水深分布"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取GIS统计面结果"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_gistj_polygon_result",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_gistj_polygon_result"}
            )
            
        except Exception as e:
            logger.error(f"获取GIS统计面结果失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_gistj_polygon_result"}
            )


class GetPointResultTool(BaseTool):
    """查询方案河道上某点的水位流量等结果工具"""
    
    @property
    def name(self) -> str:
        return "get_point_result"
    
    @property
    def description(self) -> str:
        return "查询方案河道上某点的水位流量等结果，用于在地图中点击查询某位置结果信息。如果时间为空字符串，则返回时间序列"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="now_time",
                type="string",
                description="时间字符串，如'2021/07/20 08:00:00'。如果为空字符串''，则返回时间序列",
                required=True
            ),
            ToolParameter(
                name="jd",
                type="string",
                description="经度",
                required=True
            ),
            ToolParameter(
                name="wd",
                type="string",
                description="纬度",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查询某点结果"""
        plan_code = kwargs.get('plan_code')
        now_time = kwargs.get('now_time')
        jd = kwargs.get('jd')
        wd = kwargs.get('wd')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, now_time, jd, wd])
            params = {
                "request_type": "get_point_result",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "jd": jd, "wd": wd, "request_type": "get_point_result"}
            )
            
        except Exception as e:
            logger.error(f"查询某点结果失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_point_result"}
            )


class GetZpResultTool(BaseTool):
    """获取方案某类结果的顺河道纵剖面数据工具"""
    
    @property
    def name(self) -> str:
        return "get_zp_result"
    
    @property
    def description(self) -> str:
        return "获取方案某类结果的顺河道纵剖面数据，用于前端页面纵剖图绘制"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="res_type",
                type="string",
                description="结果数据类型: 'swzd_result'(水位纵断), 'qzd_result'(流量纵断), 'vzd_result'(流速纵断)",
                required=True,
                enum=["swzd_result", "qzd_result", "vzd_result"]
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取纵剖面数据"""
        plan_code = kwargs.get('plan_code')
        res_type = kwargs.get('res_type')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, res_type])
            params = {
                "request_type": "get_zp_result",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "res_type": res_type, "request_type": "get_zp_result"}
            )
            
        except Exception as e:
            logger.error(f"获取纵剖面数据失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_zp_result"}
            )


class GetReachsectionsTool(BaseTool):
    """获取方案有水位结果的河道断面桩号清单工具"""
    
    @property
    def name(self) -> str:
        return "get_reachsections"
    
    @property
    def description(self) -> str:
        return "获取方案有水位结果的河道断面桩号清单，包括各河道基本信息和各河道有水位结果的断面桩号"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取河道断面桩号清单"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_reachsections",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_reachsections"}
            )
            
        except Exception as e:
            logger.error(f"获取河道断面桩号清单失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_reachsections"}
            )


class GetSectionresTool(BaseTool):
    """获取方案单一河道断面的水位流量过程工具"""
    
    @property
    def name(self) -> str:
        return "get_sectionres"
    
    @property
    def description(self) -> str:
        return "获取方案单一河道断面的水位流量过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="reach_name",
                type="string",
                description="河道名称(编码)",
                required=True
            ),
            ToolParameter(
                name="chainage",
                type="number",
                description="断面桩号",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取单一断面水位流量过程"""
        plan_code = kwargs.get('plan_code')
        reach_name = kwargs.get('reach_name')
        chainage = kwargs.get('chainage')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, reach_name, chainage])
            params = {
                "request_type": "get_sectionres",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "reach_name": reach_name, "chainage": chainage, "request_type": "get_sectionres"}
            )
            
        except Exception as e:
            logger.error(f"获取单一断面水位流量过程失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_sectionres"}
            )


class GetSectionlistResTool(BaseTool):
    """获取方案多个河道断面的水位流量过程工具"""
    
    @property
    def name(self) -> str:
        return "get_sectionlist_res"
    
    @property
    def description(self) -> str:
        return "获取方案多个河道断面的水位流量过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="sections",
                type="array",
                description="断面数组，格式为[{'reach':'河道编码1','chainages':[桩号1,桩号2]},{'reach':'河道编码2','chainages':[桩号1]}]",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取多断面水位流量过程"""
        plan_code = kwargs.get('plan_code')
        sections = kwargs.get('sections')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, sections])
            params = {
                "request_type": "get_sectionlist_res",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_sectionlist_res"}
            )
            
        except Exception as e:
            logger.error(f"获取多断面水位流量过程失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_sectionlist_res"}
            )


class GetCatchmentDischargesTool(BaseTool):
    """获取方案多个子流域的产汇流模型流量过程工具"""
    
    @property
    def name(self) -> str:
        return "get_catchment_discharges"
    
    @property
    def description(self) -> str:
        return "获取方案多个子流域的产汇流模型流量过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="sub_catchment_q",
                type="object",
                description="子流域属性对象，属性和值均为子流域编码，如{'jyh_czyx':'jyh_czyx','jlh_jgsk':'jlh_jgsk'}",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取子流域流量过程"""
        plan_code = kwargs.get('plan_code')
        sub_catchment_q = kwargs.get('sub_catchment_q')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, sub_catchment_q])
            params = {
                "request_type": "get_catchment_discharges",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_catchment_discharges"}
            )
            
        except Exception as e:
            logger.error(f"获取子流域流量过程失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_catchment_discharges"}
            )


class GetGateresTool(BaseTool):
    """获取方案某闸门的水力要素结果工具"""
    
    @property
    def name(self) -> str:
        return "get_gateres"
    
    @property
    def description(self) -> str:
        return "获取方案某闸门的水力要素结果，包括过闸流量、上下游水位过程、流速过程、水头差等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID",
                required=True
            ),
            ToolParameter(
                name="gate_name",
                type="string",
                description="闸门编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取闸门水力要素结果"""
        plan_code = kwargs.get('plan_code')
        gate_name = kwargs.get('gate_name')
        
        try:
            url = MODEL_SERVER_URL
            request_pars = json.dumps([plan_code, gate_name])
            params = {
                "request_type": "get_gateres",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "gate_name": gate_name, "request_type": "get_gateres"}
            )
            
        except Exception as e:
            logger.error(f"获取闸门水力要素结果失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_gateres"}
            )


class GetAtreachTool(BaseTool):
    """根据方案ID获取该方案的特殊河道断面信息工具"""
    
    @property
    def name(self) -> str:
        return "get_atreach"
    
    @property
    def description(self) -> str:
        return "根据方案ID获取该方案的特殊河道断面信息，包括河道ID和桩号"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取特殊河道断面信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_atreach",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_atreach"}
            )
            
        except Exception as e:
            logger.error(f"获取特殊河道断面信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_atreach"}
            )


class GetRiskWarningTool(BaseTool):
    """获取方案的风险预警信息工具"""
    
    @property
    def name(self) -> str:
        return "get_risk_warning"
    
    @property
    def description(self) -> str:
        return "获取方案的风险预警信息，包含水库风险预警、河道风险预警、蓄滞洪区进洪风险预警、降雨预警、南水北调交叉断面风险预警、山洪风险预警"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取风险预警信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_risk_warning",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_risk_warning"}
            )
            
        except Exception as e:
            logger.error(f"获取风险预警信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_risk_warning"}
            )


class GetHistoryAutoforcastListTool(BaseTool):
    """获取历史洪水自动预报方案信息清单工具"""
    
    @property
    def name(self) -> str:
        return "get_history_autoforcast_list"
    
    @property
    def description(self) -> str:
        return "获取历史洪水自动预报方案信息清单，包含方案ID、预报起止时间和本场次降雨总降雨量"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """无需输入参数"""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取历史自动预报方案清单"""
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_history_autoforcast_list",
                "request_pars": ""
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"request_type": "get_history_autoforcast_list"}
            )
            
        except Exception as e:
            logger.error(f"获取历史自动预报方案清单失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"request_type": "get_history_autoforcast_list"}
            )


class DelHistoryAutoforcastTool(BaseTool):
    """删除某场历史自动预报方案工具"""
    
    @property
    def name(self) -> str:
        return "del_history_autoforcast"
    
    @property
    def description(self) -> str:
        return "删除某场历史自动预报方案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="history_plan_id",
                type="string",
                description="历史预报方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行删除历史自动预报方案"""
        history_plan_id = kwargs.get('history_plan_id')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "del_history_autoforcast",
                "request_pars": history_plan_id
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"history_plan_id": history_plan_id, "request_type": "del_history_autoforcast"}
            )
            
        except Exception as e:
            logger.error(f"删除历史自动预报方案失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"history_plan_id": history_plan_id, "request_type": "del_history_autoforcast"}
            )


class GetRainFloodListTool(BaseTool):
    """获取预演场次洪水信息列表工具"""
    
    @property
    def name(self) -> str:
        return "get_rain_flood_list"
    
    @property
    def description(self) -> str:
        return "获取预演场次洪水信息列表，所有预演方案均关联有一场场次洪水，一场场次洪水可能对应多个预演方案，但只有一个推荐方案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """无需输入参数"""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取场次洪水信息列表"""
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_rain_flood_list",
                "request_pars": ""
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"request_type": "get_rain_flood_list"}
            )
            
        except Exception as e:
            logger.error(f"获取场次洪水信息列表失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"request_type": "get_rain_flood_list"}
            )


class GetRainfloodPlanListTool(BaseTool):
    """获取某场次洪水的预演方案清单工具"""
    
    @property
    def name(self) -> str:
        return "get_rainflood_plan_list"
    
    @property
    def description(self) -> str:
        return "获取某场次洪水的预演方案清单，包含方案名称、描述、业务模型、起止时间、状态等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="flood_id",
                type="string",
                description="场次洪水ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取场次洪水的预演方案清单"""
        flood_id = kwargs.get('flood_id')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_rainflood_plan_list",
                "request_pars": flood_id
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"flood_id": flood_id, "request_type": "get_rainflood_plan_list"}
            )
            
        except Exception as e:
            logger.error(f"获取场次洪水的预演方案清单失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"flood_id": flood_id, "request_type": "get_rainflood_plan_list"}
            )


class ChangeRainfloodRecomplanTool(BaseTool):
    """修改某场次洪水的推荐预演方案工具"""
    
    @property
    def name(self) -> str:
        return "change_rainflood_recomplan"
    
    @property
    def description(self) -> str:
        return "修改某场次洪水的推荐预演方案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行修改场次洪水的推荐预演方案"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "change_rainflood_recomplan",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "change_rainflood_recomplan"}
            )
            
        except Exception as e:
            logger.error(f"修改场次洪水的推荐预演方案失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "change_rainflood_recomplan"}
            )


class ImportantInspectTool(BaseTool):
    """获取预演方案的工程重点巡查区域信息工具"""
    
    @property
    def name(self) -> str:
        return "important_inspect"
    
    @property
    def description(self) -> str:
        return "获取预演方案的工程重点巡查区域信息，即通过方案预演后得到的工程风险区域作为重点巡查区域，包含水库、河道、蓄滞洪区的巡查信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取工程重点巡查区域信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "important_inspect",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "important_inspect"}
            )
            
        except Exception as e:
            logger.error(f"获取工程重点巡查区域信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "important_inspect"}
            )


class GetHistoryAutoforcastResTool(BaseTool):
    """获取历史洪水自动预报结果工具"""
    
    @property
    def name(self) -> str:
        return "get_history_autoforcast_res"
    
    @property
    def description(self) -> str:
        return "获取历史洪水自动预报结果，结果与get_tjdata_result接口返回结果相同"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="history_plan_id",
                type="string",
                description="历史预报ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取历史洪水自动预报结果"""
        history_plan_id = kwargs.get('history_plan_id')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_history_autoforcast_res",
                "request_pars": history_plan_id
            }
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"history_plan_id": history_plan_id, "request_type": "get_history_autoforcast_res"}
            )
            
        except Exception as e:
            logger.error(f"获取历史洪水自动预报结果失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"history_plan_id": history_plan_id, "request_type": "get_history_autoforcast_res"}
            )


class GetMountainForecastFloodTool(BaseTool):
    """获取山区预报信息工具"""
    
    @property
    def name(self) -> str:
        return "get_mountain_forecast_flood"
    
    @property
    def description(self) -> str:
        return "获取山区预报信息，包括山洪区域名称、村庄名称、经纬度、被淹时间、风险等级等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案ID字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取山区预报信息"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_mountain_forecast_flood",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_mountain_forecast_flood"}
            )
            
        except Exception as e:
            logger.error(f"获取山区预报信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_mountain_forecast_flood"}
            )


# 注册所有工具
def register_hydromodel_resultget_tools():
    """注册水利专业模型-获取专业模型方案及结果数据相关工具"""
    register_tool(GetModelsTool())                      # 1. get_models - 获取所有模型方案信息
    register_tool(GetDispatchPlanTool())                # 2. get_dispatch_plan - 获取调度指令
    register_tool(GetTjdataResultTool())                # 3. get_tjdata_result - 获取方案结果数据
    register_tool(GetGisgcPolygonResultTool())          # 4. get_gisgc_polygon_result - 获取GIS面要素结果
    register_tool(GetSamplelineDataResultTool())        # 5. get_sampleline_data_result - 获取GIS过程线属性结果
    register_tool(GetGistjResultTool())                 # 6. get_gistj_result - 获取GIS统计线结果
    register_tool(GetGistjPolygonResultTool())          # 7. get_gistj_polygon_result - 获取GIS统计面结果
    register_tool(GetPointResultTool())                 # 8. get_point_result - 查询某点结果
    register_tool(GetZpResultTool())                    # 9. get_zp_result - 获取纵剖面数据
    register_tool(GetReachsectionsTool())               # 10. get_reachsections - 获取河道断面桩号清单
    register_tool(GetSectionresTool())                  # 11. get_sectionres - 获取单一断面水位流量过程
    register_tool(GetSectionlistResTool())              # 12. get_sectionlist_res - 获取多断面水位流量过程
    register_tool(GetCatchmentDischargesTool())         # 13. get_catchment_discharges - 获取子流域流量过程
    register_tool(GetGateresTool())                     # 14. get_gateres - 获取闸门水力要素结果
    register_tool(GetAtreachTool())                     # 15. get_atreach - 获取特殊河道断面信息
    register_tool(GetRiskWarningTool())                 # 16. get_risk_warning - 获取风险预警信息
    register_tool(GetHistoryAutoforcastListTool())      # 17. get_history_autoforcast_list - 获取历史自动预报清单
    register_tool(DelHistoryAutoforcastTool())          # 18. del_history_autoforcast - 删除历史自动预报方案
    register_tool(GetRainFloodListTool())               # 19. get_rain_flood_list - 获取场次洪水信息列表
    register_tool(GetRainfloodPlanListTool())           # 20. get_rainflood_plan_list - 获取场次洪水预演方案清单
    register_tool(ChangeRainfloodRecomplanTool())       # 21. change_rainflood_recomplan - 修改推荐预演方案
    register_tool(ImportantInspectTool())               # 22. important_inspect - 获取工程重点巡查区域信息
    register_tool(GetHistoryAutoforcastResTool())       # 23. get_history_autoforcast_res - 获取历史自动预报结果
    register_tool(GetMountainForecastFloodTool())       # 24. get_mountain_forecast_flood - 获取山区预报信息
    logger.info("水利专业模型-获取专业模型方案及结果数据相关工具注册完成，共24个接口")


# 模块加载时自动注册
register_hydromodel_resultget_tools()
