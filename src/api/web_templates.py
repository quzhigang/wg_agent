"""
Web模板管理API
"""

import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..models.database import WebTemplate, SessionLocal
from ..config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/web-templates", tags=["模板管理"])


class TemplateCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = None
    template_path: str
    supported_sub_intents: List[str]
    template_type: str = "full_page"
    data_schema: Optional[dict] = None
    trigger_pattern: Optional[str] = None
    features: Optional[List[str]] = None
    priority: int = 0


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    template_path: Optional[str] = None
    supported_sub_intents: Optional[List[str]] = None
    template_type: Optional[str] = None
    data_schema: Optional[dict] = None
    trigger_pattern: Optional[str] = None
    features: Optional[List[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None
    page_title: Optional[str] = None
    user_query: Optional[str] = None
    replacement_config: Optional[str] = None
    required_object_types: Optional[List[str]] = None


@router.get("")
def list_templates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sub_intent: Optional[str] = None
):
    """获取模板列表"""
    db = SessionLocal()
    try:
        query = db.query(WebTemplate)
        if sub_intent:
            query = query.filter(WebTemplate.supported_sub_intents.contains(sub_intent))

        total = query.count()
        items = query.order_by(WebTemplate.priority.desc(), WebTemplate.created_at.desc())\
            .offset((page - 1) * size).limit(size).all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": [{
                "id": t.id,
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "template_path": t.template_path,
                "supported_sub_intents": json.loads(t.supported_sub_intents) if t.supported_sub_intents else [],
                "template_type": t.template_type,
                "features": json.loads(t.features) if t.features else [],
                "priority": t.priority,
                "use_count": t.use_count,
                "success_count": t.success_count,
                "is_active": t.is_active,
                "is_dynamic": t.is_dynamic,
                "created_at": t.created_at.isoformat() if t.created_at else None
            } for t in items]
        }
    finally:
        db.close()


# ============================================================================
# 动态模板管理接口 (必须放在 /{template_id} 之前，否则会被识别为 ID)
# ============================================================================

@router.get("/dynamic")
def list_dynamic_templates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    sub_intent: Optional[str] = None
):
    """
    获取动态模板列表

    不再硬编码过滤 is_active 参数，以便在管理页面查看所有记录
    """
    db = SessionLocal()
    try:
        query = db.query(WebTemplate).filter(
            WebTemplate.is_dynamic == True
        )

        if sub_intent:
            query = query.filter(WebTemplate.supported_sub_intents.contains(sub_intent))

        total = query.count()
        items = query.order_by(WebTemplate.created_at.desc())\
            .offset((page - 1) * size).limit(size).all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "items": [{
                "id": t.id,
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "user_query": t.user_query,
                "page_title": t.page_title,
                "supported_sub_intents": json.loads(t.supported_sub_intents) if t.supported_sub_intents else [],
                "required_object_types": json.loads(t.required_object_types) if t.required_object_types else [],
                "replacement_config": t.replacement_config,
                "use_count": t.use_count,
                "success_count": t.success_count,
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None
            } for t in items]
        }
    finally:
        db.close()


@router.get("/{template_id}")
def get_template(template_id: str):
    """获取模板详情"""
    db = SessionLocal()
    try:
        t = db.query(WebTemplate).filter(WebTemplate.id == template_id).first()
        if not t:
            raise HTTPException(404, "模板不存在")

        return {
            "id": t.id,
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "template_path": t.template_path,
            "supported_sub_intents": json.loads(t.supported_sub_intents) if t.supported_sub_intents else [],
            "template_type": t.template_type,
            "data_schema": json.loads(t.data_schema) if t.data_schema else None,
            "trigger_pattern": t.trigger_pattern,
            "features": json.loads(t.features) if t.features else [],
            "priority": t.priority,
            "use_count": t.use_count,
            "success_count": t.success_count,
            "is_active": t.is_active,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None
        }
    finally:
        db.close()


@router.post("")
def create_template(data: TemplateCreate):
    """创建模板"""
    db = SessionLocal()
    try:
        # 检查名称是否已存在
        existing = db.query(WebTemplate).filter(WebTemplate.name == data.name).first()
        if existing:
            raise HTTPException(400, f"模板名称 {data.name} 已存在")

        template = WebTemplate(
            id=str(uuid.uuid4()),
            name=data.name,
            display_name=data.display_name,
            description=data.description,
            template_path=data.template_path,
            supported_sub_intents=json.dumps(data.supported_sub_intents, ensure_ascii=False),
            template_type=data.template_type,
            data_schema=json.dumps(data.data_schema, ensure_ascii=False) if data.data_schema else None,
            trigger_pattern=data.trigger_pattern,
            features=json.dumps(data.features, ensure_ascii=False) if data.features else None,
            priority=data.priority,
            is_active=True
        )

        db.add(template)
        db.commit()
        db.refresh(template)

        # 同步添加到向量索引
        try:
            from ..output.template_vector_index import get_template_vector_index
            template_index = get_template_vector_index()
            template_data = {
                "name": template.name,
                "display_name": template.display_name,
                "description": template.description,
                "trigger_pattern": template.trigger_pattern,
                "supported_sub_intents": data.supported_sub_intents,
                "template_path": template.template_path,
                "template_type": template.template_type,
                "priority": template.priority
            }
            template_index.index_template(template.id, template_data)
            logger.info(f"已添加模板 {template.display_name} 到向量索引")
        except Exception as index_error:
            logger.warning(f"添加向量索引失败（不影响创建操作）: {index_error}")

        return {"id": template.id, "message": "创建成功"}
    finally:
        db.close()


@router.put("/{template_id}")
def update_template(template_id: str, data: TemplateUpdate):
    """编辑模板"""
    db = SessionLocal()
    try:
        t = db.query(WebTemplate).filter(WebTemplate.id == template_id).first()
        if not t:
            raise HTTPException(404, "模板不存在")

        # 检查名称是否与其他模板冲突
        if data.name is not None and data.name != t.name:
            existing = db.query(WebTemplate).filter(
                WebTemplate.name == data.name,
                WebTemplate.id != template_id
            ).first()
            if existing:
                raise HTTPException(400, f"模板名称 {data.name} 已存在")

        if data.name is not None:
            t.name = data.name
        if data.display_name is not None:
            t.display_name = data.display_name
        if data.description is not None:
            t.description = data.description
        if data.template_path is not None:
            t.template_path = data.template_path
        if data.supported_sub_intents is not None:
            t.supported_sub_intents = json.dumps(data.supported_sub_intents, ensure_ascii=False)
        if data.template_type is not None:
            t.template_type = data.template_type
        if data.data_schema is not None:
            t.data_schema = json.dumps(data.data_schema, ensure_ascii=False)
        if data.trigger_pattern is not None:
            t.trigger_pattern = data.trigger_pattern
        if data.features is not None:
            t.features = json.dumps(data.features, ensure_ascii=False)
        if data.priority is not None:
            t.priority = data.priority
        if data.is_active is not None:
            t.is_active = data.is_active
        if hasattr(data, 'page_title') and data.page_title is not None:
            t.page_title = data.page_title
        if hasattr(data, 'user_query') and data.user_query is not None:
            t.user_query = data.user_query
        if hasattr(data, 'replacement_config') and data.replacement_config is not None:
            t.replacement_config = data.replacement_config
        if hasattr(data, 'required_object_types') and data.required_object_types is not None:
            t.required_object_types = json.dumps(data.required_object_types, ensure_ascii=False)

        db.commit()

        # 同步更新向量索引
        if any([data.name, data.display_name, data.description, data.trigger_pattern, data.supported_sub_intents]):
            try:
                from ..output.template_vector_index import get_template_vector_index
                template_index = get_template_vector_index()
                template_data = {
                    "name": t.name,
                    "display_name": t.display_name,
                    "description": t.description,
                    "trigger_pattern": t.trigger_pattern,
                    "supported_sub_intents": json.loads(t.supported_sub_intents) if t.supported_sub_intents else [],
                    "template_path": t.template_path,
                    "template_type": t.template_type,
                    "priority": t.priority
                }
                template_index.index_template(template_id, template_data)
                logger.info(f"已更新模板 {t.display_name} 的向量索引")
            except Exception as index_error:
                logger.warning(f"更新向量索引失败（不影响更新操作）: {index_error}")

        return {"message": "更新成功"}
    finally:
        db.close()


@router.delete("/{template_id}")
def delete_template(template_id: str):
    """删除模板"""
    db = SessionLocal()
    try:
        t = db.query(WebTemplate).filter(WebTemplate.id == template_id).first()
        if not t:
            raise HTTPException(404, "模板不存在")

        db.delete(t)
        db.commit()

        # 同步删除向量索引
        try:
            from ..output.template_vector_index import get_template_vector_index
            template_index = get_template_vector_index()
            template_index.delete_template(template_id)
        except Exception as index_error:
            logger.warning(f"删除向量索引失败（不影响删除操作）: {index_error}")

        return {"message": "删除成功"}
    finally:
        db.close()


@router.patch("/{template_id}/toggle")
def toggle_template(template_id: str):
    """启用/禁用模板"""
    db = SessionLocal()
    try:
        t = db.query(WebTemplate).filter(WebTemplate.id == template_id).first()
        if not t:
            raise HTTPException(404, "模板不存在")

        t.is_active = not t.is_active
        db.commit()
        return {"is_active": t.is_active}
    finally:
        db.close()


# ============================================================================
# 向量索引相关接口
# ============================================================================

@router.post("/vector-index/rebuild")
def rebuild_vector_index():
    """
    重建所有模板的向量索引

    用于初始化或修复向量索引，会清空现有索引并重新构建
    """
    try:
        from ..output.template_vector_index import get_template_vector_index
        template_index = get_template_vector_index()
        count = template_index.rebuild_index_from_db()
        return {
            "message": "向量索引重建完成",
            "indexed_count": count
        }
    except Exception as e:
        logger.error(f"重建向量索引失败: {e}")
        raise HTTPException(500, f"重建向量索引失败: {str(e)}")


@router.get("/vector-index/stats")
def get_vector_index_stats():
    """
    获取向量索引统计信息

    返回已索引的模板数量和各子意图的分布
    """
    try:
        from ..output.template_vector_index import get_template_vector_index
        template_index = get_template_vector_index()
        stats = template_index.get_stats()
        return stats
    except Exception as e:
        logger.error(f"获取向量索引统计失败: {e}")
        raise HTTPException(500, f"获取向量索引统计失败: {str(e)}")


@router.post("/vector-index/search")
def search_templates_by_vector(
    query: str = Query(..., description="搜索查询文本"),
    sub_intent: Optional[str] = Query(None, description="业务子意图过滤"),
    top_k: int = Query(5, ge=1, le=20, description="返回结果数量")
):
    """
    向量检索模板

    根据查询文本进行语义相似度检索，返回最匹配的模板列表
    """
    try:
        from ..output.template_vector_index import get_template_vector_index
        template_index = get_template_vector_index()
        results = template_index.search(
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


@router.post("/{template_id}/index")
def index_single_template(template_id: str):
    """
    索引单个模板

    将指定模板添加到向量索引中
    """
    db = SessionLocal()
    try:
        t = db.query(WebTemplate).filter(WebTemplate.id == template_id).first()
        if not t:
            raise HTTPException(404, "模板不存在")

        from ..output.template_vector_index import get_template_vector_index
        template_index = get_template_vector_index()

        template_data = {
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "trigger_pattern": t.trigger_pattern,
            "supported_sub_intents": json.loads(t.supported_sub_intents) if t.supported_sub_intents else [],
            "template_path": t.template_path,
            "template_type": t.template_type,
            "priority": t.priority
        }

        success = template_index.index_template(template_id, template_data)
        if success:
            return {"message": f"模板 {t.display_name} 索引成功"}
        else:
            raise HTTPException(500, "索引失败")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"索引模板失败: {e}")
        raise HTTPException(500, f"索引模板失败: {str(e)}")
    finally:
        db.close()


# ============================================================================
# 模板预览接口
# ============================================================================

@router.get("/{template_id}/preview")
async def preview_template(template_id: str):
    """
    预览模板

    使用模拟数据渲染模板，返回预览页面URL
    """
    db = SessionLocal()
    try:
        t = db.query(WebTemplate).filter(WebTemplate.id == template_id).first()
        if not t:
            raise HTTPException(404, "模板不存在")

        # 获取模拟数据
        from ..output.template_mock_data import get_mock_data
        mock_data = get_mock_data(t.name)

        # 生成预览页面
        from ..output.page_generator import get_page_generator
        page_generator = get_page_generator()

        template_info = {
            "name": t.name,
            "display_name": t.display_name,
            "template_path": t.template_path,
            "template_type": t.template_type
        }

        preview_url = await page_generator.generate_page_with_template(
            template_info=template_info,
            data=mock_data,
            title=f"{t.display_name} - 预览"
        )

        return {
            "preview_url": preview_url,
            "template_name": t.display_name
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成预览失败: {e}")
        raise HTTPException(500, f"生成预览失败: {str(e)}")
    finally:
        db.close()


# ============================================================================
# 动态模板管理接口
# ============================================================================

@router.get("/dynamic/{template_id}")
def get_dynamic_template(template_id: str):
    """获取动态模板详情"""
    db = SessionLocal()
    try:
        t = db.query(WebTemplate).filter(
            WebTemplate.id == template_id,
            WebTemplate.is_dynamic == True
        ).first()

        if not t:
            raise HTTPException(404, "动态模板不存在")

        return {
            "id": t.id,
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "user_query": t.user_query,
            "page_title": t.page_title,
            "html_content": t.html_content,
            "supported_sub_intents": json.loads(t.supported_sub_intents) if t.supported_sub_intents else [],
            "use_count": t.use_count,
            "success_count": t.success_count,
            "conversation_id": t.conversation_id,
            "created_at": t.created_at.isoformat() if t.created_at else None
        }
    finally:
        db.close()


@router.get("/dynamic/{template_id}/preview")
def preview_dynamic_template(template_id: str):
    """
    预览动态模板

    注入 <base> 标签以解决 HTML 中相对路径（css/js）的加载问题
    """
    from fastapi.responses import HTMLResponse
    import re

    db = SessionLocal()
    try:
        t = db.query(WebTemplate).filter(
            WebTemplate.id == template_id,
            WebTemplate.is_dynamic == True
        ).first()

        if not t:
            raise HTTPException(404, "动态模板不存在")

        if not t.html_content:
            raise HTTPException(404, "模板内容为空")

        html = t.html_content
        # 注入 <base> 标签，使相对路径指向静态文件所在目录
        # 动态模板的 name 即为 generated_pages 下的目录名
        base_url = f"/static/pages/{t.name}/"
        base_tag = f'<base href="{base_url}">'
        
        if "<head>" in html:
            html = html.replace("<head>", f"<head>\n    {base_tag}")
        else:
            html = f"{base_tag}\n{html}"

        return HTMLResponse(content=html, media_type="text/html")
    finally:
        db.close()


@router.delete("/dynamic/{template_id}")
def delete_dynamic_template(template_id: str):
    """
    删除动态模板
    
    调用 DynamicTemplateService 完成三位一体的删除：
    1. 数据库记录
    2. 向量索引
    3. 磁盘静态文件
    """
    try:
        from ..output.dynamic_template_service import get_dynamic_template_service
        service = get_dynamic_template_service()
        
        success = service.delete_dynamic_template(template_id)
        
        if success:
            return {"success": True, "message": "删除成功"}
        else:
            raise HTTPException(404, "动态模板不存在或删除过程出错")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除动态模板 API 失败: {e}")
        return {"success": False, "message": str(e)}
