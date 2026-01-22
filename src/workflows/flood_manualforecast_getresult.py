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
    9. 获取模型预计计算时间 - 调用model_plan_detail工具获取expectSeconds
    10. 监视人工预报方案计算状态 - 每5秒调用model_plan_detail工具
    11. 获取该人工预报方案结果 - 调用get_tjdata_result工具
    12. 结果信息提取整理 - 提取主要预报结果数据
    13. 采用合适的Web页面模板进行结果输出
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
                name="获取模型预计计算时间",
                description="调用model_plan_detail工具获取expectSeconds",
                tool_name="model_plan_detail",
                tool_args_template={"plan_code": "$plan_code"},
                depends_on=[8],
                is_async=False,
                output_key="expect_seconds"
            ),
            WorkflowStep(
                step_id=10,
                name="监视人工预报方案计算状态",
                description="每5秒调用model_plan_detail工具查询计算状态",
                tool_name="model_plan_detail",
                tool_args_template={"plan_code": "$plan_code"},
                depends_on=[9],
                is_async=False,
                output_key="plan_detail"
            ),
            WorkflowStep(
                step_id=11,
                name="获取该人工预报方案结果",
                description="调用get_tjdata_result工具获取预报方案结果",
                tool_name="get_tjdata_result",
                tool_args_template={"plan_code": "$plan_code"},
                depends_on=[10],
                is_async=False,
                output_key="forecast_result"
            ),
            WorkflowStep(
                step_id=12,
                name="结果信息提取整理",
                description="根据预报对象提取全流域或单一目标主要预报结果数据",
                tool_name=None,
                tool_args_template=None,
                depends_on=[11],
                is_async=False,
                output_key="extracted_result"
            ),
            WorkflowStep(
                step_id=13,
                name="采用合适的Web页面模板进行结果输出",
                description="全流域预报结果采用web模板1，单目标预报结果采用web模板2",
                tool_name="generate_report_page",
                tool_args_template={
                    "report_type": "manual_forecast",
                    "template": "$template_name",
                    "data": "$extracted_result"
                },
                depends_on=[12],
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

            # 转换时间格式为API要求的格式 (yyyy/MM/dd HH:mm:ss)
            api_forecast_start = self._convert_time_format(forecast_start_time)
            api_forecast_end = self._convert_time_format(forecast_end_time)

            result = await registry.execute(
                "model_plan_add",
                plan_name=plan_name,
                business_code="flood_forecast_wg",
                business_name="卫共流域洪水预报应用模型",
                start_time=api_forecast_start,
                end_time=api_forecast_end,
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
                    logger.info(f"获取雨型成功，雨型ID: 1")
                    # 根据雨型分解降雨总量到逐小时
                    hourly_rain_process = self._distribute_rainfall_by_pattern(
                        total_rainfall, rain_pattern, forecast_start_time
                    )
                    results['rain_pattern'] = rain_pattern
                    results['hourly_rain_process'] = hourly_rain_process
                    logger.info(f"生成逐小时降雨过程: 共{len(hourly_rain_process)}小时，总降雨量{total_rainfall}mm")
                else:
                    logger.warning(f"获取雨型失败: {result.error}，将使用均匀分布")

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
                logger.info(f"手动设置降雨，数据点数: {len(hourly_rain_process)}，drp_json长度: {len(drp_json)}")
                logger.debug(f"drp_json内容: {drp_json[:500]}...")  # 只输出前500字符
                result = await registry.execute(
                    "model_rain_area_add_manual",
                    plan_code=plan_code,
                    bsn_code="avg",  # 添加全流域平均参数
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

            # 输出步骤8返回的数据，便于调试
            logger.info(f"步骤8返回数据: {result.data}")

            results['calc_result'] = result.data

            # 步骤9: 获取模型预计计算时间
            logger.info("执行步骤9: 获取模型预计计算时间")
            start_time = time.time()

            # 调用model_plan_detail获取expectSeconds
            detail_result = await registry.execute("model_plan_detail", plan_code=plan_code)

            execution_time_ms = int((time.time() - start_time) * 1000)

            expect_seconds = 60  # 默认60秒
            if detail_result.success and detail_result.data:
                detail_data = detail_result.data
                # model_plan_detail工具返回的data已经是API响应中的data字段
                # 数据结构: {"planCode": "...", "expectSeconds": 50, ...}
                if isinstance(detail_data, dict) and 'expectSeconds' in detail_data:
                    try:
                        expect_seconds = int(detail_data['expectSeconds'])
                    except (ValueError, TypeError):
                        pass

            logger.info(f"模型预计计算时间: {expect_seconds}秒")

            execution_results.append({
                'step_id': 9,
                'step_name': '获取模型预计计算时间',
                'tool_name': 'model_plan_detail',
                'success': detail_result.success,
                'execution_time_ms': execution_time_ms,
                'data': {'expectSeconds': expect_seconds},
                'error': detail_result.error if not detail_result.success else None
            })

            results['expect_seconds'] = expect_seconds

            # 步骤10: 监视人工预报方案计算状态
            logger.info("执行步骤10: 监视人工预报方案计算状态")

            # 计算最大请求次数：N = expectSeconds/5 + 30
            max_requests = expect_seconds // 5 + 30
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
                'step_id': 10,
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

            # 步骤11: 获取该人工预报方案结果
            logger.info("执行步骤11: 获取该人工预报方案结果")
            start_time = time.time()

            # 注意：根据文档，方案ID字符串参数固定采用"model_auto"
            # 但这里应该使用创建的方案ID，文档可能有误
            result = await registry.execute("get_tjdata_result", plan_code=plan_code)

            execution_time_ms = int((time.time() - start_time) * 1000)

            execution_results.append({
                'step_id': 11,
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

            # 步骤12: 结果信息提取整理
            logger.info("执行步骤12: 结果信息提取整理")
            forecast_target = session_params.get('forecast_target', {'type': 'basin', 'name': '全流域'})
            extracted_result = self._extract_forecast_result(forecast_target, result.data)
            results['extracted_result'] = extracted_result

            execution_results.append({
                'step_id': 12,
                'step_name': '结果信息提取整理',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': extracted_result,
                'error': None
            })

            # 步骤13: 生成Web页面
            logger.info("执行步骤13: 结果合成和前端表现")
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
                'step_id': 13,
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
    
    def _parse_session_params(self, user_message: str, params: Dict[str, Any], entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析会话参数

        Args:
            user_message: 用户消息
            params: 提取的参数
            entities: 意图分析提取的实体

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
        result["forecast_target"] = self._parse_forecast_target(user_message, params, entities)
        
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
                # 设置初始预报时间（会在步骤3根据实际降雨数据更新）
                result["forecast_start_time"] = date_info['start'].strftime("%Y-%m-%d %H:%M:%S")
                result["forecast_end_time"] = (date_info['end'] + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            else:
                # 无法解析日期时，使用当前时间作为默认值
                result["forecast_start_time"] = current_hour.strftime("%Y-%m-%d %H:%M:%S")
                result["forecast_end_time"] = (current_hour + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
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

        # 尝试解析"XXXX年X月X日"格式（完整年份）
        full_date_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
        full_matches = re.findall(full_date_pattern, message)

        if full_matches:
            # 有完整的年月日
            year = int(full_matches[0][0])
            month = int(full_matches[0][1])
            day = int(full_matches[0][2])
            start_dt = datetime(year, month, day)
            end_dt = start_dt + timedelta(days=1)
            logger.info(f"解析到完整日期: {year}年{month}月{day}日")
            return {'start': start_dt, 'end': end_dt}

        # 尝试解析"X月X日"格式（无年份，使用参考年份）
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
            # 只有日期，没有年份
            year = reference_date.year
            month = int(matches1[0][0])
            day = int(matches1[0][1])

            # 如果解析出的日期在未来，可能是指去年的日期
            try:
                parsed_date = datetime(year, month, day)
                if parsed_date > reference_date:
                    # 日期在未来，使用去年
                    year = year - 1
                    logger.info(f"日期 {month}月{day}日 在未来，调整为去年: {year}年")
            except ValueError:
                pass

            start_dt = datetime(year, month, day)
            end_dt = start_dt + timedelta(days=1)
            return {'start': start_dt, 'end': end_dt}

        return None
    
    def _parse_forecast_target(self, user_message: str, params: Dict[str, Any], entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析预报对象，支持多对象查询

        Args:
            user_message: 用户消息
            params: 提取的参数
            entities: 意图分析提取的实体

        Returns:
            预报对象信息，如果是多对象则返回 {"type": "multiple", "targets": [...]}
        """
        import re

        entities = entities or {}

        # 优先从entities中获取对象信息
        object_name = entities.get("object", "")
        object_type = entities.get("object_type", "")

        # 检查是否包含多个对象（通过"和"、"、"、","分隔）
        # 先尝试从 object_name 中解析多个对象
        multi_objects = []
        if object_name:
            # 按"和"、"、"、","分隔
            parts = re.split(r'[和、,，]', object_name)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) > 1:
                multi_objects = parts

        # 如果 object_name 没有多个对象，尝试从 user_message 中解析
        if not multi_objects:
            # 匹配常见的对象名称模式
            # 水库：XXX水库
            # 站点：XXX站、XXX水文站、XXX水位站
            # 蓄滞洪区：XXX蓄滞洪区、XXX滞洪区
            # 闸站：XXX闸、XXX拦河闸、XXX节制闸
            pattern = r'([\u4e00-\u9fa5]+(?:水库|水文站|水位站|站|蓄滞洪区|滞洪区|拦河闸|节制闸|分洪闸|进洪闸|退水闸|闸))'
            matches = re.findall(pattern, user_message)
            if len(matches) > 1:
                multi_objects = matches

        # 如果有多个对象，返回多对象结构
        if len(multi_objects) > 1:
            targets = []
            for obj_name in multi_objects:
                target = self._parse_single_target(obj_name)
                targets.append(target)
            return {
                "type": "multiple",
                "targets": targets
            }

        # 单对象或全流域
        if object_name:
            return self._parse_single_target(object_name)

        # 尝试从 user_message 中解析单个对象
        pattern = r'([\u4e00-\u9fa5]+(?:水库|水文站|水位站|站|蓄滞洪区|滞洪区|拦河闸|节制闸|分洪闸|进洪闸|退水闸|闸))'
        matches = re.findall(pattern, user_message)
        if matches:
            return self._parse_single_target(matches[0])

        # 默认返回全流域
        return {
            "type": "basin",
            "name": "全流域",
            "id": None
        }

    def _parse_single_target(self, object_name: str) -> Dict[str, Any]:
        """
        解析单个预报对象

        Args:
            object_name: 对象名称

        Returns:
            预报对象信息
        """
        target = {
            "type": "basin",
            "name": "全流域",
            "id": None
        }

        if not object_name:
            return target

        # 检查是否是水库
        if "水库" in object_name:
            target["type"] = "reservoir"
            target["name"] = object_name
        # 检查是否是蓄滞洪区
        elif "蓄滞洪区" in object_name or "滞洪区" in object_name:
            target["type"] = "detention_basin"
            target["name"] = object_name
        # 检查是否是闸站
        elif "闸" in object_name:
            target["type"] = "gate"
            target["name"] = object_name
        # 检查是否是站点
        elif "站" in object_name or "水文" in object_name or "水位" in object_name:
            target["type"] = "station"
            target["name"] = object_name
        else:
            # 无法确定类型，尝试作为站点处理
            target["type"] = "station"
            target["name"] = object_name

        return target

    def _analyze_rain_time_range(self, rain_data: Any) -> Dict[str, Any]:
        """
        分析降雨过程数据，获取具体降雨起止时间

        算法逻辑：
        1. 首先将原始数据转换为时间序列 [(time, value), ...]
        2. 计算每个时间点的3小时累积降雨量，找到最大值作为降雨核心时间
        3. 从核心时间向前搜索，当连续3小时累积降雨小于阈值(0.5mm)时，认为降雨开始
        4. 从核心时间向后搜索，当连续3小时累积降雨小于阈值(0.5mm)时，认为降雨结束

        这样可以有效排除拖沓的前期降雨和尾雨，得到主要降雨时段

        支持的数据格式：
        1. {'t': [时间数组], 'v': [值数组]} - forecast_rain_ecmwf_avg API返回格式
        2. {"data": [...], "list": [...], "records": [...]} - 嵌套数据格式
        3. {time_string: value} - 时间-降雨量字典格式
        4. [{"time": "...", "value": ...}, ...] - 列表格式
        5. [[time, value], ...] - 二维数组格式

        Args:
            rain_data: 降雨过程数据

        Returns:
            降雨时间范围字典，格式为 {"rain_start": "...", "rain_end": "...", "forecast_end": "..."}
        """
        result = {
            "rain_start": None,
            "rain_end": None,
            "forecast_end": None
        }

        if not rain_data:
            logger.warning("_analyze_rain_time_range: 降雨数据为空")
            return result

        # 记录原始数据类型用于调试
        logger.info(f"_analyze_rain_time_range: 数据类型: {type(rain_data).__name__}, 数据预览: {str(rain_data)[:500]}")

        try:
            # 提取降雨值的辅助函数
            def extract_rain_value(val):
                """从各种格式中提取降雨数值"""
                if val is None:
                    return 0.0
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    try:
                        return float(val)
                    except ValueError:
                        return 0.0
                return 0.0

            # 第一步：将各种格式的数据统一转换为时间序列 [(time_str, rain_value), ...]
            time_series = []

            if isinstance(rain_data, dict):
                # 格式1: {'t': [时间数组], 'v': [值数组]}
                # 注意：使用 in 检查键是否存在，而不是用 or 链（空列表会被跳过）
                time_array = None
                value_array = None

                for t_key in ["t", "time", "times"]:
                    if t_key in rain_data and isinstance(rain_data[t_key], list):
                        time_array = rain_data[t_key]
                        break

                for v_key in ["v", "value", "values", "p", "rain", "rainfall", "drp"]:
                    if v_key in rain_data and isinstance(rain_data[v_key], list):
                        value_array = rain_data[v_key]
                        break

                if time_array is not None and value_array is not None:
                    logger.info(f"_analyze_rain_time_range: 检测到并行数组格式: 时间数组长度={len(time_array)}, 值数组长度={len(value_array)}")
                    if len(time_array) == 0 or len(value_array) == 0:
                        logger.warning("_analyze_rain_time_range: 并行数组为空，无降雨数据")
                        return result
                    for t, v in zip(time_array, value_array):
                        time_series.append((str(t), extract_rain_value(v)))

                # 格式2: {"data": [...], "list": [...], "records": [...]}
                elif rain_data.get("data") or rain_data.get("list") or rain_data.get("records"):
                    nested_data = (rain_data.get("data") or rain_data.get("list") or
                                  rain_data.get("records") or rain_data.get("items"))
                    if nested_data and isinstance(nested_data, list):
                        logger.info(f"_analyze_rain_time_range: 检测到嵌套数据格式，递归处理")
                        return self._analyze_rain_time_range(nested_data)

                # 格式3: {time_string: value} 字典格式
                else:
                    logger.info(f"_analyze_rain_time_range: 检测到时间-值字典格式，键数量: {len(rain_data)}")
                    for time_key, rain_val in rain_data.items():
                        if time_key in ["success", "message", "code", "total", "data", "list", "t", "v", "p"]:
                            continue
                        time_series.append((str(time_key), extract_rain_value(rain_val)))

            elif isinstance(rain_data, list):
                logger.info(f"_analyze_rain_time_range: 检测到列表格式，长度: {len(rain_data)}")
                for item in rain_data:
                    if isinstance(item, dict):
                        time_val = (item.get("time") or item.get("TM") or
                                   item.get("tm") or item.get("datetime") or
                                   item.get("date") or item.get("timestamp") or item.get("t"))
                        rain_val = extract_rain_value(
                            item.get("value") or item.get("DRP") or
                            item.get("drp") or item.get("rain") or
                            item.get("rainfall") or item.get("P") or item.get("v") or 0
                        )
                        if time_val:
                            time_series.append((str(time_val), rain_val))
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        time_series.append((str(item[0]), extract_rain_value(item[1])))

            if not time_series:
                logger.warning("_analyze_rain_time_range: 未能解析出时间序列数据")
                return result

            # 按时间排序
            try:
                time_series.sort(key=lambda x: x[0])
            except:
                pass

            logger.info(f"_analyze_rain_time_range: 解析得到 {len(time_series)} 个时间点")

            # 第二步：计算每个时间点的3小时累积降雨量，找到核心时间
            window_size = 3
            threshold_3h = 0.5  # 3小时累积降雨阈值(mm)

            # 计算3小时累积降雨量
            cumulative_3h = []
            for i in range(len(time_series)):
                # 计算以当前点为中心的3小时累积（前1个 + 当前 + 后1个）
                start_idx = max(0, i - 1)
                end_idx = min(len(time_series), i + 2)
                sum_3h = sum(time_series[j][1] for j in range(start_idx, end_idx))
                cumulative_3h.append(sum_3h)

            # 找到3小时累积降雨量最大的位置作为核心时间
            if not cumulative_3h or max(cumulative_3h) == 0:
                logger.warning("_analyze_rain_time_range: 所有时间点降雨量均为0")
                return result

            core_idx = cumulative_3h.index(max(cumulative_3h))
            logger.info(f"_analyze_rain_time_range: 降雨核心时间索引={core_idx}, 时间={time_series[core_idx][0]}, 3小时累积={cumulative_3h[core_idx]:.2f}mm")

            # 第三步：从核心时间向前搜索，找到降雨开始时间
            start_idx = core_idx
            for i in range(core_idx, -1, -1):
                # 计算从i开始的3小时累积
                end_i = min(len(time_series), i + window_size)
                sum_3h = sum(time_series[j][1] for j in range(i, end_i))
                if sum_3h < threshold_3h:
                    # 找到了降雨开始前的位置，降雨开始是下一个时间点
                    start_idx = i + 1 if i + 1 < len(time_series) else i
                    break
                start_idx = i

            # 第四步：从核心时间向后搜索，找到降雨结束时间
            end_idx = core_idx
            for i in range(core_idx, len(time_series)):
                # 计算从i开始的3小时累积
                end_i = min(len(time_series), i + window_size)
                sum_3h = sum(time_series[j][1] for j in range(i, end_i))
                if sum_3h < threshold_3h:
                    # 找到了降雨结束的位置
                    end_idx = i - 1 if i > 0 else i
                    break
                end_idx = i

            # 确保索引有效
            start_idx = max(0, min(start_idx, len(time_series) - 1))
            end_idx = max(0, min(end_idx, len(time_series) - 1))

            # 确保结束时间不早于开始时间
            if end_idx < start_idx:
                end_idx = start_idx

            result["rain_start"] = time_series[start_idx][0]
            result["rain_end"] = time_series[end_idx][0]

            # 预报结束时间为本场降雨结束时间+3天
            from datetime import timedelta
            try:
                # 尝试多种时间格式解析
                rain_end_str = result["rain_end"]
                rain_end_dt = None
                for fmt in ["%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"]:
                    try:
                        rain_end_dt = datetime.strptime(rain_end_str, fmt)
                        break
                    except ValueError:
                        continue

                if rain_end_dt:
                    forecast_end_dt = rain_end_dt + timedelta(days=3)
                    result["forecast_end"] = forecast_end_dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception as e:
                logger.warning(f"_analyze_rain_time_range: 计算预报结束时间失败: {e}")

            # 计算主要降雨时段的总降雨量
            total_rain = sum(time_series[i][1] for i in range(start_idx, end_idx + 1))
            logger.info(f"_analyze_rain_time_range: 分析成功，降雨时间段: {result['rain_start']} ~ {result['rain_end']}, "
                       f"时间点数量: {end_idx - start_idx + 1}, 总降雨量: {total_rain:.2f}mm")

        except Exception as e:
            logger.warning(f"_analyze_rain_time_range: 分析降雨时间范围失败: {e}", exc_info=True)

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

    def _convert_time_format(self, time_str: str) -> str:
        """
        将时间格式从 yyyy-MM-dd HH:mm:ss 转换为 yyyy/MM/dd HH:mm:ss

        API要求时间格式为斜杠分隔

        Args:
            time_str: 输入时间字符串

        Returns:
            转换后的时间字符串
        """
        if not time_str:
            return time_str
        # 将横杠替换为斜杠
        return time_str.replace("-", "/")

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
            逐小时降雨过程字典，时间格式为 yyyy/MM/dd HH:mm:ss（API要求格式）
        """
        result = {}
        # API要求的时间格式：yyyy/MM/dd HH:mm:ss
        api_time_format = "%Y/%m/%d %H:%M:%S"

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
                        result[hour_time.strftime(api_time_format)] = round(hour_rainfall, 2)

            # 如果雨型数据无效，使用均匀分布（默认24小时）
            if not result:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                hourly_rain = total_rainfall / 24
                for i in range(24):
                    hour_time = start_dt + timedelta(hours=i)
                    result[hour_time.strftime(api_time_format)] = round(hourly_rain, 2)

        except Exception as e:
            logger.warning(f"分解降雨过程失败: {e}，使用均匀分布")
            # 使用均匀分布
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                start_dt = datetime.now().replace(minute=0, second=0, microsecond=0)
            hourly_rain = total_rainfall / 24
            for i in range(24):
                hour_time = start_dt + timedelta(hours=i)
                result[hour_time.strftime(api_time_format)] = round(hourly_rain, 2)

        return result
    
    def _extract_forecast_result(
        self,
        forecast_target: Dict[str, Any],
        forecast_data: Any
    ) -> Dict[str, Any]:
        """
        根据预报对象提取相关结果数据，支持多对象查询
        """
        if not forecast_data:
            return {
                "target": forecast_target,
                "summary": "未获取到预报数据",
                "data": {}
            }

        target_type = forecast_target.get("type", "basin")

        # 处理多对象查询
        if target_type == "multiple":
            targets = forecast_target.get("targets", [])
            if not targets:
                return {
                    "target": forecast_target,
                    "summary": "未指定预报对象",
                    "data": {}
                }

            # 提取每个对象的数据
            targets_data = []
            for target in targets:
                single_target_type = target.get("type", "basin")
                single_target_name = target.get("name", "")

                if single_target_type == "reservoir":
                    data = self._extract_reservoir_data(forecast_data, single_target_name)
                elif single_target_type == "station":
                    data = self._extract_station_data(forecast_data, single_target_name)
                elif single_target_type == "detention_basin":
                    data = self._extract_detention_data(forecast_data, single_target_name)
                elif single_target_type == "gate":
                    # 闸站数据可能在 reachsection_result 中
                    data = self._extract_station_data(forecast_data, single_target_name)
                else:
                    data = {}

                targets_data.append({
                    "name": single_target_name,
                    "type": single_target_type,
                    "data": data
                })

            target_names = [t.get("name", "") for t in targets]
            return {
                "target": forecast_target,
                "summary": f"{'、'.join(target_names)}洪水人工预报结果",
                "data": {},
                "targets": targets_data
            }

        # 单对象查询
        extracted = {
            "target": forecast_target,
            "summary": "",
            "data": {}
        }

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

        elif target_type == "gate":
            # 闸站数据可能在 reachsection_result 中
            gate_data = self._extract_station_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}洪水预报结果"
            extracted["data"] = gate_data

        return extracted

    def _normalize_name(self, name: str, name_type: str = "station") -> str:
        """
        标准化名称，去掉常见后缀以便匹配

        Args:
            name: 原始名称
            name_type: 名称类型 ("station", "reservoir", "detention", "gate")

        Returns:
            标准化后的名称

        支持的匹配方式：
        - 水文站点：修武、修武站、修武水文站、修武水位站 -> 修武
        - 水库：盘石头、盘石头水库 -> 盘石头
        - 蓄滞洪区：良相坡、良相坡蓄滞洪区、良相坡滞洪区 -> 良相坡
        - 闸站：小河口、小河口闸、小河口拦河闸、小河口节制闸 -> 小河口
        """
        if not name:
            return ""

        result = name

        if name_type == "station":
            # 水文站点：去掉"站"、"水文站"、"水位站"等后缀
            suffixes = ["水文站", "水位站", "站"]
            for suffix in suffixes:
                if result.endswith(suffix):
                    result = result[:-len(suffix)]
                    break

        elif name_type == "reservoir":
            # 水库：去掉"水库"后缀
            if result.endswith("水库"):
                result = result[:-2]

        elif name_type == "detention":
            # 蓄滞洪区：去掉"蓄滞洪区"、"滞洪区"等后缀
            suffixes = ["蓄滞洪区", "滞洪区"]
            for suffix in suffixes:
                if result.endswith(suffix):
                    result = result[:-len(suffix)]
                    break

        elif name_type == "gate":
            # 闸站：去掉"闸"、"拦河闸"、"节制闸"等后缀
            suffixes = ["拦河闸", "节制闸", "分洪闸", "进洪闸", "退水闸", "闸"]
            for suffix in suffixes:
                if result.endswith(suffix):
                    result = result[:-len(suffix)]
                    break

        return result

    def _extract_reservoir_data(self, forecast_data: Any, reservoir_name: str) -> Dict[str, Any]:
        """
        提取水库相关数据

        支持多种名称匹配方式：
        - 盘石头、盘石头水库 都能匹配到 "盘石头水库"
        """
        if isinstance(forecast_data, dict):
            # 数据结构: {'reservoir_result': {'水库名': {...}}}
            reservoir_result = forecast_data.get("reservoir_result", {})
            if isinstance(reservoir_result, dict):
                # 标准化水库名称
                reservoir_name_clean = self._normalize_name(reservoir_name, "reservoir")

                # 直接按名称查找
                if reservoir_name in reservoir_result:
                    return reservoir_result[reservoir_name]
                if reservoir_name_clean in reservoir_result:
                    return reservoir_result[reservoir_name_clean]

                # 模糊匹配
                for name, data in reservoir_result.items():
                    name_clean = self._normalize_name(name, "reservoir")
                    # 标准化后完全匹配
                    if reservoir_name_clean == name_clean:
                        return data
                    # 包含匹配
                    if reservoir_name_clean in name or name in reservoir_name_clean:
                        return data
                    if reservoir_name in name or name in reservoir_name:
                        return data
                    # 检查 ResName 字段
                    if isinstance(data, dict):
                        res_name = data.get("ResName", "")
                        res_name_clean = self._normalize_name(res_name, "reservoir")
                        if reservoir_name_clean == res_name_clean:
                            return data
                        if reservoir_name_clean in res_name or res_name in reservoir_name_clean:
                            return data

        return {"message": f"未找到{reservoir_name}的预报数据"}

    def _extract_station_data(self, forecast_data: Any, station_name: str) -> Dict[str, Any]:
        """
        提取站点/河道断面相关数据

        API返回的数据结构中，河道断面数据在 reachsection_result 字段，格式：
        {
            "reachsection_result": {
                "修武": {
                    "Stcd": "31004900",
                    "SectionName": "修武",
                    "Max_Qischarge": 22.1,
                    "Max_Level": 79.23,
                    ...
                },
                ...
            }
        }

        支持多种名称匹配方式：
        - 修武、修武站、修武水文站、修武水位站 都能匹配到 "修武"
        """
        if isinstance(forecast_data, dict):
            # 河道断面结果在 reachsection_result 字段
            reachsection_result = forecast_data.get("reachsection_result", {})
            if isinstance(reachsection_result, dict) and reachsection_result:
                # 标准化站点名称
                station_name_clean = self._normalize_name(station_name, "station")

                # 直接按名称查找
                if station_name in reachsection_result:
                    return reachsection_result[station_name]
                if station_name_clean in reachsection_result:
                    return reachsection_result[station_name_clean]

                # 模糊匹配
                for name, data in reachsection_result.items():
                    name_clean = self._normalize_name(name, "station")
                    # 标准化后完全匹配
                    if station_name_clean == name_clean:
                        return data
                    # 包含匹配
                    if station_name_clean in name or name in station_name_clean:
                        return data
                    if station_name in name or name in station_name:
                        return data
                    # 检查 SectionName 字段
                    if isinstance(data, dict):
                        section_name = data.get("SectionName", "")
                        section_name_clean = self._normalize_name(section_name, "station")
                        if station_name_clean == section_name_clean:
                            return data
                        if station_name_clean in section_name or section_name in station_name_clean:
                            return data

        return {"message": f"未找到{station_name}的预报数据"}

    def _extract_detention_data(self, forecast_data: Any, detention_name: str) -> Dict[str, Any]:
        """
        提取蓄滞洪区相关数据

        API返回的数据结构中，蓄滞洪区数据在 floodblq_result 字段，格式：
        {
            "floodblq_result": {
                "良相坡": {
                    "Stcd": "LXP_ZHQ",
                    "Name": "良相坡",
                    "Xzhq_State": "未启用",
                    ...
                },
                ...
            }
        }

        支持多种名称匹配方式：
        - 良相坡、良相坡蓄滞洪区、良相坡滞洪区 都能匹配到 "良相坡"
        """
        if isinstance(forecast_data, dict):
            # 蓄滞洪区结果在 floodblq_result 字段
            floodblq_result = forecast_data.get("floodblq_result", {})
            if isinstance(floodblq_result, dict):
                # 标准化蓄滞洪区名称
                detention_name_clean = self._normalize_name(detention_name, "detention")

                # 直接按名称查找
                if detention_name in floodblq_result:
                    return floodblq_result[detention_name]
                if detention_name_clean in floodblq_result:
                    return floodblq_result[detention_name_clean]

                # 模糊匹配
                for name, data in floodblq_result.items():
                    name_clean = self._normalize_name(name, "detention")
                    # 标准化后完全匹配
                    if detention_name_clean == name_clean:
                        return data
                    # 包含匹配
                    if detention_name_clean in name or name in detention_name_clean:
                        return data
                    if detention_name in name or name in detention_name:
                        return data
                    # 检查 Name 字段
                    if isinstance(data, dict):
                        xzhq_name = data.get("Name", "")
                        xzhq_name_clean = self._normalize_name(xzhq_name, "detention")
                        if detention_name_clean == xzhq_name_clean:
                            return data
                        if detention_name_clean in xzhq_name or xzhq_name in detention_name_clean:
                            return data

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

    # ==================== 单步执行模式支持 ====================

    @property
    def supports_step_execution(self) -> bool:
        """启用单步执行模式，支持流式显示每个步骤的进度"""
        return True

    async def prepare_execution(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备执行工作流（初始化阶段）

        解析用户消息中的参数，初始化工作流上下文
        """
        logger.info("初始化人工预报工作流执行环境")

        user_message = state.get('user_message', '')
        params = state.get('extracted_params', {})
        entities = state.get('entities', {})

        # 解析会话参数
        session_params = self._parse_session_params(user_message, params, entities)

        return {
            'workflow_context': {
                'session_params': session_params,
                'results': {},
                'plan_code': None,
                'hourly_rain_process': None,
                'forecast_start_time': session_params.get('forecast_start_time'),
                'forecast_end_time': session_params.get('forecast_end_time'),
                'expect_seconds': 60,
                'poll_count': 0,
                'max_poll_count': 0,
                'plan_completed': False
            },
            'workflow_status': 'running'
        }

    async def execute_step(self, state: Dict[str, Any], step_index: int) -> Dict[str, Any]:
        """
        执行单个步骤（单步执行模式）

        Args:
            state: 智能体状态
            step_index: 要执行的步骤索引（从0开始）

        Returns:
            步骤执行结果
        """
        registry = get_tool_registry()
        ctx = state.get('workflow_context', {})
        session_params = ctx.get('session_params', {})
        results = ctx.get('results', {})

        # 步骤索引到步骤ID的映射（步骤ID从1开始）
        step_id = step_index + 1

        logger.info(f"执行人工预报工作流步骤 {step_id}")

        try:
            if step_id == 1:
                return await self._step_1_parse_params(ctx, session_params)
            elif step_id == 2:
                return await self._step_2_get_history_rain(ctx, session_params, registry)
            elif step_id == 3:
                return await self._step_3_analyze_rain_time(ctx, results)
            elif step_id == 4:
                return await self._step_4_create_plan(ctx, session_params, registry)
            elif step_id == 5:
                return await self._step_5_get_rain_pattern(ctx, session_params, registry)
            elif step_id == 6:
                return await self._step_6_set_rain(ctx, registry)
            elif step_id == 7:
                return await self._step_7_set_boundary(ctx, registry)
            elif step_id == 8:
                return await self._step_8_start_calc(ctx, registry)
            elif step_id == 9:
                return await self._step_9_get_expect_time(ctx, registry)
            elif step_id == 10:
                return await self._step_10_poll_status(ctx, registry)
            elif step_id == 11:
                return await self._step_11_get_result(ctx, registry)
            elif step_id == 12:
                return await self._step_12_extract_result(ctx, session_params)
            elif step_id == 13:
                return await self._step_13_generate_page(ctx, session_params, registry)
            else:
                return {'success': False, 'error': f'未知步骤: {step_id}'}

        except Exception as e:
            logger.error(f"步骤 {step_id} 执行异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'workflow_context': ctx
            }

    async def finalize_execution(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        完成工作流执行（收尾阶段）
        """
        ctx = state.get('workflow_context', {})
        results = ctx.get('results', {})
        session_params = ctx.get('session_params', {})

        logger.info("人工预报工作流执行完成，生成最终响应")

        return {
            'workflow_status': 'completed',
            'output_type': self.output_type,
            'generated_page_url': results.get('report_page_url'),
            'forecast_target': session_params.get('forecast_target'),
            'extracted_result': results.get('extracted_result'),
            'plan_code': ctx.get('plan_code'),
            'next_action': 'respond'
        }

    # ==================== 各步骤的具体实现 ====================

    async def _step_1_parse_params(self, ctx: Dict, session_params: Dict) -> Dict[str, Any]:
        """步骤1: 解析会话参数"""
        ctx['results']['session_params'] = session_params
        logger.info(f"解析到会话参数: {session_params}")

        return {
            'success': True,
            'result': session_params,
            'workflow_context': ctx
        }

    async def _step_2_get_history_rain(self, ctx: Dict, session_params: Dict, registry) -> Dict[str, Any]:
        """步骤2: 获取历史面雨量过程"""
        is_future_forecast = session_params.get('is_future_forecast', True)
        rain_start_time = session_params.get('rain_start_time')
        rain_end_time = session_params.get('rain_end_time')

        if is_future_forecast or not rain_start_time or not rain_end_time:
            # 未来预报场景，跳过此步骤
            logger.info("未来预报场景，跳过步骤2")
            return {
                'success': True,
                'result': {'skipped': True, 'reason': '未来预报场景不需要历史降雨数据'},
                'workflow_context': ctx
            }

        # 获取历史面雨量
        result = await registry.execute(
            "forecast_rain_ecmwf_avg",
            st=rain_start_time,
            ed=rain_end_time
        )

        if result.success:
            ctx['results']['history_rain_process'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_3_analyze_rain_time(self, ctx: Dict, results: Dict) -> Dict[str, Any]:
        """步骤3: 获取具体降雨起止时间"""
        session_params = ctx.get('session_params', {})
        is_future_forecast = session_params.get('is_future_forecast', True)

        if is_future_forecast:
            # 未来预报场景，跳过此步骤
            logger.info("未来预报场景，跳过步骤3")
            return {
                'success': True,
                'result': {'skipped': True, 'reason': '未来预报场景使用默认预报时间'},
                'workflow_context': ctx
            }

        history_rain = ctx['results'].get('history_rain_process')
        if history_rain:
            rain_time_range = self._analyze_rain_time_range(history_rain)
            ctx['results']['rain_time_range'] = rain_time_range

            # 更新预报起止时间
            if rain_time_range.get('rain_start'):
                ctx['forecast_start_time'] = rain_time_range['rain_start']
            if rain_time_range.get('forecast_end'):
                ctx['forecast_end_time'] = rain_time_range['forecast_end']

            return {
                'success': True,
                'result': rain_time_range,
                'workflow_context': ctx
            }

        return {
            'success': True,
            'result': {'message': '无历史降雨数据，使用默认时间'},
            'workflow_context': ctx
        }

    async def _step_4_create_plan(self, ctx: Dict, session_params: Dict, registry) -> Dict[str, Any]:
        """步骤4: 新建人工预报方案"""
        plan_name = self._generate_plan_name(session_params)
        plan_desc = self._generate_plan_desc(session_params)

        forecast_start_time = ctx.get('forecast_start_time') or session_params.get('forecast_start_time')
        forecast_end_time = ctx.get('forecast_end_time') or session_params.get('forecast_end_time')

        api_forecast_start = self._convert_time_format(forecast_start_time)
        api_forecast_end = self._convert_time_format(forecast_end_time)

        result = await registry.execute(
            "model_plan_add",
            plan_name=plan_name,
            business_code="flood_forecast_wg",
            business_name="卫共流域洪水预报应用模型",
            start_time=api_forecast_start,
            end_time=api_forecast_end,
            plan_desc=plan_desc
        )

        if result.success:
            plan_code = None
            if isinstance(result.data, dict):
                plan_code = result.data.get('data')
            ctx['plan_code'] = plan_code
            ctx['results']['plan_add_result'] = result.data
            logger.info(f"创建方案成功，方案ID: {plan_code}")

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_5_get_rain_pattern(self, ctx: Dict, session_params: Dict, registry) -> Dict[str, Any]:
        """步骤5: 解析指定降雨过程"""
        total_rainfall = session_params.get('total_rainfall')

        if not total_rainfall:
            # 无指定降雨总量
            return {
                'success': True,
                'result': {'hourly_rain_process': None, 'reason': '未指定降雨总量'},
                'workflow_context': ctx
            }

        # 获取雨型
        result = await registry.execute("model_rain_pattern_detail", id=1)

        if result.success and result.data:
            forecast_start_time = ctx.get('forecast_start_time') or session_params.get('forecast_start_time')
            hourly_rain_process = self._distribute_rainfall_by_pattern(
                total_rainfall, result.data, forecast_start_time
            )
            ctx['hourly_rain_process'] = hourly_rain_process
            ctx['results']['rain_pattern'] = result.data
            ctx['results']['hourly_rain_process'] = hourly_rain_process
            logger.info(f"生成逐小时降雨过程: 共{len(hourly_rain_process)}小时，总降雨量{total_rainfall}mm")

        return {
            'success': result.success,
            'result': {'rain_pattern': result.data, 'hourly_rain_process': ctx.get('hourly_rain_process')},
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_6_set_rain(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤6: 预报方案降雨设置"""
        plan_code = ctx.get('plan_code')
        hourly_rain_process = ctx.get('hourly_rain_process')

        if hourly_rain_process:
            # 使用手动设置降雨
            drp_json = json.dumps(hourly_rain_process)
            result = await registry.execute(
                "model_rain_area_add_manual",
                plan_code=plan_code,
                bsn_code="avg",
                drp_json=drp_json,
                source="2"
            )
            tool_used = "model_rain_area_add_manual"
        else:
            # 使用格网预报降雨
            result = await registry.execute(
                "model_rain_area_add_ecmwf",
                plan_code=plan_code
            )
            tool_used = "model_rain_area_add_ecmwf"

        if result.success:
            ctx['results']['rain_setting_result'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_7_set_boundary(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤7: 预报方案边界条件设置"""
        plan_code = ctx.get('plan_code')

        result = await registry.execute(
            "change_boundry",
            plan_code=plan_code,
            bnd_type="rf_model"
        )

        if result.success:
            ctx['results']['boundry_result'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_8_start_calc(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤8: 计算该人工预报方案"""
        plan_code = ctx.get('plan_code')

        result = await registry.execute("model_plan_calc", plan_code=plan_code)

        if result.success:
            ctx['results']['calc_result'] = result.data
            logger.info(f"步骤8返回数据: {result.data}")

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_9_get_expect_time(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤9: 获取模型预计计算时间"""
        plan_code = ctx.get('plan_code')

        detail_result = await registry.execute("model_plan_detail", plan_code=plan_code)

        expect_seconds = 60  # 默认60秒
        if detail_result.success and detail_result.data:
            detail_data = detail_result.data
            if isinstance(detail_data, dict) and 'expectSeconds' in detail_data:
                try:
                    expect_seconds = int(detail_data['expectSeconds'])
                except (ValueError, TypeError):
                    pass

        ctx['expect_seconds'] = expect_seconds
        ctx['max_poll_count'] = expect_seconds // 5 + 30
        ctx['poll_count'] = 0
        ctx['results']['expect_seconds'] = expect_seconds

        logger.info(f"模型预计计算时间: {expect_seconds}秒，最大轮询次数: {ctx['max_poll_count']}")

        return {
            'success': detail_result.success,
            'result': {'expectSeconds': expect_seconds},
            'error': detail_result.error if not detail_result.success else None,
            'workflow_context': ctx
        }

    async def _step_10_poll_status(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤10: 监视人工预报方案计算状态"""
        plan_code = ctx.get('plan_code')
        max_poll_count = ctx.get('max_poll_count', 32)

        # 轮询等待计算完成
        poll_count = 0
        plan_completed = False
        final_state = None

        while poll_count < max_poll_count:
            poll_count += 1

            # 等待5秒
            await asyncio.sleep(5)

            # 查询状态
            detail_result = await registry.execute("model_plan_detail", plan_code=plan_code)

            if detail_result.success and detail_result.data:
                detail_data = detail_result.data
                current_state = detail_data.get('state', '')

                logger.info(f"人工预报计算进度查询 ({poll_count}/{max_poll_count}): state={current_state}")

                if current_state == '已完成':
                    plan_completed = True
                    final_state = current_state
                    break
                elif current_state in ['待计算', '计算错误']:
                    final_state = current_state
                else:
                    final_state = current_state
            else:
                logger.warning(f"查询人工预报进度失败: {detail_result.error}")

        ctx['poll_count'] = poll_count
        ctx['plan_completed'] = plan_completed
        ctx['results']['plan_detail'] = {'state': final_state, 'request_count': poll_count}

        if not plan_completed and final_state in ['待计算', '计算错误']:
            return {
                'success': False,
                'result': {'final_state': final_state, 'request_count': poll_count},
                'error': f"人工预报计算失败，状态: {final_state}",
                'workflow_context': ctx
            }

        return {
            'success': plan_completed,
            'result': {'final_state': final_state, 'request_count': poll_count},
            'error': None if plan_completed else f"计算未完成，最终状态: {final_state}",
            'workflow_context': ctx
        }

    async def _step_11_get_result(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤11: 获取该人工预报方案结果"""
        plan_code = ctx.get('plan_code')

        result = await registry.execute("get_tjdata_result", plan_code=plan_code)

        if result.success:
            ctx['results']['forecast_result'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_12_extract_result(self, ctx: Dict, session_params: Dict) -> Dict[str, Any]:
        """步骤12: 结果信息提取整理"""
        forecast_target = session_params.get('forecast_target', {'type': 'basin', 'name': '全流域'})
        forecast_result = ctx['results'].get('forecast_result')

        extracted_result = self._extract_forecast_result(forecast_target, forecast_result)
        ctx['results']['extracted_result'] = extracted_result

        return {
            'success': True,
            'result': extracted_result,
            'workflow_context': ctx
        }

    async def _step_13_generate_page(self, ctx: Dict, session_params: Dict, registry) -> Dict[str, Any]:
        """步骤13: 采用合适的Web页面模板进行结果输出"""
        forecast_target = session_params.get('forecast_target', {'type': 'basin', 'name': '全流域'})
        extracted_result = ctx['results'].get('extracted_result')

        template = self._select_template(forecast_target)

        page_result = await registry.execute(
            "generate_report_page",
            report_type="manual_forecast",
            template=template,
            data=extracted_result
        )

        if page_result.success:
            ctx['results']['report_page_url'] = page_result.data

        return {
            'success': page_result.success,
            'result': page_result.data if page_result.success else None,
            'error': page_result.error if not page_result.success else None,
            'workflow_context': ctx
        }


# 自动注册工作流
_flood_manualforecast_getresult_workflow = FloodManualForecastGetResultWorkflow()
register_workflow(_flood_manualforecast_getresult_workflow)
