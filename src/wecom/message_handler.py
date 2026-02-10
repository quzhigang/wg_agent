# -*- coding: utf-8 -*-
"""
消息处理器 - 调用智能体 SSE 流式接口，解析事件流
"""

import json
import httpx
from typing import AsyncGenerator, Dict, Any, Optional

from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class MessageHandler:
    """调用智能体 /chat/stream 接口，逐事件返回"""

    def __init__(self):
        self.api_url = settings.wechat_agent_api_url

    async def chat_stream(
        self,
        message: str,
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        调用 /chat/stream SSE 接口，逐事件 yield 解析后的 JSON

        Args:
            message: 用户消息文本
            user_id: 用户ID（带 wx_ 前缀）
            conversation_id: 会话ID，为空则由后端创建新会话

        Yields:
            解析后的 SSE 事件字典
        """
        url = f"{self.api_url}/chat/stream"
        payload = {
            "message": message,
            "user_id": user_id,
        }
        if conversation_id:
            payload["conversation_id"] = conversation_id

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
                async with client.stream("POST", url, json=payload) as resp:
                    if resp.status_code != 200:
                        logger.error(f"智能体接口返回异常状态码: {resp.status_code}")
                        yield {"type": "error", "data": f"接口返回状态码 {resp.status_code}"}
                        return

                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith("data: "):
                            json_str = line[6:]
                            try:
                                event = json.loads(json_str)
                                yield event
                            except json.JSONDecodeError as e:
                                logger.warning(f"SSE JSON解析失败: {e}, 原始数据: {json_str[:200]}")
                                continue

        except httpx.ConnectError as e:
            logger.error(f"无法连接智能体服务 {url}: {e}")
            yield {"type": "error", "data": f"无法连接智能体服务: {e}"}
        except httpx.ReadTimeout:
            logger.error("智能体服务响应超时")
            yield {"type": "error", "data": "智能体服务响应超时"}
        except Exception as e:
            logger.error(f"调用智能体服务异常: {e}")
            yield {"type": "error", "data": f"调用异常: {e}"}
