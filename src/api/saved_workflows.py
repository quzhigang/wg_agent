"""
自动保存流程管理API
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..models.database import SavedWorkflow, SessionLocal
from ..config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/saved-workflows", tags=["流程管理"])


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    trigger_pattern: Optional[str] = None
    sub_intent: Optional[str] = None
    plan_steps: Optional[list] = None
    is_active: Optional[bool] = None


@router.get("")
def list_workflows(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sub_intent: Optional[str] = None
):
    """获取流程清单"""
    db = SessionLocal()
    try:
        query = db.query(SavedWorkflow)
        if sub_intent:
            query = query.filter(SavedWorkflow.sub_intent == sub_intent)

        total = query.count()
        items = query.order_by(SavedWorkflow.created_at.desc())\
            .offset((page - 1) * size).limit(size).all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": [{
                "id": w.id,
                "name": w.name,
                "display_name": w.display_name,
                "description": w.description,
                "sub_intent": w.sub_intent,
                "use_count": w.use_count,
                "is_active": w.is_active,
                "created_at": w.created_at.isoformat() if w.created_at else None
            } for w in items]
        }
    finally:
        db.close()


@router.get("/{workflow_id}")
def get_workflow(workflow_id: str):
    """获取流程详情"""
    db = SessionLocal()
    try:
        w = db.query(SavedWorkflow).filter(SavedWorkflow.id == workflow_id).first()
        if not w:
            raise HTTPException(404, "流程不存在")

        return {
            "id": w.id,
            "name": w.name,
            "display_name": w.display_name,
            "description": w.description,
            "trigger_pattern": w.trigger_pattern,
            "intent_category": w.intent_category,
            "sub_intent": w.sub_intent,
            "entities_pattern": json.loads(w.entities_pattern) if w.entities_pattern else {},
            "plan_steps": json.loads(w.plan_steps) if w.plan_steps else [],
            "output_type": w.output_type,
            "source": w.source,
            "use_count": w.use_count,
            "success_count": w.success_count,
            "is_active": w.is_active,
            "created_at": w.created_at.isoformat() if w.created_at else None,
            "updated_at": w.updated_at.isoformat() if w.updated_at else None
        }
    finally:
        db.close()


@router.put("/{workflow_id}")
def update_workflow(workflow_id: str, data: WorkflowUpdate):
    """编辑流程"""
    db = SessionLocal()
    try:
        w = db.query(SavedWorkflow).filter(SavedWorkflow.id == workflow_id).first()
        if not w:
            raise HTTPException(404, "流程不存在")

        if data.name is not None:
            w.name = data.name
        if data.display_name is not None:
            w.display_name = data.display_name
        if data.description is not None:
            w.description = data.description
        if data.trigger_pattern is not None:
            w.trigger_pattern = data.trigger_pattern
        if data.sub_intent is not None:
            w.sub_intent = data.sub_intent
        if data.plan_steps is not None:
            w.plan_steps = json.dumps(data.plan_steps, ensure_ascii=False)
        if data.is_active is not None:
            w.is_active = data.is_active

        db.commit()

        # 同步更新向量索引（如果修改了影响检索的字段）
        if any([data.name, data.display_name, data.description, data.trigger_pattern, data.sub_intent]):
            try:
                from ..workflows.workflow_vector_index import get_workflow_vector_index
                workflow_index = get_workflow_vector_index()
                workflow_data = {
                    "name": w.name,
                    "display_name": w.display_name,
                    "description": w.description,
                    "trigger_pattern": w.trigger_pattern,
                    "sub_intent": w.sub_intent
                }
                workflow_index.index_workflow(workflow_id, workflow_data)
                logger.info(f"已更新工作流 {w.display_name or w.name} 的向量索引")
            except Exception as index_error:
                logger.warning(f"更新向量索引失败（不影响更新操作）: {index_error}")

        return {"message": "更新成功"}
    finally:
        db.close()


@router.delete("/{workflow_id}")
def delete_workflow(workflow_id: str):
    """删除流程"""
    db = SessionLocal()
    try:
        w = db.query(SavedWorkflow).filter(SavedWorkflow.id == workflow_id).first()
        if not w:
            raise HTTPException(404, "流程不存在")

        db.delete(w)
        db.commit()

        # 同步删除向量索引
        try:
            from ..workflows.workflow_vector_index import get_workflow_vector_index
            workflow_index = get_workflow_vector_index()
            workflow_index.delete_workflow(workflow_id)
        except Exception as index_error:
            logger.warning(f"删除向量索引失败（不影响删除操作）: {index_error}")

        return {"message": "删除成功"}
    finally:
        db.close()


@router.patch("/{workflow_id}/toggle")
def toggle_workflow(workflow_id: str):
    """启用/禁用流程"""
    db = SessionLocal()
    try:
        w = db.query(SavedWorkflow).filter(SavedWorkflow.id == workflow_id).first()
        if not w:
            raise HTTPException(404, "流程不存在")

        w.is_active = not w.is_active
        db.commit()
        return {"is_active": w.is_active}
    finally:
        db.close()


# ============================================================================
# 向量索引相关接口
# ============================================================================

@router.post("/vector-index/rebuild")
def rebuild_vector_index():
    """
    重建所有工作流的向量索引

    用于初始化或修复向量索引，会清空现有索引并重新构建
    """
    try:
        from ..workflows.workflow_vector_index import get_workflow_vector_index
        workflow_index = get_workflow_vector_index()
        count = workflow_index.rebuild_index_from_db()
        return {
            "message": f"向量索引重建完成",
            "indexed_count": count
        }
    except Exception as e:
        logger.error(f"重建向量索引失败: {e}")
        raise HTTPException(500, f"重建向量索引失败: {str(e)}")


@router.get("/vector-index/stats")
def get_vector_index_stats():
    """
    获取向量索引统计信息

    返回已索引的工作流数量和各子意图的分布
    """
    try:
        from ..workflows.workflow_vector_index import get_workflow_vector_index
        workflow_index = get_workflow_vector_index()
        stats = workflow_index.get_stats()
        return stats
    except Exception as e:
        logger.error(f"获取向量索引统计失败: {e}")
        raise HTTPException(500, f"获取向量索引统计失败: {str(e)}")


@router.post("/vector-index/search")
def search_workflows_by_vector(
    query: str = Query(..., description="搜索查询文本"),
    sub_intent: Optional[str] = Query(None, description="业务子意图过滤"),
    top_k: int = Query(5, ge=1, le=20, description="返回结果数量")
):
    """
    向量检索工作流

    根据查询文本进行语义相似度检索，返回最匹配的工作流列表
    """
    try:
        from ..workflows.workflow_vector_index import get_workflow_vector_index
        workflow_index = get_workflow_vector_index()
        results = workflow_index.search(
            query=query,
            sub_intent=sub_intent,
            top_k=top_k
        )
        return {
            "query": query,
            "sub_intent": sub_intent,
            "count": len(results),
            "results": results
        }
    except Exception as e:
        logger.error(f"向量检索失败: {e}")
        raise HTTPException(500, f"向量检索失败: {str(e)}")


@router.post("/{workflow_id}/index")
def index_single_workflow(workflow_id: str):
    """
    索引单个工作流

    将指定工作流添加到向量索引中
    """
    db = SessionLocal()
    try:
        w = db.query(SavedWorkflow).filter(SavedWorkflow.id == workflow_id).first()
        if not w:
            raise HTTPException(404, "流程不存在")

        from ..workflows.workflow_vector_index import get_workflow_vector_index
        workflow_index = get_workflow_vector_index()

        workflow_data = {
            "name": w.name,
            "display_name": w.display_name,
            "description": w.description,
            "trigger_pattern": w.trigger_pattern,
            "sub_intent": w.sub_intent
        }

        success = workflow_index.index_workflow(workflow_id, workflow_data)
        if success:
            return {"message": f"工作流 {w.display_name or w.name} 索引成功"}
        else:
            raise HTTPException(500, "索引失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"索引工作流失败: {e}")
        raise HTTPException(500, f"索引工作流失败: {str(e)}")
    finally:
        db.close()
