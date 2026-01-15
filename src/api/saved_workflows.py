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
