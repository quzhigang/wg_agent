"""
健康检查接口
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..models.database import get_db
from ..models.schemas import APIResponse

router = APIRouter(prefix="/health", tags=["健康检查"])


@router.get("", response_model=APIResponse)
async def health_check():
    """健康检查接口"""
    return APIResponse(
        success=True,
        message="服务运行正常",
        data={
            "status": "healthy",
            "service": "卫共流域数字孪生智能体"
        }
    )


@router.get("/db", response_model=APIResponse)
def database_health_check(db: Session = Depends(get_db)):
    """数据库健康检查"""
    try:
        # 执行简单查询测试数据库连接
        db.execute("SELECT 1")
        return APIResponse(
            success=True,
            message="数据库连接正常",
            data={"database": "connected"}
        )
    except Exception as e:
        return APIResponse(
            success=False,
            message="数据库连接失败",
            error=str(e)
        )
