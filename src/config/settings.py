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
    # LLM Configuration - 默认配置
    # ===========================================
    openai_api_key: str = "sk-fYNBIb1rjJveHJpsVxhb27NKyMOIa9SwRrr8U6lxFGCztIC2"
    openai_api_base: str = "https://max.openai365.top/v1"
    openai_model_name: str = "gemini-3-flash"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 4096

    # 思考模式配置（用于Qwen3等支持思考模式的模型）
    # 注意：非流式调用时必须设置为false，否则Qwen3会报错
    llm_enable_thinking: bool = False

    # ===========================================
    # LLM Configuration - 各节点独立配置
    # ===========================================
    # 意图识别节点
    intent_api_key: Optional[str] = None
    intent_api_base: Optional[str] = None
    intent_model_name: Optional[str] = None
    intent_temperature: float = 0.3

    # 业务子意图分类节点
    sub_intent_api_key: Optional[str] = None
    sub_intent_api_base: Optional[str] = None
    sub_intent_model_name: Optional[str] = None
    sub_intent_temperature: float = 0.3

    # 工作流匹配节点
    workflow_api_key: Optional[str] = None
    workflow_api_base: Optional[str] = None
    workflow_model_name: Optional[str] = None
    workflow_temperature: float = 0.3

    # 计划生成节点
    plan_api_key: Optional[str] = None
    plan_api_base: Optional[str] = None
    plan_model_name: Optional[str] = None
    plan_temperature: float = 0.3

    # 结果合成节点
    synthesis_api_key: Optional[str] = None
    synthesis_api_base: Optional[str] = None
    synthesis_model_name: Optional[str] = None
    synthesis_temperature: float = 0.7

    # 页面生成节点
    page_gen_api_key: Optional[str] = None
    page_gen_api_base: Optional[str] = None
    page_gen_model_name: Optional[str] = None
    page_gen_temperature: float = 0.5

    # 执行器节点
    executor_api_key: Optional[str] = None
    executor_api_base: Optional[str] = None
    executor_model_name: Optional[str] = None
    executor_temperature: float = 0.7

    # 工具筛选节点
    tool_select_api_key: Optional[str] = None
    tool_select_api_base: Optional[str] = None
    tool_select_model_name: Optional[str] = None
    tool_select_temperature: float = 0.3

    # Web模板匹配节点
    template_match_api_key: Optional[str] = None
    template_match_api_base: Optional[str] = None
    template_match_model_name: Optional[str] = None
    template_match_temperature: float = 0.3

    # 获取各节点配置的辅助方法（未配置时使用默认值）
    def get_intent_config(self) -> dict:
        return {
            "api_key": self.intent_api_key or self.openai_api_key,
            "api_base": self.intent_api_base or self.openai_api_base,
            "model": self.intent_model_name or self.openai_model_name,
            "temperature": self.intent_temperature
        }

    def get_sub_intent_config(self) -> dict:
        """获取业务子意图分类节点配置（未配置时回退到意图识别配置）"""
        return {
            "api_key": self.sub_intent_api_key or self.intent_api_key or self.openai_api_key,
            "api_base": self.sub_intent_api_base or self.intent_api_base or self.openai_api_base,
            "model": self.sub_intent_model_name or self.intent_model_name or self.openai_model_name,
            "temperature": self.sub_intent_temperature
        }

    def get_workflow_config(self) -> dict:
        return {
            "api_key": self.workflow_api_key or self.openai_api_key,
            "api_base": self.workflow_api_base or self.openai_api_base,
            "model": self.workflow_model_name or self.openai_model_name,
            "temperature": self.workflow_temperature
        }

    def get_plan_config(self) -> dict:
        return {
            "api_key": self.plan_api_key or self.openai_api_key,
            "api_base": self.plan_api_base or self.openai_api_base,
            "model": self.plan_model_name or self.openai_model_name,
            "temperature": self.plan_temperature
        }

    def get_synthesis_config(self) -> dict:
        return {
            "api_key": self.synthesis_api_key or self.openai_api_key,
            "api_base": self.synthesis_api_base or self.openai_api_base,
            "model": self.synthesis_model_name or self.openai_model_name,
            "temperature": self.synthesis_temperature
        }

    def get_page_gen_config(self) -> dict:
        return {
            "api_key": self.page_gen_api_key or self.openai_api_key,
            "api_base": self.page_gen_api_base or self.openai_api_base,
            "model": self.page_gen_model_name or self.openai_model_name,
            "temperature": self.page_gen_temperature
        }

    def get_executor_config(self) -> dict:
        return {
            "api_key": self.executor_api_key or self.openai_api_key,
            "api_base": self.executor_api_base or self.openai_api_base,
            "model": self.executor_model_name or self.openai_model_name,
            "temperature": self.executor_temperature
        }

    def get_tool_select_config(self) -> dict:
        return {
            "api_key": self.tool_select_api_key or self.openai_api_key,
            "api_base": self.tool_select_api_base or self.openai_api_base,
            "model": self.tool_select_model_name or self.openai_model_name,
            "temperature": self.tool_select_temperature
        }

    def get_template_match_config(self) -> dict:
        """获取Web模板匹配节点配置（未配置时回退到工作流匹配配置）"""
        return {
            "api_key": self.template_match_api_key or self.workflow_api_key or self.openai_api_key,
            "api_base": self.template_match_api_base or self.workflow_api_base or self.openai_api_base,
            "model": self.template_match_model_name or self.workflow_model_name or self.openai_model_name,
            "temperature": self.template_match_temperature
        }

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
    # ChromaDB Configuration (使用PageIndex的向量库)
    # ===========================================
    chroma_persist_directory: str = "./PageIndex/chroma_db"
    chroma_collection_name: str = "pageindex_nodes"
    
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
    wg_flood_server_url: str = "http://10.20.2.153/api/basin/modelPlatf"
    wg_flood_server_url1: str = "http://10.20.2.153/api/basin"
    
    # ===========================================
    # Auth Configuration
    # ===========================================
    basin_auth_account: str = "admin"
    basin_auth_password: str = "Pwd@6915"
    basin_token_expiry_minutes: int = 30  # Token默认过期时间（分钟）
    
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
    # Knowledge Base (已废弃，使用PageIndex)
    # ===========================================
    # knowledge_dir: str = "./knowledge"  # 已废弃
    
    # ===========================================
    # 网络搜索配置 (博查Web Search API)
    # ===========================================
    web_search_enabled: bool = False
    web_search_api_key: str = "sk-eb6f4246548a43fdb4410b7b5e3507de"
    web_search_api_url: str = "https://api.bochaai.com/v1/web-search"


@lru_cache()
def get_settings() -> Settings:
    """获取缓存的配置实例"""
    return Settings()


# 全局配置实例
settings = get_settings()
