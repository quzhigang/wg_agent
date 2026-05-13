"""
API代理模块
用于转发前端请求到外部API，解决CORS跨域问题
"""

import httpx
from fastapi import APIRouter, Query, Header, HTTPException
from typing import Optional
from ..config.logging_config import get_logger
from ..config.settings import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/proxy", tags=["代理"])

# 外部API基础URL
MIKE11_API_BASE = "http://10.20.2.153/api/model/proxy/mike11"
MAP_DATA_API = "http://10.20.2.153/api/basin/map/dataSource/table/map"
HYDRO_DATA_API_BASE = settings.wg_data_server_url.rstrip("/")


async def _proxy_hydro_process(
    endpoint: str,
    stcd: str,
    start_time: str,
    end_time: str,
    authorization: Optional[str] = None
):
    """代理水雨情过程接口，供静态模板跨域访问。"""
    url = f"{HYDRO_DATA_API_BASE}{endpoint}"
    params = {
        "STCD": stcd,
        "searchBeginTime": start_time,
        "searchEndTime": end_time
    }

    headers = {"Accept": "*/*"}
    if authorization:
        headers["Authorization"] = authorization

    logger.info(f"代理请求水情过程: endpoint={endpoint}, stcd={stcd}, {start_time} ~ {end_time}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"水情过程接口HTTP错误: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            logger.error(f"水情过程接口请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")


@router.get("/map/location")
async def get_map_location(
    ref_table: str = Query(..., description="数据表名: geo_st_base(测站), geo_res_base(水库)"),
    stcd: str = Query(..., description="测站/水库编码"),
    authorization: Optional[str] = Header(None)
):
    """
    获取测站或水库的坐标位置
    代理转发到: http://10.20.2.153/api/basin/map/dataSource/table/map
    """
    # 根据表名确定查询字段：测站表用code，水库表用stcd
    if ref_table == 'geo_st_base':
        filter_field = 'code'
    else:
        filter_field = 'stcd'

    # 构建请求参数
    params = {
        'refTable': ref_table,
        'where[0][filed]': filter_field,
        'where[0][rela]': '=',
        'where[0][value]': f"'{stcd}'"
    }

    headers = {"Accept": "*/*"}
    if authorization:
        headers["Authorization"] = authorization

    logger.info(f"代理请求地图坐标: ref_table={ref_table}, {filter_field}={stcd}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(MAP_DATA_API, params=params, headers=headers)
            response.raise_for_status()
            result = response.json()

            # 解析坐标
            if result.get('success') and result.get('data') and len(result['data']) > 0:
                data = result['data'][0]

                # 优先从 longitude/latitude 字段获取（测站表）
                lng = data.get('longitude')
                lat = data.get('latitude')

                # 如果没有，尝试从 shape 字段获取（水库表）
                if not lng or not lat:
                    shape = data.get('shape')
                    if shape:
                        lng = shape.get('x')
                        lat = shape.get('y')

                if lng and lat:
                    logger.info(f"获取到坐标: 经度={lng}, 纬度={lat}")
                    return {
                        "success": True,
                        "longitude": lng,
                        "latitude": lat
                    }

            logger.warning(f"未找到坐标数据: ref_table={ref_table}, {filter_field}={stcd}")
            return {"success": False, "message": "未找到坐标数据"}

        except httpx.HTTPStatusError as e:
            logger.error(f"地图坐标接口HTTP错误: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            logger.error(f"地图坐标接口请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")


@router.get("/mike11/station_info")
async def get_station_info(
    authorization: Optional[str] = Header(None)
):
    """
    获取站点信息列表
    代理转发到: http://10.20.2.153/api/model/proxy/mike11?request_type=get_station_info
    """
    url = f"{MIKE11_API_BASE}?request_type=get_station_info"

    headers = {"Accept": "*/*"}
    if authorization:
        headers["Authorization"] = authorization

    logger.info(f"代理请求站点信息: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"站点信息接口HTTP错误: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            logger.error(f"站点信息接口请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")


@router.get("/hydro/reservoir_process")
async def get_reservoir_process(
    stcd: str = Query(..., description="水库测站编码"),
    start_time: str = Query(..., description="查询开始时间，格式 yyyy-MM-dd HH:mm:ss"),
    end_time: str = Query(..., description="查询结束时间，格式 yyyy-MM-dd HH:mm:ss"),
    authorization: Optional[str] = Header(None)
):
    """
    获取水库实测水情过程。
    代理转发到: /api/basin/rwdb/rsvr/processList
    """
    return await _proxy_hydro_process(
        endpoint="/api/basin/rwdb/rsvr/processList",
        stcd=stcd,
        start_time=start_time,
        end_time=end_time,
        authorization=authorization
    )


@router.get("/hydro/river_process")
async def get_river_process(
    stcd: str = Query(..., description="河道测站编码"),
    start_time: str = Query(..., description="查询开始时间，格式 yyyy-MM-dd HH:mm:ss"),
    end_time: str = Query(..., description="查询结束时间，格式 yyyy-MM-dd HH:mm:ss"),
    authorization: Optional[str] = Header(None)
):
    """
    获取河道实测水情过程。
    代理转发到: /api/basin/rwdb/river/processList
    """
    return await _proxy_hydro_process(
        endpoint="/api/basin/rwdb/river/processList",
        stcd=stcd,
        start_time=start_time,
        end_time=end_time,
        authorization=authorization
    )


@router.get("/mike11/section_data")
async def get_section_data(
    reach: str = Query(..., description="河道名称"),
    chainage: float = Query(..., description="桩号"),
    authorization: Optional[str] = Header(None)
):
    """
    获取断面地形数据
    代理转发到: http://10.20.2.153/api/model/proxy/mike11?request_type=get_sectiondata&request_pars=["河道名称",桩号]
    """
    import urllib.parse
    import json

    # 构建 request_pars 参数: ["DSH", 64250]
    request_pars = json.dumps([reach, chainage])
    encoded_pars = urllib.parse.quote(request_pars)
    url = f"{MIKE11_API_BASE}?request_type=get_sectiondata&request_pars={encoded_pars}"

    headers = {"Accept": "*/*"}
    if authorization:
        headers["Authorization"] = authorization

    logger.info(f"代理请求断面数据: {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(url, headers=headers)
            logger.info(f"断面数据响应状态: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"断面数据接口HTTP错误: {e.response.status_code} - {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            logger.error(f"断面数据接口请求失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"代理请求失败: {str(e)}")
