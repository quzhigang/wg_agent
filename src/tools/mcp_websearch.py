"""
MCP网络搜索工具
通过智谱Web Search MCP进行网络搜索，作为RAG检索失败时的备选方案
"""

import json
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional

from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class MCPWebSearchClient:
    """
    MCP网络搜索客户端
    
    通过SSE连接调用智谱Web Search MCP服务
    """
    
    _instance: Optional['MCPWebSearchClient'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._base_url = settings.mcp_zhipu_websearch_url
        self._api_key = settings.mcp_zhipu_websearch_api_key
        self._enabled = settings.mcp_zhipu_websearch_enabled
        self._timeout = aiohttp.ClientTimeout(total=30)
        self._initialized = True
        
        logger.info(f"MCP网络搜索客户端初始化完成, enabled={self._enabled}")
    
    @property
    def is_enabled(self) -> bool:
        """检查MCP网络搜索是否启用"""
        return self._enabled and bool(self._base_url) and bool(self._api_key)
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        执行网络搜索
        
        Args:
            query: 搜索查询
            max_results: 最大返回结果数
            
        Returns:
            搜索结果列表，每个结果包含title, content, url等字段
        """
        if not self.is_enabled:
            logger.warning("MCP网络搜索未启用或配置不完整")
            return []
        
        logger.info(f"执行MCP网络搜索: {query[:50]}...")
        
        try:
            # 构建请求头
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream"
            }
            
            # 构建MCP工具调用请求
            request_data = {
                "method": "tools/call",
                "params": {
                    "name": "web-search",
                    "arguments": {
                        "query": query,
                        "count": max_results
                    }
                }
            }
            
            results = []
            
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.post(
                    self._base_url,
                    headers=headers,
                    json=request_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"MCP搜索请求失败: {response.status} - {error_text}")
                        return []
                    
                    # 解析SSE响应
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if not line or line.startswith(':'):
                            continue
                        
                        if line.startswith('data:'):
                            data_str = line[5:].strip()
                            if data_str:
                                try:
                                    data = json.loads(data_str)
                                    # 解析搜索结果
                                    if 'result' in data:
                                        result_content = data['result']
                                        if isinstance(result_content, dict) and 'content' in result_content:
                                            # 解析content中的搜索结果
                                            content_list = result_content.get('content', [])
                                            for item in content_list:
                                                if item.get('type') == 'text':
                                                    text_content = item.get('text', '')
                                                    # 尝试解析JSON格式的搜索结果
                                                    try:
                                                        search_results = json.loads(text_content)
                                                        if isinstance(search_results, list):
                                                            results.extend(search_results)
                                                        elif isinstance(search_results, dict):
                                                            results.append(search_results)
                                                    except json.JSONDecodeError:
                                                        # 如果不是JSON，作为纯文本结果
                                                        results.append({
                                                            'content': text_content,
                                                            'title': '搜索结果',
                                                            'url': ''
                                                        })
                                except json.JSONDecodeError as e:
                                    logger.warning(f"解析SSE数据失败: {e}")
                                    continue
            
            logger.info(f"MCP网络搜索完成，获取到 {len(results)} 条结果")
            return results[:max_results]
            
        except asyncio.TimeoutError:
            logger.error("MCP网络搜索超时")
            return []
        except aiohttp.ClientError as e:
            logger.error(f"MCP网络搜索网络错误: {e}")
            return []
        except Exception as e:
            logger.error(f"MCP网络搜索异常: {e}")
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
    """获取MCP网络搜索客户端单例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPWebSearchClient()
    return _mcp_client


async def mcp_web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    MCP网络搜索便捷函数
    
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
    MCP网络搜索并返回格式化上下文
    
    Args:
        query: 搜索查询
        max_results: 最大返回结果数
        
    Returns:
        格式化的搜索结果文本
    """
    client = get_mcp_websearch_client()
    return await client.search_and_format(query, max_results)


def is_mcp_websearch_enabled() -> bool:
    """检查MCP网络搜索是否启用"""
    client = get_mcp_websearch_client()
    return client.is_enabled
