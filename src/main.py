"""
卫共流域数字孪生智能体 - FastAPI主入口
"""

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .config.settings import settings
from .config.logging_config import setup_logging, get_logger
from .models.database import init_database
from .api import chat_router, health_router, pages_router, knowledge_router, saved_workflows_router, system_info_router
from .tools.registry import init_default_tools
from .workflows.registry import init_default_workflows


# 初始化日志
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 50)
    logger.info("卫共流域数字孪生智能体 启动中...")
    logger.info("=" * 50)
    
    # 初始化数据库
    try:
        init_database()
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise
    
    # 确保必要目录存在
    Path(settings.generated_pages_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
    # knowledge_dir 已废弃，使用 PageIndex
    logger.info("目录结构检查完成")
    
    # 初始化工具注册表
    try:
        init_default_tools()
        logger.info("工具注册表初始化完成")
    except Exception as e:
        logger.warning(f"工具初始化警告: {e}")
    
    # 初始化工作流注册表
    try:
        init_default_workflows()
        logger.info("工作流注册表初始化完成")
    except Exception as e:
        logger.warning(f"工作流初始化警告: {e}")
    
    # 初始化知识库
    try:
        from .rag.knowledge_base import get_knowledge_base
        kb = get_knowledge_base()
        stats = kb.get_stats()
        logger.info(f"知识库初始化完成，文档数: {stats['total_documents']}")
    except Exception as e:
        logger.warning(f"知识库初始化警告: {e}")
    
    logger.info(f"API服务地址: http://{settings.api_host}:{settings.api_port}")
    logger.info("智能体启动完成，等待请求...")
    
    yield
    
    # 关闭时执行
    logger.info("智能体正在关闭...")
    logger.info("智能体已关闭")


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    
    app = FastAPI(
        title="卫共流域数字孪生智能体",
        description="""
        基于LangGraph的Plan-and-Execute智能体系统
        
        ## 功能特性
        - 一般对话与流域特有知识问答
        - 流域介绍、工程信息查询
        - 实时水雨情查询
        - 洪水预报预演及应急预案生成
        
        ## 技术架构
        - Planner规划调度器
        - Executor任务执行器
        - Controller结果合成器
        - RAG知识库
        - 记忆管理
        - 异步任务处理
        
        ## API分组
        - /health - 健康检查
        - /chat - 对话接口
        - /pages - 生成页面
        - /knowledge - 知识库管理
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制来源
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册路由
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(pages_router)
    app.include_router(knowledge_router)
    app.include_router(saved_workflows_router)
    app.include_router(system_info_router)
    
    # 静态文件挂载 (注意顺序：更具体的路径应先挂载)
    
    # 1. 挂载页面模板组件 (web/web_templates/res_module -> /ui/res_module)
    # 这样 index.html 里的 res_module/ 相对路径就能正确匹配
    web_templates_path = Path(settings.web_templates_dir)
    if (web_templates_path / "res_module").exists():
        app.mount("/ui/res_module", StaticFiles(directory=str(web_templates_path / "res_module")), name="ui_res_module")

    # 2. 挂载主界面 (web/main -> /ui)
    web_main_path = Path(settings.web_main_dir)
    if web_main_path.exists():
        app.mount("/ui", StaticFiles(directory=str(web_main_path), html=True), name="ui_main")

    # 3. 挂载生成的页面 (web/generated_pages -> /static/pages)
    generated_pages_path = Path(settings.generated_pages_dir)
    generated_pages_path.mkdir(parents=True, exist_ok=True)
    app.mount(
        "/static/pages",
        StaticFiles(directory=str(generated_pages_path)),
        name="generated_pages"
    )
    
    @app.get("/", tags=["根路径"])
    async def root():
        """根路径，返回服务信息"""
        return {
            "service": "卫共流域数字孪生智能体",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "chat": "/chat",
                "stream": "/chat/stream",
                "pages": "/pages",
                "knowledge": "/knowledge"
            }
        }
    
    return app


# 创建应用实例
app = create_app()


def main():
    """主函数，启动服务"""
    # log_config=None 告诉 uvicorn 不要使用自己的日志配置，从而使用我们在 setup_logging() 中配置好的 loguru
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_level=settings.log_level.lower(),
        log_config=None,
        access_log=True
    )


if __name__ == "__main__":
    main()
