"""
模板匹配服务

实现两阶段模板匹配：
1. 第一阶段：向量检索粗筛，快速找出 Top-K 个候选模板
2. 第二阶段：LLM 精选，从候选中选择最匹配的模板
"""

import json
from typing import Dict, Any, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import settings
from ..config.logging_config import get_logger
from ..config.llm_prompt_logger import log_llm_call
from .template_vector_index import get_template_vector_index

logger = get_logger(__name__)


# LLM精选模板的提示词
TEMPLATE_SELECT_PROMPT = """你是一个Web模板选择专家。根据用户问题和可提供的参数，从候选模板中选择最合适的模板。

## 用户问题
{user_message}

## 业务子意图
{sub_intent}

## 当前对象类型
{object_type}

## 对象识别可提供的参数
（来自实体解析阶段：数据库查询+知识库查询+LLM匹配）
{entity_params}

## 工作流可提供的参数
（来自工作流执行结果）
{workflow_params}

## 候选模板列表
{candidates}

## 选择标准（按优先级排序）

### 必要条件（不满足则必须返回null）
1. **参数完全满足**：上述两类参数（对象识别参数+工作流参数）必须完全覆盖模板的"所需参数"。逐一检查模板所需的每个参数（如token、planCode、stcd、object_name等），确认都能提供。如果有任何一个所需参数无法满足，该模板不可选择。
2. **子意图匹配**：模板必须支持当前的业务子意图。
3. **对象类型匹配**：如果模板指定了"必须匹配的对象类型"（非空列表），则当前对象类型必须在该列表中。如果当前对象类型不在列表中，该模板不可选择。如果模板的"必须匹配的对象类型"为空或未指定，则跳过此校验。

### 优选条件（在满足必要条件后考虑）
4. 模板的触发模式与用户问题相关性高
5. 优先选择优先级高的模板

## 输出格式
请返回JSON格式，包含以下字段：
{{
    "selected_template_id": "模板ID或null",
    "confidence": 0.0-1.0的置信度,
    "reason": "选择理由（如果返回null，说明哪些条件不满足：参数不满足/子意图不匹配/对象类型不匹配）"
}}

请直接返回JSON，不要包含其他内容。
"""


class TemplateMatchService:
    """
    模板匹配服务

    实现两阶段模板匹配策略
    """

    _instance: Optional['TemplateMatchService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 初始化向量索引
        self.vector_index = get_template_vector_index()

        # 初始化LLM（使用独立的模板匹配配置）
        extra_body = {"enable_thinking": settings.llm_enable_thinking}
        template_match_cfg = settings.get_template_match_config()
        self.llm = ChatOpenAI(
            api_key=template_match_cfg["api_key"],
            base_url=template_match_cfg["api_base"],
            model=template_match_cfg["model"],
            temperature=template_match_cfg["temperature"],
            model_kwargs={"extra_body": extra_body}
        )

        self._initialized = True
        logger.info(f"模板匹配服务初始化完成，使用模型: {template_match_cfg['model']}")

    async def match_template(
        self,
        user_message: str,
        sub_intent: str = "",
        available_params: str = "",
        entity_params: str = "",
        workflow_params: str = "",
        object_type: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        两阶段模板匹配

        Args:
            user_message: 用户原始问题
            sub_intent: 业务子意图
            available_params: 工作流可提供的参数摘要（兼容旧接口，如果提供则会被拆分）
            entity_params: 对象识别可提供的参数（来自实体解析阶段）
            workflow_params: 工作流可提供的参数（来自工作流执行结果）
            object_type: 当前对象类型（如"水库"、"河道水文站"等，用于对象类型校验）

        Returns:
            匹配的模板信息，包含：
            - id: 模板ID
            - name: 英文名称
            - display_name: 中文名称
            - template_path: 模板路径
            - confidence: 匹配置信度
            如果没有匹配到合适的模板，返回 None
        """
        logger.info(f"开始模板匹配，用户问题: {user_message[:50]}..., 子意图: {sub_intent}, 对象类型: {object_type}")

        try:
            # 第一阶段：向量检索（使用用户问题和子意图进行检索）
            query = f"{user_message} {sub_intent}"
            candidates = self.vector_index.search(
                query=query,
                sub_intent=sub_intent,
                top_k=5
            )

            if not candidates:
                logger.info("向量检索未找到候选模板")
                return None

            logger.info(f"向量检索返回 {len(candidates)} 个候选模板")

            # 如果只有一个候选且分数很高，直接返回（但需要获取完整信息）
            if len(candidates) == 1 and candidates[0].get('score', 0) > 0.8:
                template_id = candidates[0].get('id')
                # 获取完整的模板信息（包含 replacement_config）
                full_template = self.get_template_by_id(template_id)
                if full_template:
                    full_template['confidence'] = candidates[0].get('score', 0)
                    logger.info(f"单一高分候选，直接选择: {full_template.get('display_name')}")
                    return full_template
                # 如果获取失败，回退到候选信息
                template = candidates[0]
                template['confidence'] = template.get('score', 0)
                return template

            # 第二阶段：LLM精选
            selected = await self._llm_select_template(
                user_message=user_message,
                sub_intent=sub_intent,
                entity_params=entity_params,
                workflow_params=workflow_params,
                available_params=available_params,
                candidates=candidates,
                object_type=object_type
            )

            if selected:
                # 从候选中找到完整的模板信息
                selected_id = selected.get('selected_template_id')
                if selected_id:
                    # 获取完整的模板信息（包含 replacement_config）
                    full_template = self.get_template_by_id(selected_id)
                    if full_template:
                        full_template['confidence'] = selected.get('confidence', 0)
                        logger.info(f"LLM选择模板: {full_template.get('display_name')}, 置信度: {full_template['confidence']}")
                        return full_template

                    # 如果获取失败，回退到候选信息
                    for candidate in candidates:
                        if candidate.get('id') == selected_id:
                            candidate['confidence'] = selected.get('confidence', 0)
                            logger.info(f"LLM选择模板(回退): {candidate.get('display_name')}, 置信度: {candidate['confidence']}")
                            return candidate

            logger.info("LLM未选择任何模板")
            return None

        except Exception as e:
            logger.error(f"模板匹配失败: {e}")
            return None

    async def _llm_select_template(
        self,
        user_message: str,
        sub_intent: str,
        entity_params: str,
        workflow_params: str,
        available_params: str,
        candidates: List[Dict[str, Any]],
        object_type: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        LLM精选模板

        Args:
            user_message: 用户问题
            sub_intent: 业务子意图
            entity_params: 对象识别可提供的参数（来自实体解析阶段）
            workflow_params: 工作流可提供的参数（来自工作流执行结果）
            available_params: 兼容旧接口的参数摘要
            candidates: 候选模板列表
            object_type: 当前对象类型（用于对象类型校验）

        Returns:
            选择结果，包含 selected_template_id, confidence, reason
        """
        try:
            # 格式化候选模板（增加所需参数和必须匹配的对象类型信息）
            candidates_text = "\n".join([
                f"- ID: {c.get('id')}\n"
                f"  名称: {c.get('display_name')}\n"
                f"  描述: {c.get('description', '')[:200]}\n"
                f"  触发模式: {c.get('trigger_pattern', '')[:200]}\n"
                f"  支持子意图: {','.join(c.get('supported_sub_intents', []))}\n"
                f"  所需参数: {c.get('required_params', '无')}\n"
                f"  必须匹配的对象类型: {','.join(c.get('required_object_types', [])) or '无限制'}\n"
                f"  优先级: {c.get('priority', 0)}\n"
                f"  向量分数: {c.get('score', 0):.3f}"
                for c in candidates
            ])

            # 处理参数：优先使用新的分离参数，兼容旧的合并参数
            final_entity_params = entity_params or "无"
            final_workflow_params = workflow_params or "无"

            # 如果新参数都为空但旧参数有值，则使用旧参数作为工作流参数（向后兼容）
            if entity_params == "" and workflow_params == "" and available_params:
                final_workflow_params = available_params

            context_vars = {
                "user_message": user_message,
                "sub_intent": sub_intent,
                "object_type": object_type or "未知",
                "entity_params": final_entity_params,
                "workflow_params": final_workflow_params,
                "candidates": candidates_text
            }

            prompt = ChatPromptTemplate.from_template(TEMPLATE_SELECT_PROMPT)
            chain = prompt | self.llm

            import time
            _start = time.time()
            response = await chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = TEMPLATE_SELECT_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="模板LLM精选",
                module_name="TemplateMatchService._llm_select_template",
                prompt_template_name="TEMPLATE_SELECT_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=response.content,
                elapsed_time=_elapsed
            )

            # 解析JSON响应
            content = response.content.strip()
            # 处理可能的markdown代码块
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"LLM响应JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.error(f"LLM精选模板失败: {e}")
            return None

    def get_template_by_id(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取模板信息

        Args:
            template_id: 模板UUID

        Returns:
            模板信息字典
        """
        try:
            from ..models.database import WebTemplate, SessionLocal

            db = SessionLocal()
            try:
                tpl = db.query(WebTemplate).filter(
                    WebTemplate.id == template_id,
                    WebTemplate.is_active == True
                ).first()

                if not tpl:
                    return None

                result = {
                    "id": tpl.id,
                    "name": tpl.name,
                    "display_name": tpl.display_name,
                    "description": tpl.description,
                    "template_path": tpl.template_path,
                    "supported_sub_intents": json.loads(tpl.supported_sub_intents) if tpl.supported_sub_intents else [],
                    "template_type": tpl.template_type,
                    "data_schema": json.loads(tpl.data_schema) if tpl.data_schema else None,
                    "features": json.loads(tpl.features) if tpl.features else [],
                    "priority": tpl.priority,
                    "is_dynamic": tpl.is_dynamic,
                    # 添加 replacement_config 字段
                    "replacement_config": json.loads(tpl.replacement_config) if tpl.replacement_config else None
                }

                # 动态模板包含HTML内容
                if tpl.is_dynamic and tpl.html_content:
                    result["html_content"] = tpl.html_content
                    result["user_query"] = tpl.user_query
                    result["page_title"] = tpl.page_title

                return result
            finally:
                db.close()

        except Exception as e:
            logger.error(f"获取模板失败 {template_id}: {e}")
            return None

    def get_default_template(self, sub_intent: str = "") -> Optional[Dict[str, Any]]:
        """
        获取默认模板

        当没有匹配到合适的模板时，返回默认模板

        Args:
            sub_intent: 业务子意图

        Returns:
            默认模板信息
        """
        try:
            from ..models.database import WebTemplate, SessionLocal

            db = SessionLocal()
            try:
                query = db.query(WebTemplate).filter(WebTemplate.is_active == True)

                # 如果指定了子意图，优先查找支持该子意图的模板
                if sub_intent:
                    query = query.filter(
                        WebTemplate.supported_sub_intents.contains(sub_intent)
                    )

                # 按优先级排序，取第一个
                tpl = query.order_by(WebTemplate.priority.desc()).first()

                if not tpl:
                    return None

                return {
                    "id": tpl.id,
                    "name": tpl.name,
                    "display_name": tpl.display_name,
                    "template_path": tpl.template_path,
                    "template_type": tpl.template_type,
                    "is_dynamic": tpl.is_dynamic,
                    # 添加 replacement_config 字段
                    "replacement_config": json.loads(tpl.replacement_config) if tpl.replacement_config else None
                }
            finally:
                db.close()

        except Exception as e:
            logger.error(f"获取默认模板失败: {e}")
            return None

    def increment_use_count(self, template_id: str, success: bool = True):
        """
        增加模板使用计数

        Args:
            template_id: 模板ID
            success: 是否成功使用
        """
        try:
            from ..models.database import WebTemplate, SessionLocal

            db = SessionLocal()
            try:
                tpl = db.query(WebTemplate).filter(WebTemplate.id == template_id).first()
                if tpl:
                    tpl.use_count += 1
                    if success:
                        tpl.success_count += 1
                    db.commit()
            finally:
                db.close()

        except Exception as e:
            logger.warning(f"更新模板使用计数失败: {e}")


# 全局模板匹配服务实例
_template_match_service_instance: Optional[TemplateMatchService] = None


def get_template_match_service() -> TemplateMatchService:
    """
    获取全局模板匹配服务实例（单例模式）

    Returns:
        TemplateMatchService 实例
    """
    global _template_match_service_instance
    if _template_match_service_instance is None:
        _template_match_service_instance = TemplateMatchService()
    return _template_match_service_instance
