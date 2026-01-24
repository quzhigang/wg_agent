"""
模型及方案管理相关业务工具
提供模拟方案管理、基础模型管理、模型实例管理、业务模型管理等功能
基于防洪业务接口-模型及方案管理相关业务.md文档实现
接口基础地址：http://10.20.2.153/api/basin/modelPlatf
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool
from .auth import LoginTool

logger = get_logger(__name__)

# 从配置获取模型平台API基础地址
MODEL_PLATFORM_BASE_URL = settings.wg_flood_server_url


# =============================================================================
# 一、模拟方案管理接口工具（12个，不含分页list，使用listAll）
# =============================================================================

class ModelPlanAddTool(BaseTool):
    """新增模拟方案工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_add"
    
    @property
    def description(self) -> str:
        return "新增洪水预报模拟方案，设置方案名称、时间范围、业务模型等参数"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_name",
                type="string",
                description="方案名称",
                required=True
            ),
            ToolParameter(
                name="business_code",
                type="string",
                description="业务模型编码",
                required=True
            ),
            ToolParameter(
                name="start_time",
                type="string",
                description="开始时间，格式: yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="结束时间，格式: yyyy-MM-dd HH:mm:ss",
                required=True
            ),
            ToolParameter(
                name="plan_desc",
                type="string",
                description="方案描述",
                required=False
            ),
            ToolParameter(
                name="business_name",
                type="string",
                description="业务模型名称",
                required=False
            ),
            ToolParameter(
                name="step_save_minutes",
                type="integer",
                description="模型结果保存时间步长(分钟)",
                required=False,
                default=60
            ),
            ToolParameter(
                name="inherit_plan_code",
                type="string",
                description="继承方案的编码",
                required=False
            ),
            ToolParameter(
                name="view_point",
                type="string",
                description="相机位置",
                required=False
            ),
            ToolParameter(
                name="model_object",
                type="string",
                description="模型参数JSON字符串",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行新增模拟方案"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/add"
            
            # 必填参数
            payload = {
                "planName": kwargs.get("plan_name"),
                "businessCode": kwargs.get("business_code"),
                "startTime": kwargs.get("start_time"),
                "endTime": kwargs.get("end_time")
            }
            
            # 可选参数
            if kwargs.get("plan_desc"):
                payload["planDesc"] = kwargs.get("plan_desc")
            if kwargs.get("business_name"):
                payload["businessName"] = kwargs.get("business_name")
            if kwargs.get("step_save_minutes"):
                payload["stepSaveMinutes"] = kwargs.get("step_save_minutes")
            if kwargs.get("inherit_plan_code"):
                payload["inheritPlanCode"] = kwargs.get("inherit_plan_code")
            if kwargs.get("view_point"):
                payload["viewPoint"] = kwargs.get("view_point")
            if kwargs.get("model_object"):
                payload["modelObject"] = kwargs.get("model_object")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data)
            else:
                return ToolResult(success=False, error=data.get("message", "新增方案失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"新增模拟方案HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"新增模拟方案失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanEditTool(BaseTool):
    """编辑模拟方案工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_edit"
    
    @property
    def description(self) -> str:
        return "编辑已存在的洪水预报模拟方案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案编码",
                required=True
            ),
            ToolParameter(
                name="plan_name",
                type="string",
                description="方案名称",
                required=False
            ),
            ToolParameter(
                name="business_code",
                type="string",
                description="业务模型编码",
                required=False
            ),
            ToolParameter(
                name="start_time",
                type="string",
                description="开始时间，格式: yyyy-MM-dd HH:mm:ss",
                required=False
            ),
            ToolParameter(
                name="end_time",
                type="string",
                description="结束时间，格式: yyyy-MM-dd HH:mm:ss",
                required=False
            ),
            ToolParameter(
                name="plan_desc",
                type="string",
                description="方案描述",
                required=False
            ),
            ToolParameter(
                name="business_name",
                type="string",
                description="业务模型名称",
                required=False
            ),
            ToolParameter(
                name="step_save_minutes",
                type="integer",
                description="模型结果保存时间步长(分钟)",
                required=False
            ),
            ToolParameter(
                name="inherit_plan_code",
                type="string",
                description="继承方案的编码",
                required=False
            ),
            ToolParameter(
                name="view_point",
                type="string",
                description="相机位置",
                required=False
            ),
            ToolParameter(
                name="model_object",
                type="string",
                description="模型参数JSON字符串",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行编辑模拟方案"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/edit"
            
            # 构建请求体
            payload = {"planCode": kwargs.get("plan_code")}
            
            # 可选更新参数
            if kwargs.get("plan_name"):
                payload["planName"] = kwargs.get("plan_name")
            if kwargs.get("business_code"):
                payload["businessCode"] = kwargs.get("business_code")
            if kwargs.get("start_time"):
                payload["startTime"] = kwargs.get("start_time")
            if kwargs.get("end_time"):
                payload["endTime"] = kwargs.get("end_time")
            if kwargs.get("plan_desc"):
                payload["planDesc"] = kwargs.get("plan_desc")
            if kwargs.get("business_name"):
                payload["businessName"] = kwargs.get("business_name")
            if kwargs.get("step_save_minutes"):
                payload["stepSaveMinutes"] = kwargs.get("step_save_minutes")
            if kwargs.get("inherit_plan_code"):
                payload["inheritPlanCode"] = kwargs.get("inherit_plan_code")
            if kwargs.get("view_point"):
                payload["viewPoint"] = kwargs.get("view_point")
            if kwargs.get("model_object"):
                payload["modelObject"] = kwargs.get("model_object")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data)
            else:
                return ToolResult(success=False, error=data.get("message", "编辑方案失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"编辑模拟方案HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"编辑模拟方案失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanDeleteTool(BaseTool):
    """删除模拟方案工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_delete"
    
    @property
    def description(self) -> str:
        return "删除指定的洪水预报模拟方案"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行删除模拟方案"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/delete"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "删除成功"})
            else:
                return ToolResult(success=False, error=data.get("message", "删除失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"删除模拟方案HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"删除模拟方案失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanDetailTool(BaseTool):
    """查看模拟方案详情工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_detail"
    
    @property
    def description(self) -> str:
        return "根据方案编码查看模拟方案的详细信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查看方案详情"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/detail"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询方案详情HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询方案详情失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanStateTool(BaseTool):
    """查看方案计算状态工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_state"
    
    @property
    def description(self) -> str:
        return "查看模拟方案的当前计算状态"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """查询方案状态"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/state"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"state": data.get("data")})
            else:
                return ToolResult(success=False, error=data.get("message", "查询状态失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询方案状态HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询方案状态失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanListAllTool(BaseTool):
    """查询全部模拟方案列表工具（不分页）"""
    
    @property
    def name(self) -> str:
        return "model_plan_list_all"
    
    @property
    def description(self) -> str:
        return "查询全部洪水预报模拟方案列表(不分页)，支持按方案名称、编码、状态等条件筛选"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案编码（精确匹配）",
                required=False
            ),
            ToolParameter(
                name="plan_name",
                type="string",
                description="方案名称（模糊查询）",
                required=False
            ),
            ToolParameter(
                name="business_code",
                type="string",
                description="业务模型编码",
                required=False
            ),
            ToolParameter(
                name="state",
                type="string",
                description="计算状态：待计算/计算中/计算完成/计算失败",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行查询全部模拟方案列表"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/listAll"

            params = {}
            if kwargs.get("plan_code"):
                params["planCode"] = kwargs.get("plan_code")
            if kwargs.get("plan_name"):
                params["planName"] = kwargs.get("plan_name")
            if kwargs.get("business_code"):
                params["businessCode"] = kwargs.get("business_code")
            if kwargs.get("state"):
                params["state"] = kwargs.get("state")

            # 获取认证头
            auth_headers = await LoginTool.get_auth_headers()

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params, headers=auth_headers)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询方案列表HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询方案列表失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanCalcTool(BaseTool):
    """执行模拟方案计算工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_calc"
    
    @property
    def description(self) -> str:
        return "启动指定方案的洪水预报模型计算"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def is_async(self) -> bool:
        return True  # 这是一个异步计算任务
    
    @property
    def timeout_seconds(self) -> int:
        return 300  # 5分钟超时
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行方案计算"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/calc"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(
                    success=True, 
                    data=data.get("data"),
                    metadata={"is_async_task": True}
                )
            else:
                return ToolResult(success=False, error=data.get("message", "计算启动失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"启动方案计算HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"启动方案计算失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanStopTool(BaseTool):
    """终止方案计算工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_stop"
    
    @property
    def description(self) -> str:
        return "终止正在进行的模拟方案计算"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """终止计算"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/stop"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "计算已终止"})
            else:
                return ToolResult(success=False, error=data.get("message", "终止失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"终止计算HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"终止计算失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanProgressTool(BaseTool):
    """获取方案计算进度工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_progress"
    
    @property
    def description(self) -> str:
        return "获取模拟方案的计算进度信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="plan_code",
                type="string",
                description="方案编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取计算进度"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/progress"
            params = {"planCode": kwargs.get("plan_code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询进度失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询计算进度HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询计算进度失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanCountStateTool(BaseTool):
    """获取方案状态统计工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_count_state"
    
    @property
    def description(self) -> str:
        return "获取不同计算状态的方案数量统计"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取状态统计"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/count/state"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询状态统计HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询状态统计失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanCountPlanTool(BaseTool):
    """获取业务模型方案数量统计工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_count_plan"
    
    @property
    def description(self) -> str:
        return "获取各业务模型的模拟方案数量统计"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取方案数量统计"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/count/plan"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询方案数量统计HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询方案数量统计失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelPlanAutoForecastTool(BaseTool):
    """手动执行自动预报工具"""
    
    @property
    def name(self) -> str:
        return "model_plan_auto_forecast"
    
    @property
    def description(self) -> str:
        return "手动触发一次自动洪水预报计算（无需登录）"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行自动预报"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelPlan/autoForecast/manual"
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data={"message": "自动预报已触发"})
            else:
                return ToolResult(success=False, error=data.get("message", "触发失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"触发自动预报HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"触发自动预报失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 二、基础模型管理接口工具（3个）
# =============================================================================

class ModelBasicListAllTool(BaseTool):
    """查询全部基础模型列表工具"""
    
    @property
    def name(self) -> str:
        return "model_basic_list_all"
    
    @property
    def description(self) -> str:
        return "查询全部基础模型列表(不分页)，支持按模型名称、编码、类型等条件筛选"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="模型名称",
                required=False
            ),
            ToolParameter(
                name="code",
                type="string",
                description="模型编码",
                required=False
            ),
            ToolParameter(
                name="type_id",
                type="integer",
                description="模型类型ID",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """查询基础模型列表"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelBasic/listAll"
            
            params = {}
            if kwargs.get("name"):
                params["name"] = kwargs.get("name")
            if kwargs.get("code"):
                params["code"] = kwargs.get("code")
            if kwargs.get("type_id"):
                params["typeId"] = kwargs.get("type_id")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询基础模型列表HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询基础模型列表失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelBasicDetailTool(BaseTool):
    """查看基础模型详情工具"""
    
    @property
    def name(self) -> str:
        return "model_basic_detail"
    
    @property
    def description(self) -> str:
        return "根据模型ID查看基础模型的详细信息，包括模型介绍、原理、参数等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="id",
                type="integer",
                description="模型ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """查看基础模型详情"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelBasic/detail"
            params = {"id": kwargs.get("id")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询基础模型详情HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询基础模型详情失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelBasicCountTool(BaseTool):
    """获取模型数量统计工具"""
    
    @property
    def name(self) -> str:
        return "model_basic_count"
    
    @property
    def description(self) -> str:
        return "获取基础模型、模型实例、业务模型、模拟方案的数量统计"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return []
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取模型数量统计"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelBasic/count"
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询模型数量统计HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询模型数量统计失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 三、模型实例管理接口工具（2个）
# =============================================================================

class ModelInstanceListAllTool(BaseTool):
    """查询全部模型实例列表工具"""
    
    @property
    def name(self) -> str:
        return "model_instance_list_all"
    
    @property
    def description(self) -> str:
        return "查询全部模型实例列表(不分页)，支持按实例名称、编码、基础模型、流域等条件筛选"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="实例名称",
                required=False
            ),
            ToolParameter(
                name="code",
                type="string",
                description="实例编码",
                required=False
            ),
            ToolParameter(
                name="basic_code",
                type="string",
                description="基础模型编码",
                required=False
            ),
            ToolParameter(
                name="basin_code",
                type="string",
                description="流域编码",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """查询模型实例列表"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelInstance/listAll"
            
            params = {}
            if kwargs.get("name"):
                params["name"] = kwargs.get("name")
            if kwargs.get("code"):
                params["code"] = kwargs.get("code")
            if kwargs.get("basic_code"):
                params["basicCode"] = kwargs.get("basic_code")
            if kwargs.get("basin_code"):
                params["basinCode"] = kwargs.get("basin_code")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询模型实例列表HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询模型实例列表失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelInstanceDetailTool(BaseTool):
    """查看模型实例详情工具"""
    
    @property
    def name(self) -> str:
        return "model_instance_detail"
    
    @property
    def description(self) -> str:
        return "根据实例ID查看模型实例的详细信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="id",
                type="integer",
                description="实例ID",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """查看模型实例详情"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelInstance/detail"
            params = {"id": kwargs.get("id")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询模型实例详情HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询模型实例详情失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 四、业务模型管理接口工具（3个）
# =============================================================================

class ModelBusinessListAllTool(BaseTool):
    """查询全部业务模型列表工具"""
    
    @property
    def name(self) -> str:
        return "model_business_list_all"
    
    @property
    def description(self) -> str:
        return "查询全部业务模型列表(不分页)，支持按业务模型名称、编码、类型等条件筛选"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="业务模型名称",
                required=False
            ),
            ToolParameter(
                name="code",
                type="string",
                description="业务模型编码",
                required=False
            ),
            ToolParameter(
                name="type_id",
                type="integer",
                description="业务模型类型ID",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """查询业务模型列表"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelBusiness/listAll"
            
            params = {}
            if kwargs.get("name"):
                params["name"] = kwargs.get("name")
            if kwargs.get("code"):
                params["code"] = kwargs.get("code")
            if kwargs.get("type_id"):
                params["typeId"] = kwargs.get("type_id")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询业务模型列表HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询业务模型列表失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelBusinessAddTool(BaseTool):
    """新增业务模型工具"""
    
    @property
    def name(self) -> str:
        return "model_business_add"
    
    @property
    def description(self) -> str:
        return "新增业务模型，设置业务模型名称、编码、类型等参数"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="业务模型名称",
                required=True
            ),
            ToolParameter(
                name="code",
                type="string",
                description="业务模型编码（唯一）",
                required=True
            ),
            ToolParameter(
                name="type_id",
                type="integer",
                description="业务模型类型ID",
                required=False
            ),
            ToolParameter(
                name="type_name",
                type="string",
                description="业务模型类型名称",
                required=False
            ),
            ToolParameter(
                name="instance_codes",
                type="string",
                description="模型实例编码(多个用逗号分隔)",
                required=False
            ),
            ToolParameter(
                name="view_point",
                type="string",
                description="相机位置",
                required=False
            ),
            ToolParameter(
                name="url",
                type="string",
                description="模型地址",
                required=False
            ),
            ToolParameter(
                name="remark",
                type="string",
                description="备注",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行新增业务模型"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelBusiness/add"
            
            # 必填参数
            payload = {
                "name": kwargs.get("name"),
                "code": kwargs.get("code")
            }
            
            # 可选参数
            if kwargs.get("type_id"):
                payload["typeId"] = kwargs.get("type_id")
            if kwargs.get("type_name"):
                payload["typeName"] = kwargs.get("type_name")
            if kwargs.get("instance_codes"):
                payload["instanceCodes"] = kwargs.get("instance_codes")
            if kwargs.get("view_point"):
                payload["viewPoint"] = kwargs.get("view_point")
            if kwargs.get("url"):
                payload["url"] = kwargs.get("url")
            if kwargs.get("remark"):
                payload["remark"] = kwargs.get("remark")
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data)
            else:
                return ToolResult(success=False, error=data.get("message", "新增业务模型失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"新增业务模型HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"新增业务模型失败: {e}")
            return ToolResult(success=False, error=str(e))


class ModelBusinessDetailTool(BaseTool):
    """查看业务模型详情工具"""
    
    @property
    def name(self) -> str:
        return "model_business_detail"
    
    @property
    def description(self) -> str:
        return "根据业务模型编码查看业务模型的详细信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="code",
                type="string",
                description="业务模型编码",
                required=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """查看业务模型详情"""
        try:
            url = f"{MODEL_PLATFORM_BASE_URL}/model/modelBusiness/detail"
            params = {"code": kwargs.get("code")}
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("success"):
                return ToolResult(success=True, data=data.get("data"))
            else:
                return ToolResult(success=False, error=data.get("message", "查询失败"))
                
        except httpx.HTTPError as e:
            logger.error(f"查询业务模型详情HTTP错误: {e}")
            return ToolResult(success=False, error=f"HTTP请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"查询业务模型详情失败: {e}")
            return ToolResult(success=False, error=str(e))


# =============================================================================
# 工具注册函数
# =============================================================================

def register_modelplan_control_tools():
    """注册模型及方案管理相关业务工具"""
    
    # 一、模拟方案管理工具（12个）
    register_tool(ModelPlanAddTool())          # 1. 新增模拟方案
    register_tool(ModelPlanEditTool())         # 2. 编辑模拟方案
    register_tool(ModelPlanDeleteTool())       # 3. 删除模拟方案
    register_tool(ModelPlanDetailTool())       # 4. 查看模拟方案详情
    register_tool(ModelPlanStateTool())        # 5. 查看方案计算状态
    register_tool(ModelPlanListAllTool())      # 6. 查询全部模拟方案列表
    register_tool(ModelPlanCalcTool())         # 7. 执行模拟方案计算
    register_tool(ModelPlanStopTool())         # 8. 终止方案计算
    register_tool(ModelPlanProgressTool())     # 9. 获取方案计算进度
    register_tool(ModelPlanCountStateTool())   # 10. 获取方案状态统计
    register_tool(ModelPlanCountPlanTool())    # 11. 获取业务模型方案数量统计
    register_tool(ModelPlanAutoForecastTool()) # 12. 手动执行自动预报
    
    # 二、基础模型管理工具（3个）
    register_tool(ModelBasicListAllTool())     # 13. 查询全部基础模型列表
    register_tool(ModelBasicDetailTool())      # 14. 查看基础模型详情
    register_tool(ModelBasicCountTool())       # 15. 获取模型数量统计
    
    # 三、模型实例管理工具（2个）
    register_tool(ModelInstanceListAllTool())  # 16. 查询全部模型实例列表
    register_tool(ModelInstanceDetailTool())   # 17. 查看模型实例详情
    
    # 四、业务模型管理工具（3个）
    register_tool(ModelBusinessListAllTool())  # 18. 查询全部业务模型列表
    register_tool(ModelBusinessAddTool())      # 19. 新增业务模型
    register_tool(ModelBusinessDetailTool())   # 20. 查看业务模型详情
    
    logger.info("模型及方案管理相关业务工具注册完成，共注册20个工具")


# 模块加载时自动注册
register_modelplan_control_tools()
