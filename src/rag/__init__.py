"""
RAG模块
对接PageIndex知识库检索系统，提供知识库检索和问答增强功能
"""

from .retriever import RAGRetriever, get_rag_retriever, search_knowledge, get_rag_context
from .knowledge_base import KnowledgeBase, get_knowledge_base, Document

__all__ = [
    "RAGRetriever",
    "get_rag_retriever",
    "search_knowledge",
    "get_rag_context",
    "KnowledgeBase",
    "get_knowledge_base",
    "Document"
]
