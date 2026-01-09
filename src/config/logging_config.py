"""
日志配置模块
使用Loguru进行日志管理
"""

import sys
from pathlib import Path
from loguru import logger
from .settings import settings


def setup_logging():
    """配置日志系统"""
    
    # 移除默认处理器
    logger.remove()
    
    # 日志格式
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 简化格式（用于控制台）
    console_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<level>{message}</level>"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format=console_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 确保日志目录存在
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # 清空之前的日志内容，只保留当前会话
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("")

    # 添加文件处理器
    logger.add(
        settings.log_file,
        format=log_format,
        level=settings.log_level,
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    # 添加错误日志文件处理器
    error_log_path = log_path.parent / "error.log"
    with open(error_log_path, "w", encoding="utf-8") as f:
        f.write("")
    logger.add(
        str(error_log_path),
        format=log_format,
        level="ERROR",
        encoding="utf-8",
        backtrace=True,
        diagnose=True
    )
    
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {settings.log_level}")
    logger.info(f"日志文件: {settings.log_file}")
    
    return logger


def get_logger(name: str = None):
    """获取日志记录器

    Args:
        name: 模块名称，用于日志标识

    Returns:
        配置好的logger实例
    """
    if name:
        return logger.bind(name=name)
    return logger


def clear_all_logs():
    """清空所有日志文件（新会话开始时调用）"""
    log_path = Path(settings.log_file)
    error_log_path = log_path.parent / "error.log"
    llm_prompt_path = log_path.parent / "llm_prompt.md"

    for path in [log_path, error_log_path, llm_prompt_path]:
        if path.exists():
            with open(path, "w", encoding="utf-8") as f:
                f.write("")
