"""
防洪业务其他接口工具
提供子流域洪水结果、淹没分析、防汛预案、水雨情态势研判、闸站工情、MIKE模型辅助等功能
基于防洪业务接口-子流域洪水、淹没分析、洪水态势分析及其他辅助业务文档实现
接口基础地址：http://10.20.2.153/api/basin
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)

# 从配置获取防洪业务API基础地址
FLOOD_OTHER_BASE_URL = settings.wg_flood_server_url1


# =============================================================================
# 一、获取子流域洪水结果接口（4个）
# =============================================================================

class ModelResultOutflowDeleteTool(BaseTool):
    """删除方案的子流域洪水结果工具"""
    
    @property
    def name(self) -> str:
        return "model_result_outflow_delete"
    
    @property
    def description(self) -> str:
        return "删除产流结果，根据方案编码和可选的流域编码删除子流域洪水计算结果"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True),
            ToolParameter(name="bsn_code", type="string", description="流域编码（可选）", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行删除产流结果"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/modelResultOutflow/delete"
            payload = {"planCode": kwargs.get("plan_code")}
            if kwargs.get("bsn_code"):
                payload["bsnCode"] = kwargs.get("bsn_code")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, data=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "产流结果删除成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "删除失败"))
        except Exception as e:
            logger.error(f"删除产流结果失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelResultOutflowGetBasinListTool(BaseTool):
    """获取子流域基础信息清单工具"""
    
    @property
    def name(self) -> str:
        return "model_result_outflow_get_basin_list"
    
    @property
    def description(self) -> str:
        return "获取指定方案的子流域基础信息清单，返回子流域编码和名称列表"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取子流域基础信息清单"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/modelResultOutflow/getBasinList"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取子流域基础信息清单失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelResultOutflowDetailTool(BaseTool):
    """获取子流域产流洪水过程结果及统计结果工具"""
    
    @property
    def name(self) -> str:
        return "model_result_outflow_detail"
    
    @property
    def description(self) -> str:
        return "获取指定方案、指定子流域的降雨及洪水过程结果及统计结果，包括降雨过程、洪水过程、峰值时间、累计降雨、洪峰流量等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True),
            ToolParameter(name="bsn_code", type="string", description="流域编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取子流域产流洪水过程结果"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/modelResultOutflow/detail"
            params = {
                "planCode": kwargs.get("plan_code"),
                "bsnCode": kwargs.get("bsn_code")
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取子流域产流洪水过程结果失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelResultOutflowSourceTool(BaseTool):
    """获取方案洪水来源工具"""
    
    @property
    def name(self) -> str:
        return "model_result_outflow_source"
    
    @property
    def description(self) -> str:
        return "获取洪水来源类型：0=降雨计算、1=直接导入、2=无洪水"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取方案洪水来源"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/modelResultOutflow/source"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                # 解析洪水来源类型
                source_type = data.get("data")
                source_desc = {0: "降雨计算", 1: "直接导入", 2: "无洪水"}.get(source_type, "未知")
                return ToolResult(success=True, data={"source": source_type, "description": source_desc})
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取方案洪水来源失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 二、基于DEM的洪水淹没分析接口（7个）
# =============================================================================

class LossPlanListTool(BaseTool):
    """分页查询淹没分析方案列表工具"""
    
    @property
    def name(self) -> str:
        return "loss_plan_list"
    
    @property
    def description(self) -> str:
        return "分页查询淹没分析方案列表，支持按编码、名称、状态、蓄滞洪区编码、类型等条件过滤"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="code", type="string", description="方案编码（可选）", required=False),
            ToolParameter(name="name", type="string", description="方案名称（可选）", required=False),
            ToolParameter(name="status", type="string", description="计算状态：待计算/计算中/计算成功/计算失败（可选）", required=False),
            ToolParameter(name="fsda_code", type="string", description="蓄滞洪区编码（可选）", required=False),
            ToolParameter(name="model_type", type="string", description="类型：0=蓄滞洪区, 1=滩地（可选）", required=False),
            ToolParameter(name="page", type="integer", description="页码，默认1", required=False),
            ToolParameter(name="limit", type="integer", description="每页条数，默认10", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行分页查询淹没分析方案列表"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/loss/list"
            params = {}
            if kwargs.get("code"):
                params["code"] = kwargs.get("code")
            if kwargs.get("name"):
                params["name"] = kwargs.get("name")
            if kwargs.get("status"):
                params["status"] = kwargs.get("status")
            if kwargs.get("fsda_code"):
                params["fsdaCode"] = kwargs.get("fsda_code")
            if kwargs.get("model_type"):
                params["modelType"] = kwargs.get("model_type")
            params["page"] = kwargs.get("page", 1)
            params["limit"] = kwargs.get("limit", 10)
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            # 该接口返回格式略有不同
            return ToolResult(success=True, data={
                "total": data.get("count", 0),
                "list": data.get("data", [])
            })
        except Exception as e:
            logger.error(f"查询淹没分析方案列表失败: {e}")
            return ToolResult(success=False, error=str(e))


class LossPlanAddTool(BaseTool):
    """新增淹没分析方案工具"""
    
    @property
    def name(self) -> str:
        return "loss_plan_add"
    
    @property
    def description(self) -> str:
        return "新增淹没分析方案，用于创建新的洪水淹没分析计算方案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="code", type="string", description="方案编码", required=True),
            ToolParameter(name="name", type="string", description="方案名称", required=True),
            ToolParameter(name="descrip", type="string", description="方案描述（可选）", required=False),
            ToolParameter(name="param_json", type="string", description="参数JSON（可选）", required=False),
            ToolParameter(name="fsda_code", type="string", description="蓄滞洪区编码，可多个（可选）", required=False),
            ToolParameter(name="fsda_name", type="string", description="蓄滞洪区名称，可多个（可选）", required=False),
            ToolParameter(name="model_type", type="string", description="类型：0=蓄滞洪区, 1=滩地（可选）", required=False),
            ToolParameter(name="save", type="string", description="是否保存方案（可选）", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行新增淹没分析方案"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/loss/add"
            payload = {
                "code": kwargs.get("code"),
                "name": kwargs.get("name")
            }
            if kwargs.get("descrip"):
                payload["descrip"] = kwargs.get("descrip")
            if kwargs.get("param_json"):
                payload["paramJson"] = kwargs.get("param_json")
            if kwargs.get("fsda_code"):
                payload["fsdaCode"] = kwargs.get("fsda_code")
            if kwargs.get("fsda_name"):
                payload["fsdaName"] = kwargs.get("fsda_name")
            if kwargs.get("model_type"):
                payload["modelType"] = kwargs.get("model_type")
            if kwargs.get("save"):
                payload["save"] = kwargs.get("save")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "淹没分析方案新增成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "新增失败"))
        except Exception as e:
            logger.error(f"新增淹没分析方案失败: {e}")
            return ToolResult(success=False, error=str(e))


class LossPlanDeleteTool(BaseTool):
    """删除淹没分析方案工具"""
    
    @property
    def name(self) -> str:
        return "loss_plan_delete"
    
    @property
    def description(self) -> str:
        return "删除指定的淹没分析方案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行删除淹没分析方案"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/loss/delete"
            params = {"code": kwargs.get("code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "淹没分析方案删除成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "删除失败"))
        except Exception as e:
            logger.error(f"删除淹没分析方案失败: {e}")
            return ToolResult(success=False, error=str(e))


class LossPlanCalcTool(BaseTool):
    """执行淹没分析方案计算工具"""
    
    @property
    def name(self) -> str:
        return "loss_plan_calc"
    
    @property
    def description(self) -> str:
        return "执行淹没分析方案计算，返回预计计算所需时间（秒）"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行淹没分析方案计算"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/loss/calc"
            params = {"code": kwargs.get("code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "执行计算失败"))
        except Exception as e:
            logger.error(f"执行淹没分析方案计算失败: {e}")
            return ToolResult(success=False, error=str(e))


class LossPlanDetailTool(BaseTool):
    """获取淹没分析方案及结果数据工具"""
    
    @property
    def name(self) -> str:
        return "loss_plan_detail"
    
    @property
    def description(self) -> str:
        return "获取淹没分析方案详情及计算结果数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取淹没分析方案详情"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/loss/detail"
            params = {"code": kwargs.get("code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取淹没分析方案详情失败: {e}")
            return ToolResult(success=False, error=str(e))


class LossPlanGisTool(BaseTool):
    """获取淹没分布GIS结果数据工具"""
    
    @property
    def name(self) -> str:
        return "loss_plan_gis"
    
    @property
    def description(self) -> str:
        return "获取淹没分布GIS数据，返回GeoJSON格式的淹没范围和深度信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="path", type="string", description="结果文件路径", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取淹没分布GIS数据"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/loss/gis"
            params = {"path": kwargs.get("path")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取淹没分布GIS数据失败: {e}")
            return ToolResult(success=False, error=str(e))


class LossPlanAutoTool(BaseTool):
    """自动计算淹没分析工具"""
    
    @property
    def name(self) -> str:
        return "loss_plan_auto"
    
    @property
    def description(self) -> str:
        return "自动计算淹没分析（无需登录）"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行自动计算淹没分析"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/loss/auto"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "自动淹没分析计算已触发"})
            else:
                return ToolResult(success=False, error=data.get("message", "执行失败"))
        except Exception as e:
            logger.error(f"自动计算淹没分析失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 三、防汛预案接口（5个）
# =============================================================================

class FloodPlanListAllTool(BaseTool):
    """查询全部防汛预案列表工具"""
    
    @property
    def name(self) -> str:
        return "flood_plan_list_all"
    
    @property
    def description(self) -> str:
        return "查询全部防汛预案列表（不分页），支持按预案名称、文号、年度、分类等条件过滤"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="title", type="string", description="预案名称（可选）", required=False),
            ToolParameter(name="code", type="string", description="预案文号（可选）", required=False),
            ToolParameter(name="year", type="string", description="年度（可选）", required=False),
            ToolParameter(name="type1", type="string", description="一级分类（可选）", required=False),
            ToolParameter(name="type2", type="string", description="二级分类（可选）", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查询全部防汛预案列表"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/flood/floodPlan/listAll"
            params = {}
            if kwargs.get("title"):
                params["title"] = kwargs.get("title")
            if kwargs.get("code"):
                params["code"] = kwargs.get("code")
            if kwargs.get("year"):
                params["year"] = kwargs.get("year")
            if kwargs.get("type1"):
                params["type1"] = kwargs.get("type1")
            if kwargs.get("type2"):
                params["type2"] = kwargs.get("type2")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"查询防汛预案列表失败: {e}")
            return ToolResult(success=False, error=str(e))


class FloodPlanAddTool(BaseTool):
    """新增防汛预案工具"""
    
    @property
    def name(self) -> str:
        return "flood_plan_add"
    
    @property
    def description(self) -> str:
        return "新增防汛预案（支持文件上传），用于创建新的防汛预案记录"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="title", type="string", description="预案名称", required=True),
            ToolParameter(name="code", type="string", description="预案文号（可选）", required=False),
            ToolParameter(name="year", type="string", description="年度（可选）", required=False),
            ToolParameter(name="type1", type="string", description="一级分类（可选）", required=False),
            ToolParameter(name="type2", type="string", description="二级分类（可选）", required=False),
            ToolParameter(name="remark", type="string", description="备注（可选）", required=False),
            ToolParameter(name="rela", type="string", description="关联信息（可选）", required=False),
            ToolParameter(name="file_id", type="string", description="已有文件ID（可选，如不上传新文件可直接指定）", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行新增防汛预案"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/flood/floodPlan/add"
            # 使用form-data格式
            form_data = {"title": kwargs.get("title")}
            if kwargs.get("code"):
                form_data["code"] = kwargs.get("code")
            if kwargs.get("year"):
                form_data["year"] = kwargs.get("year")
            if kwargs.get("type1"):
                form_data["type1"] = kwargs.get("type1")
            if kwargs.get("type2"):
                form_data["type2"] = kwargs.get("type2")
            if kwargs.get("remark"):
                form_data["remark"] = kwargs.get("remark")
            if kwargs.get("rela"):
                form_data["rela"] = kwargs.get("rela")
            if kwargs.get("file_id"):
                form_data["fileId"] = kwargs.get("file_id")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, data=form_data)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "防汛预案新增成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "新增失败"))
        except Exception as e:
            logger.error(f"新增防汛预案失败: {e}")
            return ToolResult(success=False, error=str(e))


class FloodPlanDeleteTool(BaseTool):
    """删除防汛预案工具"""
    
    @property
    def name(self) -> str:
        return "flood_plan_delete"
    
    @property
    def description(self) -> str:
        return "删除指定的防汛预案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="id", type="integer", description="预案ID", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行删除防汛预案"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/flood/floodPlan/delete"
            params = {"id": kwargs.get("id")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "防汛预案删除成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "删除失败"))
        except Exception as e:
            logger.error(f"删除防汛预案失败: {e}")
            return ToolResult(success=False, error=str(e))


class FloodPlanDetailTool(BaseTool):
    """查看防汛预案详情工具"""
    
    @property
    def name(self) -> str:
        return "flood_plan_detail"
    
    @property
    def description(self) -> str:
        return "查看防汛预案详情，包括预案名称、文号、年度、分类、文件信息等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="id", type="integer", description="预案ID", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查看防汛预案详情"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/flood/floodPlan/detail"
            params = {"id": kwargs.get("id")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"查看防汛预案详情失败: {e}")
            return ToolResult(success=False, error=str(e))


class FloodPlanCatalogTool(BaseTool):
    """获取防汛预案类型目录工具"""
    
    @property
    def name(self) -> str:
        return "flood_plan_catalog"
    
    @property
    def description(self) -> str:
        return "获取防汛预案类型目录，返回一级分类及其下属二级分类的树形结构"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取防汛预案类型目录"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/flood/floodPlan/catalog"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取防汛预案类型目录失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 四、水雨情态势研判接口（4个）
# =============================================================================

class MonitorRsvrNowTool(BaseTool):
    """获取水库河道实时水情工具"""
    
    @property
    def name(self) -> str:
        return "monitor_rsvr_now"
    
    @property
    def description(self) -> str:
        return "获取水库河道实时水情（无需登录），返回水位、库容、入库流量、出库流量等实时数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取水库河道实时水情"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/monitor/rsvr/now"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取水库河道实时水情失败: {e}")
            return ToolResult(success=False, error=str(e))


class MonitorRsvrStcTool(BaseTool):
    """获取水库当前形势统计工具"""
    
    @property
    def name(self) -> str:
        return "monitor_rsvr_stc"
    
    @property
    def description(self) -> str:
        return "获取水库当前形势统计，返回总数、正常数、预警数、危险数等统计信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取水库当前形势统计"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/monitor/rsvr/stc"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取水库当前形势统计失败: {e}")
            return ToolResult(success=False, error=str(e))


class MonitorRsvrTrackTool(BaseTool):
    """水雨情态势过程回溯工具"""
    
    @property
    def name(self) -> str:
        return "monitor_rsvr_track"
    
    @property
    def description(self) -> str:
        return "水雨情态势过程回溯，获取指定时段内水库水情变化过程"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="st", type="string", description="开始时间，格式: yyyy-MM-dd HH:mm:ss", required=True),
            ToolParameter(name="ed", type="string", description="结束时间，格式: yyyy-MM-dd HH:mm:ss", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水雨情态势过程回溯"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/monitor/rsvr/track"
            params = {
                "st": kwargs.get("st"),
                "ed": kwargs.get("ed")
            }
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"水雨情态势过程回溯失败: {e}")
            return ToolResult(success=False, error=str(e))


class MonitorRsvrStorageTool(BaseTool):
    """水库纳蓄能力分析工具"""
    
    @property
    def name(self) -> str:
        return "monitor_rsvr_storage"
    
    @property
    def description(self) -> str:
        return "水库纳蓄能力分析，返回总库容、当前蓄量、可用库容、蓄水率等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="goal", type="integer", description="目标水位或库容指标", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行水库纳蓄能力分析"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/monitor/rsvr/storage"
            params = {"goal": kwargs.get("goal")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"水库纳蓄能力分析失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 五、闸站工情接口（1个）
# =============================================================================

class MikeGateAllTool(BaseTool):
    """获取闸门工情工具"""
    
    @property
    def name(self) -> str:
        return "mike_gate_all"
    
    @property
    def description(self) -> str:
        return "获取闸门工情（无需登录），返回闸门状态（全开/半开/全关）、开度、开启孔数等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取闸门工情"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/init/gate"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取闸门工情失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 六、MIKE模型计算相关辅助接口（8个）
# =============================================================================

class MikeRunoffTool(BaseTool):
    """获取子流域NAM模型产流洪水结果工具"""
    
    @property
    def name(self) -> str:
        return "mike_runoff"
    
    @property
    def description(self) -> str:
        return "获取子流域NAM模型产流结果（无需登录），返回各子流域的产流时间序列"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="plan_code", type="string", description="方案编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取子流域NAM模型产流结果"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/runoff"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取子流域NAM模型产流结果失败: {e}")
            return ToolResult(success=False, error=str(e))


class MikeRsvrInfoTool(BaseTool):
    """获取水库基本信息工具"""
    
    @property
    def name(self) -> str:
        return "mike_rsvr_info"
    
    @property
    def description(self) -> str:
        return "获取水库基本信息（无需登录），包括水库编码、名称、汛限水位、正常水位、死水位、总库容等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="model_instance", type="string", description="模型实例编码（可选）", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取水库基本信息"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/rsvrInfo"
            params = {}
            if kwargs.get("model_instance"):
                params["modelInstance"] = kwargs.get("model_instance")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取水库基本信息失败: {e}")
            return ToolResult(success=False, error=str(e))


class MikeControlTool(BaseTool):
    """获取水库的可控建筑物工具"""
    
    @property
    def name(self) -> str:
        return "mike_control"
    
    @property
    def description(self) -> str:
        return "获取水库的可控建筑物，返回泄洪洞、溢洪道等可控设施信息及最大过流能力"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="stcd", type="string", description="水库编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取水库的可控建筑物"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/control"
            params = {"stcd": kwargs.get("stcd")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取水库的可控建筑物失败: {e}")
            return ToolResult(success=False, error=str(e))


class MikeHvrelaTool(BaseTool):
    """获取蓄滞洪区的库容曲线工具"""
    
    @property
    def name(self) -> str:
        return "mike_hvrela"
    
    @property
    def description(self) -> str:
        return "获取蓄滞洪区的库容曲线，返回水位-库容关系数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="code", type="string", description="蓄滞洪区编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取蓄滞洪区的库容曲线"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/hvrela"
            params = {"code": kwargs.get("code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取蓄滞洪区的库容曲线失败: {e}")
            return ToolResult(success=False, error=str(e))


class MikeSpecTimeTool(BaseTool):
    """获取指定时刻的水情工具"""
    
    @property
    def name(self) -> str:
        return "mike_spec_time"
    
    @property
    def description(self) -> str:
        return "获取指定时刻的水情，返回各水库测站的水位、入库流量、出库流量等数据"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="time", type="string", description="指定时间，格式: yyyy-MM-dd HH:mm:ss（可选，默认当前时间）", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取指定时刻的水情"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/specTime"
            params = {}
            if kwargs.get("time"):
                params["time"] = kwargs.get("time")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取指定时刻的水情失败: {e}")
            return ToolResult(success=False, error=str(e))


class MikeCalPaTool(BaseTool):
    """计算各子流域的前期影响雨量工具"""
    
    @property
    def name(self) -> str:
        return "mike_cal_pa"
    
    @property
    def description(self) -> str:
        return "计算指定时间各子流域的前期影响雨量(Pa值)，用于洪水预报模型参数计算"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="time", type="string", description="指定时间，格式: yyyy-MM-dd HH:mm:ss（可选，默认当前时间）", required=False)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行计算各子流域的前期影响雨量"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/calPa"
            params = {}
            if kwargs.get("time"):
                params["time"] = kwargs.get("time")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"计算各子流域的前期影响雨量失败: {e}")
            return ToolResult(success=False, error=str(e))


class MikeFsdaStructTool(BaseTool):
    """获取蓄滞洪区的建筑物信息工具"""
    
    @property
    def name(self) -> str:
        return "mike_fsda_struct"
    
    @property
    def description(self) -> str:
        return "获取指定业务模型对应蓄滞洪区的建筑物信息，如分洪堰等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="business_code", type="string", description="业务模型编码", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行获取蓄滞洪区的建筑物信息"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/fsda/struct"
            params = {"businessCode": kwargs.get("business_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
        except Exception as e:
            logger.error(f"获取蓄滞洪区的建筑物信息失败: {e}")
            return ToolResult(success=False, error=str(e))


class MikeFsdaSetBoundaryTool(BaseTool):
    """设置蓄滞洪区进洪预演模型的边界条件工具"""
    
    @property
    def name(self) -> str:
        return "mike_fsda_set_boundary"
    
    @property
    def description(self) -> str:
        return "设置蓄滞洪区进洪预演模型的边界条件，用于配置模型计算参数"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="boundary_config", type="object", description="边界条件配置JSON对象，根据具体蓄滞洪区模型定义", required=True)
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行设置蓄滞洪区进洪预演模型的边界条件"""
        try:
            url = f"{FLOOD_OTHER_BASE_URL}/modelPlatf/model/mike/fsda/setBoundary"
            payload = kwargs.get("boundary_config", {})
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "边界条件设置成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "设置失败"))
        except Exception as e:
            logger.error(f"设置蓄滞洪区进洪预演模型的边界条件失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 注册所有工具（共29个）
# =============================================================================

# 一、获取子流域洪水结果接口（4个）
register_tool(ModelResultOutflowDeleteTool())
register_tool(ModelResultOutflowGetBasinListTool())
register_tool(ModelResultOutflowDetailTool())
register_tool(ModelResultOutflowSourceTool())

# 二、基于DEM的洪水淹没分析接口（7个）
register_tool(LossPlanListTool())
register_tool(LossPlanAddTool())
register_tool(LossPlanDeleteTool())
register_tool(LossPlanCalcTool())
register_tool(LossPlanDetailTool())
register_tool(LossPlanGisTool())
register_tool(LossPlanAutoTool())

# 三、防汛预案接口（5个）
register_tool(FloodPlanListAllTool())
register_tool(FloodPlanAddTool())
register_tool(FloodPlanDeleteTool())
register_tool(FloodPlanDetailTool())
register_tool(FloodPlanCatalogTool())

# 四、水雨情态势研判接口（4个）
register_tool(MonitorRsvrNowTool())
register_tool(MonitorRsvrStcTool())
register_tool(MonitorRsvrTrackTool())
register_tool(MonitorRsvrStorageTool())

# 五、闸站工情接口（1个）
register_tool(MikeGateAllTool())

# 六、MIKE模型计算相关辅助接口（8个）
register_tool(MikeRunoffTool())
register_tool(MikeRsvrInfoTool())
register_tool(MikeControlTool())
register_tool(MikeHvrelaTool())
register_tool(MikeSpecTimeTool())
register_tool(MikeCalPaTool())
register_tool(MikeFsdaStructTool())
register_tool(MikeFsdaSetBoundaryTool())
