"""
知识库管理
对接PageIndex知识库系统
"""

import os
import sys
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import hashlib

# 添加PageIndex到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'PageIndex'))

from ..config.logging_config import get_logger
from pageindex.kb_manager import get_kb_manager
from pageindex.vector_index import get_multi_kb_vector_index

logger = get_logger(__name__)


class Document:
    """文档类（保持接口兼容）"""
    
    def __init__(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ):
        self.content = content
        self.metadata = metadata or {}
        self.doc_id = doc_id or self._generate_id(content)
    
    def _generate_id(self, content: str) -> str:
        """根据内容生成唯一ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        return cls(
            content=data["content"],
            metadata=data.get("metadata", {}),
            doc_id=data.get("doc_id")
        )


class KnowledgeBase:
    """
    知识库
    
    对接PageIndex的向量索引系统
    """
    
    _instance: Optional['KnowledgeBase'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return

        self._multi_kb_index = None
        self._kb_manager = None
        self._kb_base_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'PageIndex', 'knowledge_bases')

        self._init_vector_db()
        self._initialized = True

        logger.info("知识库初始化完成（对接PageIndex）")

    def _init_vector_db(self):
        """初始化多知识库向量数据库"""
        try:
            self._multi_kb_index = get_multi_kb_vector_index()
            self._kb_manager = get_kb_manager()
            kb_ids = self._kb_manager.list_ids()
            total_docs = 0
            total_nodes = 0
            for kb_id in kb_ids:
                chroma_dir = self._kb_manager.get_chroma_dir(kb_id)
                stats = self._multi_kb_index.get_stats(kb_id, chroma_dir)
                total_docs += stats.get('total_documents', 0)
                total_nodes += stats.get('total_nodes', 0)
            logger.info(f"PageIndex向量索引连接成功: {total_docs} 个文档, {total_nodes} 个节点")
        except Exception as e:
            logger.error(f"PageIndex向量索引初始化失败: {e}")
            self._multi_kb_index = None
    
    def _get_node_mapping(self, structure, mapping=None) -> Dict:
        """从树结构中构建node_id到节点的映射"""
        if mapping is None:
            mapping = {}
        if isinstance(structure, list):
            for item in structure:
                self._get_node_mapping(item, mapping)
        elif isinstance(structure, dict):
            if 'node_id' in structure:
                mapping[structure['node_id']] = structure
            if 'nodes' in structure:
                self._get_node_mapping(structure['nodes'], mapping)
        return mapping
    
    def add_document(self, document: Document) -> bool:
        """
        添加文档到知识库
        
        注意：PageIndex需要通过文档处理流程添加知识，此方法暂不支持
        
        Args:
            document: 文档对象
            
        Returns:
            是否添加成功
        """
        logger.warning("PageIndex不支持直接添加文本，请通过PageIndex前端上传文档")
        return False
    
    def add_documents(self, documents: List[Document]) -> int:
        """批量添加文档（暂不支持）"""
        logger.warning("PageIndex不支持直接添加文本，请通过PageIndex前端上传文档")
        return 0
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """获取文档（通过doc_name查找）"""
        if self._multi_kb_index is None or self._kb_manager is None:
            return None

        try:
            # 在所有知识库中查找文档
            for kb_id in self._kb_manager.list_ids():
                results_dir = os.path.join(self._kb_base_dir, kb_id, "results")
                structure_path = os.path.join(results_dir, f"{doc_id}_structure.json")
                if os.path.exists(structure_path):
                    with open(structure_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    content_parts = []
                    structure = data.get("structure", [])
                    node_map = self._get_node_mapping(structure)

                    for node_id, node in node_map.items():
                        if node.get("text"):
                            content_parts.append(node["text"])
                        elif node.get("summary"):
                            content_parts.append(node["summary"])

                    return Document(
                        content="\n\n".join(content_parts),
                        metadata={
                            "doc_name": data.get("doc_name", doc_id),
                            "doc_description": data.get("doc_description", ""),
                            "source": "pageindex"
                        },
                        doc_id=doc_id
                    )
        except Exception as e:
            logger.error(f"获取文档失败: {e}")

        return None

    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        logger.warning("PageIndex不支持直接删除文档，请通过PageIndex前端操作")
        return False
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件（暂不支持）

        Returns:
            相关文档列表
        """
        if self._multi_kb_index is None or self._kb_manager is None:
            logger.warning("向量索引未初始化")
            return []

        try:
            kb_ids = self._kb_manager.list_ids()
            kb_configs = [{"kb_id": kb_id, "chroma_dir": self._kb_manager.get_chroma_dir(kb_id)} for kb_id in kb_ids]
            search_results = self._multi_kb_index.search_multi_kb(kb_configs, query, top_k=top_k, use_rerank=False)

            documents = []
            for result in search_results:
                kb_id = result.get("kb_id", "")
                doc_name = result.get("doc_name", "")
                node_id = result.get("node_id", "")
                title = result.get("title", "")
                summary = result.get("summary", "")
                score = result.get("score", 0)

                content = summary
                results_dir = os.path.join(self._kb_base_dir, kb_id, "results")
                structure_path = os.path.join(results_dir, f"{doc_name}_structure.json")
                if os.path.exists(structure_path):
                    try:
                        with open(structure_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        node_map = self._get_node_mapping(data.get("structure", []))
                        node = node_map.get(node_id)
                        if node and node.get("text"):
                            content = node["text"]
                    except Exception:
                        pass

                documents.append({
                    'content': content,
                    'metadata': {
                        'doc_name': doc_name,
                        'node_id': node_id,
                        'title': title,
                        'category': kb_id or doc_name,
                        'source': 'pageindex'
                    },
                    'id': f"{doc_name}_{node_id}",
                    'distance': 1 - score
                })

            return documents

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def list_documents(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Document]:
        """列出文档"""
        documents = []

        if self._kb_manager is None:
            return documents

        try:
            for kb_id in self._kb_manager.list_ids():
                if category and category != kb_id:
                    continue
                results_dir = os.path.join(self._kb_base_dir, kb_id, "results")
                if not os.path.exists(results_dir):
                    continue
                structure_files = [f for f in os.listdir(results_dir) if f.endswith("_structure.json")]
                for filename in structure_files:
                    if len(documents) >= limit:
                        break
                    doc_id = filename.replace("_structure.json", "")
                    doc = self.get_document(doc_id)
                    if doc:
                        documents.append(doc)
        except Exception as e:
            logger.error(f"列出文档失败: {e}")

        return documents
    
    def get_categories(self) -> List[str]:
        """获取所有知识库ID列表"""
        if self._kb_manager is None:
            return []

        try:
            return self._kb_manager.list_ids()
        except Exception as e:
            logger.error(f"获取类别失败: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if self._multi_kb_index is None or self._kb_manager is None:
            return {
                'total_documents': 0,
                'total_nodes': 0,
                'categories': [],
                'using_vector_db': False,
                'backend': 'pageindex'
            }

        try:
            kb_ids = self._kb_manager.list_ids()
            total_docs = 0
            total_nodes = 0
            all_documents = []

            for kb_id in kb_ids:
                chroma_dir = self._kb_manager.get_chroma_dir(kb_id)
                stats = self._multi_kb_index.get_stats(kb_id, chroma_dir)
                total_docs += stats.get('total_documents', 0)
                total_nodes += stats.get('total_nodes', 0)
                all_documents.extend(stats.get('documents', []))

            return {
                'total_documents': total_docs,
                'total_nodes': total_nodes,
                'categories': all_documents,
                'knowledge_bases': kb_ids,
                'using_vector_db': True,
                'backend': 'pageindex'
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                'total_documents': 0,
                'total_nodes': 0,
                'categories': [],
                'using_vector_db': False,
                'backend': 'pageindex',
                'error': str(e)
            }
    
    def clear(self):
        """清空知识库"""
        logger.warning("PageIndex不支持直接清空知识库，请通过PageIndex前端操作")


# 全局知识库实例
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库单例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
