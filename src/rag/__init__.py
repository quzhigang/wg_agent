"""
RAG模块
提供知识库检索和问答增强功能
"""

from .retriever import RAGRetriever, get_rag_retriever, search_knowledge, get_rag_context
from .knowledge_base import KnowledgeBase, get_knowledge_base

__all__ = [
    "RAGRetriever",
    "get_rag_retriever",
    "search_knowledge",
    "get_rag_context",
    "KnowledgeBase",
    "get_knowledge_base"
]
