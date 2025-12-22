"""
历史洪水自动预报结果查询工作流
根据需求查询历史自动预报的洪水结果
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..config.logging_config import get_logger
from ..tools.registry import get_tool_registry
from .base import BaseWorkflow, WorkflowStep, WorkflowStatus
from .registry import register_workflow

logger = get_logger(__name__)


class GetHistoryAutoForecastResultWorkflow(BaseWorkflow):
    """
    历史洪水自动预报结果查询工作流
    
    触发场景：当用户询问流域、水库或水文站点、蓄滞洪区已经过去的历史某时间洪水预报情况，
    也未明确要求启动一次新的预报计算时。
    
    包含以下步骤：
    1. 解析会话参数 - 提取预报对象和降雨大概起止时间
    2. 获取历史面雨量过程 - 调用forecast_rain_ecmwf_avg工具
    3. 获取具体降雨起止时间 - 分析降雨过程数据
    4. 获取历史洪水自动预报方案ID - 调用get_history_autoforcast_list工具
    5. 获取历史洪水自动预报结果 - 调用get_tjdata_result工具
    6. 结果信息提取整理 - 提取主要预报结果数据
    7. 采用合适的Web页面模板进行结果输出
    """
    
    @property
    def name(self) -> str:
        return "get_history_autoforecast_result"
    
    @property
    def description(self) -> str:
        return "历史洪水自动预报结果查询工作流，根据需求查询历史自动预报的洪水结果"
    
    @property
    def trigger_intents(self) -> List[str]:
        return [
            "history_forecast_result_query",  # 历史预报结果查询
            "historical_flood_query",          # 历史洪水查询
            "past_forecast_query"              # 过去预报查询
        ]
    
    @property
    def trigger_keywords(self) -> List[str]:
        """
        触发关键词 - 基于文档对话示例
        注意：此工作流用于查询历史（过去）的自动预报结果
        """
        return [
            # 明确历史预报相关
            "那场洪水的预报结果",
            "那场降雨的预报结果",
            "那场洪水预报情况",
            "那场降雨预报",
            # 时间相关历史查询
            "上周那场洪水预报结果",
            "上周那场降雨预报结果",
            "月份最大的那场降雨预报结果",
            "最大降雨的洪水预报",
            "今年最大的一场降雨预报结果",
            "去年最大的一场降雨预报结果",
            "某年最大的一场降雨预报结果",
            # 具体日期查询
            "某月某日那场洪水预报结果",
            # 历史预报结果查询
            "历史洪水预报",
            "过去的预报结果"
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
                description="从用户会话中提取预报对象和降雨大概起止时间。预报对象：如果请求全流域则输出全流域，如果请求指定水库水文站点蓄滞洪区则输出其中文名称；降雨时间：根据洪水预报具体时间或时间描述信息，前后增加几天余量，得到一个能包住的降雨大概起止时间",
                tool_name=None,  # 无需调用工具，由LLM解析
                tool_args_template=None,
                depends_on=[],
                is_async=False,
                output_key="parsed_params"
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
                name="获取历史洪水自动预报方案ID",
                description="调用get_history_autoforcast_list工具获取历史自动预报方案ID清单，寻找与降雨结束时间最接近且超过的预报开始时间对应的方案ID",
                tool_name="get_history_autoforcast_list",
                tool_args_template={},  # 固定参数，无需输入
                depends_on=[3],
                is_async=False,
                output_key="history_plan_id"
            ),
            WorkflowStep(
                step_id=5,
                name="获取历史洪水自动预报结果",
                description="调用get_tjdata_result工具获取历史自动预报方案结果，包含水库、河道断面、蓄滞洪区洪水结果",
                tool_name="get_tjdata_result",
                tool_args_template={"plan_code": "$history_plan_id"},
                depends_on=[4],
                is_async=False,
                output_key="history_forecast_result"
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
                    "report_type": "history_forecast",
                    "template": "$selected_template",
                    "data": "$extracted_result"
                },
                depends_on=[6],
                is_async=False,
                output_key="report_page_url"
            )
        ]
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行历史洪水自动预报结果查询工作流
        
        Args:
            state: 智能体状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始执行历史洪水自动预报结果查询工作流")
        
        registry = get_tool_registry()
        results = {}
        
        # 从状态中提取参数
        params = state.get('extracted_params', {})
        user_message = state.get('user_message', '')
        
        execution_results = []
        
        try:
            # 步骤1: 解析会话参数 - 提取预报对象和降雨大概起止时间
            logger.info("执行步骤1: 解析会话参数")
            parsed_params = self._parse_session_params(user_message, params)
            results['parsed_params'] = parsed_params
            results['forecast_target'] = parsed_params.get('forecast_target', {})
            results['rain_start_time'] = parsed_params.get('rain_start_time', '')
            results['rain_end_time'] = parsed_params.get('rain_end_time', '')
            
            execution_results.append({
                'step_id': 1,
                'step_name': '解析会话参数',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': parsed_params,
                'error': None
            })
            
            logger.info(f"解析到预报对象: {results['forecast_target']}")
            logger.info(f"解析到降雨时间范围: {results['rain_start_time']} - {results['rain_end_time']}")
            
            # 步骤2: 获取历史面雨量过程
            logger.info("执行步骤2: 获取历史面雨量过程")
            import time
            start_time = time.time()
            
            rain_result = await registry.execute(
                "forecast_rain_ecmwf_avg",
                st=results['rain_start_time'],
                ed=results['rain_end_time']
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 2,
                'step_name': '获取历史面雨量过程',
                'tool_name': 'forecast_rain_ecmwf_avg',
                'success': rain_result.success,
                'execution_time_ms': execution_time_ms,
                'data': rain_result.data if rain_result.success else None,
                'error': rain_result.error if not rain_result.success else None
            }
            execution_results.append(step_result)
            
            if not rain_result.success:
                logger.error(f"获取历史面雨量过程失败: {rain_result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"获取历史面雨量过程失败: {rain_result.error}",
                    "next_action": "respond"
                }
            
            results['rain_process'] = rain_result.data
            
            # 步骤3: 获取具体降雨起止时间
            logger.info("执行步骤3: 获取具体降雨起止时间")
            exact_rain_time = self._analyze_rain_time(rain_result.data)
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
            
            logger.info(f"分析得到具体降雨时间: {exact_rain_time}")
            
            # 步骤4: 获取历史洪水自动预报方案ID
            logger.info("执行步骤4: 获取历史洪水自动预报方案ID")
            start_time = time.time()
            
            history_list_result = await registry.execute("get_history_autoforcast_list")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 4,
                'step_name': '获取历史洪水自动预报方案ID',
                'tool_name': 'get_history_autoforcast_list',
                'success': history_list_result.success,
                'execution_time_ms': execution_time_ms,
                'data': history_list_result.data if history_list_result.success else None,
                'error': history_list_result.error if not history_list_result.success else None
            }
            execution_results.append(step_result)
            
            if not history_list_result.success:
                logger.error(f"获取历史自动预报方案清单失败: {history_list_result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"获取历史自动预报方案清单失败: {history_list_result.error}",
                    "next_action": "respond"
                }
            
            # 从清单中找到匹配的方案ID
            history_plan_id = self._find_matching_plan_id(
                history_list_result.data, 
                exact_rain_time.get('end_time', '')
            )
            results['history_plan_id'] = history_plan_id
            
            logger.info(f"找到匹配的历史预报方案ID: {history_plan_id}")
            
            # 步骤5: 获取历史洪水自动预报结果
            logger.info("执行步骤5: 获取历史洪水自动预报结果")
            start_time = time.time()
            
            forecast_result = await registry.execute(
                "get_tjdata_result",
                plan_code=history_plan_id
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 5,
                'step_name': '获取历史洪水自动预报结果',
                'tool_name': 'get_tjdata_result',
                'success': forecast_result.success,
                'execution_time_ms': execution_time_ms,
                'data': forecast_result.data if forecast_result.success else None,
                'error': forecast_result.error if not forecast_result.success else None
            }
            execution_results.append(step_result)
            
            if not forecast_result.success:
                logger.error(f"获取历史洪水自动预报结果失败: {forecast_result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"获取历史洪水自动预报结果失败: {forecast_result.error}",
                    "next_action": "respond"
                }
            
            results['history_forecast_result'] = forecast_result.data
            
            # 步骤6: 结果信息提取整理
            logger.info("执行步骤6: 结果信息提取整理")
            extracted_result = self._extract_forecast_result(
                results['forecast_target'],
                forecast_result.data
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
            template = self._select_template(results['forecast_target'])
            
            page_result = await registry.execute(
                "generate_report_page",
                report_type="history_forecast",
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
            
            logger.info("历史洪水自动预报结果查询工作流执行完成")
            
            return {
                "execution_results": execution_results,
                "workflow_results": results,
                "output_type": self.output_type,
                "generated_page_url": results.get('report_page_url'),
                "forecast_target": results['forecast_target'],
                "history_plan_id": history_plan_id,
                "extracted_result": extracted_result,
                "next_action": "respond"
            }
            
        except Exception as e:
            logger.error(f"历史洪水自动预报结果查询工作流执行异常: {e}")
            return {
                "execution_results": execution_results,
                "error": str(e),
                "next_action": "respond"
            }
    
    def _parse_session_params(self, user_message: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析会话参数，提取预报对象和降雨大概起止时间
        
        Args:
            user_message: 用户消息
            params: 提取的参数
            
        Returns:
            解析后的参数
        """
        result = {
            "forecast_target": {
                "type": "basin",
                "name": "全流域",
                "id": None
            },
            "rain_start_time": "",
            "rain_end_time": ""
        }
        
        # 解析预报对象
        if "水库" in user_message:
            result["forecast_target"]["type"] = "reservoir"
            if params.get("reservoir_name"):
                result["forecast_target"]["name"] = params.get("reservoir_name")
                result["forecast_target"]["id"] = params.get("reservoir_id")
        elif "站" in user_message and "蓄滞洪" not in user_message:
            result["forecast_target"]["type"] = "station"
            if params.get("station_name"):
                result["forecast_target"]["name"] = params.get("station_name")
                result["forecast_target"]["id"] = params.get("station_id")
        elif "蓄滞洪区" in user_message:
            result["forecast_target"]["type"] = "detention_basin"
            if params.get("detention_name"):
                result["forecast_target"]["name"] = params.get("detention_name")
                result["forecast_target"]["id"] = params.get("detention_id")
        
        # 解析时间范围（前后增加几天余量）
        # 如果用户提供了具体时间，使用提供的时间
        if params.get("start_time") and params.get("end_time"):
            # 解析时间并前后各加3天余量
            try:
                st = datetime.fromisoformat(params.get("start_time").replace("Z", "+00:00"))
                ed = datetime.fromisoformat(params.get("end_time").replace("Z", "+00:00"))
                result["rain_start_time"] = (st - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
                result["rain_end_time"] = (ed + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            except:
                # 如果解析失败，使用默认时间范围
                now = datetime.now()
                result["rain_start_time"] = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
                result["rain_end_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
        else:
            # 根据用户消息中的时间描述推断时间范围
            now = datetime.now()
            if "上周" in user_message:
                result["rain_start_time"] = (now - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
                result["rain_end_time"] = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
            elif "今年汛期" in user_message or "7月" in user_message:
                # 汛期通常是6-9月
                year = now.year
                result["rain_start_time"] = f"{year}-06-01 00:00:00"
                result["rain_end_time"] = f"{year}-09-30 23:59:59"
            else:
                # 默认查询最近30天
                result["rain_start_time"] = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
                result["rain_end_time"] = now.strftime("%Y-%m-%d %H:%M:%S")
        
        return result
    
    def _analyze_rain_time(self, rain_data: Any) -> Dict[str, str]:
        """
        分析降雨过程数据，获取具体降雨起止时间
        通过掐头去尾，去掉主要降雨时段前后零星的少量降雨
        
        Args:
            rain_data: 降雨过程数据
            
        Returns:
            具体降雨起止时间
        """
        result = {
            "start_time": "",
            "end_time": ""
        }
        
        if not rain_data:
            return result
        
        try:
            # 假设rain_data是时间序列数据，格式为 [{time: value}, ...]
            # 找到降雨量大于阈值的时间段
            threshold = 0.5  # 降雨量阈值（mm/h）
            
            if isinstance(rain_data, list):
                rain_times = []
                for item in rain_data:
                    if isinstance(item, dict):
                        time_val = item.get("time") or item.get("TM")
                        rain_val = item.get("value") or item.get("DRP") or 0
                        if rain_val and float(rain_val) > threshold:
                            rain_times.append(time_val)
                
                if rain_times:
                    result["start_time"] = rain_times[0]
                    result["end_time"] = rain_times[-1]
            elif isinstance(rain_data, dict):
                # 如果是字典格式 {time: value}
                rain_times = []
                for time_key, rain_val in rain_data.items():
                    if rain_val and float(rain_val) > threshold:
                        rain_times.append(time_key)
                
                if rain_times:
                    rain_times.sort()
                    result["start_time"] = rain_times[0]
                    result["end_time"] = rain_times[-1]
        except Exception as e:
            logger.warning(f"分析降雨时间失败: {e}")
        
        return result
    
    def _find_matching_plan_id(self, plan_list: Any, rain_end_time: str) -> str:
        """
        从历史自动预报方案清单中找到匹配的方案ID
        寻找与降雨结束时间最接近且超过的预报开始时间对应的方案ID
        
        Args:
            plan_list: 历史预报方案清单
            rain_end_time: 降雨结束时间
            
        Returns:
            匹配的方案ID
        """
        if not plan_list:
            return ""
        
        try:
            # 解析降雨结束时间
            if rain_end_time:
                target_time = datetime.strptime(rain_end_time, "%Y-%m-%d %H:%M:%S")
            else:
                target_time = datetime.now()
            
            best_plan_id = ""
            min_diff = float('inf')
            
            if isinstance(plan_list, list):
                for plan in plan_list:
                    if isinstance(plan, dict):
                        plan_id = plan.get("planId") or plan.get("plan_id") or plan.get("id")
                        forecast_start = plan.get("forecastStart") or plan.get("start_time")
                        
                        if forecast_start:
                            try:
                                plan_time = datetime.strptime(forecast_start, "%Y-%m-%d %H:%M:%S")
                                # 找到超过降雨结束时间且差距最小的方案
                                if plan_time >= target_time:
                                    diff = (plan_time - target_time).total_seconds()
                                    if diff < min_diff:
                                        min_diff = diff
                                        best_plan_id = str(plan_id)
                            except:
                                continue
                
                # 如果没找到超过的，取最接近的
                if not best_plan_id and plan_list:
                    best_plan_id = str(plan_list[0].get("planId") or plan_list[0].get("plan_id") or plan_list[0].get("id") or "")
            
            return best_plan_id
        except Exception as e:
            logger.warning(f"查找匹配方案ID失败: {e}")
            return ""
    
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
            extracted["summary"] = f"全流域历史洪水自动预报结果"
            extracted["data"] = forecast_data
            
        elif target_type == "reservoir":
            reservoir_data = self._extract_reservoir_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}历史洪水预报结果"
            extracted["data"] = reservoir_data
            
        elif target_type == "station":
            station_data = self._extract_station_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}历史洪水预报结果"
            extracted["data"] = station_data
            
        elif target_type == "detention_basin":
            detention_data = self._extract_detention_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}历史洪水预报结果"
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
        全流域预报结果采用web模板1，单目标预报结果采用web模板2
        
        Args:
            forecast_target: 预报对象
            
        Returns:
            模板名称
        """
        target_type = forecast_target.get("type", "basin")
        
        if target_type == "basin":
            return "web_template_1"  # 全流域预报结果模板
        else:
            return "res_module"  # 单目标预报结果模板


# 自动注册工作流
_history_auto_forecast_workflow = GetHistoryAutoForecastResultWorkflow()
register_workflow(_history_auto_forecast_workflow)
