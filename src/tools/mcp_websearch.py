"""
网络搜索工具
使用Bing搜索进行网络搜索，作为RAG检索失败时的备选方案
"""

import asyncio
import re
import aiohttp
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup

from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class MCPWebSearchClient:
    """网络搜索客户端 - 使用Bing搜索"""

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
        self._timeout = aiohttp.ClientTimeout(total=30)
        self._initialized = True
        logger.info(f"网络搜索客户端初始化完成, enabled={self._enabled}")

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """执行Bing网络搜索"""
        if not self.is_enabled:
            logger.warning("网络搜索未启用")
            return []

        logger.info(f"执行网络搜索: {query[:50]}...")

        try:
            from urllib.parse import quote
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            }
            encoded_query = quote(query)
            url = f"https://www.bing.com/search?q={encoded_query}&count={max_results}"

            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Bing搜索失败: {response.status}")
                        return []
                    html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')
            results = []

            for item in soup.select('.b_algo')[:max_results]:
                title_elem = item.select_one('h2 a')
                snippet_elem = item.select_one('.b_caption p')

                if title_elem:
                    results.append({
                        'title': title_elem.get_text(strip=True),
                        'url': title_elem.get('href', ''),
                        'content': snippet_elem.get_text(strip=True) if snippet_elem else ''
                    })

            logger.info(f"网络搜索完成，获取到 {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"网络搜索异常: {e}")
            return []
    
    async def search_and_format(self, query: str, max_results: int = 5) -> str:
        """
        执行搜索并格式化为上下文文本
        
        Args:
            query: 搜索查询
            max_results: 最大返回结果数
            
        Returns:
            格式化的搜索结果文本
        """
        results = await self.search(query, max_results)
        
        if not results:
            return ""
        
        # 格式化为上下文
        context_parts = ["以下是网络搜索结果：\n"]
        
        for i, result in enumerate(results, 1):
            title = result.get('title', '无标题')
            content = result.get('content', result.get('snippet', ''))
            url = result.get('url', result.get('link', ''))
            
            context_parts.append(f"[{i}] {title}")
            if content:
                # 截断过长的内容
                if len(content) > 500:
                    content = content[:500] + "..."
                context_parts.append(content)
            if url:
                context_parts.append(f"来源: {url}")
            context_parts.append("")  # 空行分隔
        
        return "\n".join(context_parts)


# 全局客户端实例
_mcp_client: Optional[MCPWebSearchClient] = None


def get_mcp_websearch_client() -> MCPWebSearchClient:
    """获取网络搜索客户端单例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPWebSearchClient()
    return _mcp_client


async def mcp_web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    网络搜索便捷函数
    
    Args:
        query: 搜索查询
        max_results: 最大返回结果数
        
    Returns:
        搜索结果列表
    """
    client = get_mcp_websearch_client()
    return await client.search(query, max_results)


async def mcp_web_search_context(query: str, max_results: int = 5) -> str:
    """
    网络搜索并返回格式化上下文
    
    Args:
        query: 搜索查询
        max_results: 最大返回结果数
        
    Returns:
        格式化的搜索结果文本
    """
    client = get_mcp_websearch_client()
    return await client.search_and_format(query, max_results)


def is_mcp_websearch_enabled() -> bool:
    """检查网络搜索是否启用"""
    client = get_mcp_websearch_client()
    return client.is_enabled
