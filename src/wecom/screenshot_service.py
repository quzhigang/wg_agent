# -*- coding: utf-8 -*-
"""
页面截图服务 - 使用 Playwright 对生成的结果页面进行截图

采用专用单线程 + 持久化浏览器上下文方式：
- 所有 Playwright 操作在同一个专用线程中执行（Playwright sync API 要求）
- 使用 launch_persistent_context 启用磁盘缓存，ArcGIS JS SDK、地图瓦片等
  静态资源只需首次下载，后续截图直接命中缓存
- 通过 concurrent.futures 将任务提交到专用线程，不阻塞事件循环
"""

import os
import asyncio
from uuid import uuid4
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)

# 专用单线程池，确保所有 Playwright 操作在同一个线程中执行
_pw_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright")


class ScreenshotService:
    """使用 Playwright 对生成的 Web 页面进行截图，复用浏览器实例和磁盘缓存"""

    def __init__(self):
        self.base_url = settings.screenshot_base_url
        self.save_dir = settings.screenshot_save_dir
        self.timeout = settings.screenshot_timeout
        self.viewport_width = settings.screenshot_viewport_width
        self.viewport_height = settings.screenshot_viewport_height
        Path(self.save_dir).mkdir(parents=True, exist_ok=True)

        # 浏览器缓存目录
        self._cache_dir = os.path.abspath(
            os.path.join(self.save_dir, ".browser_cache")
        )

        # 持久化浏览器上下文（仅在专用线程中访问）
        self._playwright = None
        self._context = None

    def _ensure_browser(self):
        """懒初始化持久化浏览器上下文（仅在专用线程中调用）"""
        if self._context:
            try:
                _ = self._context.pages
                return
            except Exception:
                pass

        self._cleanup_browser()

        try:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
            self._context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=self._cache_dir,
                headless=True,
                viewport={"width": self.viewport_width, "height": self.viewport_height},
                args=[
                    "--disable-web-security",
                    "--ignore-certificate-errors",
                    "--disable-gpu",
                    "--no-sandbox",
                ]
            )
            logger.info(f"Playwright 持久化浏览器上下文已启动，缓存目录: {self._cache_dir}")
        except Exception as e:
            logger.error(f"启动 Playwright 浏览器失败: {e}", exc_info=True)
            self._cleanup_browser()
            raise

    def _cleanup_browser(self):
        """清理浏览器实例（不删除缓存目录，保留磁盘缓存）"""
        try:
            if self._context:
                self._context.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._context = None
        self._playwright = None

    async def capture(self, page_url: str) -> Optional[str]:
        """
        截取生成页面的截图

        将截图任务提交到专用 Playwright 线程执行。

        Args:
            page_url: 页面相对路径，如 /static/pages/xxx.html

        Returns:
            截图文件的绝对路径，失败返回 None
        """
        full_url = f"{self.base_url}{page_url}"
        filename = f"{uuid4().hex[:12]}.png"
        save_path = os.path.abspath(os.path.join(self.save_dir, filename))

        logger.info(f"开始截图: {full_url}")

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                _pw_executor,
                self._take_screenshot,
                full_url, save_path
            )

            if result:
                logger.info(f"截图完成: {save_path}")
                return save_path
            else:
                return None

        except Exception as e:
            logger.error(f"截图失败: {type(e).__name__}: {e}", exc_info=True)
            return None

    def _take_screenshot(self, full_url: str, save_path: str) -> bool:
        """在专用线程中执行截图（同步），复用浏览器实例"""
        page = None
        try:
            self._ensure_browser()

            page = self._context.new_page()
            # domcontentloaded 比 load 更快触发，后续用 JS 轮询判断渲染完成
            page.goto(full_url, wait_until="domcontentloaded", timeout=self.timeout * 1000)

            # 智能等待：轮询检测地图是否渲染完成，而非固定等待
            # 如果页面有 #viewDiv（地图容器），等待其中出现 canvas 且宽度 > 0
            # 如果页面没有 #viewDiv，立即通过
            page.wait_for_function(
                """() => {
                    const viewDiv = document.querySelector('#viewDiv');
                    if (!viewDiv) return true;
                    const canvas = viewDiv.querySelector('canvas');
                    return canvas && canvas.width > 0;
                }""",
                timeout=self.timeout * 1000
            )

            # 地图和图表已渲染，短暂等待最终绘制（瓦片填充等）
            page.wait_for_timeout(2000)

            page.screenshot(path=save_path, full_page=True)
            return True

        except Exception as e:
            logger.error(f"截图执行失败: {type(e).__name__}: {e}")
            # 检查 context 是否还活着
            if self._context:
                try:
                    _ = self._context.pages
                except Exception:
                    self._cleanup_browser()
            return False

        finally:
            if page:
                try:
                    page.close()
                except Exception:
                    pass

    def capture_sync(self, page_url: str) -> Optional[str]:
        """同步版本的截图方法，供非异步上下文调用"""
        full_url = f"{self.base_url}{page_url}"
        filename = f"{uuid4().hex[:12]}.png"
        save_path = os.path.abspath(os.path.join(self.save_dir, filename))

        logger.info(f"开始同步截图: {full_url}")

        try:
            if self._take_screenshot(full_url, save_path):
                logger.info(f"同步截图完成: {save_path}")
                return save_path
            return None
        except Exception as e:
            logger.error(f"同步截图失败: {type(e).__name__}: {e}")
            return None


# 全局单例
_screenshot_service: Optional[ScreenshotService] = None


def get_screenshot_service() -> ScreenshotService:
    """获取截图服务单例"""
    global _screenshot_service
    if _screenshot_service is None:
        _screenshot_service = ScreenshotService()
    return _screenshot_service
