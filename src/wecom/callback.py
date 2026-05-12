# -*- coding: utf-8 -*-
"""
企业微信回调路由
处理消息接收（POST）和 URL 验证（GET）
"""

import asyncio
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request, Query, Response, BackgroundTasks

from ..config.settings import settings
from ..config.logging_config import get_logger
from .crypto import WXBizMsgCrypt
from .wecom_client import get_wecom_client
from .message_handler import MessageHandler
from .screenshot_service import get_screenshot_service

logger = get_logger(__name__)

# ---- 意图中文映射（与前端保持一致） ----
CATEGORY_MAP = {
    "chat": "一般对话",
    "knowledge": "知识查询",
    "business": "业务操作",
}
SUB_INTENT_MAP = {
    "data_query": "监测数据查询",
    "flood_forecast": "洪水预报",
    "flood_simulation": "洪水预演",
    "emergency_plan": "预案生成",
    "damage_assessment": "灾损评估",
    "other": "其他业务",
}
WORKFLOW_NAME_MAP = {
    "get_auto_forecast_result": "查询最新自动预报结果",
    "get_history_autoforecast_result": "查询历史自动预报结果",
    "flood_autoforecast_getresult": "启动自动预报并获取结果",
    "get_manual_forecast_result": "查询人工预报结果",
    "flood_manualforecast_getresult": "启动人工预报并获取结果",
}

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

    消息策略：
    1. 收到消息后立即发送"正在分析意图..."，让用户感知系统已响应
    2. 意图识别三阶段累积结果，在最终阶段一次性发送完整结果
    3. 执行计划只展示中文步骤描述
    4. 执行过程用进度卡片展示（✅/⏳/○），不逐条刷屏
    5. 文字回复和页面截图谁先就先推送
    """
    handler = MessageHandler()
    screenshot_svc = get_screenshot_service()
    client = get_wecom_client()

    prefixed_user_id = f"{settings.wecom_user_id_prefix}{user_id}"
    conv_id = _conversations.get(user_id)

    # 跟踪已发送状态
    text_sent = False
    page_sent = False
    screenshot_task = None

    # 意图识别累积状态
    intent_info = {}
    intent_sent = False  # 标记意图识别结果是否已发送
    intent_done_event = asyncio.Event()  # 用于通知等待提示定时器停止
    # 执行计划步骤列表和完成状态
    plan_steps = []
    completed_steps = set()
    failed_steps = {}  # step_id -> result_summary
    # 页面生成提示延迟发送（等文字回复之后再发）
    page_generating_pending = False

    logger.info(f"处理企业微信消息 [{user_id}]: {text[:50]}...")

    # 立即发送"正在分析"提示，不等待任何后端事件
    await client.send_text(user_id, "正在分析意图...")

    # 等待提示定时器：如果意图识别耗时较长，发送递进提示让用户感知系统仍在工作
    thinking_hints = [
        (5, "正在理解您的问题..."),
        (12, "正在深入分析中，请稍候..."),
    ]
    thinking_task = asyncio.create_task(
        _send_thinking_hints(user_id, client, thinking_hints, intent_done_event)
    )

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
                # 累积意图识别结果，不逐条发送
                stage_name = event.get("stage_name", "")
                if stage_name == "intent_category":
                    intent_info["category"] = event.get("intent_category", "")
                    intent_info["confidence"] = event.get("confidence", 0)
                elif stage_name == "business_sub_intent":
                    intent_info["sub_intent"] = event.get("business_sub_intent", "")
                elif stage_name == "workflow_match":
                    intent_info["workflow"] = event.get("matched_workflow", "")
                    # 最终阶段到达，一次性发送完整意图识别结果
                    if not intent_sent:
                        await client.send_text(user_id, _format_intent_result(intent_info))
                        intent_sent = True
                        intent_done_event.set()

            elif event_type == "intent":
                # 兼容旧的一次性 intent 事件（非分阶段模式）
                if not intent_sent:
                    intent_info["category"] = event.get("intent_category", "")
                    intent_info["confidence"] = event.get("confidence", 0)
                    intent_info["sub_intent"] = event.get("business_sub_intent", "")
                    intent_info["workflow"] = event.get("matched_workflow", "")
                    await client.send_text(user_id, _format_intent_result(intent_info))
                    intent_sent = True
                    intent_done_event.set()

            elif event_type == "plan":
                # 确保意图识别结果在执行计划之前发送
                if not intent_sent and intent_info:
                    await client.send_text(user_id, _format_intent_result(intent_info))
                    intent_sent = True
                    intent_done_event.set()
                steps = event.get("steps", [])
                if steps:
                    plan_steps = steps
                    await client.send_text(user_id, _format_plan(plan_steps))

            elif event_type == "step_start":
                # 确保意图识别结果已发送
                if not intent_sent and intent_info:
                    await client.send_text(user_id, _format_intent_result(intent_info))
                    intent_sent = True
                    intent_done_event.set()

            elif event_type == "step_end":
                step_id = event.get("step_id", 0)
                success = event.get("success", True)
                if success:
                    completed_steps.add(step_id)
                else:
                    failed_steps[step_id] = event.get("result_summary", "执行失败")
                # 发送进度卡片
                if plan_steps:
                    await client.send_text(
                        user_id,
                        _format_progress(plan_steps, completed_steps, failed_steps, step_id)
                    )

            elif event_type == "rag":
                # 确保意图识别结果已发送
                if not intent_sent and intent_info:
                    await client.send_text(user_id, _format_intent_result(intent_info))
                    intent_sent = True
                    intent_done_event.set()
                doc_count = event.get("doc_count", 0)
                source = event.get("source", "rag")
                if doc_count > 0:
                    source_name = "知识库" if source == "rag" else "网络搜索"
                    await client.send_text(user_id, f"从{source_name}检索到 {doc_count} 条相关信息，正在整理回复...")

            elif event_type == "final_text":
                # 确保意图识别结果已发送
                if not intent_sent and intent_info:
                    await client.send_text(user_id, _format_intent_result(intent_info))
                    intent_sent = True
                    intent_done_event.set()
                response_text = event.get("response") or event.get("data", "")
                if response_text and not text_sent:
                    await client.send_text(user_id, response_text)
                    text_sent = True
                    # 文字回复之后，发送缓存的页面生成提示
                    if page_generating_pending:
                        await client.send_text(user_id, "正在生成结果展示页面...")
                        page_generating_pending = False

            elif event_type == "page_generating":
                # 延迟发送，等文字回复之后再发
                if text_sent:
                    await client.send_text(user_id, "正在生成结果展示页面...")
                else:
                    page_generating_pending = True

            elif event_type == "final_page":
                page_url = event.get("page_url")
                if page_url and settings.screenshot_enabled and not page_sent:
                    page_sent = True
                    screenshot_task = asyncio.create_task(
                        _capture_and_send(user_id, page_url, screenshot_svc, client)
                    )

            elif event_type == "content":
                # 确保意图识别结果已发送
                if not intent_sent and intent_info:
                    await client.send_text(user_id, _format_intent_result(intent_info))
                    intent_sent = True
                    intent_done_event.set()
                response_text = event.get("data", "")
                if response_text and not text_sent:
                    await client.send_text(user_id, response_text)
                    text_sent = True
                    # 文字回复之后，发送缓存的页面生成提示
                    if page_generating_pending:
                        await client.send_text(user_id, "正在生成结果展示页面...")
                        page_generating_pending = False
                page_url = event.get("page_url")
                if page_url and settings.screenshot_enabled and not page_sent:
                    page_sent = True
                    screenshot_task = asyncio.create_task(
                        _capture_and_send(user_id, page_url, screenshot_svc, client)
                    )

            elif event_type == "page_error":
                error_msg = event.get("error", "页面生成失败")
                await client.send_text(user_id, f"页面生成失败: {error_msg}")

            elif event_type == "error":
                error_msg = event.get("data", "处理出错")
                await client.send_text(user_id, f"处理出错: {error_msg}")

            elif event_type == "done":
                pass

        # 流处理结束，取消等待提示定时器
        thinking_task.cancel()

        if screenshot_task is not None:
            await screenshot_task

    except Exception as e:
        thinking_task.cancel()
        logger.error(f"处理企业微信消息异常 [{user_id}]: {e}", exc_info=True)
        await client.send_text(user_id, "处理消息时发生异常，请稍后重试")


# ---- 格式化辅助函数 ----

async def _send_thinking_hints(user_id: str, client, hints: list, stop_event: asyncio.Event = None):
    """
    定时发送递进等待提示，让用户感知系统仍在工作
    hints: [(delay_seconds, message), ...]
    当 stop_event 被 set 或任务被 cancel 时停止
    """
    try:
        for delay, message in hints:
            if stop_event and stop_event.is_set():
                return
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=delay) if stop_event else await asyncio.sleep(delay)
                return  # stop_event 被触发，停止发送
            except asyncio.TimeoutError:
                pass  # 超时说明还没完成，继续发送提示
            await client.send_text(user_id, message)
    except asyncio.CancelledError:
        pass

def _format_intent_result(intent_info: dict) -> str:
    """格式化意图识别结果为一条完整消息"""
    category = intent_info.get("category", "")
    category_name = CATEGORY_MAP.get(category, category)
    confidence = int(intent_info.get("confidence", 0) * 100)
    sub_intent = intent_info.get("sub_intent", "")
    workflow = intent_info.get("workflow", "")

    parts = [f"意图识别: {category_name}({confidence}%)"]

    if sub_intent:
        sub_intent_name = SUB_INTENT_MAP.get(sub_intent, sub_intent)
        parts[0] += f" > {sub_intent_name}"

    if workflow:
        workflow_name = WORKFLOW_NAME_MAP.get(workflow, workflow)
        parts.append(f"匹配工作流: {workflow_name}")

    return "\n".join(parts)


def _format_plan(steps: list) -> str:
    """格式化执行计划，只展示中文步骤描述"""
    lines = ["执行计划:"]
    for i, step in enumerate(steps):
        desc = step.get("description", str(step)) if isinstance(step, dict) else str(step)
        lines.append(f"  {i + 1}. {desc}")
    return "\n".join(lines)


def _format_progress(plan_steps: list, completed: set, failed: dict, current_step_id: int) -> str:
    """格式化执行进度卡片"""
    lines = ["执行进度:"]
    for i, step in enumerate(plan_steps):
        step_id = step.get("step_id", i + 1) if isinstance(step, dict) else (i + 1)
        desc = step.get("description", str(step)) if isinstance(step, dict) else str(step)

        if step_id in failed:
            icon = "❌"
        elif step_id in completed:
            icon = "✅"
        elif step_id == current_step_id:
            icon = "⏳"
        else:
            icon = "○"
        lines.append(f"  {icon} {i + 1}. {desc}")
    return "\n".join(lines)


async def _capture_and_send(user_id: str, page_url: str, screenshot_svc, client):
    """后台执行截图并发送"""
    try:
        img_path = await screenshot_svc.capture(page_url)
        if img_path:
            await client.send_image(user_id, img_path)
        else:
            await client.send_text(user_id, "页面截图生成失败")
    except Exception as e:
        logger.error(f"截图发送失败 [{user_id}]: {e}", exc_info=True)
        await client.send_text(user_id, "页面截图生成失败")
