"""
RAG检索器
实现知识库检索和问答增强
"""

from typing import Dict, Any, Optional, List

from ..config.logging_config import get_logger
from ..config.settings import settings
from .knowledge_base import get_knowledge_base, KnowledgeBase

logger = get_logger(__name__)


class RAGRetriever:
    """
    RAG检索器
    
    负责从知识库检索相关文档，并生成增强的上下文
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
        
        self._knowledge_base = get_knowledge_base()
        self._default_top_k = 3
        self._initialized = True
        
        logger.info("RAG检索器初始化完成")
    
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
            filter_category: 按类别过滤
            
        Returns:
            相关文档列表
        """
        logger.info(f"RAG检索: {query[:50]}...")
        
        k = top_k or self._default_top_k
        filter_metadata = None
        
        if filter_category:
            filter_metadata = {"category": filter_category}
        
        # 从知识库搜索
        results = self._knowledge_base.search(
            query=query,
            top_k=k,
            filter_metadata=filter_metadata
        )
        
        logger.info(f"检索到 {len(results)} 条相关文档")
        
        return results
    
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
            category = doc.get('metadata', {}).get('category', '未分类')
            content = doc.get('content', '').strip()
            
            context_parts.append(f"[{i}] ({category})")
            context_parts.append(content)
            context_parts.append("")  # 空行分隔
        
        return "\n".join(context_parts)
    
    async def get_relevant_context(
        self,
        user_message: str,
        intent: Optional[str] = None,
        max_length: int = 2000
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
        # 根据意图确定检索策略
        filter_category = None
        top_k = self._default_top_k
        
        if intent:
            intent_category_map = {
                'flood_forecast': '专业知识',
                'emergency_plan': '应急管理',
                'basin_info': '流域概况',
                'hydro_monitor': '监测设施',
                'general_chat': None,
                'knowledge_qa': None
            }
            filter_category = intent_category_map.get(intent)
            
            # 专业问题多检索一些
            if intent in ['knowledge_qa', 'flood_forecast']:
                top_k = 5
        
        # 检索文档（只检索一次）
        results = await self.retrieve(
            query=user_message,
            top_k=top_k,
            filter_category=filter_category
        )
        
        # 直接格式化已检索的结果（避免重复检索）
        context_text = ""
        if results:
            context_parts = ["以下是相关的知识库内容：\n"]
            for i, doc in enumerate(results, 1):
                category = doc.get('metadata', {}).get('category', '未分类')
                content = doc.get('content', '').strip()
                context_parts.append(f"[{i}] ({category})")
                context_parts.append(content)
                context_parts.append("")  # 空行分隔
            context_text = "\n".join(context_parts)
        
        # 截断过长的上下文
        if len(context_text) > max_length:
            context_text = context_text[:max_length] + "\n...(更多内容已省略)"
        
        return {
            "context": context_text,
            "documents": results,
            "document_count": len(results),
            "filter_category": filter_category
        }
    
    def add_to_knowledge_base(
        self,
        content: str,
        category: str,
        source: str = "user"
    ) -> bool:
        """
        添加新知识到知识库
        
        Args:
            content: 知识内容
            category: 知识类别
            source: 来源
            
        Returns:
            是否添加成功
        """
        from .knowledge_base import Document
        
        doc = Document(
            content=content,
            metadata={
                "category": category,
                "source": source
            }
        )
        
        return self._knowledge_base.add_document(doc)
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        return self._knowledge_base.get_stats()


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
    top_k: int = 3
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
