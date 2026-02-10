# -*- coding: utf-8 -*-
"""
企业微信回调路由
处理消息接收（POST）和 URL 验证（GET）
"""

import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request, Query, Response, BackgroundTasks

from ..config.settings import settings
from ..config.logging_config import get_logger
from .crypto import WXBizMsgCrypt
from .wecom_client import get_wecom_client
from .message_handler import MessageHandler
from .screenshot_service import get_screenshot_service

logger = get_logger(__name__)

router = APIRouter(prefix="/wecom", tags=["企业微信"])

# 加解密实例（延迟初始化）
_crypto = None


def _get_crypto() -> WXBizMsgCrypt:
    global _crypto
    if _crypto is None:
        _crypto = WXBizMsgCrypt(
            token=settings.wecom_token,
            encoding_aes_key=settings.wecom_encoding_aes_key,
            corp_id=settings.wecom_corp_id
        )
    return _crypto


# userid -> conversation_id 映射，保持会话连续性
_conversations: dict = {}


@router.get("/callback")
async def verify_url(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """
    企业微信回调 URL 验证（GET 请求）
    解密 echostr 并原样返回明文
    """
    try:
        crypto = _get_crypto()
        reply_echostr = crypto.verify_url(msg_signature, timestamp, nonce, echostr)
        logger.info("企业微信回调URL验证成功")
        return Response(content=reply_echostr, media_type="text/plain")
    except Exception as e:
        logger.error(f"回调URL验证失败: {e}")
        return Response(content="验证失败", status_code=403)


@router.post("/callback")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...)
):
    """
    接收企业微信推送的消息（POST 请求）
    解密消息后在后台异步处理，5 秒内返回空字符串
    """
    try:
        body = await request.body()
        post_data = body.decode("utf-8")

        crypto = _get_crypto()
        decrypted_xml = crypto.decrypt_msg(msg_signature, timestamp, nonce, post_data)

        xml_tree = ET.fromstring(decrypted_xml)
        msg_type = xml_tree.find("MsgType").text
        from_user = xml_tree.find("FromUserName").text

        logger.info(f"收到企业微信消息: type={msg_type}, from={from_user}")

        if msg_type == "text":
            content = xml_tree.find("Content").text
            # 检查白名单
            if not _is_allowed(from_user):
                logger.debug(f"非白名单用户消息，忽略: {from_user}")
                return Response(content="", media_type="text/plain")
            background_tasks.add_task(_handle_text_message, from_user, content)
        else:
            background_tasks.add_task(_send_unsupported_hint, from_user)

        return Response(content="", media_type="text/plain")

    except Exception as e:
        logger.error(f"处理企业微信消息异常: {e}", exc_info=True)
        return Response(content="", media_type="text/plain")


def _is_allowed(user_id: str) -> bool:
    """检查用户是否在白名单"""
    raw = settings.wecom_allowed_users.strip()
    if not raw:
        return True
    allowed = {u.strip() for u in raw.split(",") if u.strip()}
    return user_id in allowed


async def _send_unsupported_hint(user_id: str):
    """发送不支持的消息类型提示"""
    client = get_wecom_client()
    await client.send_text(user_id, "目前只支持文字消息哦~")


async def _handle_text_message(user_id: str, text: str):
    """
    处理文本消息 - 核心逻辑
    复用 MessageHandler 的 SSE 事件流处理
    """
    handler = MessageHandler()
    screenshot_svc = get_screenshot_service()
    client = get_wecom_client()

    prefixed_user_id = f"{settings.wecom_user_id_prefix}{user_id}"
    conv_id = _conversations.get(user_id)

    logger.info(f"处理企业微信消息 [{user_id}]: {text[:50]}...")

    try:
        async for event in handler.chat_stream(
            message=text,
            user_id=prefixed_user_id,
            conversation_id=conv_id
        ):
            event_type = event.get("type", "")

            if event_type == "start":
                new_conv_id = event.get("conversation_id")
                if new_conv_id:
                    _conversations[user_id] = new_conv_id
                    conv_id = new_conv_id

            elif event_type == "intent_stage":
                stage_label = event.get("stage_label", "")
                if stage_label:
                    await client.send_text(user_id, f"[分析] {stage_label}")

            elif event_type == "plan":
                steps = event.get("steps", [])
                if steps:
                    plan_lines = [f"  {i+1}. {s}" for i, s in enumerate(steps)]
                    plan_text = "[执行计划]\n" + "\n".join(plan_lines)
                    await client.send_text(user_id, plan_text)

            elif event_type == "step_start":
                desc = event.get("description", "")
                if desc:
                    await client.send_text(user_id, f"[执行] {desc}")

            elif event_type == "step_end":
                success = event.get("success", True)
                result_summary = event.get("result_summary", "")
                if not success:
                    await client.send_text(user_id, f"[步骤失败] {result_summary}")

            elif event_type == "rag":
                doc_count = event.get("doc_count", 0)
                source = event.get("source", "rag")
                if doc_count > 0:
                    source_name = "知识库" if source == "rag" else "网络搜索"
                    await client.send_text(user_id, f"[检索] 从{source_name}找到 {doc_count} 条相关信息")

            elif event_type == "content":
                response_text = event.get("data", "")
                if response_text:
                    await client.send_text(user_id, response_text)
                page_url = event.get("page_url")
                if page_url and settings.screenshot_enabled:
                    await client.send_text(user_id, "[截图] 正在生成结果页面截图...")
                    img_path = await screenshot_svc.capture(page_url)
                    if img_path:
                        await client.send_image(user_id, img_path)
                    else:
                        await client.send_text(user_id, "[截图] 页面截图生成失败")

            elif event_type == "final_text":
                response_text = event.get("data", "")
                if response_text:
                    await client.send_text(user_id, response_text)

            elif event_type == "page_generating":
                await client.send_text(user_id, "[页面] 正在生成结果展示页面...")

            elif event_type == "final_page":
                page_url = event.get("page_url")
                if page_url and settings.screenshot_enabled:
                    await client.send_text(user_id, "[截图] 正在生成结果页面截图...")
                    img_path = await screenshot_svc.capture(page_url)
                    if img_path:
                        await client.send_image(user_id, img_path)
                    else:
                        await client.send_text(user_id, "[截图] 页面截图生成失败")

            elif event_type == "page_error":
                error_msg = event.get("error", "页面生成失败")
                await client.send_text(user_id, f"[页面错误] {error_msg}")

            elif event_type == "error":
                error_msg = event.get("data", "处理出错")
                await client.send_text(user_id, f"[错误] {error_msg}")

            elif event_type == "done":
                pass

    except Exception as e:
        logger.error(f"处理企业微信消息异常 [{user_id}]: {e}", exc_info=True)
        await client.send_text(user_id, "[系统错误] 处理消息时发生异常，请稍后重试")
