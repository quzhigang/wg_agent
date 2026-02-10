# -*- coding: utf-8 -*-
"""
企业微信自建应用接入模块
通过企业微信回调接收消息，调用智能体处理后主动推送结果
"""

from .callback import router as wecom_router

__all__ = ["wecom_router"]
