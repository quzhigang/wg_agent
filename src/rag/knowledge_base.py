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
        
        self._vector_index = None
        self._results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'PageIndex', 'results')
        
        self._init_vector_db()
        self._initialized = True
        
        logger.info("知识库初始化完成（对接PageIndex）")
    
    def _init_vector_db(self):
        """初始化向量数据库"""
        try:
            from pageindex.vector_index import get_vector_index
            self._vector_index = get_vector_index()
            stats = self._vector_index.get_stats()
            logger.info(f"PageIndex向量索引连接成功: {stats['total_documents']} 个文档, {stats['total_nodes']} 个节点")
        except Exception as e:
            logger.error(f"PageIndex向量索引初始化失败: {e}")
            self._vector_index = None
    
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
        if self._vector_index is None:
            return None
        
        try:
            # 尝试加载文档结构
            structure_path = os.path.join(self._results_dir, f"{doc_id}_structure.json")
            if os.path.exists(structure_path):
                with open(structure_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # 提取文档内容
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
        if self._vector_index is None:
            return False
        
        try:
            # 删除向量索引
            deleted_count = self._vector_index.delete_document(doc_id)
            
            # 删除结构文件
            structure_path = os.path.join(self._results_dir, f"{doc_id}_structure.json")
            if os.path.exists(structure_path):
                os.remove(structure_path)
            
            logger.info(f"已删除文档 {doc_id}，共 {deleted_count} 个节点")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
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
        if self._vector_index is None:
            logger.warning("向量索引未初始化")
            return []
        
        try:
            from pageindex.vector_index import search_documents
            search_results = search_documents(query, top_k=top_k)
            
            # 转换为统一格式
            documents = []
            for result in search_results:
                doc_name = result.get("doc_name", "")
                node_id = result.get("node_id", "")
                title = result.get("title", "")
                summary = result.get("summary", "")
                score = result.get("score", 0)
                
                # 尝试获取完整文本
                content = summary
                structure_path = os.path.join(self._results_dir, f"{doc_name}_structure.json")
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
                        'category': doc_name,
                        'source': 'pageindex'
                    },
                    'id': f"{doc_name}_{node_id}",
                    'distance': 1 - score  # 转换为距离
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
        
        if not os.path.exists(self._results_dir):
            return documents
        
        try:
            structure_files = [f for f in os.listdir(self._results_dir) if f.endswith("_structure.json")]
            
            for filename in structure_files[:limit]:
                doc_id = filename.replace("_structure.json", "")
                
                # 如果指定了类别，进行过滤
                if category and category != doc_id:
                    continue
                
                doc = self.get_document(doc_id)
                if doc:
                    documents.append(doc)
        except Exception as e:
            logger.error(f"列出文档失败: {e}")
        
        return documents
    
    def get_categories(self) -> List[str]:
        """获取所有文档类别（返回文档名列表）"""
        if self._vector_index is None:
            return []
        
        try:
            return self._vector_index.get_all_documents()
        except Exception as e:
            logger.error(f"获取类别失败: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if self._vector_index is None:
            return {
                'total_documents': 0,
                'total_nodes': 0,
                'categories': [],
                'using_vector_db': False,
                'backend': 'pageindex'
            }
        
        try:
            stats = self._vector_index.get_stats()
            return {
                'total_documents': stats.get('total_documents', 0),
                'total_nodes': stats.get('total_nodes', 0),
                'categories': stats.get('documents', []),
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
        if self._vector_index is None:
            return
        
        try:
            docs = self._vector_index.get_all_documents()
            for doc in docs:
                self._vector_index.delete_document(doc)
            logger.info(f"已清空 {len(docs)} 个文档的索引")
        except Exception as e:
            logger.error(f"清空知识库失败: {e}")


# 全局知识库实例
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库单例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
