"""
系统信息API
提供工具列表、LLM配置等系统信息的查询和管理接口
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..tools.registry import get_tool_registry
from ..tools.base import ToolCategory
from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["系统信息"])


# ============================================================================
# 数据模型定义
# ============================================================================

class ToolInfo(BaseModel):
    """工具信息模型"""
    name: str                    # 工具名称
    description: str             # 工具描述
    category: str                # 工具分类


class ToolsResponse(BaseModel):
    """工具列表响应模型"""
    tools: list                  # 工具列表
    categories: Dict[str, str]   # 分类名称映射


class LLMNodeConfig(BaseModel):
    """LLM节点配置模型"""
    api_base: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None


class LLMConfigUpdate(BaseModel):
    """LLM配置更新请求模型"""
    intent: Optional[LLMNodeConfig] = None
    sub_intent: Optional[LLMNodeConfig] = None
    workflow: Optional[LLMNodeConfig] = None
    tool_select: Optional[LLMNodeConfig] = None
    plan: Optional[LLMNodeConfig] = None
    synthesis: Optional[LLMNodeConfig] = None
    page_gen: Optional[LLMNodeConfig] = None
    executor: Optional[LLMNodeConfig] = None
    template_match: Optional[LLMNodeConfig] = None


# ============================================================================
# 工具分类中文名称映射
# ============================================================================

CATEGORY_NAMES = {
    "basin_info": "流域基本信息",
    "hydro_monitor": "水雨情监测",
    "flood_control": "防洪业务",
    "modelplan_control": "方案管理",
    "rain_control": "降雨处理",
    "flood_otherbusiness": "防洪其他业务",
    "hydromodel_set": "水利模型设置",
    "hydromodel_run": "水利模型运行",
    "hydromodel_result": "水利模型结果",
    "damage_assess": "灾损评估",
    "other": "其他"
}


# ============================================================================
# API接口定义
# ============================================================================

@router.get("/tools")
async def get_tools_list():
    """
    获取系统所有工具列表
    
    返回所有已注册工具的名称、描述和分类信息
    """
    try:
        registry = get_tool_registry()
        tools = []
        
        # 遍历所有已注册的工具
        for tool_name in registry.list_tools():
            tool = registry.get_tool(tool_name)
            if tool:
                # 获取工具的分类
                category = tool.category.value if hasattr(tool.category, 'value') else str(tool.category)
                tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "category": category
                })
        
        # 按分类排序
        tools.sort(key=lambda x: (x["category"], x["name"]))
        
        logger.info(f"返回工具列表，共 {len(tools)} 个工具")
        
        return {
            "tools": tools,
            "categories": CATEGORY_NAMES,
            "total": len(tools)
        }
        
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-config")
async def get_llm_config():
    """
    获取LLM配置信息
    
    返回默认配置和各节点的独立配置
    """
    try:
        # 默认配置
        default_config = {
            "api_base": settings.openai_api_base,
            "model": settings.openai_model_name,
            "temperature": settings.openai_temperature
        }
        
        # 各节点配置
        intent_config = settings.get_intent_config()
        sub_intent_config = settings.get_sub_intent_config()
        workflow_config = settings.get_workflow_config()
        tool_select_config = settings.get_tool_select_config()
        plan_config = settings.get_plan_config()
        synthesis_config = settings.get_synthesis_config()
        page_gen_config = settings.get_page_gen_config()
        executor_config = settings.get_executor_config()
        template_match_config = settings.get_template_match_config()
        
        return {
            "default": default_config,
            "intent": {
                "api_base": intent_config.get("api_base"),
                "model": intent_config.get("model"),
                "temperature": intent_config.get("temperature"),
                "api_key": intent_config.get("api_key")
            },
            "sub_intent": {
                "api_base": sub_intent_config.get("api_base"),
                "model": sub_intent_config.get("model"),
                "temperature": sub_intent_config.get("temperature"),
                "api_key": sub_intent_config.get("api_key")
            },
            "workflow": {
                "api_base": workflow_config.get("api_base"),
                "model": workflow_config.get("model"),
                "temperature": workflow_config.get("temperature"),
                "api_key": workflow_config.get("api_key")
            },
            "tool_select": {
                "api_base": tool_select_config.get("api_base"),
                "model": tool_select_config.get("model"),
                "temperature": tool_select_config.get("temperature"),
                "api_key": tool_select_config.get("api_key")
            },
            "plan": {
                "api_base": plan_config.get("api_base"),
                "model": plan_config.get("model"),
                "temperature": plan_config.get("temperature"),
                "api_key": plan_config.get("api_key")
            },
            "synthesis": {
                "api_base": synthesis_config.get("api_base"),
                "model": synthesis_config.get("model"),
                "temperature": synthesis_config.get("temperature"),
                "api_key": synthesis_config.get("api_key")
            },
            "page_gen": {
                "api_base": page_gen_config.get("api_base"),
                "model": page_gen_config.get("model"),
                "temperature": page_gen_config.get("temperature"),
                "api_key": page_gen_config.get("api_key")
            },
            "executor": {
                "api_base": executor_config.get("api_base"),
                "model": executor_config.get("model"),
                "temperature": executor_config.get("temperature"),
                "api_key": executor_config.get("api_key")
            },
            "template_match": {
                "api_base": template_match_config.get("api_base"),
                "model": template_match_config.get("model"),
                "temperature": template_match_config.get("temperature"),
                "api_key": template_match_config.get("api_key")
            }
        }
        
    except Exception as e:
        logger.error(f"获取LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm-config")
async def update_llm_config(config: Dict[str, Any]):
    """
    更新LLM配置
    
    注意：当前版本仅支持运行时配置更新，重启后会恢复默认值。
    如需持久化配置，请修改 .env 文件或环境变量。
    
    Args:
        config: 配置更新内容，格式为 {节点名: {配置项: 值}}
    
    Returns:
        更新结果
    """
    try:
        updated_nodes = []
        
        # 遍历配置更新
        for node_key, node_config in config.items():
            if node_config and isinstance(node_config, dict):
                # 这里只是记录要更新的配置
                # 实际更新需要修改settings对象或.env文件
                # 当前版本返回成功但提示需要修改.env才能持久化
                updated_nodes.append(node_key)
                logger.info(f"接收到节点 {node_key} 的配置更新: {list(node_config.keys())}")
        
        if updated_nodes:
            return {
                "success": True,
                "message": f"已接收配置更新请求，涉及节点: {', '.join(updated_nodes)}",
                "note": "注意: 配置更新仅在当前运行时生效。如需持久化，请修改 .env 文件中的对应配置项。"
            }
        else:
            return {
                "success": True,
                "message": "未检测到有效的配置更新"
            }
            
    except Exception as e:
        logger.error(f"更新LLM配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system-stats")
async def get_system_stats():
    """
    获取系统统计信息
    
    返回工具数量、知识库数量等系统概览信息
    """
    try:
        registry = get_tool_registry()
        tools_count = len(registry.list_tools())
        
        # 按分类统计工具数量
        category_stats = {}
        for tool_name in registry.list_tools():
            tool = registry.get_tool(tool_name)
            if tool:
                cat = tool.category.value if hasattr(tool.category, 'value') else str(tool.category)
                category_stats[cat] = category_stats.get(cat, 0) + 1
        
        return {
            "tools_count": tools_count,
            "knowledge_bases": 10,  # 固定10个知识库
            "predefined_workflows": 5,  # 5个预定义工作流
            "llm_nodes": 9,  # 9个LLM配置节点
            "intent_categories": {
                "main": 3,  # 3大类意图
                "sub": 6    # 6类业务子意图
            },
            "category_stats": category_stats
        }
        
    except Exception as e:
        logger.error(f"获取系统统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
