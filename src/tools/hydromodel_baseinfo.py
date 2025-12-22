"""
水利专业模型-获取与专业模型相关的基础信息工具
提供GIS样板线、河道信息、闸站状态、断面数据、站点信息、调度规则、水情信息、设计洪水、南水北调断面信息、三维场景相机姿态等基础信息的获取功能
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


class GetSamplelineTool(BaseTool):
    """获取GIS样板线工具"""
    
    @property
    def name(self) -> str:
        return "get_sampleline"
    
    @property
    def description(self) -> str:
        return "获取GIS样板线，为geojson格式的河道分段线要素，用于在地图区分色动态渲染过程结果，如流量、流速等"
    
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
        """执行获取GIS样板线"""
        plan_code = kwargs.get('plan_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_sampleline",
                "request_pars": plan_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_sampleline"}
            )
            
        except Exception as e:
            logger.error(f"获取GIS样板线失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_sampleline"}
            )


class GetReachInfoTool(BaseTool):
    """获取河道基本信息工具"""
    
    @property
    def name(self) -> str:
        return "get_reachinfo"
    
    @property
    def description(self) -> str:
        return "获取河道基本信息，包括河道名称、编码、起止桩号及长度等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="model_instance",
                type="string",
                description="模型实例名称字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取河道基本信息"""
        model_instance = kwargs.get('model_instance')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_reachinfo",
                "request_pars": model_instance
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"model_instance": model_instance, "request_type": "get_reachinfo"}
            )
            
        except Exception as e:
            logger.error(f"获取河道基本信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"model_instance": model_instance, "request_type": "get_reachinfo"}
            )


class GetGateStateTool(BaseTool):
    """获取全流域闸站建筑最新状态监测信息工具"""
    
    @property
    def name(self) -> str:
        return "get_gatestate"
    
    @property
    def description(self) -> str:
        return "获取全流域里各闸站建筑最新状态监测信息，包括闸门状态、开孔数、开度、更新时间"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="business_code",
                type="string",
                description="业务编码字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取闸站状态"""
        business_code = kwargs.get('business_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_gatestate",
                "request_pars": business_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"business_code": business_code, "request_type": "get_gatestate"}
            )
            
        except Exception as e:
            logger.error(f"获取闸站状态失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"business_code": business_code, "request_type": "get_gatestate"}
            )


class GetSectionDataTool(BaseTool):
    """根据断面STCD和桩号获取河道断面原始测量数据工具"""
    
    @property
    def name(self) -> str:
        return "get_sectiondata"
    
    @property
    def description(self) -> str:
        return "根据断面STCD和桩号，获取河道断面原始测量数据。当断面为水文站点或闸站时，第1个参数为该站点STCD，第2个为空字符串；否则第1个参数为河道编码，第2个为桩号"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd_or_reach_code",
                type="string",
                description="站点STCD(如'31004300')或河道编码(如'GQ')",
                required=True
            ),
            ToolParameter(
                name="chainage",
                type="string",
                description="桩号。当第1个参数为站点STCD时，填空字符串''；否则填具体桩号值(如'155000')",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取河道断面数据"""
        stcd_or_reach_code = kwargs.get('stcd_or_reach_code')
        chainage = kwargs.get('chainage', '')
        
        try:
            url = MODEL_SERVER_URL
            # 构建JSON数组格式参数
            request_pars = json.dumps([stcd_or_reach_code, chainage])
            params = {
                "request_type": "get_sectiondata",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"stcd_or_reach_code": stcd_or_reach_code, "chainage": chainage, "request_type": "get_sectiondata"}
            )
            
        except Exception as e:
            logger.error(f"获取河道断面数据失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"stcd_or_reach_code": stcd_or_reach_code, "request_type": "get_sectiondata"}
            )


class GetSectionDataFromPointTool(BaseTool):
    """根据坐标点获取河道断面原始测量数据工具"""
    
    @property
    def name(self) -> str:
        return "get_sectiondata_frompoint"
    
    @property
    def description(self) -> str:
        return "根据坐标点，获取河道断面原始测量数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="longitude",
                type="string",
                description="经度，如'114.15169'",
                required=True
            ),
            ToolParameter(
                name="latitude",
                type="string",
                description="纬度，如'35.483368'",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行根据坐标点获取断面数据"""
        longitude = kwargs.get('longitude')
        latitude = kwargs.get('latitude')
        
        try:
            url = MODEL_SERVER_URL
            # 构建JSON数组格式参数
            request_pars = json.dumps([longitude, latitude])
            params = {
                "request_type": "get_sectiondata_frompoint",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"longitude": longitude, "latitude": latitude, "request_type": "get_sectiondata_frompoint"}
            )
            
        except Exception as e:
            logger.error(f"根据坐标点获取断面数据失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"longitude": longitude, "latitude": latitude, "request_type": "get_sectiondata_frompoint"}
            )


class GetReachSectionLocationTool(BaseTool):
    """根据河道断面桩号获取经纬度坐标位置信息工具"""
    
    @property
    def name(self) -> str:
        return "get_reachsection_location"
    
    @property
    def description(self) -> str:
        return "根据河道断面桩号，获取该河道断面中心点的经纬度坐标位置信息"
    
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
                name="section_location",
                type="array",
                description="断面位置信息数组，格式如[[\"GQ\",53263],[\"GQ\",43263],[\"WH\",13263]]，包含河道编码和桩号",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取河道断面中心点坐标"""
        plan_code = kwargs.get('plan_code')
        section_location = kwargs.get('section_location')
        
        try:
            url = MODEL_SERVER_URL
            # 构建JSON数组格式参数
            request_pars = json.dumps([plan_code, section_location])
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    data={
                        "request_type": "get_reachsection_location",
                        "request_pars": request_pars
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"plan_code": plan_code, "request_type": "get_reachsection_location"}
            )
            
        except Exception as e:
            logger.error(f"获取河道断面中心点坐标失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"plan_code": plan_code, "request_type": "get_reachsection_location"}
            )


class GetStationInfoTool(BaseTool):
    """获取水库、水文站点、闸站基本信息和监测水情信息工具"""
    
    @property
    def name(self) -> str:
        return "get_station_info"
    
    @property
    def description(self) -> str:
        return "获取河道上各大中型水库、河道水文站点、河道控制闸站的基本信息和监测水情信息，包括站点stcd、所在河道和桩号、控制流域面积、水位流量等监测水情信息等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """无需输入参数"""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取站点信息"""
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_station_info",
                "request_pars": ""
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"request_type": "get_station_info"}
            )
            
        except Exception as e:
            logger.error(f"获取站点信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"request_type": "get_station_info"}
            )


class GetStrddruleInfoTool(BaseTool):
    """获取洪水控制建筑调度规则信息工具"""
    
    @property
    def name(self) -> str:
        return "get_strddrule_info"
    
    @property
    def description(self) -> str:
        return "获取水库、河道闸站等所有洪水控制建筑的规则调度信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="business_code",
                type="string",
                description="业务编码字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取调度规则信息"""
        business_code = kwargs.get('business_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_strddrule_info",
                "request_pars": business_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"business_code": business_code, "request_type": "get_strddrule_info"}
            )
            
        except Exception as e:
            logger.error(f"获取调度规则信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"business_code": business_code, "request_type": "get_strddrule_info"}
            )


class GetControlStrsTool(BaseTool):
    """获取关联的洪水控制建筑物工具"""
    
    @property
    def name(self) -> str:
        return "get_control_strs"
    
    @property
    def description(self) -> str:
        return "根据业务编码和站点STCD获取关联的洪水控制建筑物，如水库的各个溢流堰和泄洪洞，蓄滞洪区的各个进洪分洪闸堰"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="business_code",
                type="string",
                description="业务编码",
                required=True
            ),
            ToolParameter(
                name="obj_stcd",
                type="string",
                description="对象站点编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取关联的洪水控制建筑物"""
        business_code = kwargs.get('business_code')
        obj_stcd = kwargs.get('obj_stcd')
        
        try:
            url = MODEL_SERVER_URL
            # 构建JSON数组格式参数
            request_pars = json.dumps([business_code, obj_stcd])
            params = {
                "request_type": "get_control_strs",
                "request_pars": request_pars
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"business_code": business_code, "obj_stcd": obj_stcd, "request_type": "get_control_strs"}
            )
            
        except Exception as e:
            logger.error(f"获取关联的洪水控制建筑物失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"business_code": business_code, "obj_stcd": obj_stcd, "request_type": "get_control_strs"}
            )


class GetNowWaterinfoTool(BaseTool):
    """获取当前最新水情信息工具"""
    
    @property
    def name(self) -> str:
        return "get_now_waterinfo"
    
    @property
    def description(self) -> str:
        return "获取所有水库、河道闸站、水文站点当前最新水情信息。如果业务编码字符串为空字符串，则获取所有水库闸站和水文站点的当前水情，否则是业务模型相关的"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="business_code",
                type="string",
                description="业务编码字符串，可为空字符串",
                required=False,
                default=""
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取当前最新水情信息"""
        business_code = kwargs.get('business_code', '')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_now_waterinfo",
                "request_pars": business_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"business_code": business_code, "request_type": "get_now_waterinfo"}
            )
            
        except Exception as e:
            logger.error(f"获取当前最新水情信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"business_code": business_code, "request_type": "get_now_waterinfo"}
            )


class GetDesignFloodTool(BaseTool):
    """获取不同量级设计洪水过程工具"""
    
    @property
    def name(self) -> str:
        return "get_design_flood"
    
    @property
    def description(self) -> str:
        return "获取和业务模型相关的各河道不同量级设计洪水过程，如50年一遇设计洪水过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="business_code",
                type="string",
                description="业务编码字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取设计洪水信息"""
        business_code = kwargs.get('business_code')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_design_flood",
                "request_pars": business_code
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"business_code": business_code, "request_type": "get_design_flood"}
            )
            
        except Exception as e:
            logger.error(f"获取设计洪水信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"business_code": business_code, "request_type": "get_design_flood"}
            )


class GetNsbdSectionInfoTool(BaseTool):
    """获取南水北调交叉断面信息工具"""
    
    @property
    def name(self) -> str:
        return "get_nsbd_sectioninfo"
    
    @property
    def description(self) -> str:
        return "获取流域范围内，各河道与南水北调交叉断面的基本信息，包括交叉断面位置、设计水位、设计流量、校核流量、堤顶高程等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """无需输入参数"""
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取南水北调交叉断面信息"""
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_nsbd_sectioninfo",
                "request_pars": ""
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"request_type": "get_nsbd_sectioninfo"}
            )
            
        except Exception as e:
            logger.error(f"获取南水北调交叉断面信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"request_type": "get_nsbd_sectioninfo"}
            )


class GetBusinessViewTool(BaseTool):
    """获取业务模型的三维场景相机姿态信息工具"""
    
    @property
    def name(self) -> str:
        return "get_business_view"
    
    @property
    def description(self) -> str:
        return "获取业务模型的默认初始三维场景相机姿态信息，包括相机位置坐标、朝向和俯仰角"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MODEL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="business_model",
                type="string",
                description="业务模型字符串",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取三维场景相机姿态信息"""
        business_model = kwargs.get('business_model')
        
        try:
            url = MODEL_SERVER_URL
            params = {
                "request_type": "get_business_view",
                "request_pars": business_model
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data,
                metadata={"business_model": business_model, "request_type": "get_business_view"}
            )
            
        except Exception as e:
            logger.error(f"获取三维场景相机姿态信息失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                metadata={"business_model": business_model, "request_type": "get_business_view"}
            )


# 注册所有工具
def register_hydromodel_baseinfo_tools():
    """注册水利专业模型-获取与专业模型相关的基础信息工具"""
    register_tool(GetSamplelineTool())              # 1. get_sampleline - 获取GIS样板线
    register_tool(GetReachInfoTool())               # 2. get_reachinfo - 获取河道基本信息
    register_tool(GetGateStateTool())               # 3. get_gatestate - 获取闸站建筑最新状态
    register_tool(GetSectionDataTool())             # 4. get_sectiondata - 根据断面STCD和桩号获取断面数据
    register_tool(GetSectionDataFromPointTool())    # 5. get_sectiondata_frompoint - 根据坐标点获取断面数据
    register_tool(GetReachSectionLocationTool())    # 6. get_reachsection_location - 获取河道断面中心点坐标
    register_tool(GetStationInfoTool())             # 7. get_station_info - 获取站点基本信息和水情
    register_tool(GetStrddruleInfoTool())           # 8. get_strddrule_info - 获取调度规则信息
    register_tool(GetControlStrsTool())             # 9. get_control_strs - 获取关联的洪水控制建筑物
    register_tool(GetNowWaterinfoTool())            # 10. get_now_waterinfo - 获取当前最新水情信息
    register_tool(GetDesignFloodTool())             # 11. get_design_flood - 获取设计洪水过程
    register_tool(GetNsbdSectionInfoTool())         # 12. get_nsbd_sectioninfo - 获取南水北调交叉断面信息
    register_tool(GetBusinessViewTool())            # 13. get_business_view - 获取三维场景相机姿态
    logger.info("水利专业模型-获取与专业模型相关的基础信息工具注册完成，共13个接口")


# 模块加载时自动注册
register_hydromodel_baseinfo_tools()
