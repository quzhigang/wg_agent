"""
聊天对话接口
"""

from typing import Optional, List
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import json
import asyncio

from ..models.database import get_db, Conversation, Message
from ..models.schemas import (
    ChatRequest, ChatResponse, APIResponse,
    ConversationCreate, ConversationResponse,
    MessageResponse, OutputType
)
from ..config.logging_config import get_logger
from ..agents.graph import run_agent, run_agent_stream

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["对话"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    对话接口
    
    处理用户对话请求，返回智能体响应
    """
    try:
        logger.info(f"收到对话请求: {request.message[:50]}...")
        
        # 获取或创建会话
        conversation_id = request.conversation_id
        if not conversation_id:
            conversation_id = str(uuid4())
            conversation = Conversation(
                id=conversation_id,
                user_id=request.user_id,
                title=request.message[:30] + "..." if len(request.message) > 30 else request.message
            )
            db.add(conversation)
            db.commit()
        
        # 保存用户消息
        user_message = Message(
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
        db.add(user_message)
        db.commit()
        db.refresh(user_message)
        
        # 获取历史消息
        history_messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).limit(10).all()
        
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in reversed(history_messages[1:])  # 排除刚添加的消息
        ]
        
        # 调用智能体
        result = await run_agent(
            conversation_id=conversation_id,
            user_message=request.message,
            user_id=request.user_id,
            chat_history=chat_history
        )
        
        # 保存助手响应
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.get("response", ""),
            msg_metadata=json.dumps({
                "output_type": result.get("output_type", "text"),
                "page_url": result.get("page_url"),
                "intent": result.get("intent")
            }, ensure_ascii=False)
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        
        # 构建响应
        output_type = OutputType.TEXT
        if result.get("output_type") == "web_page":
            output_type = OutputType.WEB_PAGE
        
        response = ChatResponse(
            conversation_id=conversation_id,
            message_id=assistant_message.id,
            content=result.get("response", ""),
            output_type=output_type,
            page_url=result.get("page_url"),
            execution_steps=result.get("execution_steps", [])
        )
        
        return response
        
    except Exception as e:
        logger.error(f"对话处理失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    """
    流式对话接口
    
    支持实时返回执行步骤和响应内容
    
    事件类型:
    - start: 开始处理
    - intent: 意图识别结果
    - rag: RAG检索结果
    - plan: 执行计划
    - step_start: 步骤开始执行
    - step_end: 步骤执行完成
    - content: 最终回答内容
    - done: 处理完成
    - error: 错误信息
    """
    async def generate():
        try:
            # 获取或创建会话
            conversation_id = request.conversation_id or str(uuid4())
            
            # 检查会话是否存在，不存在则创建
            existing_conv = db.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            
            if not existing_conv:
                new_conv = Conversation(
                    id=conversation_id,
                    user_id=request.user_id,
                    title=request.message[:30] + "..." if len(request.message) > 30 else request.message
                )
                db.add(new_conv)
                db.commit()
            
            # 发送开始信号
            start_data = json.dumps({"type": "start", "conversation_id": conversation_id}, ensure_ascii=False)
            yield f"data: {start_data}\n\n"
            
            # 保存用户消息 (如果是新消息)
            user_message = Message(
                conversation_id=conversation_id,
                role="user",
                content=request.message
            )
            db.add(user_message)
            db.commit()

            # 获取历史消息
            history_messages = db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.desc()).limit(10).all()
            
            chat_history = [
                {"role": msg.role, "content": msg.content}
                for msg in reversed(history_messages[1:])
            ]
            
            full_response = ""
            output_type = "text"
            page_url = None

            # 调用流式智能体
            async for event in run_agent_stream(
                conversation_id=conversation_id,
                user_message=request.message,
                user_id=request.user_id,
                chat_history=chat_history
            ):
                node = event.get("node", "")
                event_type = event.get("type", "step")
                
                if node == "error":
                    err_data = json.dumps({"type": "error", "data": event.get("error")}, ensure_ascii=False)
                    yield f"data: {err_data}\n\n"
                elif node == "final":
                    full_response = event.get("response", "")
                    output_type = event.get("output_type", "text")
                    page_url = event.get("page_url")
                    
                    final_data = json.dumps({
                        "type": "content", 
                        "data": full_response, 
                        "output_type": output_type, 
                        "page_url": page_url
                    }, ensure_ascii=False)
                    yield f"data: {final_data}\n\n"
                else:
                    # 根据事件类型发送不同格式的数据
                    progress = event.get("progress", {})
                    state = event.get("state", {})
                    
                    # 构建事件数据
                    event_data = {
                        "type": event_type,
                        "node": node,
                        "progress": progress,
                        "state": state
                    }
                    
                    # 添加额外的事件特定数据
                    if event_type == "intent":
                        event_data["intent"] = event.get("intent", "")
                        event_data["confidence"] = event.get("confidence", 0)
                    elif event_type == "rag":
                        event_data["doc_count"] = event.get("doc_count", 0)
                        event_data["source"] = event.get("source", "rag")
                    elif event_type == "plan":
                        event_data["steps"] = event.get("steps", [])
                    elif event_type == "step_start":
                        event_data["step_id"] = event.get("step_id", 0)
                        event_data["description"] = event.get("description", "")
                    elif event_type == "step_end":
                        event_data["step_id"] = event.get("step_id", 0)
                        event_data["success"] = event.get("success", True)
                        event_data["result_summary"] = event.get("result_summary", "")
                    
                    step_data = json.dumps(event_data, ensure_ascii=False)
                    yield f"data: {step_data}\n\n"
            
            # 保存助手响应到数据库
            if full_response:
                assistant_message = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                    msg_metadata=json.dumps({
                        "output_type": output_type,
                        "page_url": page_url
                    }, ensure_ascii=False)
                )
                db.add(assistant_message)
                db.commit()

            # 发送完成信号
            done_data = json.dumps({"type": "done", "data": None}, ensure_ascii=False)
            yield f"data: {done_data}\n\n"
            
        except Exception as e:
            logger.error(f"流式对话处理失败: {str(e)}")
            err_msg = json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False)
            yield f"data: {err_msg}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/conversations", response_model=APIResponse)
async def list_conversations(
    user_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取会话列表（历史对话）"""
    try:
        query = db.query(Conversation)
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        
        conversations = query.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()
        
        conv_list = []
        for conv in conversations:
            conv_list.append({
                "id": conv.id,
                "user_id": conv.user_id,
                "title": conv.title,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "is_active": conv.is_active,
                "summary": conv.summary
            })

        return APIResponse(
            success=True,
            message="获取成功",
            data=conv_list
        )
    except Exception as e:
        logger.error(f"获取会话列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversations", response_model=APIResponse)
async def create_conversation(
    request: ConversationCreate,
    db: Session = Depends(get_db)
):
    """创建新会话"""
    try:
        conversation = Conversation(
            id=str(uuid4()),
            user_id=request.user_id,
            title=request.title or "新对话"
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return APIResponse(
            success=True,
            message="会话创建成功",
            data={
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
                "is_active": conversation.is_active,
                "summary": conversation.summary
            }
        )
        
    except Exception as e:
        logger.error(f"创建会话失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}", response_model=APIResponse)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """获取会话详情"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return APIResponse(
            success=True,
            message="获取成功",
            data={
                "id": conversation.id,
                "user_id": conversation.user_id,
                "title": conversation.title,
                "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
                "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
                "is_active": conversation.is_active,
                "summary": conversation.summary
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/conversations/{conversation_id}", response_model=APIResponse)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """删除会话及其所有消息"""
    try:
        # 检查会话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 删除会话相关的所有消息
        db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).delete()
        
        # 删除会话
        db.delete(conversation)
        db.commit()
        
        logger.info(f"会话已删除: {conversation_id}")
        
        return APIResponse(
            success=True,
            message="会话删除成功",
            data={"id": conversation_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除会话失败: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/{conversation_id}/messages", response_model=APIResponse)
async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """获取会话消息历史"""
    try:
        # 检查会话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取消息
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).offset(offset).limit(limit).all()
        
        return APIResponse(
            success=True,
            message="获取成功",
            data=[
                {
                    "id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "metadata": msg.msg_metadata
                }
                for msg in messages
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
