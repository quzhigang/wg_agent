"""
页面服务接口
提供生成的Web报告页面的访问
"""

from typing import Optional, List
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse

from ..config.logging_config import get_logger
from ..config.settings import settings
from ..output.page_generator import get_page_generator
from ..models.schemas import APIResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/pages", tags=["页面"])


@router.get("/{filename}")
async def get_page(filename: str):
    """
    获取生成的报告页面
    
    Args:
        filename: 页面文件名
        
    Returns:
        HTML页面内容
    """
    try:
        generator = get_page_generator()
        file_path = generator._output_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="页面不存在")
        
        # 检查文件是否在允许的目录下（安全检查）
        try:
            file_path.resolve().relative_to(generator._output_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="访问被拒绝")
        
        return FileResponse(
            path=file_path,
            media_type="text/html",
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取页面失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=APIResponse)
async def list_pages():
    """
    列出所有生成的页面
    
    Returns:
        页面列表
    """
    try:
        generator = get_page_generator()
        pages = generator.list_pages()
        
        return APIResponse(
            success=True,
            message="获取成功",
            data=pages
        )
        
    except Exception as e:
        logger.error(f"列出页面失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filename}", response_model=APIResponse)
async def delete_page(filename: str):
    """
    删除生成的页面
    
    Args:
        filename: 页面文件名
        
    Returns:
        删除结果
    """
    try:
        generator = get_page_generator()
        page_url = f"/pages/{filename}"
        
        success = generator.delete_page(page_url)
        
        if not success:
            raise HTTPException(status_code=404, detail="页面不存在")
        
        return APIResponse(
            success=True,
            message="删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除页面失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
