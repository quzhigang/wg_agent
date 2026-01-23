"""
SQLAlchemy数据库模型定义
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    create_engine, Column, String, Integer, BigInteger, 
    Text, DateTime, Boolean, Enum, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, relationship
from ..config.settings import settings

# 创建Base类
Base = declarative_base()


class Conversation(Base):
    """会话表"""
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(100), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    summary = Column(Text, nullable=True)  # 长对话摘要
    
    # 关系
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    async_tasks = relationship("AsyncTask", back_populates="conversation", cascade="all, delete-orphan")
    tool_call_logs = relationship("ToolCallLog", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """消息历史表"""
    __tablename__ = "messages"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(Enum("user", "assistant", "system", name="message_role"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    msg_metadata = Column(Text, nullable=True)  # 附加元数据（JSON格式文本，兼容旧版MySQL）
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")


class AsyncTask(Base):
    """异步任务表"""
    __tablename__ = "async_tasks"
    
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True, index=True)
    task_type = Column(String(100), nullable=False)
    status = Column(
        Enum("pending", "running", "completed", "failed", "cancelled", name="task_status"),
        default="pending"
    )
    input_params = Column(Text, nullable=True)  # JSON格式文本
    result = Column(Text, nullable=True)  # JSON格式文本
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 关系
    conversation = relationship("Conversation", back_populates="async_tasks")


class SavedWorkflow(Base):
    """自动保存的动态流程表"""
    __tablename__ = "saved_workflows"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)  # 英文名，如 query_reservoir_realtime_water_level
    display_name = Column(String(100), nullable=True)  # 中文简称，如 "水库实时水位查询"
    description = Column(Text, nullable=True)
    trigger_pattern = Column(Text, nullable=False)  # 触发模式（用户消息特征）
    intent_category = Column(String(50), nullable=False)
    sub_intent = Column(String(50), nullable=True)
    entities_pattern = Column(Text, nullable=True)  # JSON
    plan_steps = Column(Text, nullable=False)  # JSON
    output_type = Column(String(50), default="text")
    source = Column(String(20), default="auto")  # auto/manual
    use_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class ToolCallLog(Base):
    """工具调用日志表"""
    __tablename__ = "tool_call_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    input_params = Column(Text, nullable=True)  # JSON格式文本
    output_result = Column(Text, nullable=True)  # JSON格式文本
    status = Column(Enum("success", "failed", name="tool_call_status"), nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    conversation = relationship("Conversation", back_populates="tool_call_logs")


class WebTemplate(Base):
    """Web模板元数据表（包含预定义模板和动态生成模板）"""
    __tablename__ = "web_templates"

    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(100), nullable=False, unique=True)  # 英文标识
    display_name = Column(String(100), nullable=False)  # 中文名称
    description = Column(Text, nullable=True)  # 详细描述
    template_path = Column(String(255), nullable=True)  # 模板路径(预定义模板用)
    supported_sub_intents = Column(Text, nullable=False)  # 支持的子意图(JSON数组)
    template_type = Column(String(50), default="full_page")  # 模板类型
    data_schema = Column(Text, nullable=True)  # 数据要求(JSON)
    trigger_pattern = Column(Text, nullable=True)  # 触发模式/关键词
    features = Column(Text, nullable=True)  # 特性标签(JSON数组)
    priority = Column(Integer, default=0)  # 优先级
    use_count = Column(Integer, default=0)  # 使用次数
    success_count = Column(Integer, default=0)  # 成功次数
    is_active = Column(Boolean, default=True)  # 是否激活
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # 动态模板字段
    is_dynamic = Column(Boolean, default=False)  # 是否为动态生成的模板
    html_content = Column(Text, nullable=True)  # 动态模板的HTML内容
    user_query = Column(Text, nullable=True)  # 触发生成的用户原始问题
    page_title = Column(String(255), nullable=True)  # 页面标题
    conversation_id = Column(String(36), nullable=True)  # 关联的会话ID
    # 数据注入配置（JSON格式，定义如何从Context提取数据并注入模板）
    replacement_config = Column(Text, nullable=True)  # 数据替换配置(JSON)


# 数据库引擎和会话工厂
def get_engine():
    """获取同步数据库引擎"""
    return create_engine(
        settings.mysql_url,
        echo=False,  # 关闭SQL语句日志输出
        pool_pre_ping=True,
        pool_recycle=3600
    )


def get_async_engine():
    """获取异步数据库引擎"""
    return create_async_engine(
        settings.async_mysql_url,
        echo=False,  # 关闭SQL语句日志输出
        pool_pre_ping=True,
        pool_recycle=3600
    )


# 同步会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

# 异步会话工厂
AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    bind=get_async_engine()
)


def get_db():
    """获取同步数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db():
    """获取异步数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def init_database():
    """初始化数据库，创建所有表"""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return engine


async def async_init_database():
    """异步初始化数据库"""
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    return engine
