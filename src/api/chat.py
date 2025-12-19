"""
聊天对话接口
"""

from typing import Optional
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
            msg_metadata={
                "output_type": result.get("output_type", "text"),
                "page_url": result.get("page_url"),
                "intent": result.get("intent")
            }
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
    """
    async def generate():
        try:
            # 获取或创建会话
            conversation_id = request.conversation_id or str(uuid4())
            
            # 发送开始信号
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"
            
            # 获取历史消息
            history_messages = db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.created_at.desc()).limit(10).all()
            
            chat_history = [
                {"role": msg.role, "content": msg.content}
                for msg in reversed(history_messages)
            ]
            
            # 调用流式智能体
            async for event in run_agent_stream(
                conversation_id=conversation_id,
                user_message=request.message,
                user_id=request.user_id,
                chat_history=chat_history
            ):
                node = event.get("node", "")
                
                if node == "error":
                    yield f"data: {json.dumps({'type': 'error', 'data': event.get('error')}, ensure_ascii=False)}\n\n"
                elif node == "final":
                    yield f"data: {json.dumps({'type': 'content', 'data': event.get('response'), 'output_type': event.get('output_type'), 'page_url': event.get('page_url')}, ensure_ascii=False)}\n\n"
                else:
                    progress = event.get("progress", {})
                    state = event.get("state", {})
                    yield f"data: {json.dumps({'type': 'step', 'node': node, 'progress': progress, 'state': state}, ensure_ascii=False)}\n\n"
            
            # 发送完成信号
            yield f"data: {json.dumps({'type': 'done', 'data': None}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"流式对话处理失败: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'data': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/conversations", response_model=APIResponse)
async def create_conversation(
    request: ConversationCreate,
    db: Session = Depends(get_db)
):
    """创建新会话"""
    try:
        from uuid import uuid4
        from ..models.database import Conversation
        
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
            data=ConversationResponse(
                id=conversation.id,
                user_id=conversation.user_id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                is_active=conversation.is_active,
                summary=conversation.summary
            ).model_dump()
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
        from ..models.database import Conversation
        
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return APIResponse(
            success=True,
            message="获取成功",
            data=ConversationResponse(
                id=conversation.id,
                user_id=conversation.user_id,
                title=conversation.title,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
                is_active=conversation.is_active,
                summary=conversation.summary
            ).model_dump()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话失败: {str(e)}")
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
        from ..models.database import Message, Conversation
        
        # 检查会话是否存在
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        # 获取消息
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc()).offset(offset).limit(limit).all()
        
        return APIResponse(
            success=True,
            message="获取成功",
            data=[
                MessageResponse(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    role=msg.role,
                    content=msg.content,
                    created_at=msg.created_at,
                    metadata=msg.msg_metadata
                ).model_dump()
                for msg in reversed(messages)
            ]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取消息历史失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
