"""
异步页面生成智能体
独立运行的智能体，负责异步生成Web页面
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

from ..config.logging_config import get_logger
from ..config.settings import settings

logger = get_logger(__name__)


class PageTaskStatus(str, Enum):
    """页面生成任务状态"""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


class AsyncPageGeneratorAgent:
    """
    异步页面生成智能体

    独立运行，不阻塞主对话流程
    """

    _instance: Optional['AsyncPageGeneratorAgent'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 任务存储: task_id -> task_info
        self._tasks: Dict[str, Dict[str, Any]] = {}
        # 后台任务引用
        self._background_tasks: Dict[str, asyncio.Task] = {}
        self._initialized = True

        logger.info("异步页面生成智能体初始化完成")

    def submit_task(
        self,
        conversation_id: str,
        report_type: str,
        data: Dict[str, Any],
        title: Optional[str] = None,
        execution_summary: Optional[str] = None
    ) -> str:
        """
        提交页面生成任务

        Args:
            conversation_id: 会话ID
            report_type: 报告类型
            data: 报告数据
            title: 页面标题
            execution_summary: 执行结果摘要

        Returns:
            任务ID
        """
        task_id = f"page_{uuid.uuid4().hex[:8]}"

        self._tasks[task_id] = {
            "task_id": task_id,
            "conversation_id": conversation_id,
            "status": PageTaskStatus.PENDING.value,
            "report_type": report_type,
            "data": data,
            "title": title,
            "execution_summary": execution_summary,
            "page_url": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "completed_at": None
        }

        # 启动后台任务
        task = asyncio.create_task(self._generate_page_async(task_id))
        self._background_tasks[task_id] = task

        logger.info(f"提交页面生成任务: {task_id}")
        return task_id

    async def _generate_page_async(self, task_id: str):
        """
        异步生成页面

        Args:
            task_id: 任务ID
        """
        task_info = self._tasks.get(task_id)
        if not task_info:
            logger.error(f"任务不存在: {task_id}")
            return

        try:
            # 更新状态为生成中
            task_info["status"] = PageTaskStatus.GENERATING.value
            logger.info(f"开始生成页面: {task_id}")

            from .page_generator import get_page_generator

            generator = get_page_generator()
            page_url = generator.generate_page(
                report_type=task_info["report_type"],
                data=task_info["data"],
                title=task_info["title"]
            )

            # 更新任务状态
            task_info["status"] = PageTaskStatus.COMPLETED.value
            task_info["page_url"] = page_url
            task_info["completed_at"] = datetime.now().isoformat()

            logger.info(f"页面生成完成: {task_id} -> {page_url}")

        except Exception as e:
            logger.error(f"页面生成失败: {task_id}, 错误: {e}")
            task_info["status"] = PageTaskStatus.FAILED.value
            task_info["error"] = str(e)
            task_info["completed_at"] = datetime.now().isoformat()

        finally:
            # 清理后台任务引用
            self._background_tasks.pop(task_id, None)

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务信息
        """
        task_info = self._tasks.get(task_id)
        if not task_info:
            return None

        return {
            "task_id": task_info["task_id"],
            "status": task_info["status"],
            "page_url": task_info["page_url"],
            "error": task_info["error"],
            "created_at": task_info["created_at"],
            "completed_at": task_info["completed_at"]
        }

    def get_conversation_tasks(self, conversation_id: str) -> list:
        """
        获取会话的所有任务

        Args:
            conversation_id: 会话ID

        Returns:
            任务列表
        """
        return [
            self.get_task_status(task_id)
            for task_id, task_info in self._tasks.items()
            if task_info["conversation_id"] == conversation_id
        ]

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """
        清理过期任务

        Args:
            max_age_hours: 最大保留时间（小时）
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        to_remove = []
        for task_id, task_info in self._tasks.items():
            created_at = datetime.fromisoformat(task_info["created_at"])
            if created_at < cutoff:
                to_remove.append(task_id)

        for task_id in to_remove:
            self._tasks.pop(task_id, None)
            self._background_tasks.pop(task_id, None)

        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个过期任务")


# 全局实例
_async_page_agent: Optional[AsyncPageGeneratorAgent] = None


def get_async_page_agent() -> AsyncPageGeneratorAgent:
    """获取异步页面生成智能体单例"""
    global _async_page_agent
    if _async_page_agent is None:
        _async_page_agent = AsyncPageGeneratorAgent()
    return _async_page_agent
