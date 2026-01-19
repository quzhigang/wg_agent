"""
人工洪水预报结果查询工作流
根据需求查询人工预报方案的洪水结果
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from ..config.logging_config import get_logger
from ..tools.registry import get_tool_registry
from .base import BaseWorkflow, WorkflowStep, WorkflowStatus
from .registry import register_workflow

logger = get_logger(__name__)


class GetManualForecastResultWorkflow(BaseWorkflow):
    """
    人工洪水预报结果查询工作流
    
    触发场景：当用户询问流域、水库或水文站点、蓄滞洪区某人工预报方案的洪水预报结果，
    也未明确要求启动一次新的预报计算时。
    
    包含以下步骤：
    1. 解析会话参数 - 提取预报对象、降雨大概起止时间、人工预报方案描述
    2. 获取历史面雨量过程 - 调用forecast_rain_ecmwf_avg工具
    3. 获取具体降雨起止时间 - 分析降雨过程数据
    4. 获取人工预报方案ID - 调用model_plan_list_all工具
    5. 获取人工预报结果 - 调用get_tjdata_result工具
    6. 结果信息提取整理 - 提取主要预报结果数据
    7. 采用合适的Web页面模板进行结果输出
    """
    
    @property
    def name(self) -> str:
        return "get_manualforecast_result"
    
    @property
    def description(self) -> str:
        return "人工洪水预报结果查询工作流，根据需求查询人工预报方案的洪水结果"
    
    @property
    def trigger_intents(self) -> List[str]:
        return [
            "manual_forecast_result_query",   # 人工预报结果查询
            "custom_forecast_result_query"   # 自定义预报结果查询
        ]
    
    @property
    def trigger_keywords(self) -> List[str]:
        """
        触发关键词 - 基于文档对话示例
        注意：此工作流用于查询人工预报方案的洪水结果
        """
        return [
            # 明确查询人工预报结果的关键词（对话示例）
            "人工预报方案",
            "人工预报结果",
            "人工预报的结果",
            # 查询特定时间的预报结果
            "那场降雨的人工预报结果",
            "那场降雨的预报结果",
            "人工预报方案中有没有",
            # 查询汛期预报结果
            "汛期最大的一场降雨的人工预报",
            "最大的一场降雨的人工预报结果",
            # 查询人工方案
            "查询人工预报",
            "查看人工预报",
            "人工方案结果"
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
                description="从用户会话中提取：1.预报对象（全流域/指定目标），2.降雨大概起止时间，3.人工预报方案描述（如果提及则跳过步骤2和3）",
                tool_name=None,  # 无需调用工具，由LLM解析
                tool_args_template=None,
                depends_on=[],
                is_async=False,
                output_key="session_params"
            ),
            WorkflowStep(
                step_id=2,
                name="获取历史面雨量过程",
                description="调用forecast_rain_ecmwf_avg工具获取该时间段内的全流域平均历史逐小时面雨量过程",
                tool_name="forecast_rain_ecmwf_avg",
                tool_args_template={"st": "$rain_start_time", "ed": "$rain_end_time"},
                depends_on=[1],
                is_async=False,
                output_key="rain_process"
            ),
            WorkflowStep(
                step_id=3,
                name="获取具体降雨起止时间",
                description="通过分析输入的逐小时降雨过程数据，获取本场降雨的具体开始和结束时间，注意掐头去尾，去掉主要降雨时段前后零星的少量降雨",
                tool_name=None,  # 无需调用工具，由LLM处理
                tool_args_template=None,
                depends_on=[2],
                is_async=False,
                output_key="exact_rain_time"
            ),
            WorkflowStep(
                step_id=4,
                name="获取人工预报方案ID",
                description="调用model_plan_list_all工具获取人工预报方案ID清单，并根据方案描述或降雨起止时间匹配方案",
                tool_name="model_plan_list_all",
                tool_args_template={"business_code": "flood_forecast_wg"},
                depends_on=[3],
                is_async=False,
                output_key="plan_id"
            ),
            WorkflowStep(
                step_id=5,
                name="获取人工预报结果",
                description="调用get_tjdata_result工具获取人工预报方案结果，包含水库、河道断面、蓄滞洪区洪水结果",
                tool_name="get_tjdata_result",
                tool_args_template={"plan_code": "$plan_id"},
                depends_on=[4],
                is_async=False,
                output_key="manual_forecast_result"
            ),
            WorkflowStep(
                step_id=6,
                name="结果信息提取整理",
                description="根据预报对象提取全流域或单一目标主要预报结果数据，包括结果概括描述和结果数据",
                tool_name=None,  # 无需调用工具，由LLM处理
                tool_args_template=None,
                depends_on=[5],
                is_async=False,
                output_key="extracted_result"
            ),
            WorkflowStep(
                step_id=7,
                name="采用合适的Web页面模板进行结果输出",
                description="全流域预报结果采用web模板1，单目标预报结果采用web模板2",
                tool_name="generate_report_page",
                tool_args_template={
                    "report_type": "manual_forecast",
                    "template": "$template_name",
                    "data": "$extracted_result"
                },
                depends_on=[6],
                is_async=False,
                output_key="report_page_url"
            )
        ]
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行人工洪水预报结果查询工作流
        
        Args:
            state: 智能体状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始执行人工洪水预报结果查询工作流")
        
        registry = get_tool_registry()
        results = {}
        
        # 从状态中提取参数
        params = state.get('extracted_params', {})
        user_message = state.get('user_message', '')
        entities = state.get('entities', {})  # 获取意图分析提取的实体

        execution_results = []

        try:
            import time

            # 步骤1: 解析会话参数
            logger.info("执行步骤1: 解析会话参数")
            session_params = self._parse_session_params(user_message, params, entities)
            results['session_params'] = session_params
            
            execution_results.append({
                'step_id': 1,
                'step_name': '解析会话参数',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': session_params,
                'error': None
            })
            
            forecast_target = session_params.get('forecast_target', {})
            rain_time_range = session_params.get('rain_time_range', {})
            plan_description = session_params.get('plan_description', '')
            
            logger.info(f"解析到预报对象: {forecast_target}")
            logger.info(f"解析到降雨时间范围: {rain_time_range}")
            logger.info(f"解析到方案描述: {plan_description}")
            
            # 如果有明确的方案描述，跳过步骤2和3
            skip_rain_analysis = bool(plan_description)
            exact_rain_time = None
            
            if not skip_rain_analysis:
                # 步骤2: 获取历史面雨量过程
                logger.info("执行步骤2: 获取历史面雨量过程")
                start_time = time.time()
                
                rain_start = rain_time_range.get('start', '')
                rain_end = rain_time_range.get('end', '')
                
                if rain_start and rain_end:
                    result = await registry.execute(
                        "forecast_rain_ecmwf_avg",
                        st=rain_start,
                        ed=rain_end
                    )
                    
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    step_result = {
                        'step_id': 2,
                        'step_name': '获取历史面雨量过程',
                        'tool_name': 'forecast_rain_ecmwf_avg',
                        'success': result.success,
                        'execution_time_ms': execution_time_ms,
                        'data': result.data if result.success else None,
                        'error': result.error if not result.success else None
                    }
                    execution_results.append(step_result)
                    
                    if result.success:
                        results['rain_process'] = result.data
                        
                        # 步骤3: 获取具体降雨起止时间
                        logger.info("执行步骤3: 获取具体降雨起止时间")
                        exact_rain_time = self._analyze_rain_time(result.data)
                        results['exact_rain_time'] = exact_rain_time
                        
                        execution_results.append({
                            'step_id': 3,
                            'step_name': '获取具体降雨起止时间',
                            'tool_name': None,
                            'success': True,
                            'execution_time_ms': 0,
                            'data': exact_rain_time,
                            'error': None
                        })
                    else:
                        logger.warning(f"获取历史面雨量过程失败: {result.error}")
                else:
                    logger.warning("未提供降雨时间范围，跳过步骤2和3")
            else:
                logger.info("已提供方案描述，跳过步骤2和3")
            
            # 步骤4: 获取人工预报方案ID
            logger.info("执行步骤4: 获取人工预报方案ID")
            start_time = time.time()
            
            # 调用model_plan_list_all工具，只传business_code参数
            result = await registry.execute(
                "model_plan_list_all",
                business_code="flood_forecast_wg"
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 4,
                'step_name': '获取人工预报方案ID',
                'tool_name': 'model_plan_list_all',
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            }
            execution_results.append(step_result)
            
            if not result.success:
                logger.error(f"获取人工预报方案列表失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"获取人工预报方案列表失败: {result.error}",
                    "next_action": "respond"
                }
            
            # 匹配方案ID
            plan_id = self._match_plan_id(
                result.data,
                plan_description,
                exact_rain_time
            )
            results['plan_id'] = plan_id
            
            if not plan_id:
                logger.error("未找到匹配的人工预报方案")
                return {
                    "execution_results": execution_results,
                    "error": "未找到匹配的人工预报方案",
                    "next_action": "respond"
                }
            
            logger.info(f"匹配到方案ID: {plan_id}")
            
            # 步骤5: 获取人工预报结果
            logger.info("执行步骤5: 获取人工预报结果")
            start_time = time.time()
            
            result = await registry.execute("get_tjdata_result", plan_code=plan_id)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 5,
                'step_name': '获取人工预报结果',
                'tool_name': 'get_tjdata_result',
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            }
            execution_results.append(step_result)
            
            if not result.success:
                logger.error(f"获取人工预报结果失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"获取人工预报结果失败: {result.error}",
                    "next_action": "respond"
                }
            
            results['manual_forecast_result'] = result.data
            
            # 步骤6: 结果信息提取整理
            logger.info("执行步骤6: 结果信息提取整理")
            extracted_result = self._extract_forecast_result(
                forecast_target, 
                result.data
            )
            results['extracted_result'] = extracted_result
            
            execution_results.append({
                'step_id': 6,
                'step_name': '结果信息提取整理',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': extracted_result,
                'error': None
            })
            
            # 步骤7: 生成Web页面
            logger.info("执行步骤7: 采用合适的Web页面模板进行结果输出")
            start_time = time.time()
            
            # 根据预报对象选择合适的模板
            template = self._select_template(forecast_target)
            
            page_result = await registry.execute(
                "generate_report_page",
                report_type="manual_forecast",
                template=template,
                data=extracted_result
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 7,
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
            
            logger.info("人工洪水预报结果查询工作流执行完成")
            
            return {
                "execution_results": execution_results,
                "workflow_results": results,
                "output_type": self.output_type,
                "generated_page_url": results.get('report_page_url'),
                "forecast_target": forecast_target,
                "extracted_result": extracted_result,
                "plan_id": plan_id,
                "next_action": "respond"
            }
            
        except Exception as e:
            logger.error(f"人工洪水预报结果查询工作流执行异常: {e}")
            return {
                "execution_results": execution_results,
                "error": str(e),
                "next_action": "respond"
            }
    
    def _parse_session_params(self, user_message: str, params: Dict[str, Any], entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析会话参数

        Args:
            user_message: 用户消息
            params: 提取的参数
            entities: 意图分析提取的实体

        Returns:
            解析后的会话参数，包含预报对象、降雨时间范围、方案描述
        """
        result = {
            "forecast_target": {
                "type": "basin",
                "name": "全流域",
                "id": None
            },
            "rain_time_range": {
                "start": "",
                "end": ""
            },
            "plan_description": ""
        }

        entities = entities or {}

        # 优先从entities中获取对象信息
        object_name = entities.get("object", "")
        object_type = entities.get("object_type", "")

        # 解析预报对象
        if object_type == "水库" or "水库" in user_message:
            result["forecast_target"]["type"] = "reservoir"
            if object_name and "水库" in object_name:
                result["forecast_target"]["name"] = object_name
            elif params.get("reservoir_name"):
                result["forecast_target"]["name"] = params.get("reservoir_name")
                result["forecast_target"]["id"] = params.get("reservoir_id")
        elif object_type in ["站点", "水文站", "站"] or (("站" in user_message or "水文站" in user_message) and "蓄滞洪" not in user_message):
            result["forecast_target"]["type"] = "station"
            if object_name and "站" in object_name:
                result["forecast_target"]["name"] = object_name
            elif params.get("station_name"):
                result["forecast_target"]["name"] = params.get("station_name")
                result["forecast_target"]["id"] = params.get("station_id")
        elif object_type == "蓄滞洪区" or "蓄滞洪区" in user_message:
            result["forecast_target"]["type"] = "detention_basin"
            if object_name and "蓄滞洪区" in object_name:
                result["forecast_target"]["name"] = object_name
            elif params.get("detention_name"):
                result["forecast_target"]["name"] = params.get("detention_name")
                result["forecast_target"]["id"] = params.get("detention_id")
        
        # 解析方案描述（如果用户提供了具体的方案名称）
        if "方案" in user_message and any(x in user_message for x in ["人工预报方案1", "方案一", "方案1"]):
            result["plan_description"] = "人工预报方案1"
        
        # 解析降雨时间范围
        # 尝试从参数中获取时间信息
        if params.get("rain_start_time") and params.get("rain_end_time"):
            result["rain_time_range"]["start"] = params.get("rain_start_time")
            result["rain_time_range"]["end"] = params.get("rain_end_time")
        elif params.get("event_date"):
            # 如果只有事件日期，增加前后几天的余量
            event_date = params.get("event_date")
            try:
                date_obj = datetime.strptime(event_date, "%Y-%m-%d")
                start_date = date_obj - timedelta(days=3)
                end_date = date_obj + timedelta(days=3)
                result["rain_time_range"]["start"] = start_date.strftime("%Y-%m-%d 00:00:00")
                result["rain_time_range"]["end"] = end_date.strftime("%Y-%m-%d 23:59:59")
            except ValueError:
                pass
        
        return result
    
    def _analyze_rain_time(self, rain_data: Any) -> Dict[str, str]:
        """
        分析降雨过程数据，获取具体降雨起止时间
        
        Args:
            rain_data: 逐小时降雨过程数据
            
        Returns:
            具体的降雨起止时间
        """
        result = {
            "start": "",
            "end": ""
        }
        
        if not rain_data:
            return result
        
        try:
            # 假设rain_data是一个时间-降雨量的字典或列表
            if isinstance(rain_data, dict):
                rain_times = []
                threshold = 0.1  # 降雨阈值，用于过滤零星降雨
                
                for time_str, rain_value in rain_data.items():
                    if isinstance(rain_value, (int, float)) and rain_value > threshold:
                        rain_times.append(time_str)
                
                if rain_times:
                    rain_times.sort()
                    result["start"] = rain_times[0]
                    result["end"] = rain_times[-1]
            
            elif isinstance(rain_data, list):
                rain_times = []
                threshold = 0.1
                
                for item in rain_data:
                    if isinstance(item, dict):
                        time_str = item.get("time") or item.get("tm")
                        rain_value = item.get("value") or item.get("drp") or item.get("rain")
                        if time_str and isinstance(rain_value, (int, float)) and rain_value > threshold:
                            rain_times.append(time_str)
                
                if rain_times:
                    rain_times.sort()
                    result["start"] = rain_times[0]
                    result["end"] = rain_times[-1]
        
        except Exception as e:
            logger.warning(f"分析降雨时间失败: {e}")
        
        return result
    
    def _match_plan_id(
        self,
        plan_list: Any,
        plan_description: str,
        exact_rain_time: Optional[Dict[str, str]]
    ) -> Optional[str]:
        """
        匹配人工预报方案ID
        
        Args:
            plan_list: 方案列表
            plan_description: 方案描述
            exact_rain_time: 具体降雨起止时间
            
        Returns:
            匹配到的方案ID或None
        """
        if not plan_list:
            return None
        
        plans = plan_list if isinstance(plan_list, list) else []
        
        # 如果有方案描述，按描述匹配
        if plan_description:
            for plan in plans:
                plan_name = plan.get("planName", "")
                plan_desc = plan.get("planDesc", "")
                plan_code = plan.get("planCode", "")
                
                if plan_description.lower() in plan_name.lower() or \
                   plan_description.lower() in plan_desc.lower():
                    return plan_code
        
        # 如果有降雨时间，按时间匹配
        if exact_rain_time and exact_rain_time.get("start") and exact_rain_time.get("end"):
            rain_start = exact_rain_time["start"]
            rain_end = exact_rain_time["end"]
            
            for plan in plans:
                plan_start = plan.get("startTime", "")
                plan_end = plan.get("endTime", "")
                plan_code = plan.get("planCode", "")
                
                # 检查方案时间是否能"包住"降雨时间
                if plan_start and plan_end:
                    if plan_start <= rain_start and plan_end >= rain_end:
                        return plan_code
        
        # 如果没有匹配到，返回最新的方案
        if plans:
            # 按创建时间或ID排序，取最新的
            sorted_plans = sorted(
                plans,
                key=lambda x: x.get("createTime", "") or x.get("planCode", ""),
                reverse=True
            )
            return sorted_plans[0].get("planCode")
        
        return None
    
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
            extracted["summary"] = f"全流域人工洪水预报结果"
            extracted["data"] = forecast_data
            
        elif target_type == "reservoir":
            # 水库数据提取
            reservoir_data = self._extract_reservoir_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}人工洪水预报结果"
            extracted["data"] = reservoir_data
            
        elif target_type == "station":
            # 站点数据提取
            station_data = self._extract_station_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}人工洪水预报结果"
            extracted["data"] = station_data
            
        elif target_type == "detention_basin":
            # 蓄滞洪区数据提取
            detention_data = self._extract_detention_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}人工洪水预报结果"
            extracted["data"] = detention_data
        
        return extracted
    
    def _extract_reservoir_data(self, forecast_data: Any, reservoir_name: str) -> Dict[str, Any]:
        """提取水库相关数据"""
        if isinstance(forecast_data, dict):
            # 数据结构: {'reservoir_result': {'水库名': {...}}}
            reservoir_result = forecast_data.get("reservoir_result", {})
            if isinstance(reservoir_result, dict):
                # 直接按名称查找
                if reservoir_name in reservoir_result:
                    return reservoir_result[reservoir_name]
                # 模糊匹配
                for name, data in reservoir_result.items():
                    if reservoir_name in name or name in reservoir_name:
                        return data
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
        
        根据文档：全流域预报结果采用web模板1，单目标预报结果采用web模板2
        
        Args:
            forecast_target: 预报对象
            
        Returns:
            模板名称
        """
        target_type = forecast_target.get("type", "basin")
        
        # 根据对象类型选择模板
        if target_type == "basin":
            return "index"  # 全流域使用web模板1（index）
        else:
            return "res_module"  # 单目标使用web模板2（res_module）


# 自动注册工作流
_get_manualforecast_result_workflow = GetManualForecastResultWorkflow()
register_workflow(_get_manualforecast_result_workflow)
