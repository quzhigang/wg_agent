"""
输出模块
提供Web页面生成和报告输出功能
"""

from .page_generator import PageGenerator, get_page_generator
from .templates import TemplateManager

__all__ = [
    "PageGenerator",
    "get_page_generator",
    "TemplateManager"
]
