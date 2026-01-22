"""
动态模板服务

负责：
1. 将实时生成的页面保存为动态模板
2. 提取页面标题、描述进行向量化
3. 支持动态模板的复用
"""

import json
import uuid
import re
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime

from ..models.database import WebTemplate, SessionLocal
from ..config.logging_config import get_logger
from .template_vector_index import get_template_vector_index

logger = get_logger(__name__)


class DynamicTemplateService:
    """
    动态模板服务

    将每次对话生成的页面自动保存为动态模板，并向量化以供后续复用
    """

    _instance: Optional['DynamicTemplateService'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.vector_index = get_template_vector_index()
        self._initialized = True
        logger.info("动态模板服务初始化完成")

    def save_dynamic_template(
        self,
        html_content: str,
        user_query: str,
        sub_intent: str = "",
        page_title: str = "",
        conversation_id: str = "",
        execution_summary: str = ""
    ) -> Optional[str]:
        """
        保存动态生成的页面为模板

        Args:
            html_content: 生成的HTML内容
            user_query: 用户原始问题
            sub_intent: 业务子意图
            page_title: 页面标题
            conversation_id: 会话ID
            execution_summary: 执行结果摘要

        Returns:
            模板ID，失败返回None
        """
        try:
            # 1. 提取页面信息
            extracted_title = self._extract_title(html_content) or page_title
            extracted_desc = self._extract_description(html_content) or execution_summary

            # 2. 生成唯一标识
            template_id = str(uuid.uuid4())
            content_hash = hashlib.md5(html_content.encode()).hexdigest()[:16]
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            name = f"dynamic_{timestamp}_{content_hash}"

            # 3. 构建显示名称
            display_name = extracted_title or f"动态页面 ({timestamp[:8]})"
            if len(display_name) > 50:
                display_name = display_name[:47] + "..."

            # 4. 构建触发模式（用于向量检索）
            trigger_pattern = f"{user_query} {extracted_title} {extracted_desc}"

            # 5. 保存到数据库
            db = SessionLocal()
            try:
                template = WebTemplate(
                    id=template_id,
                    name=name,
                    display_name=display_name,
                    description=extracted_desc[:500] if extracted_desc else None,
                    template_path=None,  # 动态模板不需要路径
                    supported_sub_intents=json.dumps([sub_intent] if sub_intent else ["other"], ensure_ascii=False),
                    template_type="dynamic",
                    trigger_pattern=trigger_pattern,
                    features=json.dumps(["dynamic"], ensure_ascii=False),
                    priority=5,  # 动态模板优先级中等
                    is_active=True,
                    is_dynamic=True,
                    html_content=html_content,
                    user_query=user_query,
                    page_title=extracted_title,
                    conversation_id=conversation_id
                )

                db.add(template)
                db.commit()

                logger.info(f"动态模板已保存: {display_name} (ID: {template_id})")

            finally:
                db.close()

            # 6. 添加到向量索引
            template_data = {
                "name": name,
                "display_name": display_name,
                "description": extracted_desc,
                "trigger_pattern": trigger_pattern,
                "supported_sub_intents": [sub_intent] if sub_intent else ["other"],
                "template_path": None,
                "template_type": "dynamic",
                "priority": 5
            }
            self.vector_index.index_template(template_id, template_data)

            logger.info(f"动态模板已向量化: {template_id}")
            return template_id

        except Exception as e:
            logger.error(f"保存动态模板失败: {e}")
            return None

    def _extract_title(self, html_content: str) -> str:
        """从HTML中提取标题"""
        # 尝试从 <title> 标签提取
        match = re.search(r'<title[^>]*>([^<]+)</title>', html_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 尝试从 <h1> 标签提取
        match = re.search(r'<h1[^>]*>([^<]+)</h1>', html_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return ""

    def _extract_description(self, html_content: str) -> str:
        """从HTML中提取描述"""
        # 尝试从 meta description 提取
        match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 尝试从第一个 <p> 标签提取
        match = re.search(r'<p[^>]*>([^<]+)</p>', html_content, re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            if len(text) > 20:  # 确保有足够内容
                return text[:200]

        return ""

    def get_dynamic_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取动态模板详情

        Args:
            template_id: 模板ID

        Returns:
            模板信息字典
        """
        db = SessionLocal()
        try:
            tpl = db.query(WebTemplate).filter(
                WebTemplate.id == template_id,
                WebTemplate.is_dynamic == True,
                WebTemplate.is_active == True
            ).first()

            if not tpl:
                return None

            return {
                "id": tpl.id,
                "name": tpl.name,
                "display_name": tpl.display_name,
                "description": tpl.description,
                "html_content": tpl.html_content,
                "user_query": tpl.user_query,
                "page_title": tpl.page_title,
                "sub_intents": json.loads(tpl.supported_sub_intents) if tpl.supported_sub_intents else [],
                "use_count": tpl.use_count,
                "created_at": tpl.created_at.isoformat() if tpl.created_at else None
            }
        finally:
            db.close()

    def reuse_dynamic_template(self, template_id: str) -> Optional[str]:
        """
        复用动态模板，返回HTML内容

        Args:
            template_id: 模板ID

        Returns:
            HTML内容
        """
        db = SessionLocal()
        try:
            tpl = db.query(WebTemplate).filter(
                WebTemplate.id == template_id,
                WebTemplate.is_dynamic == True,
                WebTemplate.is_active == True
            ).first()

            if not tpl or not tpl.html_content:
                return None

            # 更新使用计数
            tpl.use_count += 1
            tpl.success_count += 1
            db.commit()

            logger.info(f"复用动态模板: {tpl.display_name} (使用次数: {tpl.use_count})")
            return tpl.html_content

        finally:
            db.close()

    def list_dynamic_templates(
        self,
        page: int = 1,
        size: int = 20,
        sub_intent: str = None
    ) -> Dict[str, Any]:
        """
        列出动态模板

        Args:
            page: 页码
            size: 每页数量
            sub_intent: 子意图过滤

        Returns:
            分页结果
        """
        db = SessionLocal()
        try:
            query = db.query(WebTemplate).filter(
                WebTemplate.is_dynamic == True,
                WebTemplate.is_active == True
            )

            if sub_intent:
                query = query.filter(WebTemplate.supported_sub_intents.contains(sub_intent))

            total = query.count()
            items = query.order_by(WebTemplate.created_at.desc())\
                .offset((page - 1) * size).limit(size).all()

            return {
                "total": total,
                "page": page,
                "size": size,
                "items": [{
                    "id": t.id,
                    "name": t.name,
                    "display_name": t.display_name,
                    "description": t.description,
                    "user_query": t.user_query,
                    "page_title": t.page_title,
                    "supported_sub_intents": json.loads(t.supported_sub_intents) if t.supported_sub_intents else [],
                    "use_count": t.use_count,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                } for t in items]
            }
        finally:
            db.close()

    def delete_dynamic_template(self, template_id: str) -> bool:
        """删除动态模板"""
        db = SessionLocal()
        try:
            tpl = db.query(WebTemplate).filter(
                WebTemplate.id == template_id,
                WebTemplate.is_dynamic == True
            ).first()

            if not tpl:
                return False

            db.delete(tpl)
            db.commit()

            # 从向量索引删除
            self.vector_index.delete_template(template_id)

            logger.info(f"已删除动态模板: {template_id}")
            return True

        except Exception as e:
            logger.error(f"删除动态模板失败: {e}")
            db.rollback()
            return False
        finally:
            db.close()


# 全局实例
_dynamic_template_service: Optional[DynamicTemplateService] = None


def get_dynamic_template_service() -> DynamicTemplateService:
    """获取动态模板服务单例"""
    global _dynamic_template_service
    if _dynamic_template_service is None:
        _dynamic_template_service = DynamicTemplateService()
    return _dynamic_template_service
