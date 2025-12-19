"""
防洪业务工具
提供洪水预报、预演、预案相关功能
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

from ..config.settings import settings
from ..config.logging_config import get_logger
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool

logger = get_logger(__name__)


class RunFloodForecastTool(BaseTool):
    """运行洪水预报模型工具"""
    
    @property
    def name(self) -> str:
        return "run_flood_forecast"
    
    @property
    def description(self) -> str:
        return "启动洪水预报模型计算，返回任务ID用于查询结果"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def is_async(self) -> bool:
        return True  # 这是一个异步任务
    
    @property
    def timeout_seconds(self) -> int:
        return 300  # 5分钟超时
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="forecast_time",
                type="string",
                description="预报起始时间，格式: YYYY-MM-DD HH:mm:ss",
                required=False
            ),
            ToolParameter(
                name="forecast_period",
                type="integer",
                description="预报时段长度(小时)，默认72小时",
                required=False,
                default=72
            ),
            ToolParameter(
                name="scenario",
                type="string",
                description="预报场景: real(实况), design(设计), custom(自定义)",
                required=False,
                default="real",
                enum=["real", "design", "custom"]
            ),
            ToolParameter(
                name="rainfall_data",
                type="object",
                description="自定义降雨数据（scenario为custom时使用）",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行洪水预报"""
        forecast_time = kwargs.get('forecast_time') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        forecast_period = kwargs.get('forecast_period', 72)
        scenario = kwargs.get('scenario', 'real')
        rainfall_data = kwargs.get('rainfall_data')
        
        try:
            # 调用模型服务器API
            url = settings.wg_model_server_url
            
            params = {
                "method": "StartFloodForecast",
                "forecast_time": forecast_time,
                "forecast_period": forecast_period,
                "scenario": scenario
            }
            
            if scenario == "custom" and rainfall_data:
                params["rainfall_data"] = rainfall_data
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, json=params)
                response.raise_for_status()
                data = response.json()
            
            # 返回任务ID
            task_id = data.get('task_id') or data.get('TaskID')
            
            return ToolResult(
                success=True,
                data={
                    "task_id": task_id,
                    "status": "submitted",
                    "message": "洪水预报任务已提交",
                    "forecast_time": forecast_time,
                    "forecast_period": forecast_period
                },
                metadata={"is_async_task": True}
            )
            
        except httpx.HTTPError as e:
            logger.error(f"洪水预报启动HTTP错误: {e}")
            return self._get_mock_result()
        except Exception as e:
            logger.error(f"洪水预报启动失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_result(self) -> ToolResult:
        """返回模拟结果"""
        import uuid
        return ToolResult(
            success=True,
            data={
                "task_id": str(uuid.uuid4()),
                "status": "submitted",
                "message": "洪水预报任务已提交（模拟）"
            },
            metadata={"is_mock": True, "is_async_task": True}
        )


class GetForecastResultTool(BaseTool):
    """获取洪水预报结果工具"""
    
    @property
    def name(self) -> str:
        return "get_forecast_result"
    
    @property
    def description(self) -> str:
        return "获取洪水预报计算结果，包括各断面的预报水位、流量等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="task_id",
                type="string",
                description="预报任务ID",
                required=False
            ),
            ToolParameter(
                name="latest",
                type="boolean",
                description="是否获取最新的预报结果",
                required=False,
                default=True
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取预报结果"""
        task_id = kwargs.get('task_id')
        latest = kwargs.get('latest', True)
        
        try:
            url = settings.wg_model_server_url
            
            params = {
                "method": "GetForecastResult"
            }
            if task_id:
                params["task_id"] = task_id
            if latest:
                params["latest"] = True
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data.get('result', data)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"获取预报结果HTTP错误: {e}")
            return self._get_mock_result()
        except Exception as e:
            logger.error(f"获取预报结果失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_result(self) -> ToolResult:
        """返回模拟结果"""
        mock_data = {
            "forecast_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "sections": [
                {
                    "section_name": "卫辉断面",
                    "peak_time": "2024-07-15 18:00:00",
                    "peak_level": 79.85,
                    "peak_flow": 1250.5,
                    "warning_level": 79.00,
                    "guarantee_level": 80.50,
                    "level_forecast": [
                        {"time": "2024-07-15 08:00:00", "level": 78.2},
                        {"time": "2024-07-15 12:00:00", "level": 79.1},
                        {"time": "2024-07-15 18:00:00", "level": 79.85},
                        {"time": "2024-07-16 00:00:00", "level": 79.5}
                    ]
                },
                {
                    "section_name": "浚县断面",
                    "peak_time": "2024-07-15 22:00:00",
                    "peak_level": 45.65,
                    "peak_flow": 1180.2,
                    "warning_level": 45.00,
                    "guarantee_level": 46.50
                }
            ],
            "summary": "预计卫辉断面将于15日18时出现洪峰，峰值水位79.85米，超警戒水位0.85米"
        }
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


class GetFloodWarningTool(BaseTool):
    """获取洪水预警信息工具"""
    
    @property
    def name(self) -> str:
        return "get_flood_warning"
    
    @property
    def description(self) -> str:
        return "获取当前的洪水预警信息，包括超警、超保等情况"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="warning_level",
                type="string",
                description="预警级别筛选: red(红色), orange(橙色), yellow(黄色), blue(蓝色)",
                required=False,
                enum=["red", "orange", "yellow", "blue"]
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """获取洪水预警"""
        warning_level = kwargs.get('warning_level')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/flood/warning"
            
            params = {}
            if warning_level:
                params['level'] = warning_level
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data.get('data', data)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"获取预警信息HTTP错误: {e}")
            return self._get_mock_result()
        except Exception as e:
            logger.error(f"获取预警信息失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_result(self) -> ToolResult:
        """返回模拟结果"""
        mock_data = [
            {
                "station_name": "卫辉站",
                "warning_level": "yellow",
                "current_level": 79.25,
                "warning_threshold": 79.00,
                "guarantee_threshold": 80.50,
                "exceed_warning": 0.25,
                "warning_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "trend": "rising"
            }
        ]
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


class QueryHistoricalFloodTool(BaseTool):
    """查询历史洪水工具"""
    
    @property
    def name(self) -> str:
        return "query_historical_flood"
    
    @property
    def description(self) -> str:
        return "查询历史洪水记录，用于对比分析和参考"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="year",
                type="integer",
                description="年份",
                required=False
            ),
            ToolParameter(
                name="station_name",
                type="string",
                description="测站名称",
                required=False
            ),
            ToolParameter(
                name="min_peak_flow",
                type="float",
                description="最小洪峰流量筛选",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """查询历史洪水"""
        year = kwargs.get('year')
        station_name = kwargs.get('station_name')
        min_peak_flow = kwargs.get('min_peak_flow')
        
        try:
            base_url = settings.wg_data_server_url
            url = f"{base_url}/api/flood/historical"
            
            params = {}
            if year:
                params['year'] = year
            if station_name:
                params['stnm'] = station_name
            if min_peak_flow:
                params['min_flow'] = min_peak_flow
            
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
            
            return ToolResult(
                success=True,
                data=data.get('data', data)
            )
            
        except httpx.HTTPError as e:
            logger.error(f"查询历史洪水HTTP错误: {e}")
            return self._get_mock_result()
        except Exception as e:
            logger.error(f"查询历史洪水失败: {e}")
            return ToolResult(success=False, error=str(e))
    
    def _get_mock_result(self) -> ToolResult:
        """返回模拟结果"""
        mock_data = [
            {
                "year": 2021,
                "flood_name": "21·7特大暴雨洪水",
                "station_name": "卫辉站",
                "peak_time": "2021-07-22 08:00:00",
                "peak_level": 81.35,
                "peak_flow": 2850,
                "total_rainfall": 458.5,
                "duration_hours": 72,
                "description": "百年一遇特大洪水"
            },
            {
                "year": 2016,
                "flood_name": "16·7洪水",
                "station_name": "卫辉站",
                "peak_time": "2016-07-19 12:00:00",
                "peak_level": 79.85,
                "peak_flow": 1580,
                "total_rainfall": 285.2,
                "duration_hours": 48
            }
        ]
        return ToolResult(success=True, data=mock_data, metadata={"is_mock": True})


class GenerateEmergencyPlanTool(BaseTool):
    """生成应急预案工具"""
    
    @property
    def name(self) -> str:
        return "generate_emergency_plan"
    
    @property
    def description(self) -> str:
        return "根据当前洪水形势生成应急响应预案建议"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.FLOOD_CONTROL
    
    @property
    def is_async(self) -> bool:
        return True
    
    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="forecast_result",
                type="object",
                description="洪水预报结果",
                required=False
            ),
            ToolParameter(
                name="warning_level",
                type="string",
                description="预警级别",
                required=False,
                enum=["red", "orange", "yellow", "blue"]
            ),
            ToolParameter(
                name="affected_area",
                type="string",
                description="影响区域",
                required=False
            )
        ]
    
    async def execute(self, **kwargs) -> ToolResult:
        """生成应急预案"""
        forecast_result = kwargs.get('forecast_result')
        warning_level = kwargs.get('warning_level', 'yellow')
        affected_area = kwargs.get('affected_area')
        
        # 根据预警级别生成预案建议
        plan_templates = {
            "red": {
                "response_level": "I级（特别重大）",
                "actions": [
                    "启动防汛I级应急响应",
                    "组织危险区域群众紧急转移",
                    "启用所有蓄滞洪区",
                    "请求上级支援和军队参与救援",
                    "24小时值班，实时监控水情"
                ],
                "evacuation": "立即转移全部受威胁群众",
                "resources": "调动全部抢险队伍和物资"
            },
            "orange": {
                "response_level": "II级（重大）",
                "actions": [
                    "启动防汛II级应急响应",
                    "组织低洼地区群众转移",
                    "加强重点堤段巡查",
                    "备用蓄滞洪区做好启用准备",
                    "12小时值班制度"
                ],
                "evacuation": "转移低洼地区和危险区域群众",
                "resources": "调集主要抢险队伍和物资"
            },
            "yellow": {
                "response_level": "III级（较大）",
                "actions": [
                    "启动防汛III级应急响应",
                    "加强水情监测频次",
                    "检查防洪工程设施",
                    "做好群众转移准备",
                    "8小时值班制度"
                ],
                "evacuation": "做好转移准备，划定转移路线",
                "resources": "备齐抢险物资，队伍待命"
            },
            "blue": {
                "response_level": "IV级（一般）",
                "actions": [
                    "启动防汛IV级应急响应",
                    "密切关注雨水情变化",
                    "检查排水设施",
                    "发布预警信息",
                    "正常值班"
                ],
                "evacuation": "暂不需要转移",
                "resources": "检查物资储备情况"
            }
        }
        
        plan = plan_templates.get(warning_level, plan_templates["yellow"])
        plan["warning_level"] = warning_level
        plan["generated_time"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if affected_area:
            plan["affected_area"] = affected_area
        
        return ToolResult(
            success=True,
            data=plan,
            metadata={"warning_level": warning_level}
        )


# 注册工具
def register_flood_control_tools():
    """注册防洪业务工具"""
    register_tool(RunFloodForecastTool())
    register_tool(GetForecastResultTool())
    register_tool(GetFloodWarningTool())
    register_tool(QueryHistoricalFloodTool())
    register_tool(GenerateEmergencyPlanTool())
    logger.info("防洪业务工具注册完成")


# 模块加载时自动注册
register_flood_control_tools()
