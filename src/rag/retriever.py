"""
RAG检索器
对接PageIndex知识库检索系统
"""

import os
import sys
from typing import Dict, Any, Optional, List

# 添加PageIndex到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'PageIndex'))

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class RAGRetriever:
    """
    RAG检索器
    
    对接PageIndex的向量检索功能，从知识库检索相关文档
    """
    
    _instance: Optional['RAGRetriever'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._default_top_k = 5
        self._vector_index = None
        self._results_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'PageIndex', 'results')
        
        self._init_vector_index()
        self._initialized = True
        
        logger.info("RAG检索器初始化完成（对接PageIndex）")
    
    def _init_vector_index(self):
        """初始化向量索引"""
        try:
            from pageindex.vector_index import get_vector_index
            self._vector_index = get_vector_index()
            stats = self._vector_index.get_stats()
            logger.info(f"PageIndex向量索引连接成功: {stats['total_documents']} 个文档, {stats['total_nodes']} 个节点")
        except Exception as e:
            logger.error(f"PageIndex向量索引初始化失败: {e}")
            self._vector_index = None
    
    def _load_document_structure(self, doc_name: str) -> Optional[Dict]:
        """加载文档的结构JSON文件"""
        import json
        
        possible_names = [
            f"{doc_name}_structure.json",
            f"{doc_name.replace('.pdf', '')}_structure.json",
            f"{doc_name.replace('.md', '')}_structure.json",
        ]
        
        for name in possible_names:
            path = os.path.join(self._results_dir, name)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"加载文档结构失败 {path}: {e}")
        return None
    
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
    
    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_category: 按类别过滤（暂不支持，保留接口兼容）
            
        Returns:
            相关文档列表
        """
        logger.info(f"RAG检索: {query[:50]}...")
        
        if self._vector_index is None:
            logger.warning("向量索引未初始化")
            return []
        
        k = top_k or self._default_top_k
        
        try:
            from pageindex.vector_index import search_documents
            search_results = search_documents(query, top_k=k)
            
            # 转换为统一格式
            results = []
            for result in search_results:
                doc_name = result.get("doc_name", "")
                node_id = result.get("node_id", "")
                title = result.get("title", "")
                summary = result.get("summary", "")
                score = result.get("score", 0)
                
                # 尝试获取完整文本
                content = summary
                doc_data = self._load_document_structure(doc_name)
                if doc_data:
                    node_map = self._get_node_mapping(doc_data.get("structure", []))
                    node = node_map.get(node_id)
                    if node and node.get("text"):
                        content = node["text"]
                
                results.append({
                    'content': content,
                    'metadata': {
                        'doc_name': doc_name,
                        'node_id': node_id,
                        'title': title,
                        'category': doc_name,  # 使用文档名作为类别
                        'source': 'pageindex'
                    },
                    'id': f"{doc_name}_{node_id}",
                    'score': score
                })
            
            logger.info(f"检索到 {len(results)} 条相关文档")
            return results
            
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []
    
    async def retrieve_and_format(
        self,
        query: str,
        top_k: Optional[int] = None,
        filter_category: Optional[str] = None
    ) -> str:
        """
        检索并格式化为上下文文本
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            filter_category: 按类别过滤
            
        Returns:
            格式化的上下文文本
        """
        results = await self.retrieve(query, top_k, filter_category)
        
        if not results:
            return ""
        
        # 格式化为上下文
        context_parts = ["以下是相关的知识库内容：\n"]
        
        for i, doc in enumerate(results, 1):
            doc_name = doc.get('metadata', {}).get('doc_name', '未知文档')
            title = doc.get('metadata', {}).get('title', '未知章节')
            content = doc.get('content', '').strip()
            score = doc.get('score', 0)
            
            context_parts.append(f"[{i}] 文档: {doc_name}, 章节: {title} (相似度: {score:.3f})")
            context_parts.append(content[:2000])  # 限制每个文档的长度
            context_parts.append("")  # 空行分隔
        
        return "\n".join(context_parts)
    
    async def get_relevant_context(
        self,
        user_message: str,
        intent: Optional[str] = None,
        max_length: int = 8000
    ) -> Dict[str, Any]:
        """
        获取与用户消息相关的上下文
        
        Args:
            user_message: 用户消息
            intent: 用户意图（可用于优化检索）
            max_length: 上下文最大长度
            
        Returns:
            包含上下文和元信息的字典
        """
        # 根据意图确定检索数量
        top_k = self._default_top_k
        if intent in ['knowledge_qa', 'flood_forecast']:
            top_k = 8
        
        # 检索文档
        results = await self.retrieve(
            query=user_message,
            top_k=top_k
        )
        
        # 格式化上下文
        context_text = ""
        if results:
            context_parts = ["以下是相关的知识库内容：\n"]
            for i, doc in enumerate(results, 1):
                doc_name = doc.get('metadata', {}).get('doc_name', '未知文档')
                title = doc.get('metadata', {}).get('title', '未知章节')
                content = doc.get('content', '').strip()
                
                context_parts.append(f"[{i}] 文档: {doc_name}, 章节: {title}")
                context_parts.append(content[:2000])
                context_parts.append("")
            context_text = "\n".join(context_parts)
        
        # 截断过长的上下文
        if len(context_text) > max_length:
            context_text = context_text[:max_length] + "\n...(更多内容已省略)"
        
        return {
            "context": context_text,
            "documents": results,
            "document_count": len(results),
            "filter_category": None
        }
    
    def add_to_knowledge_base(
        self,
        content: str,
        category: str,
        source: str = "user"
    ) -> bool:
        """
        添加新知识到知识库
        
        注意：PageIndex需要通过文档处理流程添加知识，此方法暂不支持
        
        Args:
            content: 知识内容
            category: 知识类别
            source: 来源
            
        Returns:
            是否添加成功
        """
        logger.warning("PageIndex不支持直接添加文本，请通过PageIndex前端上传文档")
        return False
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if self._vector_index is None:
            return {
                'total_documents': 0,
                'total_nodes': 0,
                'documents': [],
                'using_vector_db': False,
                'backend': 'pageindex'
            }
        
        try:
            stats = self._vector_index.get_stats()
            return {
                'total_documents': stats.get('total_documents', 0),
                'total_nodes': stats.get('total_nodes', 0),
                'documents': stats.get('documents', []),
                'using_vector_db': True,
                'backend': 'pageindex'
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                'total_documents': 0,
                'total_nodes': 0,
                'documents': [],
                'using_vector_db': False,
                'backend': 'pageindex',
                'error': str(e)
            }


# 全局检索器实例
_retriever: Optional[RAGRetriever] = None


def get_rag_retriever() -> RAGRetriever:
    """获取RAG检索器单例"""
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever


async def search_knowledge(
    query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    搜索知识库的便捷函数
    
    Args:
        query: 查询文本
        top_k: 返回结果数量
        
    Returns:
        相关文档列表
    """
    retriever = get_rag_retriever()
    return await retriever.retrieve(query, top_k)


async def get_rag_context(
    user_message: str,
    intent: Optional[str] = None
) -> str:
    """
    获取RAG上下文的便捷函数
    
    Args:
        user_message: 用户消息
        intent: 用户意图
        
    Returns:
        格式化的上下文文本
    """
    retriever = get_rag_retriever()
    result = await retriever.get_relevant_context(user_message, intent)
    return result.get("context", "")
