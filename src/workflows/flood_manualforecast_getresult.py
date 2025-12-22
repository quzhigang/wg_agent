"""
进行洪水人工预报并查询结果工作流
根据需求新建人工预报方案并计算，然后查询该方案洪水结果
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ..config.logging_config import get_logger
from ..tools.registry import get_tool_registry
from .base import BaseWorkflow, WorkflowStep, WorkflowStatus
from .registry import register_workflow

logger = get_logger(__name__)


class FloodManualForecastGetResultWorkflow(BaseWorkflow):
    """
    进行洪水人工预报并查询结果工作流
    
    触发场景：当用户询问流域、水库或水文站的未来洪水预报情况，且明确指明具体的降雨条件
    (如未来降雨100mm)，或直接指明进行一次新的人工预报时，或指明对历时某场降雨洪水进行预报时。
    
    包含以下步骤：
    1. 解析会话参数 - 提取预报对象、降雨时间、预报时间、降雨条件描述
    2. 获取历史面雨量过程 - 调用forecast_rain_ecmwf_avg工具
    3. 获取具体降雨起止时间 - 分析降雨过程数据
    4. 新建人工预报方案 - 调用model_plan_add工具
    5. 解析指定降雨过程 - 调用model_rain_pattern_detail工具
    6. 预报方案降雨设置 - 调用model_rain_area_add_ecmwf或model_rain_area_add_manual工具
    7. 预报方案边界条件设置 - 调用change_boundry工具
    8. 计算该人工预报方案 - 调用model_plan_calc工具
    9. 监视人工预报方案计算状态 - 每5秒调用model_plan_detail工具
    10. 获取该人工预报方案结果 - 调用get_tjdata_result工具
    11. 结果信息提取整理 - 提取主要预报结果数据
    12. 采用合适的Web页面模板进行结果输出
    """
    
    @property
    def name(self) -> str:
        return "flood_manualforecast_getresult"
    
    @property
    def description(self) -> str:
        return "进行洪水人工预报并查询结果工作流，根据需求新建人工预报方案并计算，然后查询该方案洪水结果"
    
    @property
    def trigger_intents(self) -> List[str]:
        return [
            "manual_flood_forecast",       # 人工洪水预报
            "new_manual_forecast",         # 新建人工预报
            "custom_rain_forecast",        # 自定义降雨预报
            "history_rain_forecast"        # 历史降雨预报
        ]
    
    @property
    def trigger_keywords(self) -> List[str]:
        """
        触发关键词 - 基于文档对话示例
        注意：此工作流用于进行人工预报（需要指定降雨条件或历史降雨）
        """
        return [
            # 明确进行人工预报的关键词（对话示例）
            "进行一次人工预报",
            "新建一个人工预报方案",
            "人工预报",
            # 指定降雨条件的关键词
            "假设未来降雨",
            "如果未来降雨",
            "未来降雨",
            "假设降雨",
            "指定降雨",
            # 历史降雨预报的关键词
            "对那场降雨进行洪水预报",
            "对降雨进行洪水预报",
            "历史降雨预报",
            "那场降雨",
            # 降雨量相关表达
            "降雨100mm",
            "降雨200mm",
            "降雨量",
            "mm降雨"
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
                description="从用户会话中提取预报对象、降雨大概起止时间、预报起止时间、降雨条件描述",
                tool_name=None,
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
                output_key="history_rain_process"
            ),
            WorkflowStep(
                step_id=3,
                name="获取具体降雨起止时间",
                description="通过分析输入的逐小时降雨过程数据，获取本场降雨的具体开始和结束时间",
                tool_name=None,
                tool_args_template=None,
                depends_on=[2],
                is_async=False,
                output_key="rain_time_range"
            ),
            WorkflowStep(
                step_id=4,
                name="新建人工预报方案",
                description="调用model_plan_add工具新建人工预报方案",
                tool_name="model_plan_add",
                tool_args_template={
                    "plan_name": "$plan_name",
                    "business_code": "flood_forecast_wg",
                    "business_name": "卫共流域洪水预报应用模型",
                    "start_time": "$forecast_start_time",
                    "end_time": "$forecast_end_time",
                    "plan_desc": "$plan_desc"
                },
                depends_on=[3],
                is_async=False,
                output_key="plan_add_result"
            ),
            WorkflowStep(
                step_id=5,
                name="解析指定降雨过程",
                description="调用model_rain_pattern_detail工具获取雨型，用于将降雨总量分解到逐小时",
                tool_name="model_rain_pattern_detail",
                tool_args_template={"id": 1},  # 默认使用ID为1的雨型
                depends_on=[1],
                is_async=False,
                output_key="rain_pattern"
            ),
            WorkflowStep(
                step_id=6,
                name="预报方案降雨设置",
                description="根据降雨条件调用model_rain_area_add_ecmwf或model_rain_area_add_manual工具",
                tool_name="model_rain_area_add_ecmwf",  # 默认工具，实际执行时动态选择
                tool_args_template={"plan_code": "$plan_code"},
                depends_on=[4, 5],
                is_async=False,
                output_key="rain_setting_result"
            ),
            WorkflowStep(
                step_id=7,
                name="预报方案边界条件设置",
                description="调用change_boundry工具设置边界条件为降雨计算洪水",
                tool_name="change_boundry",
                tool_args_template={"plan_code": "$plan_code", "bnd_type": "rf_model"},
                depends_on=[6],
                is_async=False,
                output_key="boundry_result"
            ),
            WorkflowStep(
                step_id=8,
                name="计算该人工预报方案",
                description="调用model_plan_calc工具启动方案计算",
                tool_name="model_plan_calc",
                tool_args_template={"plan_code": "$plan_code"},
                depends_on=[7],
                is_async=True,
                output_key="calc_result"
            ),
            WorkflowStep(
                step_id=9,
                name="监视人工预报方案计算状态",
                description="每5秒调用model_plan_detail工具查询计算状态",
                tool_name="model_plan_detail",
                tool_args_template={"plan_code": "$plan_code"},
                depends_on=[8],
                is_async=False,
                output_key="plan_detail"
            ),
            WorkflowStep(
                step_id=10,
                name="获取该人工预报方案结果",
                description="调用get_tjdata_result工具获取预报方案结果",
                tool_name="get_tjdata_result",
                tool_args_template={"plan_code": "$plan_code"},
                depends_on=[9],
                is_async=False,
                output_key="forecast_result"
            ),
            WorkflowStep(
                step_id=11,
                name="结果信息提取整理",
                description="根据预报对象提取全流域或单一目标主要预报结果数据",
                tool_name=None,
                tool_args_template=None,
                depends_on=[10],
                is_async=False,
                output_key="extracted_result"
            ),
            WorkflowStep(
                step_id=12,
                name="采用合适的Web页面模板进行结果输出",
                description="全流域预报结果采用web模板1，单目标预报结果采用web模板2",
                tool_name="generate_report_page",
                tool_args_template={
                    "report_type": "manual_forecast",
                    "template": "$template_name",
                    "data": "$extracted_result"
                },
                depends_on=[11],
                is_async=False,
                output_key="report_page_url"
            )
        ]
    
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行进行洪水人工预报并查询结果工作流
        
        Args:
            state: 智能体状态
            
        Returns:
            更新后的状态
        """
        logger.info("开始执行进行洪水人工预报并查询结果工作流")
        
        registry = get_tool_registry()
        results = {}
        
        # 从状态中提取参数
        params = state.get('extracted_params', {})
        user_message = state.get('user_message', '')
        
        execution_results = []
        
        try:
            import time
            
            # 步骤1: 解析会话参数
            logger.info("执行步骤1: 解析会话参数")
            session_params = self._parse_session_params(user_message, params)
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
            
            logger.info(f"解析到会话参数: {session_params}")
            
            # 判断是否需要获取历史降雨数据
            # 如果用户指定的是未来时间，则跳过步骤2和3
            is_future_forecast = session_params.get('is_future_forecast', True)
            rain_start_time = session_params.get('rain_start_time')
            rain_end_time = session_params.get('rain_end_time')
            forecast_start_time = session_params.get('forecast_start_time')
            forecast_end_time = session_params.get('forecast_end_time')
            
            if not is_future_forecast and rain_start_time and rain_end_time:
                # 步骤2: 获取历史面雨量过程
                logger.info("执行步骤2: 获取历史面雨量过程")
                start_time = time.time()
                
                result = await registry.execute(
                    "forecast_rain_ecmwf_avg",
                    st=rain_start_time,
                    ed=rain_end_time
                )
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                execution_results.append({
                    'step_id': 2,
                    'step_name': '获取历史面雨量过程',
                    'tool_name': 'forecast_rain_ecmwf_avg',
                    'success': result.success,
                    'execution_time_ms': execution_time_ms,
                    'data': result.data if result.success else None,
                    'error': result.error if not result.success else None
                })
                
                if result.success:
                    results['history_rain_process'] = result.data
                    
                    # 步骤3: 获取具体降雨起止时间
                    logger.info("执行步骤3: 获取具体降雨起止时间")
                    rain_time_range = self._analyze_rain_time_range(result.data)
                    results['rain_time_range'] = rain_time_range
                    
                    execution_results.append({
                        'step_id': 3,
                        'step_name': '获取具体降雨起止时间',
                        'tool_name': None,
                        'success': True,
                        'execution_time_ms': 0,
                        'data': rain_time_range,
                        'error': None
                    })
                    
                    # 更新预报起止时间
                    if rain_time_range.get('rain_start'):
                        forecast_start_time = rain_time_range['rain_start']
                    if rain_time_range.get('forecast_end'):
                        forecast_end_time = rain_time_range['forecast_end']
                else:
                    logger.warning(f"获取历史面雨量过程失败: {result.error}，使用默认预报时间")
            else:
                # 未来预报，跳过步骤2和3
                logger.info("未来预报场景，跳过步骤2和3")
                execution_results.append({
                    'step_id': 2,
                    'step_name': '获取历史面雨量过程',
                    'tool_name': None,
                    'success': True,
                    'execution_time_ms': 0,
                    'data': {'skipped': True, 'reason': '未来预报场景不需要历史降雨数据'},
                    'error': None
                })
                execution_results.append({
                    'step_id': 3,
                    'step_name': '获取具体降雨起止时间',
                    'tool_name': None,
                    'success': True,
                    'execution_time_ms': 0,
                    'data': {'skipped': True, 'reason': '未来预报场景使用默认预报时间'},
                    'error': None
                })
            
            # 步骤4: 新建人工预报方案
            logger.info("执行步骤4: 新建人工预报方案")
            start_time = time.time()
            
            # 生成方案名称和描述
            plan_name = self._generate_plan_name(session_params)
            plan_desc = self._generate_plan_desc(session_params)
            
            result = await registry.execute(
                "model_plan_add",
                plan_name=plan_name,
                business_code="flood_forecast_wg",
                business_name="卫共流域洪水预报应用模型",
                start_time=forecast_start_time,
                end_time=forecast_end_time,
                plan_desc=plan_desc
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            execution_results.append({
                'step_id': 4,
                'step_name': '新建人工预报方案',
                'tool_name': 'model_plan_add',
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            })
            
            if not result.success:
                logger.error(f"新建人工预报方案失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"新建人工预报方案失败: {result.error}",
                    "next_action": "respond"
                }
            
            # 提取方案ID
            plan_code = None
            if isinstance(result.data, dict):
                plan_code = result.data.get('data')
            results['plan_add_result'] = result.data
            results['plan_code'] = plan_code
            logger.info(f"创建方案成功，方案ID: {plan_code}")
            
            # 步骤5: 解析指定降雨过程
            logger.info("执行步骤5: 解析指定降雨过程")
            start_time = time.time()
            
            rain_condition = session_params.get('rain_condition', '')
            total_rainfall = session_params.get('total_rainfall')
            hourly_rain_process = None
            
            if total_rainfall:
                # 需要获取雨型来分解降雨
                result = await registry.execute("model_rain_pattern_detail", id=1)
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                if result.success and result.data:
                    rain_pattern = result.data
                    # 根据雨型分解降雨总量到逐小时
                    hourly_rain_process = self._distribute_rainfall_by_pattern(
                        total_rainfall, rain_pattern, forecast_start_time
                    )
                    results['rain_pattern'] = rain_pattern
                    results['hourly_rain_process'] = hourly_rain_process
                
                execution_results.append({
                    'step_id': 5,
                    'step_name': '解析指定降雨过程',
                    'tool_name': 'model_rain_pattern_detail',
                    'success': result.success,
                    'execution_time_ms': execution_time_ms,
                    'data': {'rain_pattern': result.data, 'hourly_rain_process': hourly_rain_process},
                    'error': result.error if not result.success else None
                })
            else:
                # 无指定降雨总量，输出为null
                execution_results.append({
                    'step_id': 5,
                    'step_name': '解析指定降雨过程',
                    'tool_name': None,
                    'success': True,
                    'execution_time_ms': 0,
                    'data': {'hourly_rain_process': None, 'reason': '未指定降雨总量'},
                    'error': None
                })
            
            # 步骤6: 预报方案降雨设置
            logger.info("执行步骤6: 预报方案降雨设置")
            start_time = time.time()
            
            if hourly_rain_process:
                # 使用手动设置降雨
                drp_json = json.dumps(hourly_rain_process)
                result = await registry.execute(
                    "model_rain_area_add_manual",
                    plan_code=plan_code,
                    drp_json=drp_json,
                    source="2"  # 指定降雨
                )
                tool_used = "model_rain_area_add_manual"
            else:
                # 使用格网预报降雨
                result = await registry.execute(
                    "model_rain_area_add_ecmwf",
                    plan_code=plan_code
                )
                tool_used = "model_rain_area_add_ecmwf"
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            execution_results.append({
                'step_id': 6,
                'step_name': '预报方案降雨设置',
                'tool_name': tool_used,
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            })
            
            if not result.success:
                logger.error(f"预报方案降雨设置失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"预报方案降雨设置失败: {result.error}",
                    "next_action": "respond"
                }
            
            results['rain_setting_result'] = result.data
            
            # 步骤7: 预报方案边界条件设置
            logger.info("执行步骤7: 预报方案边界条件设置")
            start_time = time.time()
            
            result = await registry.execute(
                "change_boundry",
                plan_code=plan_code,
                bnd_type="rf_model"
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            execution_results.append({
                'step_id': 7,
                'step_name': '预报方案边界条件设置',
                'tool_name': 'change_boundry',
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            })
            
            if not result.success:
                logger.error(f"预报方案边界条件设置失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"预报方案边界条件设置失败: {result.error}",
                    "next_action": "respond"
                }
            
            results['boundry_result'] = result.data
            
            # 步骤8: 计算该人工预报方案
            logger.info("执行步骤8: 计算该人工预报方案")
            start_time = time.time()
            
            result = await registry.execute("model_plan_calc", plan_code=plan_code)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            execution_results.append({
                'step_id': 8,
                'step_name': '计算该人工预报方案',
                'tool_name': 'model_plan_calc',
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            })
            
            if not result.success:
                logger.error(f"启动人工预报计算失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"启动人工预报计算失败: {result.error}",
                    "next_action": "respond"
                }
            
            results['calc_result'] = result.data
            
            # 步骤9: 监视人工预报方案计算状态
            logger.info("执行步骤9: 监视人工预报方案计算状态")
            
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
                detail_result = await registry.execute("model_plan_detail", plan_code=plan_code)
                
                if detail_result.success and detail_result.data:
                    detail_data = detail_result.data
                    current_state = detail_data.get('state', '')
                    
                    logger.info(f"人工预报计算进度查询 ({request_count}/{max_requests}): state={current_state}")
                    
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
                    logger.warning(f"查询人工预报进度失败: {detail_result.error}")
            
            execution_results.append({
                'step_id': 9,
                'step_name': '监视人工预报方案计算状态',
                'tool_name': 'model_plan_detail',
                'success': plan_completed,
                'execution_time_ms': request_count * 5000,
                'data': {'final_state': final_state, 'request_count': request_count},
                'error': None if plan_completed else f"计算未完成，最终状态: {final_state}"
            })
            
            if not plan_completed:
                logger.warning(f"人工预报计算未在预期时间内完成，最终状态: {final_state}")
                # 根据文档，如果超时且状态还是"待计算"或"计算错误"，直接结束流程
                if final_state in ['待计算', '计算错误']:
                    return {
                        "execution_results": execution_results,
                        "error": f"人工预报计算失败，状态: {final_state}",
                        "next_action": "respond"
                    }
            
            results['plan_detail'] = {'state': final_state, 'request_count': request_count}
            
            # 步骤10: 获取该人工预报方案结果
            logger.info("执行步骤10: 获取该人工预报方案结果")
            start_time = time.time()
            
            # 注意：根据文档，方案ID字符串参数固定采用"model_auto"
            # 但这里应该使用创建的方案ID，文档可能有误
            result = await registry.execute("get_tjdata_result", plan_code=plan_code)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            execution_results.append({
                'step_id': 10,
                'step_name': '获取该人工预报方案结果',
                'tool_name': 'get_tjdata_result',
                'success': result.success,
                'execution_time_ms': execution_time_ms,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            })
            
            if not result.success:
                logger.error(f"获取人工预报结果失败: {result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"获取人工预报结果失败: {result.error}",
                    "next_action": "respond"
                }
            
            results['forecast_result'] = result.data
            
            # 步骤11: 结果信息提取整理
            logger.info("执行步骤11: 结果信息提取整理")
            forecast_target = session_params.get('forecast_target', {'type': 'basin', 'name': '全流域'})
            extracted_result = self._extract_forecast_result(forecast_target, result.data)
            results['extracted_result'] = extracted_result
            
            execution_results.append({
                'step_id': 11,
                'step_name': '结果信息提取整理',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': extracted_result,
                'error': None
            })
            
            # 步骤12: 生成Web页面
            logger.info("执行步骤12: 采用合适的Web页面模板进行结果输出")
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
            
            execution_results.append({
                'step_id': 12,
                'step_name': '采用合适的Web页面模板进行结果输出',
                'tool_name': 'generate_report_page',
                'success': page_result.success,
                'execution_time_ms': execution_time_ms,
                'data': page_result.data if page_result.success else None,
                'error': page_result.error if not page_result.success else None
            })
            
            if page_result.success:
                results['report_page_url'] = page_result.data
            
            logger.info("进行洪水人工预报并查询结果工作流执行完成")
            
            return {
                "execution_results": execution_results,
                "workflow_results": results,
                "output_type": self.output_type,
                "generated_page_url": results.get('report_page_url'),
                "forecast_target": forecast_target,
                "extracted_result": extracted_result,
                "plan_code": plan_code,
                "next_action": "respond"
            }
            
        except Exception as e:
            logger.error(f"进行洪水人工预报并查询结果工作流执行异常: {e}")
            return {
                "execution_results": execution_results,
                "error": str(e),
                "next_action": "respond"
            }
    
    def _parse_session_params(self, user_message: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析会话参数
        
        Args:
            user_message: 用户消息
            params: 提取的参数
            
        Returns:
            会话参数字典，包含：
            - forecast_target: 预报对象
            - rain_start_time: 降雨大概起始时间
            - rain_end_time: 降雨大概结束时间
            - forecast_start_time: 预报起始时间
            - forecast_end_time: 预报结束时间
            - rain_condition: 降雨条件描述
            - total_rainfall: 降雨总量（如果指定）
            - is_future_forecast: 是否为未来预报
        """
        result = {
            "forecast_target": {"type": "basin", "name": "全流域", "id": None},
            "rain_start_time": None,
            "rain_end_time": None,
            "forecast_start_time": None,
            "forecast_end_time": None,
            "rain_condition": "",
            "total_rainfall": None,
            "is_future_forecast": True
        }
        
        # 解析预报对象
        result["forecast_target"] = self._parse_forecast_target(user_message, params)
        
        # 解析降雨条件描述
        result["rain_condition"] = user_message
        
        # 尝试提取降雨总量（例如"100mm"、"200毫米"）
        import re
        rainfall_pattern = r'(\d+(?:\.\d+)?)\s*(?:mm|毫米|MM)'
        rainfall_match = re.search(rainfall_pattern, user_message)
        if rainfall_match:
            result["total_rainfall"] = float(rainfall_match.group(1))
        
        # 判断是否为历史降雨预报
        history_keywords = ["那场降雨", "历史", "月", "日", "号"]
        is_history = any(keyword in user_message for keyword in history_keywords)
        
        # 获取当前时间
        now = datetime.now()
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        
        if is_history:
            # 历史降雨预报场景
            result["is_future_forecast"] = False
            
            # 尝试解析日期
            date_info = self._parse_date_from_message(user_message, now)
            if date_info:
                # 前后增加几天余量
                result["rain_start_time"] = (date_info['start'] - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
                result["rain_end_time"] = (date_info['end'] + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            # 未来预报场景
            result["is_future_forecast"] = True
            result["forecast_start_time"] = current_hour.strftime("%Y-%m-%d %H:%M:%S")
            result["forecast_end_time"] = (current_hour + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        
        return result
    
    def _parse_date_from_message(self, message: str, reference_date: datetime) -> Optional[Dict[str, datetime]]:
        """
        从消息中解析日期信息
        
        Args:
            message: 用户消息
            reference_date: 参考日期（当前时间）
            
        Returns:
            日期范围字典或None
        """
        import re
        
        # 尝试解析"X月X日"格式
        date_pattern1 = r'(\d{1,2})月(\d{1,2})日'
        matches1 = re.findall(date_pattern1, message)
        
        # 尝试解析"X月X日X点"格式
        datetime_pattern = r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2})[点时]'
        matches2 = re.findall(datetime_pattern, message)
        
        if matches2 and len(matches2) >= 2:
            # 有完整的起止时间
            year = reference_date.year
            start_dt = datetime(year, int(matches2[0][0]), int(matches2[0][1]), int(matches2[0][2]))
            end_dt = datetime(year, int(matches2[1][0]), int(matches2[1][1]), int(matches2[1][2]))
            return {'start': start_dt, 'end': end_dt}
        elif matches1:
            # 只有日期
            year = reference_date.year
            month = int(matches1[0][0])
            day = int(matches1[0][1])
            start_dt = datetime(year, month, day)
            end_dt = start_dt + timedelta(days=1)
            return {'start': start_dt, 'end': end_dt}
        
        return None
    
    def _parse_forecast_target(self, user_message: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析预报对象
        """
        target = {
            "type": "basin",
            "name": "全流域",
            "id": None
        }
        
        # 检查是否指定了具体的水库
        reservoir_keywords = ["水库"]
        for keyword in reservoir_keywords:
            if keyword in user_message:
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
    
    def _analyze_rain_time_range(self, rain_data: Any) -> Dict[str, Any]:
        """
        分析降雨过程数据，获取具体降雨起止时间
        
        Args:
            rain_data: 逐小时降雨过程数据
            
        Returns:
            降雨时间范围字典
        """
        result = {
            "rain_start": None,
            "rain_end": None,
            "forecast_end": None
        }
        
        if not rain_data:
            return result
        
        # 假设rain_data是时间-降雨量的字典或列表
        try:
            if isinstance(rain_data, dict):
                # 按时间排序
                sorted_times = sorted(rain_data.keys())
                rain_values = [(t, rain_data[t]) for t in sorted_times]
            elif isinstance(rain_data, list):
                rain_values = rain_data
            else:
                return result
            
            # 找出主要降雨时段（过滤掉零星降雨）
            threshold = 0.5  # 降雨阈值
            rain_start_idx = None
            rain_end_idx = None
            
            for i, (t, v) in enumerate(rain_values):
                if v > threshold:
                    if rain_start_idx is None:
                        rain_start_idx = i
                    rain_end_idx = i
            
            if rain_start_idx is not None and rain_end_idx is not None:
                result["rain_start"] = rain_values[rain_start_idx][0]
                result["rain_end"] = rain_values[rain_end_idx][0]
                
                # 预报结束时间为本场降雨结束时间+3天
                from datetime import datetime, timedelta
                rain_end_dt = datetime.strptime(result["rain_end"], "%Y-%m-%d %H:%M:%S")
                forecast_end_dt = rain_end_dt + timedelta(days=3)
                result["forecast_end"] = forecast_end_dt.strftime("%Y-%m-%d %H:%M:%S")
                
        except Exception as e:
            logger.warning(f"分析降雨时间范围失败: {e}")
        
        return result
    
    def _generate_plan_name(self, session_params: Dict[str, Any]) -> str:
        """
        生成方案名称
        """
        now = datetime.now()
        timestamp = now.strftime("%m%d%H%M")
        
        if session_params.get('total_rainfall'):
            return f"人工预报_{session_params['total_rainfall']}mm_{timestamp}"
        elif not session_params.get('is_future_forecast'):
            return f"历史降雨预报_{timestamp}"
        else:
            return f"人工预报_{timestamp}"
    
    def _generate_plan_desc(self, session_params: Dict[str, Any]) -> str:
        """
        生成方案描述
        """
        if session_params.get('total_rainfall'):
            return f"指定降雨量{session_params['total_rainfall']}mm的人工预报方案"
        elif not session_params.get('is_future_forecast'):
            return "基于历史降雨的人工预报方案"
        else:
            return "基于格网预报降雨的人工预报方案"
    
    def _distribute_rainfall_by_pattern(
        self, 
        total_rainfall: float, 
        rain_pattern: Any,
        start_time: str
    ) -> Dict[str, float]:
        """
        根据雨型将降雨总量分解到逐小时
        
        Args:
            total_rainfall: 降雨总量(mm)
            rain_pattern: 雨型数据
            start_time: 开始时间
            
        Returns:
            逐小时降雨过程字典
        """
        result = {}
        
        try:
            # 解析雨型数据
            pattern_data = rain_pattern
            if isinstance(rain_pattern, dict):
                pattern_json = rain_pattern.get('json', '[]')
                if isinstance(pattern_json, str):
                    pattern_data = json.loads(pattern_json)
                else:
                    pattern_data = pattern_json
            
            # 计算雨型总和
            if isinstance(pattern_data, list):
                pattern_sum = sum(pattern_data)
                if pattern_sum > 0:
                    # 按雨型比例分配降雨
                    start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                    for i, ratio in enumerate(pattern_data):
                        hour_time = start_dt + timedelta(hours=i)
                        hour_rainfall = (ratio / pattern_sum) * total_rainfall
                        result[hour_time.strftime("%Y-%m-%d %H:%M:%S")] = round(hour_rainfall, 2)
            
            # 如果雨型数据无效，使用均匀分布（默认24小时）
            if not result:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                hourly_rain = total_rainfall / 24
                for i in range(24):
                    hour_time = start_dt + timedelta(hours=i)
                    result[hour_time.strftime("%Y-%m-%d %H:%M:%S")] = round(hourly_rain, 2)
                    
        except Exception as e:
            logger.warning(f"分解降雨过程失败: {e}，使用均匀分布")
            # 使用均匀分布
            start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            hourly_rain = total_rainfall / 24
            for i in range(24):
                hour_time = start_dt + timedelta(hours=i)
                result[hour_time.strftime("%Y-%m-%d %H:%M:%S")] = round(hourly_rain, 2)
        
        return result
    
    def _extract_forecast_result(
        self, 
        forecast_target: Dict[str, Any], 
        forecast_data: Any
    ) -> Dict[str, Any]:
        """
        根据预报对象提取相关结果数据
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
            extracted["summary"] = f"全流域洪水人工预报结果"
            extracted["data"] = forecast_data
            
        elif target_type == "reservoir":
            reservoir_data = self._extract_reservoir_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}洪水预报结果"
            extracted["data"] = reservoir_data
            
        elif target_type == "station":
            station_data = self._extract_station_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}洪水预报结果"
            extracted["data"] = station_data
            
        elif target_type == "detention_basin":
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
        """
        target_type = forecast_target.get("type", "basin")
        
        if target_type == "basin":
            return "index"  # 全流域使用web模板1（index）
        else:
            return "res_module"  # 单目标使用web模板2（res_module）


# 自动注册工作流
_flood_manualforecast_getresult_workflow = FloodManualForecastGetResultWorkflow()
register_workflow(_flood_manualforecast_getresult_workflow)
