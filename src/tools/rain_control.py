"""
降雨相关业务工具
提供降雨预报、降雨等值面、降雨监测、设计暴雨雨型、典型暴雨、方案降雨查询与设置等功能
基于防洪业务接口-降雨相关业务文档实现，接口基础地址：http://10.20.2.153/api/basin
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool
from .auth import LoginTool

logger = get_logger(__name__)

# 从配置获取防洪业务API基础地址
RAIN_CONTROL_BASE_URL = settings.wg_flood_server_url


# =============================================================================
# 一、降雨预报接口（5个）
# =============================================================================

class ForecastRainEcmwfAvgTool(BaseTool):
    """获取流域平均的格网预报降雨过程工具"""
    
    @property
    def name(self) -> str:
        return "forecast_rain_ecmwf_avg"
    
    @property
    def description(self) -> str:
        return "获取流域平均的格网预报降雨过程(无需登录)，返回时序降雨数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间，格式: yyyy-MM-dd HH:mm:ss", required=True),
            ToolParameter(name="ed", type="string", description="结束时间，格式: yyyy-MM-dd HH:mm:ss", required=True),
            ToolParameter(name="business_code", type="string", description="业务模型编码", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取流域平均格网预报降雨"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/forecast/forecastRainEcmwf/avg"
            params = {"st": kwargs.get("st"), "ed": kwargs.get("ed")}
            if kwargs.get("business_code"):
                params["businessCode"] = kwargs.get("business_code")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取流域平均格网预报降雨失败: {e}")
            return ToolResult(success=False, error=str(e))


class ForecastRainEcmwfEachTool(BaseTool):
    """获取各子流域的格网预报降雨过程工具"""
    
    @property
    def name(self) -> str:
        return "forecast_rain_ecmwf_each"
    
    @property
    def description(self) -> str:
        return "获取各子流域的格网预报降雨过程，返回按子流域编码分组的降雨时序数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间，格式: yyyy-MM-dd HH:mm:ss", required=True),
            ToolParameter(name="ed", type="string", description="结束时间，格式: yyyy-MM-dd HH:mm:ss", required=True),
            ToolParameter(name="business_code", type="string", description="业务模型编码", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取各子流域格网预报降雨"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/forecast/forecastRainEcmwf/each"
            params = {"st": kwargs.get("st"), "ed": kwargs.get("ed")}
            if kwargs.get("business_code"):
                params["businessCode"] = kwargs.get("business_code")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取各子流域格网预报降雨失败: {e}")
            return ToolResult(success=False, error=str(e))


class ForecastRainEcmwfRectTool(BaseTool):
    """获取矩形区域内的格网预报降雨过程工具"""
    
    @property
    def name(self) -> str:
        return "forecast_rain_ecmwf_rect"
    
    @property
    def description(self) -> str:
        return "获取矩形区域内的格网预报降雨过程，通过经纬度范围指定区域"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间", required=True),
            ToolParameter(name="ed", type="string", description="结束时间", required=True),
            ToolParameter(name="xmin", type="float", description="矩形左边界经度", required=True),
            ToolParameter(name="xmax", type="float", description="矩形右边界经度", required=True),
            ToolParameter(name="ymin", type="float", description="矩形下边界纬度", required=True),
            ToolParameter(name="ymax", type="float", description="矩形上边界纬度", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取矩形区域格网预报降雨"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/forecast/forecastRainEcmwf/rect"
            params = {
                "st": kwargs.get("st"), "ed": kwargs.get("ed"),
                "xmin": kwargs.get("xmin"), "xmax": kwargs.get("xmax"),
                "ymin": kwargs.get("ymin"), "ymax": kwargs.get("ymax")
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取矩形区域格网预报降雨失败: {e}")
            return ToolResult(success=False, error=str(e))


class ForecastRainEcmwfStcTool(BaseTool):
    """获取指定时段的ECMWF降雨分区统计信息工具"""
    
    @property
    def name(self) -> str:
        return "forecast_rain_ecmwf_stc"
    
    @property
    def description(self) -> str:
        return "获取指定时段的ECMWF降雨分区统计信息，包括各子流域累计、平均、最大降雨量"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间，默认当前时间", required=False),
            ToolParameter(name="ed", type="string", description="结束时间，默认开始时间后24小时", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取ECMWF降雨分区统计"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/forecast/forecastRainEcmwf/stc"
            params = {}
            if kwargs.get("st"):
                params["st"] = kwargs.get("st")
            if kwargs.get("ed"):
                params["ed"] = kwargs.get("ed")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取ECMWF降雨分区统计失败: {e}")
            return ToolResult(success=False, error=str(e))


class ForecastRainEcmwfAccTool(BaseTool):
    """获取所有格网点指定时段的ECMWF累计降雨工具"""
    
    @property
    def name(self) -> str:
        return "forecast_rain_ecmwf_acc"
    
    @property
    def description(self) -> str:
        return "获取所有格网点指定时段的ECMWF累计降雨，返回经纬度和累计降雨值"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间", required=True),
            ToolParameter(name="ed", type="string", description="结束时间", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取ECMWF累计降雨"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/forecast/forecastRainEcmwf/acc"
            params = {"st": kwargs.get("st"), "ed": kwargs.get("ed")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取ECMWF累计降雨失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 二、降雨等值面接口（7个）
# =============================================================================

class ContourRainTodayTool(BaseTool):
    """获取8点以后降雨等值面工具"""
    
    @property
    def name(self) -> str:
        return "contour_rain_today"
    
    @property
    def description(self) -> str:
        return "获取8点以后降雨等值面，返回GeoJSON格式的等值面数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="t", type="string", description="时间，默认当前时间，格式: yyyy-MM-dd HH:mm:ss", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取当日降雨等值面"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/contour/rainProc/today"
            params = {}
            if kwargs.get("t"):
                params["t"] = kwargs.get("t")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取当日降雨等值面失败: {e}")
            return ToolResult(success=False, error=str(e))


class ContourRainAnyTool(BaseTool):
    """生成/获取任意时段累计降雨等值面工具"""
    
    @property
    def name(self) -> str:
        return "contour_rain_any"
    
    @property
    def description(self) -> str:
        return "生成/获取任意时段累计降雨等值面"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间", required=True),
            ToolParameter(name="ed", type="string", description="结束时间", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取任意时段累计降雨等值面"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/contour/rainProc/any"
            params = {"st": kwargs.get("st"), "ed": kwargs.get("ed")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取任意时段累计降雨等值面失败: {e}")
            return ToolResult(success=False, error=str(e))


class ContourRainPlanTool(BaseTool):
    """生成/获取方案累计降雨等值面工具"""
    
    @property
    def name(self) -> str:
        return "contour_rain_plan"
    
    @property
    def description(self) -> str:
        return "生成/获取方案累计降雨等值面"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取方案累计降雨等值面"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/contour/rainProc/plan"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取方案累计降雨等值面失败: {e}")
            return ToolResult(success=False, error=str(e))


class ContourRainProcTool(BaseTool):
    """获取逐小时降雨等值面过程工具"""
    
    @property
    def name(self) -> str:
        return "contour_rain_proc"
    
    @property
    def description(self) -> str:
        return "获取逐小时降雨等值面过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="t", type="string", description="时间，默认当前时间", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取逐小时降雨等值面过程"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/contour/rainProc/proc"
            params = {}
            if kwargs.get("t"):
                params["t"] = kwargs.get("t")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取逐小时降雨等值面过程失败: {e}")
            return ToolResult(success=False, error=str(e))


class ContourRainAccTool(BaseTool):
    """获取不同时段累计降雨等值面工具"""
    
    @property
    def name(self) -> str:
        return "contour_rain_acc"
    
    @property
    def description(self) -> str:
        return "获取不同时段累计降雨等值面，interval负数表示历史，正数表示未来"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="t", type="string", description="时间，默认当前时间", required=False),
            ToolParameter(name="interval", type="integer", description="时段间隔(小时)，可选值: -1/-12/-24/-48/-72/1/12/24/48/72", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取不同时段累计降雨等值面"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/contour/rainProc/acc"
            params = {"interval": kwargs.get("interval")}
            if kwargs.get("t"):
                params["t"] = kwargs.get("t")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取不同时段累计降雨等值面失败: {e}")
            return ToolResult(success=False, error=str(e))


class ContourRainFutureImgTool(BaseTool):
    """获取未来降雨等值面图片工具"""
    
    @property
    def name(self) -> str:
        return "contour_rain_future_img"
    
    @property
    def description(self) -> str:
        return "获取未来24/48/72小时降雨等值面图片(Base64格式)"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="ind", type="integer", description="时段索引: 0=24小时, 1=48小时, 2=72小时", required=True),
            ToolParameter(name="time", type="string", description="时间，默认当前时间", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取未来降雨等值面图片"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/contour/rainProc/futureimg"
            params = {"ind": kwargs.get("ind")}
            if kwargs.get("time"):
                params["time"] = kwargs.get("time")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取未来降雨等值面图片失败: {e}")
            return ToolResult(success=False, error=str(e))


class ContourRainUpdateTool(BaseTool):
    """更新等值面工具"""
    
    @property
    def name(self) -> str:
        return "contour_rain_update"
    
    @property
    def description(self) -> str:
        return "更新等值面(无需登录)"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行更新等值面"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/contour/rainProc/update"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "等值面更新成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "更新失败"))
        except Exception as e:
            logger.error(f"更新等值面失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 注册所有工具（第一部分：降雨预报+等值面接口，共12个）
# =============================================================================

# 降雨预报接口（5个）
register_tool(ForecastRainEcmwfAvgTool())
register_tool(ForecastRainEcmwfEachTool())
register_tool(ForecastRainEcmwfRectTool())
register_tool(ForecastRainEcmwfStcTool())
register_tool(ForecastRainEcmwfAccTool())

# 降雨等值面接口（7个）
register_tool(ContourRainTodayTool())
register_tool(ContourRainAnyTool())
register_tool(ContourRainPlanTool())
register_tool(ContourRainProcTool())
register_tool(ContourRainAccTool())
register_tool(ContourRainFutureImgTool())
register_tool(ContourRainUpdateTool())


# =============================================================================
# 三、降雨监测接口（2个）
# =============================================================================

class MonitorRainAreaProcWholeTool(BaseTool):
    """获取指定时段流域整体面雨量过程工具"""
    
    @property
    def name(self) -> str:
        return "monitor_rain_area_proc_whole"
    
    @property
    def description(self) -> str:
        return "获取指定时段的流域整体面雨量过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间", required=True),
            ToolParameter(name="ed", type="string", description="结束时间", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取流域整体面雨量过程"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/monitor/monitorRainH/areaRainProcWhole"
            params = {"st": kwargs.get("st"), "ed": kwargs.get("ed")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取流域整体面雨量过程失败: {e}")
            return ToolResult(success=False, error=str(e))


class MonitorRainManualTool(BaseTool):
    """手动更新降水监测数据工具"""
    
    @property
    def name(self) -> str:
        return "monitor_rain_manual"
    
    @property
    def description(self) -> str:
        return "手动更新降水监测数据(无需登录)"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间", required=True),
            ToolParameter(name="ed", type="string", description="结束时间", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行手动更新降水监测数据"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/monitor/monitorRainH/manual"
            params = {"st": kwargs.get("st"), "ed": kwargs.get("ed")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "降水监测数据更新成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "更新失败"))
        except Exception as e:
            logger.error(f"手动更新降水监测数据失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 四、设计暴雨雨型管理接口（3个）
# =============================================================================

class ModelRainPatternListTool(BaseTool):
    """查询雨型列表工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_pattern_list"
    
    @property
    def description(self) -> str:
        return "查询设计雨型列表"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查询雨型列表"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainPattern/list"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"查询雨型列表失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainPatternAddTool(BaseTool):
    """新增雨型工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_pattern_add"
    
    @property
    def description(self) -> str:
        return "新增设计雨型"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="name", type="string", description="雨型名称", required=True),
            ToolParameter(name="type", type="string", description="雨型类型: 0=自定义雨型, 1=设计雨型", required=False),
            ToolParameter(name="json", type="string", description="雨型过程JSON", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行新增雨型"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainPattern/add"
            payload = {"name": kwargs.get("name"), "json": kwargs.get("json")}
            if kwargs.get("type"):
                payload["type"] = kwargs.get("type")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "雨型新增成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "新增失败"))
        except Exception as e:
            logger.error(f"新增雨型失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainPatternDetailTool(BaseTool):
    """查看雨型详情工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_pattern_detail"
    
    @property
    def description(self) -> str:
        return "查看设计雨型详情"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="id", type="integer", description="雨型ID", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查看雨型详情"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainPattern/detail"
            params = {"id": kwargs.get("id")}

            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()

            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"查看雨型详情失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 五、典型暴雨雨型管理接口（4个）
# =============================================================================

class ModelTypicalRainListTool(BaseTool):
    """分页查询典型暴雨列表工具"""
    
    @property
    def name(self) -> str:
        return "model_typical_rain_list"
    
    @property
    def description(self) -> str:
        return "分页查询典型暴雨列表"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="id", type="integer", description="暴雨ID", required=False),
            ToolParameter(name="name", type="string", description="暴雨名称", required=False),
            ToolParameter(name="page", type="integer", description="页码，默认1", required=False, default=1),
            ToolParameter(name="limit", type="integer", description="每页条数，默认10", required=False, default=10)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查询典型暴雨列表"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelTypicalRain/list"
            params = {"page": kwargs.get("page", 1), "limit": kwargs.get("limit", 10)}
            if kwargs.get("id"):
                params["id"] = kwargs.get("id")
            if kwargs.get("name"):
                params["name"] = kwargs.get("name")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(success=True, data=data)
        except Exception as e:
            logger.error(f"查询典型暴雨列表失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelTypicalRainAddTool(BaseTool):
    """新增典型暴雨工具"""
    
    @property
    def name(self) -> str:
        return "model_typical_rain_add"
    
    @property
    def description(self) -> str:
        return "新增典型暴雨"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="name", type="string", description="暴雨名称", required=True),
            ToolParameter(name="process", type="array", description="降雨过程数据", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行新增典型暴雨"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelTypicalRain/add"
            payload = {"name": kwargs.get("name"), "process": kwargs.get("process")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "典型暴雨新增成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "新增失败"))
        except Exception as e:
            logger.error(f"新增典型暴雨失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelTypicalRainDetailTool(BaseTool):
    """查看典型暴雨详情工具"""
    
    @property
    def name(self) -> str:
        return "model_typical_rain_detail"
    
    @property
    def description(self) -> str:
        return "查看典型暴雨详情"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="id", type="integer", description="暴雨ID", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查看典型暴雨详情"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelTypicalRain/detail"
            params = {"id": kwargs.get("id")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"查看典型暴雨详情失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelTypicalRainAddFromHistoryTool(BaseTool):
    """从历史数据新增典型暴雨工具"""
    
    @property
    def name(self) -> str:
        return "model_typical_rain_add_from_history"
    
    @property
    def description(self) -> str:
        return "从历史数据新增典型暴雨"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间", required=True),
            ToolParameter(name="ed", type="string", description="结束时间", required=True),
            ToolParameter(name="name", type="string", description="暴雨名称", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行从历史数据新增典型暴雨"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelTypicalRain/addFromHistory"
            params = {"st": kwargs.get("st"), "ed": kwargs.get("ed"), "name": kwargs.get("name")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "从历史数据新增典型暴雨成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "新增失败"))
        except Exception as e:
            logger.error(f"从历史数据新增典型暴雨失败: {e}")
            return ToolResult(success=False, error=str(e))


# 注册降雨监测接口（2个）
register_tool(MonitorRainAreaProcWholeTool())
register_tool(MonitorRainManualTool())

# 注册设计暴雨雨型管理接口（3个）
register_tool(ModelRainPatternListTool())
register_tool(ModelRainPatternAddTool())
register_tool(ModelRainPatternDetailTool())

# 注册典型暴雨雨型管理接口（4个）
register_tool(ModelTypicalRainListTool())
register_tool(ModelTypicalRainAddTool())
register_tool(ModelTypicalRainDetailTool())
register_tool(ModelTypicalRainAddFromHistoryTool())


# =============================================================================
# 六、方案降雨查询接口（7个）
# =============================================================================

class ModelRainAreaGetByPlanTool(BaseTool):
    """获取指定方案的各子流域降雨过程工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_get_by_plan"
    
    @property
    def description(self) -> str:
        return "获取指定方案的各子流域降雨过程(无需登录)，返回按子流域编码分组的降雨时序数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取指定方案的各子流域降雨过程"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/getByPlan"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取指定方案的各子流域降雨过程失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaGetBasinAreaRainStcTool(BaseTool):
    """获取方案全流域平均面雨量过程及统计值工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_get_basin_area_rain_stc"
    
    @property
    def description(self) -> str:
        return "获取指定方案的全流域平均面雨量过程及统计值(无需登录)，包括累计、最大降雨量和平均值"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取方案全流域平均面雨量过程及统计值"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/getBasinAreaRainStc"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取方案全流域平均面雨量过程及统计值失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaGetBasinAreaRainAccTool(BaseTool):
    """获取方案全流域平均面雨量过程及实时累计降雨工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_get_basin_area_rain_acc"
    
    @property
    def description(self) -> str:
        return "获取指定方案的全流域平均面雨量过程及实时累计降雨"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取方案全流域平均面雨量过程及实时累计降雨"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/getBasinAreaRainAcc"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取方案全流域平均面雨量过程及实时累计降雨失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaGetBasinListTool(BaseTool):
    """获取有降雨预报的流域清单工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_get_basin_list"
    
    @property
    def description(self) -> str:
        return "获取指定方案有降雨预报的流域清单"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取有降雨预报的流域清单"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/getBasinList"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取有降雨预报的流域清单失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaDetailTool(BaseTool):
    """获取指定方案、指定流域的降雨过程及统计工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_detail"
    
    @property
    def description(self) -> str:
        return "获取指定方案、指定流域的降雨过程及统计，包括累计、最大降雨量和时间"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True),
            ToolParameter(name="bsn_code", type="string", description="流域编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取指定方案、指定流域的降雨过程及统计"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/detail"
            params = {"planCode": kwargs.get("plan_code"), "bsnCode": kwargs.get("bsn_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取指定方案、指定流域的降雨过程及统计失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaGetByRsvrTool(BaseTool):
    """获取指定方案、指定水文站的上游流域降雨过程工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_get_by_rsvr"
    
    @property
    def description(self) -> str:
        return "获取指定方案、指定水文站的上游流域降雨过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True),
            ToolParameter(name="stcd", type="string", description="水文站编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取指定方案、指定水文站的上游流域降雨过程"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/getByRsvr"
            params = {"planCode": kwargs.get("plan_code"), "stcd": kwargs.get("stcd")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取指定方案、指定水文站的上游流域降雨过程失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaForecastRainStcTool(BaseTool):
    """获取自动预报方案的降雨态势工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_forecast_rain_stc"
    
    @property
    def description(self) -> str:
        return "获取自动预报方案的降雨态势，包括平均、最大降雨量和降雨等级"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="interval", type="integer", description="时段间隔(小时)", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取自动预报方案的降雨态势"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/forecastRainStc"
            params = {"interval": kwargs.get("interval")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取自动预报方案的降雨态势失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 七、方案降雨设置接口（5个）
# =============================================================================

class ModelRainAreaAddEcmwfTool(BaseTool):
    """根据格网预报设置方案降雨过程工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_add_ecmwf"
    
    @property
    def description(self) -> str:
        return "根据格网预报(ECMWF)设置方案降雨过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行根据格网预报设置方案降雨过程"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/add/ecmwf"
            params = {"planCode": kwargs.get("plan_code")}

            auth_headers = await LoginTool.get_auth_headers()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()

            if data.get("success"):
                return ToolResult(success=True, data={"message": "根据格网预报设置方案降雨过程成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "设置失败"))
        except Exception as e:
            logger.error(f"根据格网预报设置方案降雨过程失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaAddEcmwfTranslateTool(BaseTool):
    """根据格网预报设置方案降雨过程（可放大平移）工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_add_ecmwf_translate"
    
    @property
    def description(self) -> str:
        return "根据格网预报设置方案降雨过程(可放大平移)，支持设置放大倍数和经纬度偏移量"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True),
            ToolParameter(name="factor", type="float", description="放大倍数，默认1.0", required=False),
            ToolParameter(name="dlgtd", type="float", description="经度偏移量，默认0", required=False),
            ToolParameter(name="dlttd", type="float", description="纬度偏移量，默认0", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行根据格网预报设置方案降雨过程（可放大平移）"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/add/ecmwf/translate"
            payload = {"planCode": kwargs.get("plan_code")}
            # 添加可选参数
            if kwargs.get("factor") is not None:
                payload["factor"] = kwargs.get("factor")
            if kwargs.get("dlgtd") is not None:
                payload["dlgtd"] = kwargs.get("dlgtd")
            if kwargs.get("dlttd") is not None:
                payload["dlttd"] = kwargs.get("dlttd")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "根据格网预报设置方案降雨过程(可放大平移)成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "设置失败"))
        except Exception as e:
            logger.error(f"根据格网预报设置方案降雨过程(可放大平移)失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaAddManualTool(BaseTool):
    """手动设置方案降雨过程工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_add_manual"
    
    @property
    def description(self) -> str:
        return "手动设置方案降雨过程，通过JSON格式指定降水量时序数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True),
            ToolParameter(name="bsn_code", type="string", description="子流域编码(avg表示全流域平均)", required=False),
            ToolParameter(name="drp_json", type="string", description="降水量JSON字符串，格式如：{\"2025-12-16 08:00:00\":3.68,\"2025-12-16 09:00:00\":6.2}", required=True),
            ToolParameter(name="source", type="string", description="数据来源: 0=实测, 1=预报, 2=指定, 3=无降雨", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行手动设置方案降雨过程"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/add/manual"
            payload = {
                "planCode": kwargs.get("plan_code"),
                "drpJson": kwargs.get("drp_json")
            }
            # 添加可选参数
            if kwargs.get("bsn_code"):
                payload["bsnCode"] = kwargs.get("bsn_code")
            if kwargs.get("source"):
                payload["source"] = kwargs.get("source")

            logger.info(f"手动设置方案降雨请求: planCode={payload.get('planCode')}, bsnCode={payload.get('bsnCode')}, source={payload.get('source')}")

            auth_headers = await LoginTool.get_auth_headers()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload, headers=auth_headers)
                # 先获取响应内容，再检查状态码
                try:
                    data = response.json()
                except Exception:
                    data = {"raw_text": response.text[:500]}

                if response.status_code >= 400:
                    logger.error(f"手动设置方案降雨HTTP错误: status={response.status_code}, response={data}")
                    return ToolResult(success=False, error=f"HTTP {response.status_code}: {data}")

            if data.get("success"):
                logger.info("手动设置方案降雨过程成功")
                return ToolResult(success=True, data={"message": "手动设置方案降雨过程成功"})
            else:
                error_msg = data.get("message", "设置失败")
                logger.error(f"手动设置方案降雨业务失败: {error_msg}")
                return ToolResult(success=False, error=error_msg)
        except Exception as e:
            logger.error(f"手动设置方案降雨过程失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaAddManualCenterTool(BaseTool):
    """手动设置方案降雨过程（可设降雨中心）工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_add_manual_center"
    
    @property
    def description(self) -> str:
        return "手动设置方案降雨过程(可设降雨中心)，支持设置多个降雨中心区域"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True),
            ToolParameter(name="centers", type="array", description="降雨中心列表，每个中心需包含drpJson(降雨过程JSON)和polyWkt(面要素WKT格式)", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行手动设置方案降雨过程（可设降雨中心）"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/add/manual/center"
            payload = {
                "planCode": kwargs.get("plan_code"),
                "centers": kwargs.get("centers")
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "手动设置方案降雨过程(可设降雨中心)成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "设置失败"))
        except Exception as e:
            logger.error(f"手动设置方案降雨过程(可设降雨中心)失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelRainAreaAddBndTool(BaseTool):
    """从数据库导入方案降雨过程工具"""
    
    @property
    def name(self) -> str:
        return "model_rain_area_add_bnd"
    
    @property
    def description(self) -> str:
        return "从数据库导入方案降雨过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行从数据库导入方案降雨过程"""
        try:
            url = f"{RAIN_CONTROL_BASE_URL}/model/modelRainArea/add/bnd"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "从数据库导入方案降雨过程成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "导入失败"))
        except Exception as e:
            logger.error(f"从数据库导入方案降雨过程失败: {e}")
            return ToolResult(success=False, error=str(e))


# 注册方案降雨查询接口（7个）
register_tool(ModelRainAreaGetByPlanTool())
register_tool(ModelRainAreaGetBasinAreaRainStcTool())
register_tool(ModelRainAreaGetBasinAreaRainAccTool())
register_tool(ModelRainAreaGetBasinListTool())
register_tool(ModelRainAreaDetailTool())
register_tool(ModelRainAreaGetByRsvrTool())
register_tool(ModelRainAreaForecastRainStcTool())

# 注册方案降雨设置接口（5个）
register_tool(ModelRainAreaAddEcmwfTool())
register_tool(ModelRainAreaAddEcmwfTranslateTool())
register_tool(ModelRainAreaAddManualTool())
register_tool(ModelRainAreaAddManualCenterTool())
register_tool(ModelRainAreaAddBndTool())
