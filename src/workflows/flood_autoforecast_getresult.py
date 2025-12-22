"""
进行洪水自动预报并查询结果工作流
启动一次新的自动预报计算并查询本次自动预报的洪水结果
"""

import asyncio
from typing import Dict, Any, List

from ..config.logging_config import get_logger
from ..tools.registry import get_tool_registry
from .base import BaseWorkflow, WorkflowStep, WorkflowStatus
from .registry import register_workflow

logger = get_logger(__name__)


class FloodAutoForecastGetResultWorkflow(BaseWorkflow):
    """
    进行洪水自动预报并查询结果工作流
    
    触发场景：当用户询问流域、水库或水文站点、蓄滞洪区的未来洪水预报情况，
    并明确要求启动一次新的自动预报计算时，或明确要求启动一次新的预报但未指明降雨等条件时。
    
    包含以下步骤：
    1. 解析会话参数 - 提取预报对象
    2. 进行自动预报 - 调用auto_forcast工具
    3. 监视自动预报计算进度 - 每5秒调用一次model_plan_detail工具
    4. 获取最新洪水自动预报结果 - 调用get_tjdata_result工具
    5. 结果信息提取整理 - 提取主要预报结果数据
    6. 采用合适的Web页面模板进行结果输出
    """
    
    @property
    def name(self) -> str:
        return "flood_autoforecast_getresult"
    
    @property
    def description(self) -> str:
        return "进行洪水自动预报并查询结果工作流，启动一次新的自动预报计算并查询本次自动预报的洪水结果"
    
    @property
    def trigger_intents(self) -> List[str]:
        return [
            "start_auto_forecast",         # 启动自动预报
            "run_auto_forecast",           # 运行自动预报
            "new_flood_forecast"           # 新的洪水预报
        ]
    
    @property
    def trigger_keywords(self) -> List[str]:
        """
        触发关键词 - 基于文档对话示例
        注意：此工作流用于启动新的自动预报计算并查询结果
        """
        return [
            # 明确要求启动新预报的关键词（对话示例）
            "自动预报一次",
            "更新自动预报",
            "预报一下",
            # 启动/开始预报的表达
            "启动自动预报",
            "启动一次自动预报",
            "开始自动预报",
            "开始一次预报",
            "进行一次预报",
            "做一次预报",
            "执行自动预报",
            # 更新预报结果
            "重新预报",
            "刷新预报",
            "更新预报结果",
            # 新预报相关
            "新的洪水预报",
            "新一次预报"
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
                name="进行自动预报",
                description="调用auto_forcast工具创建洪水自动预报模型方案并进行计算",
                tool_name="auto_forcast",
                tool_args_template={},  # 无需输入参数
                depends_on=[1],
                is_async=True,
                output_key="auto_forcast_result"
            ),
            WorkflowStep(
                step_id=3,
                name="监视自动预报计算进度",
                description="每5秒调用一次model_plan_detail工具，方案编码固定为model_auto，当state字段值为'已完成'时进行步骤4",
                tool_name="model_plan_detail",
                tool_args_template={"plan_code": "model_auto"},
                depends_on=[2],
                is_async=False,
                output_key="plan_detail"
            ),
            WorkflowStep(
                step_id=4,
                name="获取最新洪水自动预报结果",
                description="调用get_tjdata_result工具获取自动预报方案结果，包含水库、河道断面、蓄滞洪区洪水结果",
                tool_name="get_tjdata_result",
                tool_args_template={"plan_code": "model_auto"},  # 固定采用model_auto
                depends_on=[3],
                is_async=False,
                output_key="auto_forecast_result"
            ),
            WorkflowStep(
                step_id=5,
                name="结果信息提取整理",
                description="根据预报对象提取全流域或单一目标主要预报结果数据，包括结果概括描述和结果数据",
                tool_name=None,  # 无需调用工具，由LLM处理
                tool_args_template=None,
                depends_on=[4],
                is_async=False,
                output_key="extracted_result"
            ),
            WorkflowStep(
                step_id=6,
                name="采用合适的Web页面模板进行结果输出",
                description="全流域预报结果采用web模板1，单目标预报结果采用web模板2",
                tool_name="generate_report_page",
                tool_args_template={
                    "report_type": "auto_forecast",
                    "template": "$template_name",
                    "data": "$extracted_result"
                },
                depends_on=[5],
                is_async=False,
                output_key="report_page_url"
            )
        ]
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行进行洪水自动预报并查询结果工作流
        
        Args:
            state: 智能体状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始执行进行洪水自动预报并查询结果工作流")
        
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
        
        execution_results.append({
            'step_id': 1,
            'step_name': '解析会话参数',
            'tool_name': None,
            'success': True,
            'execution_time_ms': 0,
            'data': forecast_target,
            'error': None
        })
        
        try:
            import time
            
            # 步骤2: 进行自动预报
            logger.info("执行步骤2: 进行自动预报")
            start_time = time.time()
            
            # 调用auto_forcast工具，无需参数
            result = await registry.execute("auto_forcast")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 2,
                'step_name': '进行自动预报',
                'tool_name': 'auto_forcast',
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            }
            execution_results.append(step_result)
            
            if not result.success:
                logger.error(f"启动自动预报失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"启动自动预报失败: {result.error}",
                    "next_action": "respond"
                }
            
            results['auto_forcast_result'] = result.data
            logger.info("自动预报已启动")
            
            # 步骤3: 监视自动预报计算进度
            logger.info("执行步骤3: 监视自动预报计算进度")
            
            # 获取预计计算时间
            expect_seconds = 60  # 默认60秒
            if isinstance(result.data, dict) and result.data.get('expect_seconds'):
                try:
                    expect_seconds = int(result.data.get('expect_seconds', 60))
                except (ValueError, TypeError):
                    expect_seconds = 60
            
            # 计算最大请求次数：N = expectSeconds/5 + 10
            max_requests = expect_seconds // 5 + 10
            request_count = 0
            plan_completed = False
            final_state = None
            
            while request_count < max_requests:
                request_count += 1
                
                # 等待5秒
                await asyncio.sleep(5)
                
                # 调用model_plan_detail查询状态
                detail_result = await registry.execute("model_plan_detail", plan_code="model_auto")
                
                if detail_result.success and detail_result.data:
                    detail_data = detail_result.data
                    current_state = detail_data.get('state', '')
                    
                    logger.info(f"自动预报计算进度查询 ({request_count}/{max_requests}): state={current_state}")
                    
                    if current_state == '已完成':
                        plan_completed = True
                        final_state = current_state
                        break
                    elif current_state in ['待计算', '计算错误']:
                        final_state = current_state
                        # 继续等待，直到超过最大请求次数
                    else:
                        final_state = current_state
                        # 其他状态（如"计算中"），继续等待
                else:
                    logger.warning(f"查询自动预报进度失败: {detail_result.error}")
            
            step_result = {
                'step_id': 3,
                'step_name': '监视自动预报计算进度',
                'tool_name': 'model_plan_detail',
                'success': plan_completed,
                'execution_time_ms': request_count * 5000,
                'data': {'final_state': final_state, 'request_count': request_count},
                'error': None if plan_completed else f"计算未完成，最终状态: {final_state}"
            }
            execution_results.append(step_result)
            
            if not plan_completed:
                logger.warning(f"自动预报计算未在预期时间内完成，最终状态: {final_state}")
                # 根据文档，如果超时且状态还是"待计算"或"计算错误"，直接结束流程
                if final_state in ['待计算', '计算错误']:
                    return {
                        "execution_results": execution_results,
                        "error": f"自动预报计算失败，状态: {final_state}",
                        "next_action": "respond"
                    }
            
            results['plan_detail'] = {'state': final_state, 'request_count': request_count}
            
            # 步骤4: 获取最新洪水自动预报结果
            logger.info("执行步骤4: 获取最新洪水自动预报结果")
            start_time = time.time()
            
            # 调用get_tjdata_result工具，plan_code固定为"model_auto"
            result = await registry.execute("get_tjdata_result", plan_code="model_auto")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 4,
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
            
            # 步骤5: 结果信息提取整理
            logger.info("执行步骤5: 结果信息提取整理")
            extracted_result = self._extract_forecast_result(
                forecast_target, 
                result.data
            )
            results['extracted_result'] = extracted_result
            
            execution_results.append({
                'step_id': 5,
                'step_name': '结果信息提取整理',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': extracted_result,
                'error': None
            })
            
            # 步骤6: 生成Web页面
            logger.info("执行步骤6: 采用合适的Web页面模板进行结果输出")
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
                'step_id': 6,
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
            
            logger.info("进行洪水自动预报并查询结果工作流执行完成")
            
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
            logger.error(f"进行洪水自动预报并查询结果工作流执行异常: {e}")
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
_flood_autoforecast_getresult_workflow = FloodAutoForecastGetResultWorkflow()
register_workflow(_flood_autoforecast_getresult_workflow)
