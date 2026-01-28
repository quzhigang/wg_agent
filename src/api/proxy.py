"""
API代理模块
用于转发前端请求到外部API，解决CORS跨域问题
"""

import httpx
from fastapi import APIRouter, Query, Header, HTTPException
from typing import Optional
from ..config.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/proxy", tags=["代理"])

# 外部API基础URL
MIKE11_API_BASE = "http://10.20.2.153/api/model/proxy/mike11"


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
