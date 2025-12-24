"""
工具模块
封装5类API工具：流域基本信息、水雨情监测数据、防洪业务、水利专业模型、灾损评估
以及MCP网络搜索工具
"""

from .registry import ToolRegistry, get_tool_registry, register_tool
from .base import BaseTool, ToolResult
from .mcp_websearch import (
    MCPWebSearchClient,
    get_mcp_websearch_client,
    mcp_web_search,
    mcp_web_search_context,
    is_mcp_websearch_enabled
)

__all__ = [
    "ToolRegistry",
    "get_tool_registry",
    "register_tool",
    "BaseTool",
    "ToolResult",
    # MCP网络搜索
    "MCPWebSearchClient",
    "get_mcp_websearch_client",
    "mcp_web_search",
    "mcp_web_search_context",
    "is_mcp_websearch_enabled"
]
