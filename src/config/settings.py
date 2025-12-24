"""
全局配置设置
使用Pydantic Settings进行环境变量管理
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """应用程序配置"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # ===========================================
    # LLM Configuration
    # ===========================================
    openai_api_key: str = "sk-ZMhmsdJOewyxBlSBr1trAPTtG59VcVhD6nTKGJNdSSHtxifm"
    openai_api_base: str = "https://max.openai365.top/v1"
    openai_model_name: str = "gemini-3-flash"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4096
    
    # Embedding Model
    embedding_model_name: str = "bge-m3:latest"
    embedding_model_api_url: str = "http://10.20.2.135:11434"
    embedding_model_type: str = "ollama"
    
    # ===========================================
    # MySQL Database Configuration
    # ===========================================
    mysql_host: str = "172.16.16.253"
    mysql_port: int = 3306
    mysql_user: str = "quzhigang"
    mysql_password: str = "633587"
    mysql_database: str = "wg_agent"
    
    @property
    def mysql_url(self) -> str:
        """MySQL连接URL"""
        return f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
    
    @property
    def async_mysql_url(self) -> str:
        """异步MySQL连接URL"""
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
    
    # ===========================================
    # ChromaDB Configuration
    # ===========================================
    chroma_persist_directory: str = "./chroma_db"
    chroma_collection_name: str = "wg_knowledge"
    
    # ===========================================
    # API Server Configuration
    # ===========================================
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_debug: bool = True
    
    # ===========================================
    # External API Base URLs (卫共流域业务系统)
    # ===========================================
    # .NET模型服务接口地址
    wg_model_server_url: str = "http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx"
    # 基础数据服务接口地址
    wg_data_server_url: str = "http://10.20.2.153"
    # 防洪业务服务接口地址（Java Spring Boot）
    wg_flood_server_url: str = "http://10.20.2.153:8089/modelPlatf"
    
    # ===========================================
    # Auth Configuration
    # ===========================================
    basin_auth_account: str = "admin"
    basin_auth_password: str = "Pwd@6915"
    
    # ===========================================
    # Session Configuration
    # ===========================================
    session_timeout_minutes: int = 30
    max_context_length: int = 8000
    summary_threshold_messages: int = 20
    
    # ===========================================
    # Async Task Configuration
    # ===========================================
    task_polling_interval_seconds: int = 5
    task_max_retries: int = 3
    task_retry_delay_seconds: int = 10
    
    # ===========================================
    # Web Page Generation
    # ===========================================
    generated_pages_dir: str = "./web/generated_pages"
    web_templates_dir: str = "./web/web_templates"
    web_main_dir: str = "./web/main"
    
    # ===========================================
    # Logging
    # ===========================================
    log_level: str = "INFO"
    log_file: str = "./logs/wg_agent.log"
    
    # ===========================================
    # Knowledge Base
    # ===========================================
    knowledge_dir: str = "./knowledge"
    
    # ===========================================
    # MCP Server Configuration (MCP服务器配置)
    # ===========================================
    # 智谱Web Search MCP配置
    mcp_zhipu_websearch_enabled: bool = False
    mcp_zhipu_websearch_type: str = "sse"
    mcp_zhipu_websearch_name: str = "智谱搜索MCP"
    mcp_zhipu_websearch_description: str = "智谱Web Search MCP，整合了5家头部搜索引擎"
    mcp_zhipu_websearch_url: str = ""
    mcp_zhipu_websearch_api_key: str = ""


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()


# 全局配置实例
settings = get_settings()
