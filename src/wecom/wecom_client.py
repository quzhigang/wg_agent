# -*- coding: utf-8 -*-
"""
企业微信 API 客户端
封装 access_token 管理、消息发送、素材上传等接口
"""

import time
import asyncio
from typing import Optional, List

import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)

WECOM_API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"


class WeComClient:
    """企业微信 API 客户端"""

    def __init__(self):
        self.corp_id = settings.wecom_corp_id
        self.secret = settings.wecom_secret
        self.agent_id = settings.wecom_agent_id
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._token_lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        """获取 access_token，带缓存和自动刷新（提前 5 分钟）"""
        if self._access_token and time.time() < self._token_expires_at - 300:
            return self._access_token

        async with self._token_lock:
            # 双重检查
            if self._access_token and time.time() < self._token_expires_at - 300:
                return self._access_token

            url = f"{WECOM_API_BASE}/gettoken"
            params = {"corpid": self.corp_id, "corpsecret": self.secret}

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, params=params)
                data = resp.json()

            if data.get("errcode") != 0:
                raise RuntimeError(f"获取 access_token 失败: {data}")

            self._access_token = data["access_token"]
            self._token_expires_at = time.time() + data.get("expires_in", 7200)
            logger.info(f"access_token 已刷新，有效期至 {time.strftime('%H:%M:%S', time.localtime(self._token_expires_at))}")
            return self._access_token

    async def send_text(self, user_id: str, content: str):
        """发送文本消息，超长自动分段（企业微信限制 2048 字节）"""
        if not content or not content.strip():
            return
        segments = self._split_text(content, max_bytes=2048)
        for segment in segments:
            await self._send_message({
                "touser": user_id,
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {"content": segment}
            })

    async def send_image(self, user_id: str, image_path: str):
        """发送图片消息：先上传临时素材获取 media_id，再发送"""
        media_id = await self._upload_media(image_path, media_type="image")
        if not media_id:
            logger.error(f"图片上传失败，无法发送: {image_path}")
            return
        await self._send_message({
            "touser": user_id,
            "msgtype": "image",
            "agentid": self.agent_id,
            "image": {"media_id": media_id}
        })

    async def send_markdown(self, user_id: str, content: str):
        """发送 Markdown 消息（仅企业微信内部可见，外部联系人不支持）"""
        if not content or not content.strip():
            return
        await self._send_message({
            "touser": user_id,
            "msgtype": "markdown",
            "agentid": self.agent_id,
            "markdown": {"content": content}
        })

    async def _send_message(self, payload: dict):
        """调用 message/send 接口，token 过期自动重试"""
        token = await self.get_access_token()
        url = f"{WECOM_API_BASE}/message/send?access_token={token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()

        if data.get("errcode") == 0:
            return

        logger.error(f"发送消息失败: {data}")

        # token 过期（42001）或无效（40014），清除缓存重试一次
        if data.get("errcode") in (42001, 40014):
            self._access_token = None
            token = await self.get_access_token()
            url = f"{WECOM_API_BASE}/message/send?access_token={token}"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
            if data.get("errcode") != 0:
                logger.error(f"重试发送消息仍失败: {data}")

    async def _upload_media(self, file_path: str, media_type: str = "image") -> Optional[str]:
        """上传临时素材，返回 media_id"""
        import os
        if not os.path.exists(file_path):
            logger.error(f"素材文件不存在: {file_path}")
            return None

        token = await self.get_access_token()
        url = f"{WECOM_API_BASE}/media/upload?access_token={token}&type={media_type}"

        try:
            filename = os.path.basename(file_path)
            async with httpx.AsyncClient(timeout=30.0) as client:
                with open(file_path, "rb") as f:
                    files = {"media": (filename, f, "image/png")}
                    resp = await client.post(url, files=files)
                    data = resp.json()

            if data.get("errcode") and data["errcode"] != 0:
                logger.error(f"上传素材失败: {data}")
                return None
            return data.get("media_id")
        except Exception as e:
            logger.error(f"上传素材异常: {e}")
            return None

    @staticmethod
    def _split_text(text: str, max_bytes: int = 2048) -> List[str]:
        """按字节数分段文本，避免截断 UTF-8 多字节字符"""
        if len(text.encode("utf-8")) <= max_bytes:
            return [text]

        segments = []
        current = ""
        for char in text:
            test = current + char
            if len(test.encode("utf-8")) > max_bytes - 20:  # 留余量
                segments.append(current)
                current = char
            else:
                current = test
        if current:
            segments.append(current)
        return segments


# 全局单例
_wecom_client: Optional[WeComClient] = None


def get_wecom_client() -> WeComClient:
    """获取企业微信客户端单例"""
    global _wecom_client
    if _wecom_client is None:
        _wecom_client = WeComClient()
    return _wecom_client
