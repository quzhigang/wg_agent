"""
网络搜索工具
使用博查Web Search API进行网络搜索
"""

import asyncio
import aiohttp
from typing import Dict, Any, List, Optional

from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class MCPWebSearchClient:
    """网络搜索客户端 - 使用博查API"""

    _instance: Optional['MCPWebSearchClient'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._enabled = settings.web_search_enabled
        self._api_key = settings.web_search_api_key
        self._api_url = settings.web_search_api_url
        self._initialized = True
        logger.info(f"网络搜索客户端初始化完成, enabled={self._enabled}")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """执行博查网络搜索"""
        if not self.is_enabled:
            logger.warning("网络搜索未启用")
            return []

        logger.info(f"执行网络搜索: {query[:50]}...")

        try:
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "query": query,
                "count": max_results,
                "summary": True
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self._api_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        logger.error(f"搜索失败: {resp.status}")
                        return []
                    data = await resp.json()
                    logger.info(f"博查API返回结构: {list(data.keys()) if isinstance(data, dict) else type(data)}")

            results = []
            web_pages = data.get("data", {}).get("webPages", {}).get("value", [])
            if not web_pages:
                web_pages = data.get("webPages", {}).get("value", [])
            if not web_pages:
                web_pages = data.get("results", [])
            if web_pages:
                logger.info(f"第一条结果字段: {list(web_pages[0].keys()) if web_pages else 'empty'}")
            for item in web_pages:
                results.append({
                    'title': item.get('name', '') or item.get('title', ''),
                    'url': item.get('url', '') or item.get('link', ''),
                    'content': item.get('snippet', '') or item.get('summary', '') or item.get('content', ''),
                    'siteName': item.get('siteName', '')
                })

            logger.info(f"网络搜索完成，获取到 {len(results)} 条结果")
            return results
        except Exception as e:
            logger.error(f"网络搜索异常: {e}")
            return []

    async def search_and_format(self, query: str, max_results: int = 5) -> str:
        """执行搜索并格式化为上下文文本"""
        results = await self.search(query, max_results)

        if not results:
            return ""

        context_parts = ["以下是网络搜索结果：\n"]

        for i, result in enumerate(results, 1):
            title = result.get('title', '无标题')
            content = result.get('content', '')
            url = result.get('url', '')
            site_name = result.get('siteName', '')

            context_parts.append(f"[{i}] {title}")
            if content:
                if len(content) > 500:
                    content = content[:500] + "..."
                context_parts.append(content)
            if url:
                source = f"来源: {site_name} - {url}" if site_name else f"来源: {url}"
                context_parts.append(source)
            context_parts.append("")

        return "\n".join(context_parts)


_mcp_client: Optional[MCPWebSearchClient] = None


def get_mcp_websearch_client() -> MCPWebSearchClient:
    """获取网络搜索客户端单例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPWebSearchClient()
    return _mcp_client


async def mcp_web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """网络搜索便捷函数"""
    client = get_mcp_websearch_client()
    return await client.search(query, max_results)


async def mcp_web_search_context(query: str, max_results: int = 5) -> str:
    """网络搜索并返回格式化上下文"""
    client = get_mcp_websearch_client()
    return await client.search_and_format(query, max_results)


def is_mcp_websearch_enabled() -> bool:
    """检查网络搜索是否启用"""
    client = get_mcp_websearch_client()
    return client.is_enabled
