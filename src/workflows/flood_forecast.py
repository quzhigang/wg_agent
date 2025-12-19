"""
洪水预报工作流
实现完整的洪水预报预演流程
"""

from typing import Dict, Any, List

from ..config.logging_config import get_logger
from ..tools.registry import get_tool_registry
from .base import BaseWorkflow, WorkflowStep, WorkflowStatus
from .registry import register_workflow

logger = get_logger(__name__)


class FloodForecastWorkflow(BaseWorkflow):
    """
    洪水预报工作流
    
    包含以下步骤：
    1. 获取流域基本信息
    2. 查询当前水雨情数据
    3. 执行洪水预报模型
    4. 获取预报结果
    5. 生成预报报告（Web页面）
    """
    
    @property
    def name(self) -> str:
        return "flood_forecast"
    
    @property
    def description(self) -> str:
        return "洪水预报预演工作流，包括数据获取、模型运行、结果分析"
    
    @property
    def trigger_intents(self) -> List[str]:
        return ["flood_forecast", "flood_prediction", "flood_simulation"]
    
    @property
    def trigger_keywords(self) -> List[str]:
        return ["洪水预报", "洪水预测", "洪水预演", "预报洪水", "洪峰预报"]
    
    @property
    def output_type(self) -> str:
        return "web_page"
    
    @property
    def steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                step_id=1,
                name="获取流域信息",
                description="查询目标流域的基本信息",
                tool_name="get_basin_info",
                tool_args_template={"basin_id": "$basin_id"},
                depends_on=[],
                is_async=False,
                output_key="basin_info"
            ),
            WorkflowStep(
                step_id=2,
                name="查询水位数据",
                description="获取流域内各站点的实时水位",
                tool_name="query_water_level",
                tool_args_template={
                    "station_ids": "$station_ids",
                    "start_time": "$start_time",
                    "end_time": "$end_time"
                },
                depends_on=[1],
                is_async=False,
                output_key="water_level_data"
            ),
            WorkflowStep(
                step_id=3,
                name="查询雨量数据",
                description="获取流域内各站点的降雨数据",
                tool_name="query_rainfall",
                tool_args_template={
                    "station_ids": "$station_ids",
                    "start_time": "$start_time",
                    "end_time": "$end_time"
                },
                depends_on=[1],
                is_async=False,
                output_key="rainfall_data"
            ),
            WorkflowStep(
                step_id=4,
                name="运行洪水预报模型",
                description="调用水文模型进行洪水预报",
                tool_name="run_flood_forecast",
                tool_args_template={
                    "basin_id": "$basin_id",
                    "forecast_hours": "$forecast_hours",
                    "scenario": "$scenario"
                },
                depends_on=[2, 3],
                is_async=True,
                output_key="forecast_task_id"
            ),
            WorkflowStep(
                step_id=5,
                name="获取预报结果",
                description="获取洪水预报模型的运行结果",
                tool_name="get_forecast_result",
                tool_args_template={"task_id": "$forecast_task_id"},
                depends_on=[4],
                is_async=False,
                output_key="forecast_result"
            ),
            WorkflowStep(
                step_id=6,
                name="生成预报报告",
                description="生成包含图表的洪水预报报告页面",
                tool_name="generate_report_page",
                tool_args_template={
                    "report_type": "flood_forecast",
                    "data": {
                        "basin_info": "$basin_info",
                        "water_level": "$water_level_data",
                        "rainfall": "$rainfall_data",
                        "forecast": "$forecast_result"
                    }
                },
                depends_on=[5],
                is_async=False,
                output_key="report_page_url"
            )
        ]
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行洪水预报工作流
        
        Args:
            state: 智能体状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始执行洪水预报工作流")
        
        registry = get_tool_registry()
        results = {}
        
        # 从状态中提取参数
        params = state.get('extracted_params', {})
        basin_id = params.get('basin_id', 'default_basin')
        
        # 设置默认参数
        import datetime
        now = datetime.datetime.now()
        default_params = {
            'basin_id': basin_id,
            'station_ids': params.get('station_ids', []),
            'start_time': params.get('start_time', (now - datetime.timedelta(hours=24)).isoformat()),
            'end_time': params.get('end_time', now.isoformat()),
            'forecast_hours': params.get('forecast_hours', 72),
            'scenario': params.get('scenario', 'normal')
        }
        
        execution_results = []
        
        try:
            # 按依赖顺序执行步骤
            for step in self.steps:
                logger.info(f"执行步骤 {step.step_id}: {step.name}")
                
                # 构建工具参数
                tool_args = {}
                if step.tool_args_template:
                    for key, value_template in step.tool_args_template.items():
                        if isinstance(value_template, str) and value_template.startswith('$'):
                            param_key = value_template[1:]
                            # 先从之前的结果中查找，再从默认参数中查找
                            tool_args[key] = results.get(param_key, default_params.get(param_key, value_template))
                        elif isinstance(value_template, dict):
                            # 处理嵌套字典
                            tool_args[key] = self._resolve_dict_template(value_template, results, default_params)
                        else:
                            tool_args[key] = value_template
                
                # 执行工具
                if step.tool_name:
                    import time
                    start_time = time.time()
                    
                    result = await registry.execute(step.tool_name, **tool_args)
                    
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    step_result = {
                        'step_id': step.step_id,
                        'step_name': step.name,
                        'tool_name': step.tool_name,
                        'success': result.success,
                        'execution_time_ms': execution_time_ms,
                        'data': result.data if result.success else None,
                        'error': result.error if not result.success else None
                    }
                    execution_results.append(step_result)
                    
                    if result.success and step.output_key:
                        results[step.output_key] = result.data
                    
                    if not result.success:
                        logger.error(f"步骤 {step.step_id} 执行失败: {result.error}")
                        # 对于关键步骤，失败则终止
                        if step.step_id in [4, 5]:  # 预报模型和结果是关键步骤
                            return {
                                "execution_results": execution_results,
                                "error": f"工作流执行失败: 步骤 {step.name} - {result.error}",
                                "next_action": "respond"
                            }
            
            logger.info("洪水预报工作流执行完成")
            
            return {
                "execution_results": execution_results,
                "workflow_results": results,
                "output_type": self.output_type,
                "generated_page_url": results.get('report_page_url'),
                "next_action": "respond"
            }
            
        except Exception as e:
            logger.error(f"洪水预报工作流执行异常: {e}")
            return {
                "execution_results": execution_results,
                "error": str(e),
                "next_action": "respond"
            }
    
    def _resolve_dict_template(
        self, 
        template: Dict[str, Any], 
        results: Dict[str, Any],
        default_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析字典模板中的变量引用"""
        resolved = {}
        for key, value in template.items():
            if isinstance(value, str) and value.startswith('$'):
                param_key = value[1:]
                resolved[key] = results.get(param_key, default_params.get(param_key, value))
            elif isinstance(value, dict):
                resolved[key] = self._resolve_dict_template(value, results, default_params)
            else:
                resolved[key] = value
        return resolved


class EmergencyPlanWorkflow(BaseWorkflow):
    """
    应急预案生成工作流
    
    根据洪水预报结果生成应急响应预案
    """
    
    @property
    def name(self) -> str:
        return "emergency_plan"
    
    @property
    def description(self) -> str:
        return "根据洪水预报生成应急响应预案"
    
    @property
    def trigger_intents(self) -> List[str]:
        return ["emergency_plan", "response_plan", "flood_response"]
    
    @property
    def trigger_keywords(self) -> List[str]:
        return ["应急预案", "响应预案", "防洪预案", "生成预案", "制定预案"]
    
    @property
    def output_type(self) -> str:
        return "web_page"
    
    @property
    def steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                step_id=1,
                name="获取预警信息",
                description="获取当前的洪水预警信息",
                tool_name="get_flood_warning",
                tool_args_template={"basin_id": "$basin_id"},
                depends_on=[],
                is_async=False,
                output_key="warning_info"
            ),
            WorkflowStep(
                step_id=2,
                name="查询历史洪水",
                description="查询历史相似洪水事件",
                tool_name="query_historical_flood",
                tool_args_template={
                    "basin_id": "$basin_id",
                    "limit": 5
                },
                depends_on=[],
                is_async=False,
                output_key="historical_floods"
            ),
            WorkflowStep(
                step_id=3,
                name="获取脆弱性数据",
                description="获取区域脆弱性评估数据",
                tool_name="get_vulnerability_data",
                tool_args_template={"region_id": "$region_id"},
                depends_on=[],
                is_async=False,
                output_key="vulnerability_data"
            ),
            WorkflowStep(
                step_id=4,
                name="生成应急预案",
                description="基于分析结果生成应急预案",
                tool_name="generate_emergency_plan",
                tool_args_template={
                    "basin_id": "$basin_id",
                    "warning_level": "$warning_level",
                    "affected_areas": "$affected_areas"
                },
                depends_on=[1, 2, 3],
                is_async=True,
                output_key="emergency_plan"
            ),
            WorkflowStep(
                step_id=5,
                name="生成预案报告",
                description="生成应急预案报告页面",
                tool_name="generate_report_page",
                tool_args_template={
                    "report_type": "emergency_plan",
                    "data": {
                        "warning": "$warning_info",
                        "historical": "$historical_floods",
                        "vulnerability": "$vulnerability_data",
                        "plan": "$emergency_plan"
                    }
                },
                depends_on=[4],
                is_async=False,
                output_key="report_page_url"
            )
        ]
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """执行应急预案工作流"""
        logger.info("开始执行应急预案生成工作流")
        
        registry = get_tool_registry()
        results = {}
        
        params = state.get('extracted_params', {})
        default_params = {
            'basin_id': params.get('basin_id', 'default_basin'),
            'region_id': params.get('region_id', 'default_region'),
            'warning_level': params.get('warning_level', 'yellow'),
            'affected_areas': params.get('affected_areas', [])
        }
        
        execution_results = []
        
        try:
            for step in self.steps:
                logger.info(f"执行步骤 {step.step_id}: {step.name}")
                
                tool_args = {}
                if step.tool_args_template:
                    for key, value_template in step.tool_args_template.items():
                        if isinstance(value_template, str) and value_template.startswith('$'):
                            param_key = value_template[1:]
                            tool_args[key] = results.get(param_key, default_params.get(param_key, value_template))
                        elif isinstance(value_template, dict):
                            tool_args[key] = self._resolve_dict_template(value_template, results, default_params)
                        else:
                            tool_args[key] = value_template
                
                if step.tool_name:
                    import time
                    start_time = time.time()
                    
                    result = await registry.execute(step.tool_name, **tool_args)
                    
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    step_result = {
                        'step_id': step.step_id,
                        'step_name': step.name,
                        'tool_name': step.tool_name,
                        'success': result.success,
                        'execution_time_ms': execution_time_ms,
                        'data': result.data if result.success else None,
                        'error': result.error if not result.success else None
                    }
                    execution_results.append(step_result)
                    
                    if result.success and step.output_key:
                        results[step.output_key] = result.data
            
            logger.info("应急预案工作流执行完成")
            
            return {
                "execution_results": execution_results,
                "workflow_results": results,
                "output_type": self.output_type,
                "generated_page_url": results.get('report_page_url'),
                "next_action": "respond"
            }
            
        except Exception as e:
            logger.error(f"应急预案工作流执行异常: {e}")
            return {
                "execution_results": execution_results,
                "error": str(e),
                "next_action": "respond"
            }
    
    def _resolve_dict_template(
        self, 
        template: Dict[str, Any], 
        results: Dict[str, Any],
        default_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """解析字典模板中的变量引用"""
        resolved = {}
        for key, value in template.items():
            if isinstance(value, str) and value.startswith('$'):
                param_key = value[1:]
                resolved[key] = results.get(param_key, default_params.get(param_key, value))
            elif isinstance(value, dict):
                resolved[key] = self._resolve_dict_template(value, results, default_params)
            else:
                resolved[key] = value
        return resolved


# 自动注册工作流
_flood_forecast_workflow = FloodForecastWorkflow()
_emergency_plan_workflow = EmergencyPlanWorkflow()

register_workflow(_flood_forecast_workflow)
register_workflow(_emergency_plan_workflow)
