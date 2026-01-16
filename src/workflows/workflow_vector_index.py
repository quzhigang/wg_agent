"""
工作流向量索引模块

为已保存的动态工作流提供向量检索能力，实现两阶段工作流匹配：
1. 第一阶段：向量检索粗筛，快速找出 Top-K 个候选工作流
2. 第二阶段：LLM 精选，从候选中选择最匹配的工作流

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

# 工作流向量索引存储目录（独立于知识库）
_default_workflow_chroma_dir = os.path.join(_project_root, "workflow_vectors")
WORKFLOW_CHROMA_DIR = os.getenv("WORKFLOW_CHROMA_DIR", _default_workflow_chroma_dir)

# 默认检索数量（与 PageIndex 的 RERANKER_TOP_K 保持一致）
DEFAULT_TOP_K = int(os.getenv("RERANKER_TOP_K", "5"))


class WorkflowVectorIndex:
    """
    工作流向量索引管理类

    为已保存的动态工作流提供向量检索能力，支持：
    - 按子意图过滤检索
    - 向量相似度排序
    - 自动索引新工作流
    """

    _instance: Optional['WorkflowVectorIndex'] = None

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
        os.makedirs(WORKFLOW_CHROMA_DIR, exist_ok=True)
        self.client = chromadb.PersistentClient(path=WORKFLOW_CHROMA_DIR)

        # 获取或创建工作流 collection
        self.collection = self.client.get_or_create_collection(
            name="saved_workflows",
            metadata={"description": "已保存的动态工作流向量索引"}
        )

        self._initialized = True
        logger.info(f"工作流向量索引初始化完成，存储目录: {WORKFLOW_CHROMA_DIR}")

    def _build_workflow_text(self, workflow_data: Dict[str, Any]) -> str:
        """
        构建工作流的文本表示（用于生成 embedding）

        组合多个字段以提高检索准确性：
        - trigger_pattern: 触发模式（最重要）
        - description: 工作流描述
        - display_name: 中文显示名称
        """
        parts = []

        # 触发模式是最重要的匹配依据
        trigger_pattern = workflow_data.get('trigger_pattern', '')
        if trigger_pattern:
            parts.append(trigger_pattern)

        # 描述提供额外的语义信息
        description = workflow_data.get('description', '')
        if description:
            parts.append(description)

        # 中文名称有助于匹配
        display_name = workflow_data.get('display_name', '')
        if display_name:
            parts.append(display_name)

        return " ".join(parts)

    def index_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]) -> bool:
        """
        索引单个工作流

        Args:
            workflow_id: 工作流 UUID
            workflow_data: 工作流数据，包含以下字段：
                - name: 英文名称
                - display_name: 中文显示名称
                - description: 描述
                - trigger_pattern: 触发模式
                - sub_intent: 业务子意图

        Returns:
            是否索引成功
        """
        try:
            # 构建文本表示
            text = self._build_workflow_text(workflow_data)
            if not text:
                logger.warning(f"工作流 {workflow_id} 无有效文本，跳过索引")
                return False

            # 生成 embedding
            embedding = self.embedding_model.embed(text)

            # 构建元数据
            metadata = {
                "name": workflow_data.get('name', ''),
                "display_name": workflow_data.get('display_name', ''),
                "sub_intent": workflow_data.get('sub_intent', 'other'),
                "description": workflow_data.get('description', '')[:500],  # 限制长度
                "trigger_pattern": workflow_data.get('trigger_pattern', '')[:500],
                "indexed_at": datetime.now().isoformat()
            }

            # 添加或更新到 ChromaDB
            self.collection.upsert(
                ids=[workflow_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[text]
            )

            logger.info(f"已索引工作流: {workflow_data.get('display_name', workflow_id)}")
            return True

        except Exception as e:
            logger.error(f"索引工作流失败 {workflow_id}: {e}")
            return False

    def delete_workflow(self, workflow_id: str) -> bool:
        """
        删除工作流索引

        Args:
            workflow_id: 工作流 UUID

        Returns:
            是否删除成功
        """
        try:
            self.collection.delete(ids=[workflow_id])
            logger.info(f"已删除工作流索引: {workflow_id}")
            return True
        except Exception as e:
            logger.error(f"删除工作流索引失败 {workflow_id}: {e}")
            return False

    def search(
        self,
        query: str,
        sub_intent: Optional[str] = None,
        top_k: int = None
    ) -> List[Dict[str, Any]]:
        """
        向量检索工作流

        Args:
            query: 用户查询文本
            sub_intent: 业务子意图（可选，用于过滤）
            top_k: 返回的最大结果数，默认为 DEFAULT_TOP_K (5)

        Returns:
            检索结果列表，每个元素包含：
            - id: 工作流 UUID
            - name: 英文名称
            - display_name: 中文显示名称
            - description: 描述
            - trigger_pattern: 触发模式
            - sub_intent: 业务子意图
            - score: 相似度分数 (0-1)
        """
        top_k = top_k or DEFAULT_TOP_K

        try:
            # 生成查询 embedding
            query_embedding = self.embedding_model.embed(query)

            # 构建过滤条件
            where_filter = None
            if sub_intent:
                where_filter = {"sub_intent": sub_intent}

            # 执行检索
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter,
                include=["metadatas", "distances", "documents"]
            )

            # 格式化结果
            formatted_results = []
            if results and results["ids"] and results["ids"][0]:
                for i, workflow_id in enumerate(results["ids"][0]):
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0

                    # L2 距离转相似度分数（与 PageIndex 保持一致）
                    score = math.exp(-distance / 800.0)

                    formatted_results.append({
                        "id": workflow_id,
                        "name": metadata.get("name", ""),
                        "display_name": metadata.get("display_name", ""),
                        "description": metadata.get("description", ""),
                        "trigger_pattern": metadata.get("trigger_pattern", ""),
                        "sub_intent": metadata.get("sub_intent", ""),
                        "score": score
                    })

            # 按分数排序
            formatted_results.sort(key=lambda x: x.get("score", 0), reverse=True)

            logger.info(f"工作流向量检索完成，查询: '{query[:50]}...', 子意图: {sub_intent}, 返回 {len(formatted_results)} 个结果")
            return formatted_results

        except Exception as e:
            logger.error(f"工作流向量检索失败: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """获取向量索引统计信息"""
        try:
            total_count = self.collection.count()

            # 统计各子意图的工作流数量
            sub_intent_counts = {}
            results = self.collection.get(include=["metadatas"])
            if results and results["metadatas"]:
                for metadata in results["metadatas"]:
                    sub_intent = metadata.get("sub_intent", "unknown")
                    sub_intent_counts[sub_intent] = sub_intent_counts.get(sub_intent, 0) + 1

            return {
                "total_workflows": total_count,
                "sub_intent_distribution": sub_intent_counts,
                "storage_dir": WORKFLOW_CHROMA_DIR
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"total_workflows": 0, "sub_intent_distribution": {}, "storage_dir": WORKFLOW_CHROMA_DIR}

    def rebuild_index_from_db(self) -> int:
        """
        从数据库重建所有工作流的向量索引

        用于初始化或修复索引

        Returns:
            成功索引的工作流数量
        """
        try:
            from ..models.database import SavedWorkflow, SessionLocal

            db = SessionLocal()
            try:
                # 查询所有活跃的工作流
                workflows = db.query(SavedWorkflow).filter(
                    SavedWorkflow.is_active == True
                ).all()

                if not workflows:
                    logger.info("数据库中没有活跃的工作流，无需索引")
                    return 0

                # 清空现有索引
                existing_ids = self.collection.get()["ids"]
                if existing_ids:
                    self.collection.delete(ids=existing_ids)
                    logger.info(f"已清空 {len(existing_ids)} 个旧索引")

                # 重新索引所有工作流
                success_count = 0
                for wf in workflows:
                    workflow_data = {
                        "name": wf.name,
                        "display_name": wf.display_name,
                        "description": wf.description,
                        "trigger_pattern": wf.trigger_pattern,
                        "sub_intent": wf.sub_intent
                    }
                    if self.index_workflow(wf.id, workflow_data):
                        success_count += 1

                logger.info(f"工作流向量索引重建完成，成功索引 {success_count}/{len(workflows)} 个工作流")
                return success_count

            finally:
                db.close()

        except Exception as e:
            logger.error(f"重建工作流向量索引失败: {e}")
            return 0

    def ensure_indexed(self, workflow_id: str) -> bool:
        """
        确保工作流已被索引，如果未索引则从数据库加载并索引

        Args:
            workflow_id: 工作流 UUID

        Returns:
            是否已索引
        """
        try:
            # 检查是否已索引
            result = self.collection.get(ids=[workflow_id])
            if result and result["ids"]:
                return True

            # 从数据库加载并索引
            from ..models.database import SavedWorkflow, SessionLocal

            db = SessionLocal()
            try:
                wf = db.query(SavedWorkflow).filter(
                    SavedWorkflow.id == workflow_id,
                    SavedWorkflow.is_active == True
                ).first()

                if wf:
                    workflow_data = {
                        "name": wf.name,
                        "display_name": wf.display_name,
                        "description": wf.description,
                        "trigger_pattern": wf.trigger_pattern,
                        "sub_intent": wf.sub_intent
                    }
                    return self.index_workflow(workflow_id, workflow_data)
                return False
            finally:
                db.close()

        except Exception as e:
            logger.error(f"确保工作流索引失败 {workflow_id}: {e}")
            return False


# 全局工作流向量索引实例
_workflow_vector_index_instance: Optional[WorkflowVectorIndex] = None


def get_workflow_vector_index() -> WorkflowVectorIndex:
    """
    获取全局工作流向量索引实例（单例模式）

    Returns:
        WorkflowVectorIndex 实例
    """
    global _workflow_vector_index_instance
    if _workflow_vector_index_instance is None:
        _workflow_vector_index_instance = WorkflowVectorIndex()
    return _workflow_vector_index_instance


def reset_workflow_vector_index():
    """重置工作流向量索引实例（用于测试）"""
    global _workflow_vector_index_instance
    if _workflow_vector_index_instance is not None:
        _workflow_vector_index_instance._initialized = False
    _workflow_vector_index_instance = None
