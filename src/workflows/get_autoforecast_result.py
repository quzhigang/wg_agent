"""
洪水自动预报结果查询工作流
根据需求查询最新自动预报的洪水结果
"""

from typing import Dict, Any, List

from ..config.logging_config import get_logger
from ..tools.registry import get_tool_registry
from .base import BaseWorkflow, WorkflowStep, WorkflowStatus
from .registry import register_workflow

logger = get_logger(__name__)


class GetAutoForecastResultWorkflow(BaseWorkflow):
    """
    洪水自动预报结果查询工作流
    
    触发场景：当用户询问流域、水库或水文站点、蓄滞洪区的未来洪水预报情况，
    且未提供具体的降雨条件（如自定义雨量）或指定采用预报降雨时，
    也未明确要求启动一次新的预报计算时。
    
    包含以下步骤：
    1. 解析会话参数 - 提取预报对象
    2. 获取最新洪水自动预报结果 - 调用get_tjdata_result工具
    3. 结果信息提取整理 - 提取主要预报结果数据
    4. 采用合适的Web页面模板进行结果输出
    """
    
    @property
    def name(self) -> str:
        return "get_auto_forecast_result"
    
    @property
    def description(self) -> str:
        return "洪水自动预报结果查询工作流，根据需求查询最新自动预报的洪水结果"
    
    @property
    def trigger_intents(self) -> List[str]:
        return [
            "auto_forecast_result_query",  # 自动预报结果查询
            "forecast_result_query",       # 预报结果查询
            "flood_situation_query"        # 洪水情况查询
        ]
    
    @property
    def trigger_keywords(self) -> List[str]:
        """
        触发关键词 - 基于文档对话示例
        注意：此工作流仅用于查询已有的自动预报结果，不是启动新的预报计算
        """
        return [
            # 明确查询自动预报结果的关键词
            "自动预报结果",
            "自动预报的结果",
            "最新的自动预报",
            "最近一次自动预报",
            # 查询预报情况（非启动计算）
            "洪水预报情况",
            "预报情况",
            "当前洪水预报情况",
            "最新洪水预报情况",
            # 查询未来洪水情况
            "未来几天流域洪水",
            "未来三天卫河流域洪水",
            "未来几天卫河流域洪水",
            "流域会发生洪水吗",
            # 查询具体对象的预报结果
            "水库未来的水位",
            "预报入库洪峰流量",
            "站点预报洪水情况",
            "站点预报洪峰流量",
            "蓄滞洪区预报洪水情况"
        ]
    
    @property
    def output_type(self) -> str:
        return "web_page"
    
    @property
    def steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(
                step_id=1,
                name="解析会话参数",
                description="从用户会话中提取预报对象，如果请求全流域洪水预报结果则输出全流域，如果请求指定水库水文站点蓄滞洪区预报结果则输出其中文名称",
                tool_name=None,  # 无需调用工具，由LLM解析
                tool_args_template=None,
                depends_on=[],
                is_async=False,
                output_key="forecast_target"
            ),
            WorkflowStep(
                step_id=2,
                name="获取最新洪水自动预报结果",
                description="调用get_tjdata_result工具获取自动预报方案结果，包含水库、河道断面、蓄滞洪区洪水结果",
                tool_name="get_tjdata_result",
                tool_args_template={"plan_code": "model_auto"},  # 固定采用model_auto
                depends_on=[1],
                is_async=False,
                output_key="auto_forecast_result"
            ),
            WorkflowStep(
                step_id=3,
                name="结果信息提取整理",
                description="根据预报对象提取全流域或单一目标主要预报结果数据，包括结果概括描述和结果数据",
                tool_name=None,  # 无需调用工具，由LLM处理
                tool_args_template=None,
                depends_on=[2],
                is_async=False,
                output_key="extracted_result"
            ),
            WorkflowStep(
                step_id=4,
                name="采用合适的Web页面模板进行结果输出",
                description="调用相应合适的web页面模板，如单一水库则调用单一水库洪水结果展示web页面模板(res_module)",
                tool_name="generate_report_page",
                tool_args_template={
                    "report_type": "auto_forecast",
                    "template": "res_module",
                    "data": "$extracted_result"
                },
                depends_on=[3],
                is_async=False,
                output_key="report_page_url"
            )
        ]
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行洪水自动预报结果查询工作流
        
        Args:
            state: 智能体状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始执行洪水自动预报结果查询工作流")
        
        registry = get_tool_registry()
        results = {}
        
        # 从状态中提取参数
        params = state.get('extracted_params', {})
        user_message = state.get('user_message', '')
        
        # 步骤1: 解析会话参数 - 提取预报对象
        forecast_target = self._parse_forecast_target(user_message, params)
        results['forecast_target'] = forecast_target
        logger.info(f"解析到预报对象: {forecast_target}")
        
        execution_results = []
        
        try:
            # 步骤2: 获取最新洪水自动预报结果
            logger.info("执行步骤2: 获取最新洪水自动预报结果")
            import time
            start_time = time.time()
            
            # 调用get_tjdata_result工具，plan_code固定为"model_auto"
            result = await registry.execute("get_tjdata_result", plan_code="model_auto")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 2,
                'step_name': '获取最新洪水自动预报结果',
                'tool_name': 'get_tjdata_result',
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            }
            execution_results.append(step_result)
            
            if not result.success:
                logger.error(f"获取自动预报结果失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"获取自动预报结果失败: {result.error}",
                    "next_action": "respond"
                }
            
            results['auto_forecast_result'] = result.data
            
            # 步骤3: 结果信息提取整理
            logger.info("执行步骤3: 结果信息提取整理")
            extracted_result = self._extract_forecast_result(
                forecast_target, 
                result.data
            )
            results['extracted_result'] = extracted_result
            
            execution_results.append({
                'step_id': 3,
                'step_name': '结果信息提取整理',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': extracted_result,
                'error': None
            })
            
            # 步骤4: 生成Web页面
            logger.info("执行步骤4: 采用合适的Web页面模板进行结果输出")
            start_time = time.time()
            
            # 根据预报对象选择合适的模板
            template = self._select_template(forecast_target)
            
            page_result = await registry.execute(
                "generate_report_page",
                report_type="auto_forecast",
                template=template,
                data=extracted_result
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 4,
                'step_name': '采用合适的Web页面模板进行结果输出',
                'tool_name': 'generate_report_page',
                'success': page_result.success,
                'execution_time_ms': execution_time_ms,
                'data': page_result.data if page_result.success else None,
                'error': page_result.error if not page_result.success else None
            }
            execution_results.append(step_result)
            
            if page_result.success:
                results['report_page_url'] = page_result.data
            
            logger.info("洪水自动预报结果查询工作流执行完成")
            
            return {
                "execution_results": execution_results,
                "workflow_results": results,
                "output_type": self.output_type,
                "generated_page_url": results.get('report_page_url'),
                "forecast_target": forecast_target,
                "extracted_result": extracted_result,
                "next_action": "respond"
            }
            
        except Exception as e:
            logger.error(f"洪水自动预报结果查询工作流执行异常: {e}")
            return {
                "execution_results": execution_results,
                "error": str(e),
                "next_action": "respond"
            }
    
    def _parse_forecast_target(self, user_message: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析预报对象
        
        Args:
            user_message: 用户消息
            params: 提取的参数
            
        Returns:
            预报对象信息
        """
        target = {
            "type": "basin",  # 默认全流域
            "name": "全流域",
            "id": None
        }
        
        # 检查是否指定了具体的水库
        reservoir_keywords = ["水库"]
        for keyword in reservoir_keywords:
            if keyword in user_message:
                # 尝试提取水库名称
                target["type"] = "reservoir"
                if params.get("reservoir_name"):
                    target["name"] = params.get("reservoir_name")
                    target["id"] = params.get("reservoir_id")
                break
        
        # 检查是否指定了具体的站点
        station_keywords = ["站", "水文站"]
        for keyword in station_keywords:
            if keyword in user_message and "蓄滞洪" not in user_message:
                target["type"] = "station"
                if params.get("station_name"):
                    target["name"] = params.get("station_name")
                    target["id"] = params.get("station_id")
                break
        
        # 检查是否指定了蓄滞洪区
        detention_keywords = ["蓄滞洪区"]
        for keyword in detention_keywords:
            if keyword in user_message:
                target["type"] = "detention_basin"
                if params.get("detention_name"):
                    target["name"] = params.get("detention_name")
                    target["id"] = params.get("detention_id")
                break
        
        return target
    
    def _extract_forecast_result(
        self, 
        forecast_target: Dict[str, Any], 
        forecast_data: Any
    ) -> Dict[str, Any]:
        """
        根据预报对象提取相关结果数据
        
        Args:
            forecast_target: 预报对象
            forecast_data: 完整的预报数据
            
        Returns:
            提取后的结果数据
        """
        extracted = {
            "target": forecast_target,
            "summary": "",
            "data": {}
        }
        
        if not forecast_data:
            extracted["summary"] = "未获取到预报数据"
            return extracted
        
        target_type = forecast_target.get("type", "basin")
        target_name = forecast_target.get("name", "全流域")
        
        if target_type == "basin":
            # 全流域数据提取
            extracted["summary"] = f"全流域洪水自动预报结果"
            extracted["data"] = forecast_data
            
        elif target_type == "reservoir":
            # 水库数据提取
            reservoir_data = self._extract_reservoir_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}洪水预报结果"
            extracted["data"] = reservoir_data
            
        elif target_type == "station":
            # 站点数据提取
            station_data = self._extract_station_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}洪水预报结果"
            extracted["data"] = station_data
            
        elif target_type == "detention_basin":
            # 蓄滞洪区数据提取
            detention_data = self._extract_detention_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}洪水预报结果"
            extracted["data"] = detention_data
        
        return extracted
    
    def _extract_reservoir_data(self, forecast_data: Any, reservoir_name: str) -> Dict[str, Any]:
        """提取水库相关数据"""
        if isinstance(forecast_data, dict):
            reservoirs = forecast_data.get("reservoirs", [])
            for res in reservoirs:
                if res.get("name") == reservoir_name or reservoir_name in str(res.get("name", "")):
                    return res
        return {"message": f"未找到{reservoir_name}的预报数据"}
    
    def _extract_station_data(self, forecast_data: Any, station_name: str) -> Dict[str, Any]:
        """提取站点相关数据"""
        if isinstance(forecast_data, dict):
            stations = forecast_data.get("stations", [])
            for sta in stations:
                if sta.get("name") == station_name or station_name in str(sta.get("name", "")):
                    return sta
        return {"message": f"未找到{station_name}的预报数据"}
    
    def _extract_detention_data(self, forecast_data: Any, detention_name: str) -> Dict[str, Any]:
        """提取蓄滞洪区相关数据"""
        if isinstance(forecast_data, dict):
            detentions = forecast_data.get("detention_basins", [])
            for det in detentions:
                if det.get("name") == detention_name or detention_name in str(det.get("name", "")):
                    return det
        return {"message": f"未找到{detention_name}的预报数据"}
    
    def _select_template(self, forecast_target: Dict[str, Any]) -> str:
        """
        根据预报对象选择合适的Web页面模板
        
        Args:
            forecast_target: 预报对象
            
        Returns:
            模板名称
        """
        target_type = forecast_target.get("type", "basin")
        
        # 根据对象类型选择模板
        if target_type == "reservoir":
            return "res_module"  # 单一水库洪水结果展示模板
        elif target_type == "station":
            return "res_module"  # 站点结果展示模板
        elif target_type == "detention_basin":
            return "res_module"  # 蓄滞洪区结果展示模板
        else:
            return "res_module"  # 默认使用res_module模板


# 自动注册工作流
_auto_forecast_workflow = GetAutoForecastResultWorkflow()
register_workflow(_auto_forecast_workflow)
