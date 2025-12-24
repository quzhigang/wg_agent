"""
水雨情监测数据工具
提供水位、雨量、流量等实时和历史数据查询功能

本模块包含以下15个接口工具：
1. 雨量过程数据查询接口
2. 雨量统计数据查询接口
3. 雨量累计查询接口
4. 水库最新水情查询接口
5. 水库水情过程查询接口
6. 河道最新水情查询接口
7. 河道水情过程查询接口
8. AI水情最新数据查询接口
9. AI水情过程数据查询接口
10. AI雨量最新数据查询接口
11. AI雨量过程数据查询接口
12. 视频监控预览接口
13. 传感器数据过程查询接口
14. 无人机设备状态查询接口
15. 短信发送接口

所有接口的基础地址为: http://10.20.2.153
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool
from .auth import LoginTool

logger = get_logger(__name__)


# =============================================================================
# 一、雨情监测接口（3个）
# =============================================================================

class QueryRainProcessTool(BaseTool):
    """
    1. 雨量过程数据查询接口
    根据测站编码和时间范围查询雨量历史过程数据
    """
    
    @property
    def name(self) -> str:
        return "query_rain_process"
    
    @property
    def description(self) -> str:
        return "根据测站编码和时间范围查询雨量历史过程数据，返回时段降水量、日降水量、累计降水量等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码",
                required=True
            ),
            ToolParameter(
                name="search_begin_time",
                type="string",
                description="查询开始时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="search_end_time",
                type="string",
                description="查询结束时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行雨量过程数据查询
        
        Args:
            stcd: 测站编码
            search_begin_time: 查询开始时间
            search_end_time: 查询结束时间
            
        Returns:
            ToolResult: 包含雨量过程数据的查询结果
        """
        stcd = kwargs.get('stcd')
        search_begin_time = kwargs.get('search_begin_time')
        search_end_time = kwargs.get('search_end_time')
        
        try:
            # 构建API请求
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/rwdb/rain/processList"
            params = {
                'STCD': stcd,
                'searchBeginTime': search_begin_time,
                'searchEndTime': search_end_time
            }
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            # 处理返回数据
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "rain_process",
                        "stcd": stcd,
                        "time_range": f"{search_begin_time} ~ {search_end_time}",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"雨量过程数据查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"雨量过程数据查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class QueryRainStatisticsTool(BaseTool):
    """
    2. 雨量统计数据查询接口
    根据测站编码查询雨量统计数据，包含1小时、3小时、6小时、12小时、24小时等多时段的雨量统计信息
    """
    
    @property
    def name(self) -> str:
        return "query_rain_statistics"
    
    @property
    def description(self) -> str:
        return "根据测站编码查询雨量统计数据，返回1小时、3小时、6小时、12小时、24小时等多时段的雨量统计信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行雨量统计数据查询
        
        Args:
            stcd: 测站编码
            
        Returns:
            ToolResult: 包含不同时段雨量统计数据的查询结果
        """
        stcd = kwargs.get('stcd')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/rwdb/rain/statistics"
            params = {'STCD': stcd}
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', {})
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "rain_statistics",
                        "stcd": stcd,
                        "time_periods": ["1hour", "3hour", "6hour", "12hour", "24hour"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"雨量统计数据查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"雨量统计数据查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class QueryRainSumTool(BaseTool):
    """
    3. 雨量累计查询接口
    根据时间范围查询所有测站的雨量累计数据
    """
    
    @property
    def name(self) -> str:
        return "query_rain_sum"
    
    @property
    def description(self) -> str:
        return "根据时间范围查询所有测站的雨量累计数据，返回测站编码、名称、累计降水量、测站位置等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="search_begin_time",
                type="string",
                description="查询开始时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="search_end_time",
                type="string",
                description="查询结束时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行雨量累计查询
        
        Args:
            search_begin_time: 查询开始时间
            search_end_time: 查询结束时间
            
        Returns:
            ToolResult: 包含所有测站雨量累计数据的查询结果
        """
        search_begin_time = kwargs.get('search_begin_time')
        search_end_time = kwargs.get('search_end_time')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/rwdb/rain/sum"
            params = {
                'searchBeginTime': search_begin_time,
                'searchEndTime': search_end_time
            }
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "rain_sum",
                        "time_range": f"{search_begin_time} ~ {search_end_time}",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"雨量累计查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"雨量累计查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 二、水库水情监测接口（2个）
# =============================================================================

class QueryReservoirLastTool(BaseTool):
    """
    4. 水库最新水情查询接口
    获取所有水库的最新实时水情数据，包括水位、蓄水量、入库流量、出库流量等
    """
    
    @property
    def name(self) -> str:
        return "query_reservoir_last"
    
    @property
    def description(self) -> str:
        return "获取所有水库的最新实时水情数据，包括库水位、蓄水量、入库流量、出库流量等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        # 该接口无需参数
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行水库最新水情查询
        
        Returns:
            ToolResult: 包含所有水库最新水情数据的查询结果
        """
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/rwdb/rsvr/last"
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "reservoir_last",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"水库最新水情查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"水库最新水情查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class QueryReservoirProcessTool(BaseTool):
    """
    5. 水库水情过程查询接口
    根据测站编码和时间范围查询水库的历史水情过程数据
    """
    
    @property
    def name(self) -> str:
        return "query_reservoir_process"
    
    @property
    def description(self) -> str:
        return "根据测站编码和时间范围查询水库的历史水情过程数据，返回库水位、蓄水量、入库流量、出库流量等时序数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码",
                required=True
            ),
            ToolParameter(
                name="search_begin_time",
                type="string",
                description="查询开始时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="search_end_time",
                type="string",
                description="查询结束时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行水库水情过程查询
        
        Args:
            stcd: 测站编码
            search_begin_time: 查询开始时间
            search_end_time: 查询结束时间
            
        Returns:
            ToolResult: 包含水库历史水情过程数据的查询结果
        """
        stcd = kwargs.get('stcd')
        search_begin_time = kwargs.get('search_begin_time')
        search_end_time = kwargs.get('search_end_time')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/rwdb/rsvr/processList"
            params = {
                'STCD': stcd,
                'searchBeginTime': search_begin_time,
                'searchEndTime': search_end_time
            }
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "reservoir_process",
                        "stcd": stcd,
                        "time_range": f"{search_begin_time} ~ {search_end_time}",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"水库水情过程查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"水库水情过程查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 三、河道水情监测接口（2个）
# =============================================================================

class QueryRiverLastTool(BaseTool):
    """
    6. 河道最新水情查询接口
    获取所有河道测站的最新实时水情数据，包括水位、流量等
    """
    
    @property
    def name(self) -> str:
        return "query_river_last"
    
    @property
    def description(self) -> str:
        return "获取所有河道测站的最新实时水情数据，包括水位、流量、水势、告警级别等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        # 该接口无需参数
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行河道最新水情查询
        
        Returns:
            ToolResult: 包含所有河道测站最新水情数据的查询结果
        """
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/rwdb/river/last"
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "river_last",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"河道最新水情查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"河道最新水情查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class QueryRiverProcessTool(BaseTool):
    """
    7. 河道水情过程查询接口
    根据测站编码和时间范围查询河道水情历史过程数据
    """
    
    @property
    def name(self) -> str:
        return "query_river_process"
    
    @property
    def description(self) -> str:
        return "根据测站编码和时间范围查询河道水情历史过程数据，返回水位、流量、水势等时序数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码",
                required=True
            ),
            ToolParameter(
                name="search_begin_time",
                type="string",
                description="查询开始时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="search_end_time",
                type="string",
                description="查询结束时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行河道水情过程查询
        
        Args:
            stcd: 测站编码
            search_begin_time: 查询开始时间
            search_end_time: 查询结束时间
            
        Returns:
            ToolResult: 包含河道历史水情过程数据的查询结果
        """
        stcd = kwargs.get('stcd')
        search_begin_time = kwargs.get('search_begin_time')
        search_end_time = kwargs.get('search_end_time')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/rwdb/river/processList"
            params = {
                'STCD': stcd,
                'searchBeginTime': search_begin_time,
                'searchEndTime': search_end_time
            }
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "river_process",
                        "stcd": stcd,
                        "time_range": f"{search_begin_time} ~ {search_end_time}",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"河道水情过程查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"河道水情过程查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 四、AI智能监测数据接口（4个）
# =============================================================================

class QueryAiWaterLastTool(BaseTool):
    """
    8. AI水情最新数据查询接口
    获取AI智能监测设备的最新水情数据
    """
    
    @property
    def name(self) -> str:
        return "query_ai_water_last"
    
    @property
    def description(self) -> str:
        return "获取AI智能监测设备的最新水情数据，返回测站编码、名称、水位、数据时间等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        # 该接口无需参数
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行AI水情最新数据查询
        
        Returns:
            ToolResult: 包含AI智能监测设备最新水情数据的查询结果
        """
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/monitor/ai/water/last"
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "ai_water_last",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"AI水情最新数据查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"AI水情最新数据查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class QueryAiWaterProcessTool(BaseTool):
    """
    9. AI水情过程数据查询接口
    根据测站编码和时间范围查询AI智能监测设备的水情历史过程数据
    """
    
    @property
    def name(self) -> str:
        return "query_ai_water_process"
    
    @property
    def description(self) -> str:
        return "根据测站编码和时间范围查询AI智能监测设备的水情历史过程数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码",
                required=True
            ),
            ToolParameter(
                name="st",
                type="string",
                description="开始时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="ed",
                type="string",
                description="结束时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行AI水情过程数据查询
        
        Args:
            stcd: 测站编码
            st: 开始时间
            ed: 结束时间
            
        Returns:
            ToolResult: 包含AI智能监测设备水情历史过程数据的查询结果
        """
        stcd = kwargs.get('stcd')
        st = kwargs.get('st')
        ed = kwargs.get('ed')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/monitor/ai/water/process"
            params = {
                'stcd': stcd,
                'st': st,
                'ed': ed
            }
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "ai_water_process",
                        "stcd": stcd,
                        "time_range": f"{st} ~ {ed}",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"AI水情过程数据查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"AI水情过程数据查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class QueryAiRainLastTool(BaseTool):
    """
    10. AI雨量最新数据查询接口
    获取AI智能监测设备的最新雨量数据
    """
    
    @property
    def name(self) -> str:
        return "query_ai_rain_last"
    
    @property
    def description(self) -> str:
        return "获取AI智能监测设备的最新雨量数据，返回测站编码、名称、时段降水量、数据时间等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        # 该接口无需参数
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行AI雨量最新数据查询
        
        Returns:
            ToolResult: 包含AI智能监测设备最新雨量数据的查询结果
        """
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/monitor/ai/rain/last"
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "ai_rain_last",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"AI雨量最新数据查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"AI雨量最新数据查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class QueryAiRainProcessTool(BaseTool):
    """
    11. AI雨量过程数据查询接口
    根据测站编码和时间范围查询AI智能监测设备的雨量历史过程数据
    """
    
    @property
    def name(self) -> str:
        return "query_ai_rain_process"
    
    @property
    def description(self) -> str:
        return "根据测站编码和时间范围查询AI智能监测设备的雨量历史过程数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码",
                required=True
            ),
            ToolParameter(
                name="st",
                type="string",
                description="开始时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="ed",
                type="string",
                description="结束时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行AI雨量过程数据查询
        
        Args:
            stcd: 测站编码
            st: 开始时间
            ed: 结束时间
            
        Returns:
            ToolResult: 包含AI智能监测设备雨量历史过程数据的查询结果
        """
        stcd = kwargs.get('stcd')
        st = kwargs.get('st')
        ed = kwargs.get('ed')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/monitor/ai/rain/process"
            params = {
                'stcd': stcd,
                'st': st,
                'ed': ed
            }
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "ai_rain_process",
                        "stcd": stcd,
                        "time_range": f"{st} ~ {ed}",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"AI雨量过程数据查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"AI雨量过程数据查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 五、视频监控接口（1个）
# =============================================================================

class QueryCameraPreviewTool(BaseTool):
    """
    12. 视频监控预览接口
    根据摄像头编码获取实时视频预览地址
    """
    
    @property
    def name(self) -> str:
        return "query_camera_preview"
    
    @property
    def description(self) -> str:
        return "根据摄像头编码获取实时视频预览流地址"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="摄像头编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行视频监控预览查询
        
        Args:
            code: 摄像头编码
            
        Returns:
            ToolResult: 包含视频预览流地址的查询结果
        """
        code = kwargs.get('code')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/camera/preview"
            params = {'code': code}
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', {})
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "camera_preview",
                        "camera_code": code
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"视频监控预览查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"视频监控预览查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 六、传感器监测接口（1个）
# =============================================================================

class QuerySensorDataProcessTool(BaseTool):
    """
    13. 传感器数据过程查询接口
    根据传感器ID和时间范围查询传感器的历史监测数据
    """
    
    @property
    def name(self) -> str:
        return "query_sensor_data_process"
    
    @property
    def description(self) -> str:
        return "根据传感器ID和时间范围查询传感器的历史监测数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sensor_id",
                type="string",
                description="传感器ID",
                required=True
            ),
            ToolParameter(
                name="st",
                type="string",
                description="开始时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="ed",
                type="string",
                description="结束时间，格式：yyyy-MM-dd HH:mm:ss",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行传感器数据过程查询
        
        Args:
            sensor_id: 传感器ID
            st: 开始时间
            ed: 结束时间
            
        Returns:
            ToolResult: 包含传感器历史监测数据的查询结果
        """
        sensor_id = kwargs.get('sensor_id')
        st = kwargs.get('st')
        ed = kwargs.get('ed')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/monitor/sensor/data/process"
            params = {
                'sensorId': sensor_id,
                'st': st,
                'ed': ed
            }
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', [])
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "sensor_data_process",
                        "sensor_id": sensor_id,
                        "time_range": f"{st} ~ {ed}",
                        "record_count": len(result_data) if isinstance(result_data, list) else 1
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"传感器数据过程查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"传感器数据过程查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 七、无人机监测接口（1个）
# =============================================================================

class QueryDroneStatusTool(BaseTool):
    """
    14. 无人机设备状态查询接口
    查询大疆无人机设备的实时状态
    """
    
    @property
    def name(self) -> str:
        return "query_drone_status"
    
    @property
    def description(self) -> str:
        return "查询大疆无人机设备的实时状态，包括设备序列号、状态、电量、位置等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="device_sn",
                type="string",
                description="无人机设备序列号",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行无人机设备状态查询
        
        Args:
            device_sn: 无人机设备序列号
            
        Returns:
            ToolResult: 包含无人机设备实时状态的查询结果
        """
        device_sn = kwargs.get('device_sn')
        
        try:
            base_url = settings.wg_data_server_url
            # 注意：设备序列号作为URL路径参数
            url = f"{base_url}/api/djiuav/openapi/v0.1/device/{device_sn}/state"
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                result_data = data.get('data', {})
                return ToolResult(
                    success=True,
                    data=result_data,
                    metadata={
                        "query_type": "drone_status",
                        "device_sn": device_sn
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '查询失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"无人机设备状态查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"无人机设备状态查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 八、告警短信接口（1个）
# =============================================================================

class SendSmsTool(BaseTool):
    """
    15. 短信发送接口
    发送告警短信通知
    """
    
    @property
    def name(self) -> str:
        return "send_sms"
    
    @property
    def description(self) -> str:
        return "发送告警短信通知，需要提供接收手机号码和短信内容"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.HYDRO_MONITOR
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="phone",
                type="string",
                description="接收短信的手机号码",
                required=True
            ),
            ToolParameter(
                name="content",
                type="string",
                description="短信内容",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行短信发送
        
        Args:
            phone: 接收短信的手机号码
            content: 短信内容
            
        Returns:
            ToolResult: 短信发送结果
        """
        phone = kwargs.get('phone')
        content = kwargs.get('content')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/basin/modelPlatf/sms/sendMsg"
            
            # 注意：这是POST请求，需要发送JSON请求体
            json_data = {
                'phone': phone,
                'content': content
            }
            
            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()
            auth_headers['Content-Type'] = 'application/json'
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json=json_data,
                    headers=auth_headers
                )
                response.raise_for_status()
                data = response.json()
            
            if data.get('success'):
                return ToolResult(
                    success=True,
                    data={"message": "短信发送成功"},
                    metadata={
                        "query_type": "send_sms",
                        "phone": phone
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=data.get('message', '短信发送失败')
                )
            
        except httpx.HTTPError as e:
            logger.error(f"短信发送HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求失败: {str(e)}")
        except Exception as e:
            logger.error(f"短信发送失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 工具注册
# =============================================================================

def register_hydro_monitor_tools():
    """
    注册水雨情监测工具
    
    共注册15个工具：
    - 雨情监测: 3个 (雨量过程、雨量统计、雨量累计)
    - 水库水情: 2个 (最新水情、水情过程)
    - 河道水情: 2个 (最新水情、水情过程)
    - AI智能监测: 4个 (水情最新、水情过程、雨量最新、雨量过程)
    - 视频监控: 1个 (摄像头预览)
    - 传感器监测: 1个 (数据过程)
    - 无人机监测: 1个 (设备状态)
    - 告警短信: 1个 (短信发送)
    """
    # 一、雨情监测接口
    register_tool(QueryRainProcessTool())
    register_tool(QueryRainStatisticsTool())
    register_tool(QueryRainSumTool())
    
    # 二、水库水情监测接口
    register_tool(QueryReservoirLastTool())
    register_tool(QueryReservoirProcessTool())
    
    # 三、河道水情监测接口
    register_tool(QueryRiverLastTool())
    register_tool(QueryRiverProcessTool())
    
    # 四、AI智能监测数据接口
    register_tool(QueryAiWaterLastTool())
    register_tool(QueryAiWaterProcessTool())
    register_tool(QueryAiRainLastTool())
    register_tool(QueryAiRainProcessTool())
    
    # 五、视频监控接口
    register_tool(QueryCameraPreviewTool())
    
    # 六、传感器监测接口
    register_tool(QuerySensorDataProcessTool())
    
    # 七、无人机监测接口
    register_tool(QueryDroneStatusTool())
    
    # 八、告警短信接口
    register_tool(SendSmsTool())
    
    logger.info("水雨情监测工具注册完成，共15个工具")


# 模块加载时自动注册
register_hydro_monitor_tools()
