"""
Web模板向量索引模块

为Web模板提供向量检索能力，实现两阶段模板匹配：
1. 第一阶段：向量检索粗筛，快速找出 Top-K 个候选模板
2. 第二阶段：LLM 精选，从候选中选择最匹配的模板

复用 PageIndex 的 OllamaEmbedding 类和 .env 中的嵌入模型配置
"""

import os
import math
from typing import List, Dict, Any, Optional
from datetime import datetime

import chromadb
from chromadb.config import Settings

# 复用 PageIndex 的 Embedding 模型
import sys
_module_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_module_dir))
_pageindex_dir = os.path.join(_project_root, "PageIndex")
if _pageindex_dir not in sys.path:
    sys.path.insert(0, _pageindex_dir)

from pageindex.vector_index import OllamaEmbedding

from ..config.logging_config import get_logger

logger = get_logger(__name__)

# 模板向量索引存储目录
_default_template_chroma_dir = os.path.join(_project_root, "template_vectors")
TEMPLATE_CHROMA_DIR = os.getenv("TEMPLATE_CHROMA_DIR", _default_template_chroma_dir)

# 默认检索数量
DEFAULT_TOP_K = int(os.getenv("RERANKER_TOP_K", "5"))


class WebTemplateVectorIndex:
    """
    Web模板向量索引管理类

    为Web模板提供向量检索能力，支持：
    - 按子意图过滤检索
    - 向量相似度排序
    - 自动索引新模板
    """

    _instance: Optional['WebTemplateVectorIndex'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 初始化 Embedding 模型（复用 PageIndex 的配置）
        self.embedding_model = OllamaEmbedding()

        # 初始化 ChromaDB 客户端
        os.makedirs(TEMPLATE_CHROMA_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=TEMPLATE_CHROMA_DIR)

        # 获取或创建模板 collection
        self.collection = self.client.get_or_create_collection(
            name="web_templates",
            metadata={"description": "Web模板向量索引"}
        )

        self._initialized = True
        logger.info(f"Web模板向量索引初始化完成，存储目录: {TEMPLATE_CHROMA_DIR}")

    def _build_template_text(self, template_data: Dict[str, Any]) -> str:
        """
        构建模板的文本表示（用于生成 embedding）

        组合多个字段以提高检索准确性：
        - trigger_pattern: 触发模式（最重要）
        - description: 模板描述
        - display_name: 中文显示名称
        - supported_sub_intents: 支持的子意图
        """
        parts = []

        # 触发模式是最重要的匹配依据
        trigger_pattern = template_data.get('trigger_pattern', '')
        if trigger_pattern:
            parts.append(trigger_pattern)

        # 描述提供额外的语义信息
        description = template_data.get('description', '')
        if description:
            parts.append(description)

        # 中文名称有助于匹配
        display_name = template_data.get('display_name', '')
        if display_name:
            parts.append(display_name)

        # 支持的子意图
        sub_intents = template_data.get('supported_sub_intents', [])
        if sub_intents:
            if isinstance(sub_intents, list):
                parts.append(' '.join(sub_intents))
            else:
                parts.append(str(sub_intents))

        return " ".join(parts)

    def _extract_required_params(self, replacement_config: Optional[Dict[str, Any]]) -> str:
        """
        从 replacement_config 提取模板所需参数信息

        Args:
            replacement_config: 模板的数据注入配置

        Returns:
            参数信息字符串，格式如: "token(登录认证令牌),planCode(预报方案ID),..."
        """
        if not replacement_config:
            return ""

        mappings = replacement_config.get('mappings', [])
        if not mappings:
            return ""

        params = []
        for mapping in mappings:
            param_name = mapping.get('param_name', '')
            param_desc = mapping.get('param_desc', '')
            if param_name:
                if param_desc:
                    params.append(f"{param_name}({param_desc})")
                else:
                    params.append(param_name)

        return ','.join(params)

    def index_template(self, template_id: str, template_data: Dict[str, Any]) -> bool:
        """
        索引单个模板

        Args:
            template_id: 模板 UUID
            template_data: 模板数据，包含以下字段：
                - name: 英文名称
                - display_name: 中文显示名称
                - description: 描述
                - trigger_pattern: 触发模式
                - supported_sub_intents: 支持的子意图列表

        Returns:
            是否索引成功
        """
        try:
            # 构建文本表示
            text = self._build_template_text(template_data)
            if not text:
                logger.warning(f"模板 {template_id} 无有效文本，跳过索引")
                return False

            # 生成 embedding
            embedding = self.embedding_model.embed(text)

            # 处理 supported_sub_intents
            sub_intents = template_data.get('supported_sub_intents', [])
            if isinstance(sub_intents, list):
                sub_intents_str = ','.join(sub_intents)
            else:
                sub_intents_str = str(sub_intents)

            # 提取模板所需参数信息（从 replacement_config）
            required_params_str = self._extract_required_params(template_data.get('replacement_config'))

            # 提取必须匹配的对象类型
            required_object_types = template_data.get('required_object_types', [])
            if isinstance(required_object_types, list):
                required_object_types_str = ','.join(required_object_types)
            else:
                required_object_types_str = str(required_object_types) if required_object_types else ''

            # 构建元数据
            metadata = {
                "name": template_data.get('name', ''),
                "display_name": template_data.get('display_name', ''),
                "supported_sub_intents": sub_intents_str,
                "description": (template_data.get('description', '') or '')[:500],
                "trigger_pattern": (template_data.get('trigger_pattern', '') or '')[:500],
                "template_path": template_data.get('template_path', '') or '',
                "template_type": template_data.get('template_type', 'full_page'),
                "priority": template_data.get('priority', 0),
                "is_dynamic": template_data.get('is_dynamic', False),
                "required_params": required_params_str,
                "required_object_types": required_object_types_str,
                "indexed_at": datetime.now().isoformat()
            }

            # 添加或更新到 ChromaDB
            self.collection.upsert(
                ids=[template_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text]
            )

            logger.info(f"已索引模板: {template_data.get('display_name', template_id)}")
            return True

        except Exception as e:
            logger.error(f"索引模板失败 {template_id}: {e}")
            return False

    def delete_template(self, template_id: str) -> bool:
        """
        删除模板索引

        Args:
            template_id: 模板 UUID

        Returns:
            是否删除成功
        """
        try:
            self.collection.delete(ids=[template_id])
            logger.info(f"已删除模板索引: {template_id}")
            return True
        except Exception as e:
            logger.error(f"删除模板索引失败 {template_id}: {e}")
            return False

    def search(
        self,
        query: str,
        sub_intent: Optional[str] = None,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        向量检索模板

        Args:
            query: 用户查询文本
            sub_intent: 业务子意图（可选，用于过滤）
            top_k: 返回的最大结果数，默认为 DEFAULT_TOP_K (5)

        Returns:
            检索结果列表，每个元素包含：
            - id: 模板 UUID
            - name: 英文名称
            - display_name: 中文显示名称
            - description: 描述
            - trigger_pattern: 触发模式
            - supported_sub_intents: 支持的子意图
            - template_path: 模板路径
            - score: 相似度分数 (0-1)
        """
        top_k = top_k or DEFAULT_TOP_K

        try:
            # 生成查询 embedding
            query_embedding = self.embedding_model.embed(query)

            # 执行检索（不使用 where 过滤，后续手动过滤）
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2 if sub_intent else top_k,  # 如果需要过滤，多取一些
                include=["metadatas", "distances", "documents"]
            )

            # 格式化结果
            formatted_results = []
            if results and results["ids"] and results["ids"][0]:
                for i, template_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0

                    # 如果指定了子意图，检查是否匹配
                    if sub_intent:
                        supported = metadata.get("supported_sub_intents", "")
                        if sub_intent not in supported:
                            continue

                    # L2 距离转相似度分数（与 PageIndex 保持一致）
                    score = math.exp(-distance / 800.0)

                    formatted_results.append({
                        "id": template_id,
                        "name": metadata.get("name", ""),
                        "display_name": metadata.get("display_name", ""),
                        "description": metadata.get("description", ""),
                        "trigger_pattern": metadata.get("trigger_pattern", ""),
                        "supported_sub_intents": metadata.get("supported_sub_intents", "").split(','),
                        "template_path": metadata.get("template_path", ""),
                        "template_type": metadata.get("template_type", "full_page"),
                        "priority": metadata.get("priority", 0),
                        "is_dynamic": metadata.get("is_dynamic", False),
                        "required_params": metadata.get("required_params", ""),
                        "required_object_types": [t for t in metadata.get("required_object_types", "").split(',') if t],
                        "score": score
                    })

            # 按分数排序并限制数量
            formatted_results.sort(key=lambda x: (-x.get("priority", 0), -x.get("score", 0)))
            formatted_results = formatted_results[:top_k]

            logger.info(f"模板向量检索完成，查询: '{query[:50]}...', 子意图: {sub_intent}, 返回 {len(formatted_results)} 个结果")
            return formatted_results

        except Exception as e:
            logger.error(f"模板向量检索失败: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取向量索引统计信息"""
        try:
            indexed_count = self.collection.count()

            # 统计各子意图的模板数量
            sub_intent_counts = {}
            results = self.collection.get(include=["metadatas"])
            if results and results["metadatas"]:
                for metadata in results["metadatas"]:
                    sub_intents = metadata.get("supported_sub_intents", "")
                    for intent in sub_intents.split(','):
                        intent = intent.strip()
                        if intent:
                            sub_intent_counts[intent] = sub_intent_counts.get(intent, 0) + 1

            # 获取数据库中的总模板数
            try:
                from ..models.database import WebTemplate, SessionLocal
                db = SessionLocal()
                try:
                    total_templates = db.query(WebTemplate).filter(WebTemplate.is_active == True).count()
                finally:
                    db.close()
            except Exception:
                total_templates = indexed_count

            return {
                "total_templates": total_templates,
                "indexed_count": indexed_count,
                "sub_intent_distribution": sub_intent_counts,
                "storage_dir": TEMPLATE_CHROMA_DIR
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"total_templates": 0, "indexed_count": 0, "sub_intent_distribution": {}, "storage_dir": TEMPLATE_CHROMA_DIR}

    def rebuild_index_from_db(self) -> int:
        """
        从数据库重建所有模板的向量索引

        用于初始化或修复索引

        Returns:
            成功索引的模板数量
        """
        try:
            from ..models.database import WebTemplate, SessionLocal

            db = SessionLocal()
            try:
                # 查询所有活跃的模板
                templates = db.query(WebTemplate).filter(
                    WebTemplate.is_active == True
                ).all()

                if not templates:
                    logger.info("数据库中没有活跃的模板，无需索引")
                    return 0

                # 清空现有索引
                existing_ids = self.collection.get()["ids"]
                if existing_ids:
                    self.collection.delete(ids=existing_ids)
                    logger.info(f"已清空 {len(existing_ids)} 个旧索引")

                # 重新索引所有模板
                success_count = 0
                for tpl in templates:
                    import json
                    template_data = {
                        "name": tpl.name,
                        "display_name": tpl.display_name,
                        "description": tpl.description,
                        "trigger_pattern": tpl.trigger_pattern,
                        "supported_sub_intents": json.loads(tpl.supported_sub_intents) if tpl.supported_sub_intents else [],
                        "template_path": tpl.template_path,
                        "template_type": tpl.template_type,
                        "priority": tpl.priority,
                        "is_dynamic": tpl.is_dynamic
                    }
                    if self.index_template(tpl.id, template_data):
                        success_count += 1

                logger.info(f"模板向量索引重建完成，成功索引 {success_count}/{len(templates)} 个模板")
                return success_count

            finally:
                db.close()

        except Exception as e:
            logger.error(f"重建模板向量索引失败: {e}")
            return 0


# 全局模板向量索引实例
_template_vector_index_instance: Optional[WebTemplateVectorIndex] = None


def get_template_vector_index() -> WebTemplateVectorIndex:
    """
    获取全局模板向量索引实例（单例模式）

    Returns:
        WebTemplateVectorIndex 实例
    """
    global _template_vector_index_instance
    if _template_vector_index_instance is None:
        _template_vector_index_instance = WebTemplateVectorIndex()
    return _template_vector_index_instance


def reset_template_vector_index():
    """重置模板向量索引实例（用于测试）"""
    global _template_vector_index_instance
    if _template_vector_index_instance is not None:
        _template_vector_index_instance._initialized = False
    _template_vector_index_instance = None
