"""
知识库管理
管理流域专业知识的存储和索引
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import hashlib

from ..config.logging_config import get_logger
from ..config.settings import settings

logger = get_logger(__name__)


class Document:
    """文档类"""
    
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
    
    管理流域专业知识文档的存储和检索
    使用ChromaDB作为向量数据库（简化版使用内存存储）
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
        
        self._documents: Dict[str, Document] = {}
        self._embeddings: Dict[str, List[float]] = {}
        self._collection = None
        self._embedding_model = None
        
        self._init_vector_db()
        self._load_default_knowledge()
        self._initialized = True
        
        logger.info("知识库初始化完成")
    
    def _init_vector_db(self):
        """初始化向量数据库"""
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            # 创建ChromaDB客户端
            self._chroma_client = chromadb.Client(ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            ))
            
            # 获取或创建集合
            self._collection = self._chroma_client.get_or_create_collection(
                name="wg_knowledge",
                metadata={"description": "卫共流域知识库"}
            )
            
            logger.info("ChromaDB向量数据库初始化成功")
            
        except ImportError:
            logger.warning("ChromaDB未安装，使用简化的内存存储")
            self._collection = None
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {e}")
            self._collection = None
    
    def _load_default_knowledge(self):
        """加载默认知识库内容"""
        
        # 流域基础知识
        default_docs = [
            Document(
                content="""卫共流域位于中国华北地区，是海河流域的重要组成部分。
                流域面积约15000平方公里，主要河流包括卫河、共产主义渠等。
                流域地形以平原为主，气候属于温带季风气候，年均降水量约600mm。
                汛期主要集中在7-8月，易发生洪涝灾害。""",
                metadata={"category": "流域概况", "source": "default"}
            ),
            Document(
                content="""洪水预报是根据实测和预报的水文气象资料，应用水文学方法，
                对未来一定时期内的洪水过程进行预测。主要方法包括：
                1. 降雨径流预报：根据降雨量预测径流量
                2. 河道洪水演进：利用马斯京根法等计算洪水传播
                3. 水库调度：考虑水库调蓄作用优化泄洪方案
                预报精度受数据质量、模型参数等因素影响。""",
                metadata={"category": "专业知识", "source": "default"}
            ),
            Document(
                content="""防洪预警等级分为四级：
                - 蓝色预警（IV级）：可能发生一般洪水
                - 黄色预警（III级）：可能发生较大洪水
                - 橙色预警（II级）：可能发生大洪水
                - 红色预警（I级）：可能发生特大洪水
                各级预警对应不同的应急响应措施和人员转移要求。""",
                metadata={"category": "防洪知识", "source": "default"}
            ),
            Document(
                content="""水文监测站网是水文信息采集的基础设施，包括：
                - 水位站：监测河道、水库水位变化
                - 雨量站：监测降雨量和降雨强度
                - 流量站：监测河道流量
                - 水质站：监测水体水质指标
                卫共流域共有各类水文监测站点约200个，实现了重点区域全覆盖。""",
                metadata={"category": "监测设施", "source": "default"}
            ),
            Document(
                content="""应急预案编制要点：
                1. 明确组织指挥体系和职责分工
                2. 制定预警信息发布和传递机制
                3. 确定人员转移路线和安置点
                4. 准备应急物资和救援力量
                5. 建立信息报告和值班制度
                预案应定期演练和修订，确保可操作性。""",
                metadata={"category": "应急管理", "source": "default"}
            )
        ]
        
        for doc in default_docs:
            self.add_document(doc)
        
        logger.info(f"加载默认知识文档 {len(default_docs)} 条")
    
    def add_document(self, document: Document) -> bool:
        """
        添加文档到知识库
        
        Args:
            document: 文档对象
            
        Returns:
            是否添加成功
        """
        try:
            self._documents[document.doc_id] = document
            
            if self._collection is not None:
                # 添加到ChromaDB
                self._collection.add(
                    documents=[document.content],
                    metadatas=[document.metadata],
                    ids=[document.doc_id]
                )
            
            logger.debug(f"添加文档: {document.doc_id}")
            return True
            
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False
    
    def add_documents(self, documents: List[Document]) -> int:
        """批量添加文档"""
        success_count = 0
        for doc in documents:
            if self.add_document(doc):
                success_count += 1
        return success_count
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """获取文档"""
        return self._documents.get(doc_id)
    
    def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        if doc_id in self._documents:
            del self._documents[doc_id]
            
            if self._collection is not None:
                try:
                    self._collection.delete(ids=[doc_id])
                except Exception as e:
                    logger.warning(f"从向量库删除文档失败: {e}")
            
            return True
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
            filter_metadata: 元数据过滤条件
            
        Returns:
            相关文档列表
        """
        if self._collection is not None:
            try:
                # 使用ChromaDB搜索
                results = self._collection.query(
                    query_texts=[query],
                    n_results=top_k,
                    where=filter_metadata
                )
                
                documents = []
                if results['documents'] and results['documents'][0]:
                    for i, doc_content in enumerate(results['documents'][0]):
                        documents.append({
                            'content': doc_content,
                            'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                            'id': results['ids'][0][i] if results['ids'] else None,
                            'distance': results['distances'][0][i] if results.get('distances') else None
                        })
                
                return documents
                
            except Exception as e:
                logger.error(f"向量搜索失败: {e}")
        
        # 降级到简单关键词搜索
        return self._simple_search(query, top_k, filter_metadata)
    
    def _simple_search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """简单关键词搜索（降级方案）"""
        
        results = []
        query_lower = query.lower()
        
        for doc_id, doc in self._documents.items():
            # 元数据过滤
            if filter_metadata:
                match = all(
                    doc.metadata.get(k) == v 
                    for k, v in filter_metadata.items()
                )
                if not match:
                    continue
            
            # 简单相关性计算
            content_lower = doc.content.lower()
            score = 0
            
            # 计算查询词出现次数
            for word in query_lower.split():
                if len(word) >= 2:
                    score += content_lower.count(word)
            
            if score > 0:
                results.append({
                    'content': doc.content,
                    'metadata': doc.metadata,
                    'id': doc_id,
                    'score': score
                })
        
        # 按分数排序
        results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return results[:top_k]
    
    def list_documents(
        self,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[Document]:
        """列出文档"""
        docs = list(self._documents.values())
        
        if category:
            docs = [d for d in docs if d.metadata.get('category') == category]
        
        return docs[:limit]
    
    def get_categories(self) -> List[str]:
        """获取所有文档类别"""
        categories = set()
        for doc in self._documents.values():
            cat = doc.metadata.get('category')
            if cat:
                categories.add(cat)
        return list(categories)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return {
            'total_documents': len(self._documents),
            'categories': self.get_categories(),
            'using_vector_db': self._collection is not None
        }
    
    def clear(self):
        """清空知识库"""
        self._documents.clear()
        
        if self._collection is not None:
            try:
                # 重新创建集合
                self._chroma_client.delete_collection("wg_knowledge")
                self._collection = self._chroma_client.create_collection(
                    name="wg_knowledge",
                    metadata={"description": "卫共流域知识库"}
                )
            except Exception as e:
                logger.error(f"清空向量库失败: {e}")
        
        logger.info("知识库已清空")


# 全局知识库实例
_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """获取知识库单例"""
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase()
    return _knowledge_base
