"""
模板元数据生成器

使用 LLM 智能生成动态模板的核心元数据：
1. display_name - 有意义的中文名称
2. page_title - 页面标题
3. description - 页面描述
4. trigger_pattern - 触发模式/关键词（用于向量检索匹配）
5. object_type_synonyms - 对象类型同义词列表
6. replacement_config - 参数配置
"""

import json
from typing import Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..config.settings import settings
from ..config.logging_config import get_logger
from ..config.llm_prompt_logger import log_llm_call

logger = get_logger(__name__)

# 模板元数据生成提示词
TEMPLATE_METADATA_PROMPT = """你是一个Web模板元数据生成专家。根据用户对话和页面内容，生成模板的核心元数据。

## 用户原始问题
{user_query}

## 意图大类
{intent_category}

## 业务子意图
{sub_intent}

## 提取的实体
{entities}

## 页面标题（从HTML提取）
{extracted_title}

## 页面描述（从HTML提取）
{extracted_desc}

## 执行结果摘要
{execution_summary}

## 任务
请生成模板的核心元数据，返回JSON格式：

{{
    "display_name": "简短的中文名称（4-10字，根据用户意图归纳，如'查询闸站信息'、'水库详情展示'、'洪水预报结果'）",
    "page_title": "页面标题（使用通用格式，如'闸站详情'、'水库信息'、'洪水预报结果'）",
    "description": "页面描述（20-50字，描述页面展示的数据类型和用途，如'展示某闸的基本信息、功能特点及现场图片等详细内容'）",
    "trigger_pattern": "触发模式（用于向量检索匹配的关键词和场景描述，包含对象类型、操作类型、相关同义词，如'查询 闸 水闸 信息 介绍 详情 参数'）",
    "object_type_synonyms": ["对象类型，如拦河闸、节制闸、分洪闸、退水闸、雨量站、水文站、视频监测站等"],
    "replacement_config": {{
        "mode": "json_injection",
        "mappings": [
            {{"param_name": "参数名", "param_desc": "参数描述", "context_path": "上下文路径"}}
        ]
    }}
}}

## 生成规则（重要）
1. display_name：根据用户意图归纳，简洁明了，【禁止】包含具体对象名称（如"盐土庄闸"、"盘石头水库"等）
2. page_title：使用通用格式，【禁止】包含具体对象名称，应使用"某闸详情"、"水库信息"等通用表述
3. description：描述页面展示的数据类型和用途，【禁止】包含具体对象名称，应使用"某闸"、"某水库"等通用表述
4. trigger_pattern：包含对象类型、操作类型、相关同义词，用空格分隔，【禁止】包含具体对象名称
5. object_type_synonyms：严格提炼对象类型，不得混用，如分洪闸不得提炼为闸、拦河闸，水文站不得笼统提炼为站点
6. replacement_config：根据实体信息生成参数映射配置，如果没有明确的参数需求，mappings可以为空数组

【核心原则】：模板元数据用于复用，必须是通用的、可泛化的，不能包含任何具体的对象名称！

请直接返回JSON，不要包含Markdown代码块标记或其他内容。
"""


class TemplateMetadataGenerator:
    """
    模板元数据生成器

    使用 LLM 智能生成动态模板的核心元数据
    """

    _instance: Optional['TemplateMetadataGenerator'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 使用 Web 模板匹配节点的 LLM 配置
        # 思考模式配置（用于Qwen3等模型，非流式调用需设置为false）
        extra_body = {"enable_thinking": settings.llm_enable_thinking}
        template_match_cfg = settings.get_template_match_config()
        self.llm = ChatOpenAI(
            api_key=template_match_cfg["api_key"],
            base_url=template_match_cfg["api_base"],
            model=template_match_cfg["model"],
            temperature=template_match_cfg["temperature"],
            model_kwargs={"extra_body": extra_body}
        )

        self.json_parser = JsonOutputParser()
        self.prompt = ChatPromptTemplate.from_template(TEMPLATE_METADATA_PROMPT)
        self.chain = self.prompt | self.llm | self.json_parser

        self._initialized = True
        logger.info(f"模板元数据生成器初始化完成，使用模型: {template_match_cfg['model']}")

    async def generate_metadata_async(
        self,
        user_query: str,
        intent_category: str = "",
        sub_intent: str = "",
        entities: Optional[Dict[str, Any]] = None,
        extracted_title: str = "",
        extracted_desc: str = "",
        execution_summary: str = ""
    ) -> Dict[str, Any]:
        """
        异步生成模板元数据

        Args:
            user_query: 用户原始问题
            intent_category: 意图大类
            sub_intent: 业务子意图
            entities: 提取的实体
            extracted_title: 从HTML提取的标题
            extracted_desc: 从HTML提取的描述
            execution_summary: 执行结果摘要

        Returns:
            包含 display_name, page_title, description, trigger_pattern,
            object_type_synonyms, replacement_config 的字典
        """
        import time
        start_time = time.time()

        try:
            context_vars = {
                "user_query": user_query,
                "intent_category": intent_category or "unknown",
                "sub_intent": sub_intent or "unknown",
                "entities": json.dumps(entities, ensure_ascii=False) if entities else "{}",
                "extracted_title": extracted_title or "无",
                "extracted_desc": extracted_desc[:500] if extracted_desc else "无",
                "execution_summary": execution_summary[:500] if execution_summary else "无"
            }

            result = await self.chain.ainvoke(context_vars)

            elapsed_time = time.time() - start_time

            # 记录 LLM 调用日志
            log_llm_call(
                step_name="模板元数据生成",
                module_name="TemplateMetadataGenerator",
                prompt_template_name="TEMPLATE_METADATA_PROMPT",
                context_variables=context_vars,
                full_prompt=self.prompt.format(**context_vars),
                response=json.dumps(result, ensure_ascii=False),
                elapsed_time=elapsed_time
            )

            logger.info(f"模板元数据生成成功: display_name={result.get('display_name')}, 耗时: {elapsed_time:.2f}s")
            return result

        except Exception as e:
            logger.warning(f"LLM生成模板元数据失败，使用默认值: {e}")
            return self._generate_default_metadata(
                user_query, intent_category, sub_intent, entities, extracted_title
            )

    def _generate_default_metadata(
        self,
        user_query: str,
        intent_category: str,
        sub_intent: str,
        entities: Optional[Dict[str, Any]],
        extracted_title: str
    ) -> Dict[str, Any]:
        """
        生成默认元数据（LLM失败时的降级方案）

        注意：元数据用于模板复用，必须是通用的，不能包含具体对象名称

        Args:
            user_query: 用户原始问题
            intent_category: 意图大类
            sub_intent: 业务子意图
            entities: 提取的实体
            extracted_title: 从HTML提取的标题

        Returns:
            默认的元数据字典
        """
        object_type = entities.get('object_type', '') if entities else ''
        action = entities.get('action', '查询') if entities else '查询'

        # 生成 display_name（不包含具体对象名称）
        if object_type:
            display_name = f"{action}{object_type}信息"
        elif sub_intent and sub_intent != "unknown":
            display_name = f"{sub_intent}查询"
        else:
            display_name = "信息查询"

        # 生成 page_title（使用通用格式，不包含具体对象名称）
        if object_type:
            page_title = f"{object_type}详情"
        else:
            page_title = "查询结果"

        # 生成 description（使用通用表述，不包含具体对象名称）
        if object_type:
            description = f"展示某{object_type}的基本信息、功能特点及相关数据等详细内容"
        else:
            description = "展示查询对象的详细信息和相关数据"

        # 生成 trigger_pattern（不包含具体对象名称，只包含类型和操作）
        trigger_parts = []
        if object_type:
            trigger_parts.append(object_type)
        if action:
            trigger_parts.append(action)
        trigger_parts.extend(["信息", "详情", "查询", "介绍"])
        trigger_pattern = " ".join(trigger_parts)

        # 生成 object_type_synonyms
        object_type_synonyms = [object_type] if object_type else []

        logger.info(f"使用默认元数据: display_name={display_name}")

        return {
            "display_name": display_name[:50],
            "page_title": page_title,
            "description": description,
            "trigger_pattern": trigger_pattern,
            "object_type_synonyms": object_type_synonyms,
            "replacement_config": {
                "mode": "json_injection",
                "mappings": []
            }
        }


# 全局实例
_metadata_generator: Optional[TemplateMetadataGenerator] = None


def get_template_metadata_generator() -> TemplateMetadataGenerator:
    """获取模板元数据生成器单例"""
    global _metadata_generator
    if _metadata_generator is None:
        _metadata_generator = TemplateMetadataGenerator()
    return _metadata_generator
