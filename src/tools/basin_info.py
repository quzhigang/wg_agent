"""
流域基本信息工具
基于卫共流域数字孪生系统API接口进行封装，提供流域内测站基础信息、水库/水闸配置参数、
蓄滞洪区信息、设备列表等静态或配置类信息的查询功能

接口基础地址: http://10.20.2.153
"""

from typing import Dict, Any, List, Optional
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool
from .auth import LoginTool

logger = get_logger(__name__)

# API基础地址常量
API_BASE_URL = "http://10.20.2.153"


# ============================================================
# 一、地图数据源接口
# ============================================================

class GetMapDataTool(BaseTool):
    """
    地图数据源查询工具
    查询各类地理要素的地图数据（包含空间坐标shape字段），
    支持测站、水库、蓄滞洪区、分洪闸堰等多种类型的查询
    """
    
    @property
    def name(self) -> str:
        return "get_map_data"
    
    @property
    def description(self) -> str:
        return "查询各类地理要素的地图数据（包含空间坐标），支持测站、水库、蓄滞洪区、分洪闸堰等类型"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="ref_table",
                type="string",
                description="数据表名: geo_st_base(测站), geo_res_base(水库), geo_fld_stor(蓄滞洪区), geo_flo_dam(分洪闸堰)",
                required=True,
                enum=["geo_st_base", "geo_res_base", "geo_fld_stor", "geo_flo_dam"]
            ),
            ToolParameter(
                name="filter_field",
                type="string",
                description="查询字段名。水库使用stcd(编码)和res_name(名称)；测站、蓄滞洪区、分洪闸堰使用code(编码)和name(名称)",
                required=False
            ),
            ToolParameter(
                name="filter_operator",
                type="string",
                description="关系运算符: =, in, like, >, <",
                required=False,
                enum=["=", "in", "like", ">", "<"]
            ),
            ToolParameter(
                name="filter_value",
                type="string",
                description="查询值",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行地图数据源查询"""
        ref_table = kwargs.get('ref_table')
        filter_field = kwargs.get('filter_field')
        filter_operator = kwargs.get('filter_operator')
        filter_value = kwargs.get('filter_value')
        
        try:
            url = f"{API_BASE_URL}/api/basin/map/dataSource/table/map"
            
            # 构建请求参数
            params = {'refTable': ref_table}
            if filter_field and filter_operator and filter_value:
                params['where[0][filed]'] = filter_field
                params['where[0][rela]'] = filter_operator
                # 参数值需要带单引号
                # 如果使用like操作符，自动添加%通配符以支持模糊匹配
                if filter_operator == 'like':
                    params['where[0][value]'] = f"'%{filter_value}%'"
                else:
                    params['where[0][value]'] = f"'{filter_value}'"
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"地图数据源查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"地图数据源查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class GetListDataTool(BaseTool):
    """
    列表数据源查询工具
    查询各类要素的列表数据（不含空间坐标），支持水库扩展信息、防洪责任人等查询
    """
    
    @property
    def name(self) -> str:
        return "get_list_data"
    
    @property
    def description(self) -> str:
        return "查询各类要素的列表数据（不含空间坐标），如水库防洪责任人扩展信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="ref_table",
                type="string",
                description="数据表名，如geo_res_flood_ext(水库防洪责任人扩展信息)",
                required=True,
                enum=["geo_res_flood_ext"]
            ),
            ToolParameter(
                name="filter_field",
                type="string",
                description="查询字段名",
                required=False
            ),
            ToolParameter(
                name="filter_operator",
                type="string",
                description="关系运算符: =, in, like",
                required=False,
                enum=["=", "in", "like"]
            ),
            ToolParameter(
                name="filter_value",
                type="string",
                description="查询值",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行列表数据源查询"""
        ref_table = kwargs.get('ref_table')
        filter_field = kwargs.get('filter_field')
        filter_operator = kwargs.get('filter_operator')
        filter_value = kwargs.get('filter_value')
        
        try:
            url = f"{API_BASE_URL}/api/basin/map/dataSource/table/list"
            
            # 构建请求参数
            params = {'refTable': ref_table}
            if filter_field and filter_operator and filter_value:
                params['where[0][filed]'] = filter_field
                params['where[0][rela]'] = filter_operator
                params['where[0][value]'] = filter_value
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"列表数据源查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"列表数据源查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 二、水库基础信息接口
# ============================================================

class GetReservoirInfoTool(BaseTool):
    """
    水库基础信息查询工具
    查询水库的基础属性信息，包括位置、所属水系、工程等级、库容等静态配置
    """
    
    @property
    def name(self) -> str:
        return "get_reservoir_info"
    
    @property
    def description(self) -> str:
        return "查询水库的基础属性信息，包括位置、工程等级、流域面积、库容、校核洪水位等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码，可选，不传则查询所有水库",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水库基础信息查询"""
        stcd = kwargs.get('stcd')
        
        try:
            url = f"{API_BASE_URL}/api/basin/map/dataSource/table/map"
            
            # 构建请求参数
            params = {'refTable': 'geo_res_base'}
            if stcd:
                params['where[0][filed]'] = 'stcd'
                params['where[0][rela]'] = '='
                params['where[0][value]'] = stcd
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"水库基础信息查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"水库基础信息查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class GetReservoirFloodDetailTool(BaseTool):
    """
    水库防洪特征值详情查询工具
    根据测站编码查询单个水库的防洪特征值详情，包括校核洪水位、设计洪水位、正常蓄水位、死水位等
    """
    
    @property
    def name(self) -> str:
        return "get_reservoir_flood_detail"
    
    @property
    def description(self) -> str:
        return "查询单个水库的防洪特征值详情，包括校核洪水位、设计洪水位、正常蓄水位、死水位、库容等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码（必填）",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水库防洪特征值详情查询"""
        stcd = kwargs.get('stcd')
        
        try:
            url = f"{API_BASE_URL}/api/basin/rwdb/rsvr/fcch/detail"
            params = {'STCD': stcd}
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', {}),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"水库防洪特征值详情查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"水库防洪特征值详情查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class GetReservoirFloodListTool(BaseTool):
    """
    水库防洪特征值列表查询工具
    获取所有水库的防洪特征值信息列表，包括校核洪水位、设计洪水位、正常蓄水位、死水位等
    """
    
    @property
    def name(self) -> str:
        return "get_reservoir_flood_list"
    
    @property
    def description(self) -> str:
        return "获取所有水库的防洪特征值信息列表，包含各水库的校核洪水位、设计洪水位、正常蓄水位、库容等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []  # 无参数
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水库防洪特征值列表查询"""
        try:
            url = f"{API_BASE_URL}/api/basin/rwdb/rsvr/fcch/list"
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"水库防洪特征值列表查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"水库防洪特征值列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 三、水闸堰基础信息接口
# ============================================================

class GetSluiceInfoTool(BaseTool):
    """
    水闸基础信息查询工具
    查询水闸的基础属性信息，包括位置、所属水系、工程规模、设计流量等
    """
    
    @property
    def name(self) -> str:
        return "get_sluice_info"
    
    @property
    def description(self) -> str:
        return "查询水闸的基础属性信息，包括位置、河流名称、工程规模、设计流量等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码，可选，不传则查询所有水闸",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水闸基础信息查询"""
        stcd = kwargs.get('stcd')
        
        try:
            url = f"{API_BASE_URL}/api/basin/map/dataSource/table/map"
            
            # 构建请求参数
            params = {'refTable': 'geo_sluice_base'}
            if stcd:
                params['where[0][filed]'] = 'stcd'
                params['where[0][rela]'] = '='
                params['where[0][value]'] = stcd
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"水闸基础信息查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"水闸基础信息查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class GetFloodDamInfoTool(BaseTool):
    """
    分洪闸堰信息查询工具
    查询分洪闸堰的基础信息，包括设计分洪流量、启用条件等
    """
    
    @property
    def name(self) -> str:
        return "get_flood_dam_info"
    
    @property
    def description(self) -> str:
        return "查询分洪闸堰的基础信息，包括位置、设计分洪流量等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="分洪闸堰名称，可选，支持模糊查询",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行分洪闸堰信息查询"""
        name = kwargs.get('name')
        
        try:
            url = f"{API_BASE_URL}/api/basin/map/dataSource/table/map"
            
            # 构建请求参数
            params = {'refTable': 'geo_flo_dam'}
            if name:
                params['where[0][filed]'] = 'name'
                params['where[0][rela]'] = 'like'
                params['where[0][value]'] = name
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"分洪闸堰信息查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"分洪闸堰信息查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 四、蓄滞洪区接口
# ============================================================

class GetFloodStorageAreaTool(BaseTool):
    """
    蓄滞洪区信息查询工具
    查询蓄滞洪区的基础信息，包括面积、进洪设施、设计蓄洪水位等
    """
    
    @property
    def name(self) -> str:
        return "get_flood_storage_area"
    
    @property
    def description(self) -> str:
        return "查询蓄滞洪区的基础信息，包括面积、进洪设施、设计蓄洪库容、设计蓄洪水位等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="蓄滞洪区名称，可选，支持模糊查询",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行蓄滞洪区信息查询"""
        name = kwargs.get('name')
        
        try:
            url = f"{API_BASE_URL}/api/basin/map/dataSource/table/map"
            
            # 构建请求参数
            params = {'refTable': 'geo_fld_stor'}
            if name:
                params['where[0][filed]'] = 'name'
                params['where[0][rela]'] = 'like'
                params['where[0][value]'] = name
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"蓄滞洪区信息查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"蓄滞洪区信息查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 五、河道基础信息接口
# ============================================================

class GetRiverFloodListTool(BaseTool):
    """
    河道防洪特征值列表查询工具
    获取所有河道测站的防洪特征值信息列表，包括警戒水位、保证水位等
    """
    
    @property
    def name(self) -> str:
        return "get_river_flood_list"
    
    @property
    def description(self) -> str:
        return "获取所有河道测站的防洪特征值信息列表，包括警戒水位、保证水位、左右堤高程、实测最高水位等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []  # 无参数
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行河道防洪特征值列表查询"""
        try:
            url = f"{API_BASE_URL}/api/basin/rwdb/river/fcch/list"
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"河道防洪特征值列表查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"河道防洪特征值列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 六、测站基础信息接口
# ============================================================

class GetStationListTool(BaseTool):
    """
    测站列表查询工具
    按测站类型查询测站的基础信息列表
    """
    
    @property
    def name(self) -> str:
        return "get_station_list"
    
    @property
    def description(self) -> str:
        return "按测站类型查询测站的基础信息列表，包括测站编码、名称、位置、河流名称等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="sttp",
                type="string",
                description="测站类型: ZQ(水文站), ZZ(水位站), PP(雨量站), RR(水库站), DD(闸坝站), ZB(水位遥测站), AI(智能监测站)",
                required=True,
                enum=["ZQ", "ZZ", "PP", "RR", "DD", "ZB", "AI"]
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行测站列表查询"""
        sttp = kwargs.get('sttp')
        
        try:
            url = f"{API_BASE_URL}/api/basin/rwdb/station/list"
            params = {'STTP': sttp}
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"测站列表查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"测站列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 七、视频监控基础信息接口
# ============================================================

class GetCameraListTool(BaseTool):
    """
    视频监控列表查询工具
    获取视频监控摄像头列表，可根据测站编码筛选
    """
    
    @property
    def name(self) -> str:
        return "get_camera_list"
    
    @property
    def description(self) -> str:
        return "获取视频监控摄像头列表，包括摄像头编码、名称、关联测站、视频流地址等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stcd",
                type="string",
                description="测站编码，可选，不传则查询所有摄像头",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行视频监控列表查询"""
        stcd = kwargs.get('stcd')
        
        try:
            url = f"{API_BASE_URL}/api/basin/camera/list"
            params = {}
            if stcd:
                params['stcd'] = stcd
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"视频监控列表查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"视频监控列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 八、无人机基础信息接口
# ============================================================

class GetDroneProjectListTool(BaseTool):
    """
    无人机项目列表查询工具
    查询无人机项目列表
    """
    
    @property
    def name(self) -> str:
        return "get_drone_project_list"
    
    @property
    def description(self) -> str:
        return "查询无人机项目列表，获取项目ID和项目名称"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []  # 无参数
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行无人机项目列表查询"""
        try:
            url = f"{API_BASE_URL}/api/djiuav/openapi/v0.1/project"
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"无人机项目列表查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"无人机项目列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


class GetDroneDeviceListTool(BaseTool):
    """
    无人机项目设备列表查询工具
    查询指定项目下的无人机设备列表
    """
    
    @property
    def name(self) -> str:
        return "get_drone_device_list"
    
    @property
    def description(self) -> str:
        return "查询无人机设备列表，获取设备序列号、名称、类型、状态等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []  # 无参数
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行无人机设备列表查询"""
        try:
            url = f"{API_BASE_URL}/api/djiuav/openapi/v0.1/project/device"
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', []),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"无人机设备列表查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"无人机设备列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 九、遥感任务接口
# ============================================================

class GetRemoteSensingTaskListTool(BaseTool):
    """
    遥感任务列表查询工具
    查询各类遥感监测任务列表
    """
    
    @property
    def name(self) -> str:
        return "get_remote_sensing_task_list"
    
    @property
    def description(self) -> str:
        return "查询遥感监测任务列表，支持洪涝水淹、洪涝监测、水利工程变形、小流域监测等任务类型"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="task_type",
                type="string",
                description="任务类型: HHSL(洪涝水淹), HLJC(洪涝监测), SLGCBX(水利工程变形), XDMJC(小流域监测)",
                required=True,
                enum=["HHSL", "HLJC", "SLGCBX", "XDMJC"]
            ),
            ToolParameter(
                name="task_name",
                type="string",
                description="任务名称，支持模糊查询",
                required=False
            ),
            ToolParameter(
                name="page",
                type="integer",
                description="页码，从1开始",
                required=True,
                default=1
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="每页条数",
                required=True,
                default=10
            ),
            ToolParameter(
                name="user_id",
                type="string",
                description="用户ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行遥感任务列表查询"""
        task_type = kwargs.get('task_type')
        task_name = kwargs.get('task_name')
        page = kwargs.get('page', 1)
        limit = kwargs.get('limit', 10)
        user_id = kwargs.get('user_id')
        
        try:
            url = f"{API_BASE_URL}/api/rs/datamanager/task/getTaskList"
            
            # 构建请求参数
            params = {
                'tasktype': task_type,
                'page': page,
                'limit': limit,
                'userId': user_id
            }
            if task_name:
                params['taskname'] = task_name
            
            headers = await LoginTool.get_auth_headers()
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                result = response.json()
            
            if result.get('success'):
                return ToolResult(
                    success=True,
                    data=result.get('data', {}),
                    metadata={"code": result.get('code'), "message": result.get('message')}
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get('message', '请求失败'),
                    metadata={"code": result.get('code')}
                )
                
        except httpx.HTTPError as e:
            logger.error(f"遥感任务列表查询HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"遥感任务列表查询失败: {e}")
            return ToolResult(success=False, error=str(e))


# ============================================================
# 工具注册
# ============================================================

def register_basin_info_tools():
    """
    注册流域基本信息工具
    共14个工具对应接口文档中的14个API接口
    """
    # 一、地图数据源接口（2个）
    register_tool(GetMapDataTool())
    register_tool(GetListDataTool())
    
    # 二、水库基础信息接口（3个）
    register_tool(GetReservoirInfoTool())
    register_tool(GetReservoirFloodDetailTool())
    register_tool(GetReservoirFloodListTool())
    
    # 三、水闸堰基础信息接口（2个）
    register_tool(GetSluiceInfoTool())
    register_tool(GetFloodDamInfoTool())
    
    # 四、蓄滞洪区接口（1个）
    register_tool(GetFloodStorageAreaTool())
    
    # 五、河道基础信息接口（1个）
    register_tool(GetRiverFloodListTool())
    
    # 六、测站基础信息接口（1个）
    register_tool(GetStationListTool())
    
    # 七、视频监控基础信息接口（1个）
    register_tool(GetCameraListTool())
    
    # 八、无人机基础信息接口（2个）
    register_tool(GetDroneProjectListTool())
    register_tool(GetDroneDeviceListTool())
    
    # 九、遥感任务接口（1个）
    register_tool(GetRemoteSensingTaskListTool())
    
    logger.info("流域基本信息工具注册完成，共注册14个工具")


# 模块加载时自动注册
register_basin_info_tools()
