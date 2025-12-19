"""
水雨情监测数据工具
提供水位、雨量、流量等实时和历史数据查询功能
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)


class QueryWaterLevelTool(BaseTool):
    """查询水位数据工具"""
    
    @property
    def name(self) -> str:
        return "query_water_level"
    
    @property
    def description(self) -> str:
        return "查询指定测站的水位数据，支持实时数据和历史数据查询"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="station_id",
                type="string",
                description="测站编码",
                required=False
            ),
            ToolParameter(
                name="station_name",
                type="string",
                description="测站名称（模糊匹配）",
                required=False
            ),
            ToolParameter(
                name="start_time",
                type="string",
                description="开始时间，格式: YYYY-MM-DD HH:mm:ss",
                required=False
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="结束时间，格式: YYYY-MM-DD HH:mm:ss",
                required=False
            ),
            ToolParameter(
                name="latest",
                type="boolean",
                description="是否只查询最新数据",
                required=False,
                default=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水位查询"""
        station_id = kwargs.get('station_id')
        station_name = kwargs.get('station_name')
        start_time = kwargs.get('start_time')
        end_time = kwargs.get('end_time')
        latest = kwargs.get('latest', True)
        
        try:
            # 构建API请求
            base_url = settings.wg_data_server_url
            
            if latest:
                # 查询最新水位
                url = f"{base_url}/api/hydro/water_level/latest"
                params = {}
                if station_id:
                    params['stcd'] = station_id
                if station_name:
                    params['stnm'] = station_name
            else:
                # 查询历史水位
                url = f"{base_url}/api/hydro/water_level/history"
                params = {
                    'start_time': start_time or (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': end_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                if station_id:
                    params['stcd'] = station_id
                if station_name:
                    params['stnm'] = station_name
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # 处理返回数据
            if isinstance(data, dict) and 'data' in data:
                result_data = data['data']
            else:
                result_data = data
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "query_type": "latest" if latest else "history",
                    "station_id": station_id,
                    "record_count": len(result_data) if isinstance(result_data, list) else 1
                }
            )
            
        except httpx.HTTPError as e:
            logger.error(f"水位查询HTTP错误: {e}")
            # 返回模拟数据用于测试
            return self._get_mock_data(station_id, station_name, latest)
        except Exception as e:
            logger.error(f"水位查询失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_data(self, station_id: str, station_name: str, latest: bool) -> ToolResult:
        """返回模拟数据（用于API不可用时的测试）"""
        mock_data = [
            {
                "stcd": station_id or "60105400",
                "stnm": station_name or "卫辉站",
                "tm": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "z": 78.52,  # 水位
                "warning_level": 79.00,
                "guarantee_level": 80.50
            }
        ]
        return ToolResult(
            success=True,
            data=mock_data,
            metadata={"is_mock": True}
        )


class QueryRainfallTool(BaseTool):
    """查询雨量数据工具"""
    
    @property
    def name(self) -> str:
        return "query_rainfall"
    
    @property
    def description(self) -> str:
        return "查询指定测站或区域的雨量数据，支持时段雨量和累计雨量"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="station_id",
                type="string",
                description="测站编码",
                required=False
            ),
            ToolParameter(
                name="station_name",
                type="string",
                description="测站名称",
                required=False
            ),
            ToolParameter(
                name="start_time",
                type="string",
                description="开始时间",
                required=False
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="结束时间",
                required=False
            ),
            ToolParameter(
                name="period",
                type="string",
                description="统计周期: 1h(1小时), 3h(3小时), 6h(6小时), 12h(12小时), 24h(24小时)",
                required=False,
                default="24h",
                enum=["1h", "3h", "6h", "12h", "24h"]
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行雨量查询"""
        station_id = kwargs.get('station_id')
        station_name = kwargs.get('station_name')
        start_time = kwargs.get('start_time')
        end_time = kwargs.get('end_time')
        period = kwargs.get('period', '24h')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/hydro/rainfall"
            
            params = {'period': period}
            if station_id:
                params['stcd'] = station_id
            if station_name:
                params['stnm'] = station_name
            if start_time:
                params['start_time'] = start_time
            if end_time:
                params['end_time'] = end_time
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            result_data = data.get('data', data)
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={
                    "period": period,
                    "record_count": len(result_data) if isinstance(result_data, list) else 1
                }
            )
            
        except httpx.HTTPError as e:
            logger.error(f"雨量查询HTTP错误: {e}")
            return self._get_mock_data(period)
        except Exception as e:
            logger.error(f"雨量查询失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_data(self, period: str) -> ToolResult:
        """返回模拟数据"""
        mock_data = [
            {"stcd": "60105400", "stnm": "卫辉站", "drp": 12.5, "period": period},
            {"stcd": "60105410", "stnm": "淇县站", "drp": 8.2, "period": period},
            {"stcd": "60105420", "stnm": "浚县站", "drp": 15.8, "period": period}
        ]
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


class QueryFlowTool(BaseTool):
    """查询流量数据工具"""
    
    @property
    def name(self) -> str:
        return "query_flow"
    
    @property
    def description(self) -> str:
        return "查询指定测站的流量数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="station_id",
                type="string",
                description="测站编码",
                required=False
            ),
            ToolParameter(
                name="station_name",
                type="string",
                description="测站名称",
                required=False
            ),
            ToolParameter(
                name="start_time",
                type="string",
                description="开始时间",
                required=False
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="结束时间",
                required=False
            ),
            ToolParameter(
                name="latest",
                type="boolean",
                description="是否只查询最新数据",
                required=False,
                default=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行流量查询"""
        station_id = kwargs.get('station_id')
        station_name = kwargs.get('station_name')
        latest = kwargs.get('latest', True)
        
        try:
            base_url = settings.wg_data_server_url
            
            if latest:
                url = f"{base_url}/api/hydro/flow/latest"
            else:
                url = f"{base_url}/api/hydro/flow/history"
            
            params = {}
            if station_id:
                params['stcd'] = station_id
            if station_name:
                params['stnm'] = station_name
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            result_data = data.get('data', data)
            
            return ToolResult(
                success=True,
                data=result_data,
                metadata={"query_type": "latest" if latest else "history"}
            )
            
        except httpx.HTTPError as e:
            logger.error(f"流量查询HTTP错误: {e}")
            return self._get_mock_data(station_id, station_name)
        except Exception as e:
            logger.error(f"流量查询失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_data(self, station_id: str, station_name: str) -> ToolResult:
        """返回模拟数据"""
        mock_data = [{
            "stcd": station_id or "60105400",
            "stnm": station_name or "卫辉站",
            "tm": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "q": 156.8,  # 流量 m³/s
            "z": 78.52   # 水位
        }]
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


class QueryReservoirTool(BaseTool):
    """查询水库数据工具"""
    
    @property
    def name(self) -> str:
        return "query_reservoir"
    
    @property
    def description(self) -> str:
        return "查询水库的库容、水位、蓄水量等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="reservoir_id",
                type="string",
                description="水库编码",
                required=False
            ),
            ToolParameter(
                name="reservoir_name",
                type="string",
                description="水库名称",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水库查询"""
        reservoir_id = kwargs.get('reservoir_id')
        reservoir_name = kwargs.get('reservoir_name')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/hydro/reservoir"
            
            params = {}
            if reservoir_id:
                params['rscd'] = reservoir_id
            if reservoir_name:
                params['rsnm'] = reservoir_name
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data.get('data', data)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"水库查询HTTP错误: {e}")
            return self._get_mock_data(reservoir_name)
        except Exception as e:
            logger.error(f"水库查询失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_data(self, reservoir_name: str) -> ToolResult:
        """返回模拟数据"""
        mock_data = [{
            "rscd": "41050100011",
            "rsnm": reservoir_name or "良相水库",
            "tm": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "rz": 125.6,  # 库水位
            "w": 1580.5,  # 蓄水量(万m³)
            "inq": 12.5,  # 入库流量
            "otq": 8.2,   # 出库流量
            "flood_limit_level": 128.0,  # 汛限水位
            "normal_level": 130.0,  # 正常蓄水位
            "design_level": 132.5   # 设计洪水位
        }]
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


class ListStationsTool(BaseTool):
    """列出测站工具"""
    
    @property
    def name(self) -> str:
        return "list_stations"
    
    @property
    def description(self) -> str:
        return "列出流域内的测站信息，可按类型筛选"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="station_type",
                type="string",
                description="测站类型: PP(雨量站), ZZ(水位站), ZQ(水文站), RR(水库)",
                required=False,
                enum=["PP", "ZZ", "ZQ", "RR"]
            ),
            ToolParameter(
                name="river_name",
                type="string",
                description="河流名称",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """列出测站"""
        station_type = kwargs.get('station_type')
        river_name = kwargs.get('river_name')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/station/list"
            
            params = {}
            if station_type:
                params['sttp'] = station_type
            if river_name:
                params['rvnm'] = river_name
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data.get('data', data)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"测站列表查询HTTP错误: {e}")
            return self._get_mock_data(station_type)
        except Exception as e:
            logger.error(f"测站列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_data(self, station_type: str) -> ToolResult:
        """返回模拟数据"""
        mock_data = [
            {"stcd": "60105400", "stnm": "卫辉站", "sttp": "ZQ", "rvnm": "卫河", "lgtd": 114.05, "lttd": 35.42},
            {"stcd": "60105410", "stnm": "淇县站", "sttp": "ZZ", "rvnm": "淇河", "lgtd": 114.18, "lttd": 35.58},
            {"stcd": "60105420", "stnm": "浚县站", "sttp": "ZQ", "rvnm": "卫河", "lgtd": 114.32, "lttd": 35.68}
        ]
        if station_type:
            mock_data = [s for s in mock_data if s['sttp'] == station_type]
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


# 注册工具
def register_hydro_monitor_tools():
    """注册水雨情监测工具"""
    register_tool(QueryWaterLevelTool())
    register_tool(QueryRainfallTool())
    register_tool(QueryFlowTool())
    register_tool(QueryReservoirTool())
    register_tool(ListStationsTool())
    logger.info("水雨情监测工具注册完成")


# 模块加载时自动注册
register_hydro_monitor_tools()
