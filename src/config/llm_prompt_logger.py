"""
LLM提示词日志记录模块
记录每个会话中各步骤调用大模型时的完整上下文和提示词
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import threading

from .settings import settings


class LLMPromptLogger:
    """LLM提示词日志记录器"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 日志文件路径
        self.log_file = Path(settings.log_file).parent / "llm_prompt.md"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 当前会话ID
        self._current_session_id: Optional[str] = None
        self._current_question: Optional[str] = None
        self._session_started = False
        
        self._initialized = True
    
    def start_session(self, session_id: str, question: str):
        """
        开始新会话

        Args:
            session_id: 会话ID
            question: 用户问题
        """
        self._current_session_id = session_id
        self._current_question = question
        self._session_started = False
    
    def _write_session_header(self):
        """写入会话头部"""
        if self._session_started:
            return
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"\n*****会话ID: {self._current_session_id} | 问题: {self._current_question}*****\n\n")
        
        self._session_started = True
    
    def log_llm_call(
        self,
        step_name: str,
        module_name: str,
        prompt_template_name: str,
        context_variables: Dict[str, Any],
        full_prompt: str,
        response: Optional[str] = None
    ):
        """
        记录LLM调用
        
        Args:
            step_name: 步骤名称（如"意图分析"、"计划生成"等）
            module_name: 模块名称（如"Planner.analyze_intent"）
            prompt_template_name: 提示词模板名称
            context_variables: 上下文变量字典
            full_prompt: 完整的提示词（已填充变量）
            response: LLM响应（可选）
        """
        if not self._current_session_id:
            return
        
        # 确保会话头部已写入
        self._write_session_header()
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"## {step_name} ({module_name})\n")
            f.write(f"**时间**: {timestamp}\n")
            f.write(f"**提示词模板**: {prompt_template_name}\n\n")
            
            # 写入上下文变量
            f.write("**上下文变量**:\n")
            for key, value in context_variables.items():
                # 截断过长的值
                value_str = str(value)
                if len(value_str) > 500:
                    value_str = value_str[:500] + "...(已截断)"
                f.write(f"- {key}: {value_str}\n")
            f.write("\n")
            
            # 写入完整提示词
            f.write("**完整提示词**:\n")
            f.write("```\n")
            f.write(full_prompt)
            f.write("\n```\n")
            
            # 写入响应（如果有）
            if response:
                f.write("\n**LLM响应**:\n")
                f.write("```\n")
                response_str = str(response)
                if len(response_str) > 1000:
                    response_str = response_str[:1000] + "...(已截断)"
                f.write(response_str)
                f.write("\n```\n")
            
            f.write("\n")
    
    def end_session(self):
        """结束当前会话"""
        if self._current_session_id and self._session_started:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write("---\n\n")
        
        self._current_session_id = None
        self._current_question = None
        self._session_started = False


# 全局实例
_logger_instance: Optional[LLMPromptLogger] = None


def get_llm_prompt_logger() -> LLMPromptLogger:
    """获取LLM提示词日志记录器单例"""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = LLMPromptLogger()
    return _logger_instance


def log_llm_call(
    step_name: str,
    module_name: str,
    prompt_template_name: str,
    context_variables: Dict[str, Any],
    full_prompt: str,
    response: Optional[str] = None
):
    """
    便捷函数：记录LLM调用
    
    Args:
        step_name: 步骤名称
        module_name: 模块名称
        prompt_template_name: 提示词模板名称
        context_variables: 上下文变量
        full_prompt: 完整提示词
        response: LLM响应
    """
    logger = get_llm_prompt_logger()
    logger.log_llm_call(
        step_name=step_name,
        module_name=module_name,
        prompt_template_name=prompt_template_name,
        context_variables=context_variables,
        full_prompt=full_prompt,
        response=response
    )


def start_session(session_id: str, question: str):
    """
    便捷函数：开始新会话
    
    Args:
        session_id: 会话ID
        question: 用户问题
    """
    logger = get_llm_prompt_logger()
    logger.start_session(session_id, question)


def end_session():
    """便捷函数：结束当前会话"""
    logger = get_llm_prompt_logger()
    logger.end_session()
