# -*- coding: utf-8 -*-
"""
页面截图服务 - 使用 Playwright 对生成的结果页面进行截图
只截取 iframe 内的结果展示页面，不包含对话框区域
"""

import os
import asyncio
from uuid import uuid4
from pathlib import Path
from typing import Optional

from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


class ScreenshotService:
    """使用 Playwright 对生成的 Web 页面进行截图"""

    def __init__(self):
        self.base_url = settings.screenshot_base_url
        self.save_dir = settings.screenshot_save_dir
        self.timeout = settings.screenshot_timeout
        self.viewport_width = settings.screenshot_viewport_width
        self.viewport_height = settings.screenshot_viewport_height
        Path(self.save_dir).mkdir(parents=True, exist_ok=True)

    async def capture(self, page_url: str) -> Optional[str]:
        """
        截取生成页面的截图

        直接访问 page_url 指向的页面（即 iframe src），
        而不是包含对话框的主页面，这样截图只包含结果展示内容。

        Args:
            page_url: 页面相对路径，如 /static/pages/xxx.html

        Returns:
            截图文件的绝对路径，失败返回 None
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("playwright 未安装，请执行: pip install playwright && playwright install chromium")
            return None

        full_url = f"{self.base_url}{page_url}"
        filename = f"{uuid4().hex[:12]}.png"
        save_path = os.path.join(self.save_dir, filename)

        logger.info(f"开始截图: {full_url}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(
                    viewport={
                        "width": self.viewport_width,
                        "height": self.viewport_height
                    }
                )

                await page.goto(full_url, wait_until="networkidle",
                                timeout=self.timeout * 1000)
                # 额外等待，确保 ECharts 等图表渲染完成
                await page.wait_for_timeout(3000)

                await page.screenshot(path=save_path, full_page=True)
                await browser.close()

            logger.info(f"截图完成: {save_path}")
            return os.path.abspath(save_path)

        except Exception as e:
            logger.error(f"截图失败: {e}")
            return None

    def capture_sync(self, page_url: str) -> Optional[str]:
        """同步版本的截图方法，供非异步上下文调用"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已有事件循环在运行，创建新线程执行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, self.capture(page_url))
                    return future.result(timeout=self.timeout + 10)
            else:
                return loop.run_until_complete(self.capture(page_url))
        except Exception as e:
            logger.error(f"同步截图失败: {e}")
            return None


# 全局单例
_screenshot_service: Optional[ScreenshotService] = None


def get_screenshot_service() -> ScreenshotService:
    """获取截图服务单例"""
    global _screenshot_service
    if _screenshot_service is None:
        _screenshot_service = ScreenshotService()
    return _screenshot_service
