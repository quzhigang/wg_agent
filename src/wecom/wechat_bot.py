# -*- coding: utf-8 -*-
"""
微信机器人主服务 - 基于 WeChatFerry (wcferry)
接收微信消息 → 调用智能体 SSE 接口 → 将流式结果转发回微信
"""

import asyncio
import os
import time
from pathlib import Path
from threading import Thread
from typing import Dict, Optional

from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class WeChatBot:
    """微信机器人，桥接微信消息与智能体服务"""

    def __init__(self):
        self.wcf = None
        # wxid -> conversation_id 映射，保持会话连续性
        self.conversations: Dict[str, str] = {}
        # 允许对话的微信号白名单
        self.allowed_users = self._parse_allowed_users()
        # 消息发送间隔控制
        self.msg_interval = settings.wechat_msg_interval
        self._last_send_time: Dict[str, float] = {}
        # 异步事件循环（在独立线程中运行）
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _parse_allowed_users(self) -> set:
        """解析白名单配置"""
        raw = settings.wechat_allowed_users.strip()
        if not raw:
            return set()
        return {u.strip() for u in raw.split(",") if u.strip()}

    def _is_allowed(self, wxid: str) -> bool:
        """检查是否允许该用户与机器人对话"""
        if not self.allowed_users:
            return True  # 白名单为空则允许所有人
        return wxid in self.allowed_users

    def _throttle_send(self, wxid: str):
        """消息发送节流，避免频率过高"""
        now = time.time()
        last = self._last_send_time.get(wxid, 0)
        wait = self.msg_interval - (now - last)
        if wait > 0:
            time.sleep(wait)
        self._last_send_time[wxid] = time.time()

    def _send_text(self, text: str, wxid: str):
        """发送文本消息（带节流）"""
        if not text or not text.strip():
            return
        self._throttle_send(wxid)
        try:
            self.wcf.send_text(text, wxid)
        except Exception as e:
            logger.error(f"发送文本消息失败 [{wxid}]: {e}")

    def _send_image(self, img_path: str, wxid: str):
        """发送图片消息（带节流）"""
        if not img_path or not os.path.exists(img_path):
            logger.warning(f"图片文件不存在: {img_path}")
            return
        self._throttle_send(wxid)
        try:
            self.wcf.send_image(img_path, wxid)
        except Exception as e:
            logger.error(f"发送图片消息失败 [{wxid}]: {e}")

    async def _handle_message_async(self, wxid: str, text: str):
        """异步处理单条微信消息，调用智能体 SSE 接口"""
        from .message_handler import MessageHandler
        from .screenshot_service import get_screenshot_service

        handler = MessageHandler()
        screenshot_svc = get_screenshot_service()

        user_id = f"{settings.wechat_user_id_prefix}{wxid}"
        conv_id = self.conversations.get(wxid)

        logger.info(f"处理消息 [{wxid}]: {text[:50]}...")

        try:
            async for event in handler.chat_stream(
                message=text,
                user_id=user_id,
                conversation_id=conv_id
            ):
                event_type = event.get("type", "")

                if event_type == "start":
                    # 记录会话ID
                    new_conv_id = event.get("conversation_id")
                    if new_conv_id:
                        self.conversations[wxid] = new_conv_id
                        conv_id = new_conv_id

                elif event_type == "intent_stage":
                    # 发送意图识别阶段提示
                    stage_label = event.get("stage_label", "")
                    if stage_label:
                        self._send_text(f"[分析] {stage_label}", wxid)

                elif event_type == "plan":
                    # 发送执行计划
                    steps = event.get("steps", [])
                    if steps:
                        plan_lines = [f"  {i+1}. {s}" for i, s in enumerate(steps)]
                        plan_text = "[执行计划]\n" + "\n".join(plan_lines)
                        self._send_text(plan_text, wxid)

                elif event_type == "step_start":
                    # 发送步骤执行提示
                    desc = event.get("description", "")
                    if desc:
                        self._send_text(f"[执行] {desc}", wxid)

                elif event_type == "step_end":
                    # 步骤完成（可选发送）
                    success = event.get("success", True)
                    result_summary = event.get("result_summary", "")
                    if not success:
                        self._send_text(f"[步骤失败] {result_summary}", wxid)

                elif event_type == "rag":
                    # RAG检索完成
                    doc_count = event.get("doc_count", 0)
                    source = event.get("source", "rag")
                    if doc_count > 0:
                        source_name = "知识库" if source == "rag" else "网络搜索"
                        self._send_text(f"[检索] 从{source_name}找到 {doc_count} 条相关信息", wxid)

                elif event_type == "content":
                    # 兼容旧的 content 事件（非分离模式）
                    response_text = event.get("data", "")
                    if response_text:
                        self._send_text(response_text, wxid)
                    page_url = event.get("page_url")
                    if page_url and settings.screenshot_enabled:
                        self._send_text("[截图] 正在生成结果页面截图...", wxid)
                        img_path = await screenshot_svc.capture(page_url)
                        if img_path:
                            self._send_image(img_path, wxid)
                        else:
                            self._send_text("[截图] 页面截图生成失败", wxid)

                elif event_type == "final_text":
                    # 文字回复完成
                    response_text = event.get("data", "")
                    if response_text:
                        self._send_text(response_text, wxid)

                elif event_type == "page_generating":
                    self._send_text("[页面] 正在生成结果展示页面...", wxid)

                elif event_type == "final_page":
                    # 页面生成完成 → 截图 → 发送图片
                    page_url = event.get("page_url")
                    if page_url and settings.screenshot_enabled:
                        self._send_text("[截图] 正在生成结果页面截图...", wxid)
                        img_path = await screenshot_svc.capture(page_url)
                        if img_path:
                            self._send_image(img_path, wxid)
                        else:
                            self._send_text("[截图] 页面截图生成失败", wxid)

                elif event_type == "page_error":
                    error_msg = event.get("error", "页面生成失败")
                    self._send_text(f"[页面错误] {error_msg}", wxid)

                elif event_type == "error":
                    error_msg = event.get("data", "处理出错")
                    self._send_text(f"[错误] {error_msg}", wxid)

                elif event_type == "done":
                    pass  # 流结束

        except Exception as e:
            logger.error(f"处理消息异常 [{wxid}]: {e}", exc_info=True)
            self._send_text(f"[系统错误] 处理消息时发生异常，请稍后重试", wxid)

    def _process_message(self, wxid: str, text: str):
        """在异步事件循环中处理消息"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._handle_message_async(wxid, text),
                self._loop
            )
        else:
            logger.error("异步事件循环未运行，无法处理消息")

    def _start_async_loop(self):
        """在独立线程中启动异步事件循环"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def start(self):
        """启动微信机器人（阻塞方法，应在独立线程中调用）"""
        try:
            from wcferry import Wcf
        except ImportError:
            logger.error("wcferry 未安装，请执行: pip install --upgrade wcferry")
            logger.error("同时需要安装对应版本的 PC 微信并登录")
            return

        logger.info("=" * 50)
        logger.info("微信机器人「小卫」启动中...")
        logger.info(f"wcferry RPC 端口: {settings.wechat_wcf_port}")
        logger.info(f"智能体 API 地址: {settings.wechat_agent_api_url}")
        if self.allowed_users:
            logger.info(f"白名单用户: {self.allowed_users}")
        else:
            logger.info("白名单: 未设置（允许所有人）")
        logger.info("=" * 50)

        # 启动异步事件循环线程
        async_thread = Thread(target=self._start_async_loop, daemon=True)
        async_thread.start()

        try:
            # 初始化 wcferry，阻塞等待微信登录
            self.wcf = Wcf(port=settings.wechat_wcf_port, debug=False, block=True)
            self_wxid = self.wcf.get_self_wxid()
            user_info = self.wcf.get_user_info()
            logger.info(f"微信登录成功! wxid: {self_wxid}")
            logger.info(f"昵称: {user_info.get('name', '未知')}")

            # 开启消息接收
            self.wcf.enable_receiving_msg()
            logger.info("消息接收已开启，等待消息...")

            # 消息循环
            while self.wcf.is_receiving_msg():
                try:
                    msg = self.wcf.get_msg()

                    # 忽略自己发的消息
                    if msg.from_self():
                        continue

                    # 只处理私聊文本消息（type=1 为文本）
                    if msg.from_group():
                        continue  # 暂不处理群消息

                    if not msg.is_text():
                        self._send_text("目前只支持文字消息哦~", msg.sender)
                        continue

                    # 检查白名单
                    if not self._is_allowed(msg.sender):
                        logger.debug(f"非白名单用户消息，忽略: {msg.sender}")
                        continue

                    # 异步处理消息
                    self._process_message(msg.sender, msg.content)

                except Exception as e:
                    logger.error(f"消息循环异常: {e}", exc_info=True)
                    time.sleep(1)

        except KeyboardInterrupt:
            logger.info("收到中断信号，微信机器人停止")
        except Exception as e:
            logger.error(f"微信机器人启动失败: {e}", exc_info=True)
        finally:
            if self.wcf:
                try:
                    self.wcf.cleanup()
                except Exception:
                    pass
            if self._loop:
                self._loop.call_soon_threadsafe(self._loop.stop)
            logger.info("微信机器人已停止")


def start_wechat_bot():
    """启动微信机器人的入口函数"""
    bot = WeChatBot()
    bot.start()
