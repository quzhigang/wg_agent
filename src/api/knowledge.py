"""
知识库管理接口
提供知识库的增删改查功能
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config.logging_config import get_logger
from ..rag.knowledge_base import get_knowledge_base, Document
from ..rag.retriever import get_rag_retriever
from ..models.schemas import APIResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库"])


class DocumentCreate(BaseModel):
    """创建文档请求"""
    content: str = Field(..., description="文档内容")
    category: str = Field(..., description="文档类别")
    source: str = Field(default="user", description="来源")


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str = Field(..., description="搜索查询")
    top_k: int = Field(default=5, description="返回结果数量")
    category: Optional[str] = Field(default=None, description="按类别过滤")


@router.get("", response_model=APIResponse)
async def get_knowledge_stats():
    """
    获取知识库统计信息
    
    Returns:
        知识库统计数据
    """
    try:
        kb = get_knowledge_base()
        stats = kb.get_stats()
        
        return APIResponse(
            success=True,
            message="获取成功",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"获取知识库统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories", response_model=APIResponse)
async def get_categories():
    """
    获取所有文档类别
    
    Returns:
        类别列表
    """
    try:
        kb = get_knowledge_base()
        categories = kb.get_categories()
        
        return APIResponse(
            success=True,
            message="获取成功",
            data=categories
        )
        
    except Exception as e:
        logger.error(f"获取类别失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=APIResponse)
async def list_documents(
    category: Optional[str] = None,
    limit: int = 100
):
    """
    列出知识库文档
    
    Args:
        category: 按类别过滤
        limit: 返回数量限制
        
    Returns:
        文档列表
    """
    try:
        kb = get_knowledge_base()
        docs = kb.list_documents(category=category, limit=limit)
        
        return APIResponse(
            success=True,
            message="获取成功",
            data=[doc.to_dict() for doc in docs]
        )
        
    except Exception as e:
        logger.error(f"列出文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{doc_id}", response_model=APIResponse)
async def get_document(doc_id: str):
    """
    获取单个文档
    
    Args:
        doc_id: 文档ID
        
    Returns:
        文档详情
    """
    try:
        kb = get_knowledge_base()
        doc = kb.get_document(doc_id)
        
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return APIResponse(
            success=True,
            message="获取成功",
            data=doc.to_dict()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents", response_model=APIResponse)
async def add_document(request: DocumentCreate):
    """
    添加文档到知识库
    
    Args:
        request: 文档创建请求
        
    Returns:
        创建结果
    """
    try:
        kb = get_knowledge_base()
        
        doc = Document(
            content=request.content,
            metadata={
                "category": request.category,
                "source": request.source
            }
        )
        
        success = kb.add_document(doc)
        
        if not success:
            raise HTTPException(status_code=500, detail="添加文档失败")
        
        return APIResponse(
            success=True,
            message="添加成功",
            data={"doc_id": doc.doc_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}", response_model=APIResponse)
async def delete_document(doc_id: str):
    """
    删除文档
    
    Args:
        doc_id: 文档ID
        
    Returns:
        删除结果
    """
    try:
        kb = get_knowledge_base()
        success = kb.delete_document(doc_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        return APIResponse(
            success=True,
            message="删除成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=APIResponse)
async def search_documents(request: SearchRequest):
    """
    搜索知识库
    
    Args:
        request: 搜索请求
        
    Returns:
        搜索结果
    """
    try:
        retriever = get_rag_retriever()
        
        results = await retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            filter_category=request.category
        )
        
        return APIResponse(
            success=True,
            message="搜索成功",
            data=results
        )
        
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
