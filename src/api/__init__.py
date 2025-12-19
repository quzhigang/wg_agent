"""
API模块
提供RESTful API接口
"""

from .health import router as health_router
from .chat import router as chat_router
from .pages import router as pages_router
from .knowledge import router as knowledge_router

__all__ = [
    "health_router",
    "chat_router",
    "pages_router",
    "knowledge_router"
]
