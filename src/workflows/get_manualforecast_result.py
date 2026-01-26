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
    1. 登录系统获取认证token - 调用login_basin_system工具
    2. 解析会话参数 - 提取预报对象、降雨大概起止时间、人工预报方案描述
    3. 获取历史面雨量过程 - 调用forecast_rain_ecmwf_avg工具
    4. 获取具体降雨起止时间 - 分析降雨过程数据
    5. 获取人工预报方案ID - 调用model_plan_list_all工具
    6. 获取人工预报结果 - 调用get_tjdata_result工具
    7. 结果信息提取整理 - 提取主要预报结果数据

    注意：Web页面生成由Controller统一处理，通过模板向量化检索+LLM匹配实现
    """
    
    @property
    def name(self) -> str:
        return "get_manual_forecast_result"
    
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
                name="登录系统获取认证token",
                description="调用login_basin_system工具登录卫共流域数字孪生系统，获取访问令牌用于后续接口调用鉴权",
                tool_name="login_basin_system",
                tool_args_template={},
                depends_on=[],
                is_async=False,
                output_key="auth_token",
                result_display="skip"  # 仅返回token，对合成无用
            ),
            WorkflowStep(
                step_id=2,
                name="解析会话参数",
                description="从用户会话中提取：1.预报对象（全流域/指定目标），2.降雨大概起止时间，3.人工预报方案描述（如果提及则跳过步骤3和4）",
                tool_name=None,  # 无需调用工具，由LLM解析
                tool_args_template=None,
                depends_on=[1],
                is_async=False,
                output_key="session_params",
                result_display="skip"  # 仅解析参数，对合成无用
            ),
            WorkflowStep(
                step_id=3,
                name="获取历史面雨量过程",
                description="调用forecast_rain_ecmwf_avg工具获取该时间段内的全流域平均历史逐小时面雨量过程",
                tool_name="forecast_rain_ecmwf_avg",
                tool_args_template={"st": "$rain_start_time", "ed": "$rain_end_time"},
                depends_on=[2],
                is_async=False,
                output_key="rain_process",
                result_display="skip"
            ),
            WorkflowStep(
                step_id=4,
                name="获取具体降雨起止时间",
                description="通过分析输入的逐小时降雨过程数据，获取本场降雨的具体开始和结束时间，注意掐头去尾，去掉主要降雨时段前后零星的少量降雨",
                tool_name=None,  # 无需调用工具，由LLM处理
                tool_args_template=None,
                depends_on=[3],
                is_async=False,
                output_key="exact_rain_time",
                result_display="skip"  # 仅返回时间范围，对合成无用
            ),
            WorkflowStep(
                step_id=5,
                name="获取人工预报方案ID",
                description="调用model_plan_list_all工具获取人工预报方案ID清单，并根据方案描述或降雨起止时间匹配方案",
                tool_name="model_plan_list_all",
                tool_args_template={"business_code": "flood_forecast_wg"},
                depends_on=[4],
                is_async=False,
                output_key="plan_id",
                result_display="skip"  # 仅返回方案ID，对合成无用
            ),
            WorkflowStep(
                step_id=6,
                name="获取人工预报结果",
                description="调用get_tjdata_result工具获取人工预报方案结果，包含水库、河道断面、蓄滞洪区洪水结果",
                tool_name="get_tjdata_result",
                tool_args_template={"plan_code": "$plan_id"},
                depends_on=[5],
                is_async=False,
                output_key="manual_forecast_result",
                result_display="skip"
            ),
            WorkflowStep(
                step_id=7,
                name="结果信息提取整理",
                description="根据预报对象提取全流域或单一目标主要预报结果数据，包括结果概括描述和结果数据",
                tool_name=None,  # 无需调用工具，由LLM处理
                tool_args_template=None,
                depends_on=[6],
                is_async=False,
                output_key="extracted_result",
                result_display="full"  # 最后一步，必须完整提交
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

            # 步骤1: 登录系统获取认证token
            logger.info("执行步骤1: 登录系统获取认证token")
            start_time = time.time()

            auth_result = await registry.execute("login_basin_system")

            execution_time_ms = int((time.time() - start_time) * 1000)

            step_result = {
                'step_id': 1,
                'step_name': '登录系统获取认证token',
                'tool_name': 'login_basin_system',
                'success': auth_result.success,
                'execution_time_ms': execution_time_ms,
                'data': auth_result.data if auth_result.success else None,
                'error': auth_result.error if not auth_result.success else None
            }
            execution_results.append(step_result)

            if not auth_result.success:
                logger.error(f"登录系统失败: {auth_result.error}")
                return {
                    "execution_results": execution_results,
                    "error": f"登录系统失败: {auth_result.error}",
                    "next_action": "respond"
                }

            results['auth_token'] = auth_result.data.get('token') if auth_result.data else None
            logger.info("登录系统成功，获取到认证token")

            # 步骤2: 解析会话参数
            logger.info("执行步骤2: 解析会话参数")
            session_params = self._parse_session_params(user_message, params, entities)
            results['session_params'] = session_params
            
            execution_results.append({
                'step_id': 2,
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
                # 步骤3: 获取历史面雨量过程
                logger.info("执行步骤3: 获取历史面雨量过程")
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
                        'step_id': 3,
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
                        logger.info(f"步骤2返回数据类型: {type(result.data)}, 数据长度: {len(result.data) if isinstance(result.data, (list, dict)) else 'N/A'}")
                        # 打印数据的所有字段名，便于调试
                        if isinstance(result.data, dict):
                            logger.info(f"步骤2返回数据字段: {list(result.data.keys())}")
                        logger.info(f"步骤2返回数据内容: {str(result.data)[:500]}")  # 打印前500字符

                        # 步骤4: 获取具体降雨起止时间
                        logger.info("执行步骤4: 获取具体降雨起止时间")
                        exact_rain_time = self._analyze_rain_time(result.data)
                        results['exact_rain_time'] = exact_rain_time
                        logger.info(f"步骤3分析结果 - 降雨起止时间: {exact_rain_time}")

                        # 如果分析降雨时间失败，使用用户提供的时间范围作为回退
                        if not exact_rain_time.get("start") or not exact_rain_time.get("end"):
                            logger.warning("降雨时间分析结果为空，使用用户提供的时间范围作为回退")
                            exact_rain_time = {
                                "start": rain_start,
                                "end": rain_end
                            }
                            logger.info(f"回退使用时间范围: {exact_rain_time}")
                        
                        execution_results.append({
                            'step_id': 4,
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
                    logger.warning("未提供降雨时间范围，跳过步骤3和4")
            else:
                logger.info("已提供方案描述，跳过步骤3和4")
            
            # 步骤5: 获取人工预报方案ID
            logger.info("执行步骤5: 获取人工预报方案ID")
            start_time = time.time()
            
            # 调用model_plan_list_all工具，只传business_code参数
            result = await registry.execute(
                "model_plan_list_all",
                business_code="flood_forecast_wg"
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 5,
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
            
            # 步骤6: 获取人工预报结果
            logger.info("执行步骤6: 获取人工预报结果")
            start_time = time.time()
            
            result = await registry.execute("get_tjdata_result", plan_code=plan_id)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 6,
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
            logger.info(f"步骤5返回数据类型: {type(result.data)}")
            logger.info(f"步骤5返回数据keys: {result.data.keys() if isinstance(result.data, dict) else 'N/A'}")
            logger.info(f"步骤5返回数据内容: {str(result.data)[:1000]}")  # 打印前1000字符

            # 步骤7: 结果信息提取整理
            logger.info("执行步骤7: 结果信息提取整理")
            extracted_result = self._extract_forecast_result(
                forecast_target,
                result.data
            )
            results['extracted_result'] = extracted_result
            logger.info(f"步骤6提取结果: {extracted_result}")
            
            execution_results.append({
                'step_id': 7,
                'step_name': '结果信息提取整理',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': extracted_result,
                'error': None
            })

            logger.info("人工洪水预报结果查询工作流执行完成")

            return {
                "execution_results": execution_results,
                "workflow_results": results,
                "output_type": self.output_type,
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
        解析会话参数，支持多对象查询

        Args:
            user_message: 用户消息
            params: 提取的参数
            entities: 意图分析提取的实体

        Returns:
            解析后的会话参数，包含预报对象、降雨时间范围、方案描述
        """
        import re

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

        # 洪水预报的有效对象只能是：水库、水文站、闸站、蓄滞洪区、流域
        # 其他类型的实体（如时间描述、事件名称等）不是有效预报对象
        valid_keywords = ['水库', '水文站', '水位站', '站', '蓄滞洪区', '滞洪区', '闸', '流域']
        is_valid_object = object_name and any(kw in object_name for kw in valid_keywords)
        if object_name and not is_valid_object:
            logger.info(f"'{object_name}'不是有效预报对象，将从user_message中重新解析")
            object_name = ""

        # 检查是否包含多个对象（通过"和"、"、"、","分隔）
        multi_objects = []
        if object_name:
            parts = re.split(r'[和、,，]', object_name)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) > 1:
                multi_objects = parts

        # 如果 object_name 没有多个对象，尝试从 user_message 中解析
        if not multi_objects:
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
            result["forecast_target"] = {
                "type": "multiple",
                "targets": targets
            }
        elif object_name:
            result["forecast_target"] = self._parse_single_target(object_name)
        else:
            # 尝试从 user_message 中解析单个对象
            pattern = r'([\u4e00-\u9fa5]+(?:水库|水文站|水位站|站|蓄滞洪区|滞洪区|拦河闸|节制闸|分洪闸|进洪闸|退水闸|闸))'
            matches = re.findall(pattern, user_message)
            if matches:
                result["forecast_target"] = self._parse_single_target(matches[0])

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
        else:
            # 尝试从entities.time或user_message中解析时间
            time_range = self._parse_time_from_text(user_message, entities)
            if time_range["start"] and time_range["end"]:
                result["rain_time_range"] = time_range

        return result

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

    def _parse_time_from_text(self, user_message: str, entities: Dict[str, Any]) -> Dict[str, str]:
        """
        从用户消息或entities中解析时间范围

        Args:
            user_message: 用户消息
            entities: 意图分析提取的实体

        Returns:
            包含start和end的时间范围字典
        """
        import re

        result = {"start": "", "end": ""}
        now = datetime.now()

        # 合并用户消息和entities中的时间信息
        time_str = entities.get("time", "") if entities else ""
        text_to_parse = f"{user_message} {time_str}"

        # 尝试解析具体日期
        parsed_date = self._extract_date_from_text(text_to_parse, now)
        if parsed_date:
            # 找到具体日期，前后各加3天余量
            result["start"] = (parsed_date - timedelta(days=3)).strftime("%Y-%m-%d 00:00:00")
            result["end"] = (parsed_date + timedelta(days=3)).strftime("%Y-%m-%d 23:59:59")
            return result

        # 处理相对时间描述
        if "上周" in text_to_parse:
            result["start"] = (now - timedelta(days=14)).strftime("%Y-%m-%d 00:00:00")
            result["end"] = (now - timedelta(days=7)).strftime("%Y-%m-%d 23:59:59")
        elif "上个月" in text_to_parse:
            last_month = now.replace(day=1) - timedelta(days=1)
            result["start"] = last_month.replace(day=1).strftime("%Y-%m-%d 00:00:00")
            result["end"] = last_month.strftime("%Y-%m-%d 23:59:59")
        elif "今年汛期" in text_to_parse:
            year = now.year
            result["start"] = f"{year}-06-01 00:00:00"
            result["end"] = f"{year}-09-30 23:59:59"
        elif "去年汛期" in text_to_parse:
            year = now.year - 1
            result["start"] = f"{year}-06-01 00:00:00"
            result["end"] = f"{year}-09-30 23:59:59"
        else:
            # 尝试匹配月份
            month_match = re.search(r'(\d{1,2})月', text_to_parse)
            if month_match:
                month = int(month_match.group(1))
                year = now.year
                if month > now.month:
                    year = now.year - 1

                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

                result["start"] = f"{year}-{month:02d}-01 00:00:00"
                result["end"] = end_date.strftime("%Y-%m-%d %H:%M:%S")

        return result

    def _extract_date_from_text(self, text: str, now: datetime) -> Optional[datetime]:
        """
        从文本中提取具体日期

        支持格式：
        - X月X日、X月X号
        - XXXX年X月X日
        - 今年X月X日、去年X月X日

        Args:
            text: 待解析的文本
            now: 当前时间

        Returns:
            解析出的日期，如果解析失败返回None
        """
        import re

        # 模式1: XXXX年X月X日 或 XXXX年X月X号
        pattern1 = r'(\d{4})年(\d{1,2})月(\d{1,2})[日号]'
        match = re.search(pattern1, text)
        if match:
            year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

        # 模式2: X月X日 或 X月X号（无年份，需要推断）
        pattern2 = r'(\d{1,2})月(\d{1,2})[日号]'
        match = re.search(pattern2, text)
        if match:
            month, day = int(match.group(1)), int(match.group(2))
            year = now.year
            try:
                target_date = datetime(year, month, day)
                if target_date > now:
                    year = now.year - 1
                    target_date = datetime(year, month, day)
                return target_date
            except ValueError:
                pass

        # 模式3: 今年/去年 + X月X日
        pattern3 = r'(今年|去年)(\d{1,2})月(\d{1,2})[日号]?'
        match = re.search(pattern3, text)
        if match:
            year_hint, month, day = match.group(1), int(match.group(2)), int(match.group(3))
            year = now.year if year_hint == "今年" else now.year - 1
            try:
                return datetime(year, month, day)
            except ValueError:
                pass

        return None
    
    def _analyze_rain_time(self, rain_data: Any) -> Dict[str, str]:
        """
        分析降雨过程数据，获取具体降雨起止时间

        算法逻辑：
        1. 首先将原始数据转换为时间序列 [(time, value), ...]
        2. 计算每个时间点的3小时累积降雨量，找到最大值作为降雨核心时间
        3. 从核心时间向前搜索，当连续3小时累积降雨小于阈值(1mm)时，认为降雨开始
        4. 从核心时间向后搜索，当连续3小时累积降雨小于阈值(1mm)时，认为降雨结束

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
            具体降雨起止时间，格式为 {"start": "...", "end": "..."}
        """
        result = {
            "start": "",
            "end": ""
        }

        if not rain_data:
            logger.warning("_analyze_rain_time: 降雨数据为空")
            return result

        # 记录原始数据类型用于调试
        logger.info(f"_analyze_rain_time: 数据类型: {type(rain_data).__name__}, 数据预览: {str(rain_data)[:500]}")

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
                    logger.info(f"_analyze_rain_time: 检测到并行数组格式: 时间数组长度={len(time_array)}, 值数组长度={len(value_array)}")
                    if len(time_array) == 0 or len(value_array) == 0:
                        logger.warning("_analyze_rain_time: 并行数组为空，无降雨数据")
                        return result
                    for t, v in zip(time_array, value_array):
                        time_series.append((str(t), extract_rain_value(v)))

                # 格式2: {"data": [...], "list": [...], "records": [...]}
                elif rain_data.get("data") or rain_data.get("list") or rain_data.get("records"):
                    nested_data = (rain_data.get("data") or rain_data.get("list") or
                                  rain_data.get("records") or rain_data.get("items"))
                    if nested_data and isinstance(nested_data, list):
                        logger.info(f"_analyze_rain_time: 检测到嵌套数据格式，递归处理")
                        return self._analyze_rain_time(nested_data)

                # 格式3: {time_string: value} 字典格式
                else:
                    logger.info(f"_analyze_rain_time: 检测到时间-值字典格式，键数量: {len(rain_data)}")
                    for time_key, rain_val in rain_data.items():
                        if time_key in ["success", "message", "code", "total", "data", "list", "t", "v", "p"]:
                            continue
                        time_series.append((str(time_key), extract_rain_value(rain_val)))

            elif isinstance(rain_data, list):
                logger.info(f"_analyze_rain_time: 检测到列表格式，长度: {len(rain_data)}")
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
                logger.warning("_analyze_rain_time: 未能解析出时间序列数据")
                return result

            # 按时间排序
            try:
                time_series.sort(key=lambda x: x[0])
            except:
                pass

            logger.info(f"_analyze_rain_time: 解析得到 {len(time_series)} 个时间点")

            # 第二步：计算每个时间点的3小时累积降雨量，找到核心时间
            # 假设数据是小时级别的，3小时窗口 = 当前点 + 前2个点
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
                logger.warning("_analyze_rain_time: 所有时间点降雨量均为0")
                return result

            core_idx = cumulative_3h.index(max(cumulative_3h))
            logger.info(f"_analyze_rain_time: 降雨核心时间索引={core_idx}, 时间={time_series[core_idx][0]}, 3小时累积={cumulative_3h[core_idx]:.2f}mm")

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

            result["start"] = time_series[start_idx][0]
            result["end"] = time_series[end_idx][0]

            # 计算主要降雨时段的总降雨量
            total_rain = sum(time_series[i][1] for i in range(start_idx, end_idx + 1))
            logger.info(f"_analyze_rain_time: 分析成功，降雨时间段: {result['start']} ~ {result['end']}, "
                       f"时间点数量: {end_idx - start_idx + 1}, 总降雨量: {total_rain:.2f}mm")

        except Exception as e:
            logger.warning(f"_analyze_rain_time: 分析降雨时间失败: {e}", exc_info=True)

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
            logger.warning("方案列表为空")
            return None

        plans = plan_list if isinstance(plan_list, list) else []
        logger.info(f"获取到 {len(plans)} 个方案")

        # 过滤掉自动预报方案（model_auto），只保留人工预报方案
        manual_plans = [p for p in plans if p.get("planCode", "") != "model_auto"]
        logger.info(f"过滤后剩余 {len(manual_plans)} 个人工预报方案")

        if not manual_plans:
            logger.warning("没有找到人工预报方案")
            return None

        # 如果有方案描述，按描述匹配
        if plan_description:
            logger.info(f"按方案描述匹配: {plan_description}")
            for plan in manual_plans:
                plan_name = plan.get("planName", "")
                plan_desc = plan.get("planDesc", "")
                plan_code = plan.get("planCode", "")

                if plan_description.lower() in plan_name.lower() or \
                   plan_description.lower() in plan_desc.lower():
                    logger.info(f"按描述匹配到方案: {plan_code} ({plan_name})")
                    return plan_code

        # 如果有降雨时间，按时间匹配
        if exact_rain_time and exact_rain_time.get("start") and exact_rain_time.get("end"):
            rain_start = exact_rain_time["start"]
            rain_end = exact_rain_time["end"]
            logger.info(f"按时间匹配 - 降雨时间: {rain_start} ~ {rain_end}")

            # 统一时间格式为 YYYY/MM/DD HH:MM:SS（方案时间格式）
            rain_start_normalized = self._normalize_time_format(rain_start)
            rain_end_normalized = self._normalize_time_format(rain_end)
            logger.info(f"标准化后降雨时间: {rain_start_normalized} ~ {rain_end_normalized}")

            matched_plans = []
            for plan in manual_plans:
                plan_start = plan.get("startTime", "")
                plan_end = plan.get("endTime", "")
                plan_code = plan.get("planCode", "")
                plan_name = plan.get("planName", "")

                # 检查方案时间是否能"包住"降雨时间
                if plan_start and plan_end:
                    # 标准化方案时间格式
                    plan_start_normalized = self._normalize_time_format(plan_start)
                    plan_end_normalized = self._normalize_time_format(plan_end)

                    logger.info(f"比较方案 {plan_code}: 方案时间 {plan_start_normalized} ~ {plan_end_normalized}")

                    if plan_start_normalized <= rain_start_normalized and plan_end_normalized >= rain_end_normalized:
                        logger.info(f"时间匹配成功（包含）: {plan_code} ({plan_name})")
                        matched_plans.append(plan)
                    elif not (plan_end_normalized < rain_start_normalized or plan_start_normalized > rain_end_normalized):
                        # 时间重叠（更宽松的匹配）
                        logger.info(f"时间匹配成功（重叠）: {plan_code} ({plan_name})")
                        matched_plans.append(plan)

            if matched_plans:
                # 如果有多个匹配，选择时间最接近的
                best_plan = matched_plans[0]
                logger.info(f"选择匹配方案: {best_plan.get('planCode')} ({best_plan.get('planName')})")
                return best_plan.get("planCode")

        # 如果没有匹配到，返回最新的人工预报方案（不是model_auto）
        logger.warning("未能按描述或时间匹配到方案，尝试返回最新的人工预报方案")
        if manual_plans:
            # 按创建时间排序，取最新的
            sorted_plans = sorted(
                manual_plans,
                key=lambda x: x.get("createTime", "") or x.get("planCode", ""),
                reverse=True
            )
            latest_plan = sorted_plans[0]
            logger.info(f"返回最新人工预报方案: {latest_plan.get('planCode')} ({latest_plan.get('planName')})")
            return latest_plan.get("planCode")

        logger.warning("没有找到任何可用的人工预报方案")
        return None

    def _normalize_time_format(self, time_str: str) -> str:
        """
        统一时间格式，将各种格式转换为 YYYY/MM/DD HH:MM:SS

        支持的输入格式：
        - 2025-07-01 00:00:00 (使用 - 分隔)
        - 2025/07/01 00:00:00 (使用 / 分隔)

        Args:
            time_str: 时间字符串

        Returns:
            标准化后的时间字符串
        """
        if not time_str:
            return ""

        # 将 - 替换为 /，统一格式
        return time_str.replace("-", "/")
    
    def _extract_forecast_result(
        self,
        forecast_target: Dict[str, Any],
        forecast_data: Any
    ) -> Dict[str, Any]:
        """
        根据预报对象提取相关结果数据，支持多对象查询

        Args:
            forecast_target: 预报对象
            forecast_data: 完整的预报数据

        Returns:
            提取后的结果数据
        """
        if not forecast_data:
            logger.warning("步骤6: forecast_data 为空")
            return {
                "target": forecast_target,
                "summary": "未获取到预报数据",
                "data": {}
            }

        target_type = forecast_target.get("type", "basin")
        logger.info(f"步骤6: 提取目标类型={target_type}")

        # 记录可用的数据字段
        if isinstance(forecast_data, dict):
            available_keys = list(forecast_data.keys())
            logger.info(f"步骤6: forecast_data 可用字段: {available_keys}")

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
                "summary": f"{'、'.join(target_names)}人工洪水预报结果",
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
        logger.info(f"步骤6: 提取目标名称={target_name}")

        if target_type == "basin":
            # 全流域数据提取
            extracted["summary"] = f"全流域人工洪水预报结果"
            extracted["data"] = forecast_data

        elif target_type == "reservoir":
            # 水库数据提取
            reservoir_data = self._extract_reservoir_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}人工洪水预报结果"
            extracted["data"] = reservoir_data
            logger.info(f"步骤6: 水库数据提取结果: {str(reservoir_data)[:200]}")

        elif target_type == "station":
            # 站点数据提取
            station_data = self._extract_station_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}人工洪水预报结果"
            extracted["data"] = station_data
            logger.info(f"步骤6: 站点数据提取结果: {str(station_data)[:200]}")

        elif target_type == "detention_basin":
            # 蓄滞洪区数据提取
            detention_data = self._extract_detention_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}人工洪水预报结果"
            extracted["data"] = detention_data
            logger.info(f"步骤6: 蓄滞洪区数据提取结果: {str(detention_data)[:200]}")

        elif target_type == "gate":
            # 闸站数据提取
            gate_data = self._extract_station_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}人工洪水预报结果"
            extracted["data"] = gate_data
            logger.info(f"步骤6: 闸站数据提取结果: {str(gate_data)[:200]}")

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
        提取站点（河道断面）相关数据

        数据结构: {"reachsection_result": {"修武": {"Stcd": "...", "SectionName": "修武", ...}, ...}}

        支持多种名称匹配方式：
        - 修武、修武站、修武水文站、修武水位站 都能匹配到 "修武"
        """
        if isinstance(forecast_data, dict):
            # 河道断面结果在 reachsection_result 字段中
            reachsection_result = forecast_data.get("reachsection_result", {})
            logger.info(f"_extract_station_data: 查找站点 '{station_name}'")
            logger.info(f"_extract_station_data: reachsection_result 可用断面: {list(reachsection_result.keys()) if isinstance(reachsection_result, dict) else 'N/A'}")

            if isinstance(reachsection_result, dict):
                # 标准化站点名称
                station_name_clean = self._normalize_name(station_name, "station")
                logger.info(f"_extract_station_data: 标准化后站名 '{station_name_clean}'")

                # 直接按名称查找
                if station_name in reachsection_result:
                    logger.info(f"_extract_station_data: 直接匹配成功 '{station_name}'")
                    return reachsection_result[station_name]
                if station_name_clean in reachsection_result:
                    logger.info(f"_extract_station_data: 标准化名称匹配成功 '{station_name_clean}'")
                    return reachsection_result[station_name_clean]

                # 模糊匹配
                for name, data in reachsection_result.items():
                    name_clean = self._normalize_name(name, "station")
                    # 标准化后完全匹配
                    if station_name_clean == name_clean:
                        logger.info(f"_extract_station_data: 标准化后完全匹配成功 '{name}'")
                        return data
                    # 包含匹配
                    if station_name_clean in name or name in station_name_clean:
                        logger.info(f"_extract_station_data: 包含匹配成功 '{name}'")
                        return data
                    if station_name in name or name in station_name:
                        logger.info(f"_extract_station_data: 模糊匹配成功 '{name}'")
                        return data
                    # 也检查 SectionName 字段
                    if isinstance(data, dict):
                        section_name = data.get("SectionName", "")
                        section_name_clean = self._normalize_name(section_name, "station")
                        if station_name_clean == section_name_clean:
                            logger.info(f"_extract_station_data: SectionName 标准化匹配成功 '{section_name}'")
                            return data
                        if station_name_clean in section_name or section_name in station_name_clean:
                            logger.info(f"_extract_station_data: SectionName 包含匹配成功 '{section_name}'")
                            return data

        logger.warning(f"_extract_station_data: 未找到站点 '{station_name}'")
        return {"message": f"未找到{station_name}的预报数据"}
    
    def _extract_detention_data(self, forecast_data: Any, detention_name: str) -> Dict[str, Any]:
        """
        提取蓄滞洪区相关数据

        数据结构: {"floodblq_result": {"良相坡": {"Stcd": "...", "Name": "良相坡", ...}, ...}}

        支持多种名称匹配方式：
        - 良相坡、良相坡蓄滞洪区、良相坡滞洪区 都能匹配到 "良相坡"
        """
        if isinstance(forecast_data, dict):
            # 蓄滞洪区结果在 floodblq_result 字段中
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
                    # 也检查 Name 字段
                    if isinstance(data, dict):
                        xzhq_name = data.get("Name", "")
                        xzhq_name_clean = self._normalize_name(xzhq_name, "detention")
                        if detention_name_clean == xzhq_name_clean:
                            return data
                        if detention_name_clean in xzhq_name or xzhq_name in detention_name_clean:
                            return data

        return {"message": f"未找到{detention_name}的预报数据"}

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
        logger.info("初始化人工预报结果查询工作流执行环境")

        user_message = state.get('user_message', '')
        params = state.get('extracted_params', {})
        entities = state.get('entities', {})

        # 解析会话参数
        session_params = self._parse_session_params(user_message, params, entities)

        return {
            'workflow_context': {
                'session_params': session_params,
                'auth_token': None,  # 将在步骤1中获取
                'results': {},
                'exact_rain_time': None,
                'plan_id': None
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

        logger.info(f"执行人工预报结果查询工作流步骤 {step_id}")

        try:
            if step_id == 1:
                return await self._step_1_login(ctx, registry)
            elif step_id == 2:
                return await self._step_2_parse_params(ctx, session_params)
            elif step_id == 3:
                return await self._step_3_get_history_rain(ctx, session_params, registry)
            elif step_id == 4:
                return await self._step_4_analyze_rain_time(ctx, session_params)
            elif step_id == 5:
                return await self._step_5_get_plan_id(ctx, session_params, registry)
            elif step_id == 6:
                return await self._step_6_get_result(ctx, registry)
            elif step_id == 7:
                return await self._step_7_extract_result(ctx, session_params)
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
        forecast_target = session_params.get('forecast_target', {})

        logger.info("人工预报结果查询工作流执行完成，生成最终响应")

        return {
            'workflow_status': 'completed',
            'output_type': self.output_type,
            'forecast_target': forecast_target,
            'extracted_result': results.get('extracted_result'),
            'plan_id': ctx.get('plan_id'),
            'next_action': 'respond'
        }

    # ==================== 各步骤的具体实现 ====================

    async def _step_1_login(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤1: 登录系统获取认证token"""
        result = await registry.execute("login_basin_system")

        if result.success:
            token = result.data.get('token') if result.data else None
            ctx['auth_token'] = token
            ctx['results']['auth_token'] = token
            logger.info("登录系统成功，获取到认证token")

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_2_parse_params(self, ctx: Dict, session_params: Dict) -> Dict[str, Any]:
        """步骤2: 解析会话参数"""
        ctx['results']['session_params'] = session_params
        logger.info(f"解析到会话参数: {session_params}")

        return {
            'success': True,
            'result': session_params,
            'workflow_context': ctx
        }

    async def _step_3_get_history_rain(self, ctx: Dict, session_params: Dict, registry) -> Dict[str, Any]:
        """步骤3: 获取历史面雨量过程"""
        plan_description = session_params.get('plan_description', '')
        rain_time_range = session_params.get('rain_time_range', {})

        # 如果有明确的方案描述，跳过此步骤
        if plan_description:
            logger.info("已提供方案描述，跳过步骤2")
            return {
                'success': True,
                'result': {'skipped': True, 'reason': '已提供方案描述'},
                'workflow_context': ctx
            }

        rain_start = rain_time_range.get('start', '')
        rain_end = rain_time_range.get('end', '')

        if not rain_start or not rain_end:
            logger.warning("未提供降雨时间范围，跳过步骤2")
            return {
                'success': True,
                'result': {'skipped': True, 'reason': '未提供降雨时间范围'},
                'workflow_context': ctx
            }

        result = await registry.execute(
            "forecast_rain_ecmwf_avg",
            st=rain_start,
            ed=rain_end
        )

        if result.success:
            ctx['results']['rain_process'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_4_analyze_rain_time(self, ctx: Dict, session_params: Dict) -> Dict[str, Any]:
        """步骤4: 获取具体降雨起止时间"""
        plan_description = session_params.get('plan_description', '')

        # 如果有明确的方案描述，跳过此步骤
        if plan_description:
            logger.info("已提供方案描述，跳过步骤3")
            return {
                'success': True,
                'result': {'skipped': True, 'reason': '已提供方案描述'},
                'workflow_context': ctx
            }

        rain_process = ctx['results'].get('rain_process')
        if not rain_process:
            logger.warning("无降雨过程数据，跳过步骤3")
            return {
                'success': True,
                'result': {'skipped': True, 'reason': '无降雨过程数据'},
                'workflow_context': ctx
            }

        exact_rain_time = self._analyze_rain_time(rain_process)
        ctx['exact_rain_time'] = exact_rain_time
        ctx['results']['exact_rain_time'] = exact_rain_time

        # 如果分析失败，使用用户提供的时间范围作为回退
        rain_time_range = session_params.get('rain_time_range', {})
        if not exact_rain_time.get("start") or not exact_rain_time.get("end"):
            logger.warning("降雨时间分析结果为空，使用用户提供的时间范围作为回退")
            exact_rain_time = {
                "start": rain_time_range.get('start', ''),
                "end": rain_time_range.get('end', '')
            }
            ctx['exact_rain_time'] = exact_rain_time

        return {
            'success': True,
            'result': exact_rain_time,
            'workflow_context': ctx
        }

    async def _step_5_get_plan_id(self, ctx: Dict, session_params: Dict, registry) -> Dict[str, Any]:
        """步骤5: 获取人工预报方案ID"""
        result = await registry.execute(
            "model_plan_list_all",
            business_code="flood_forecast_wg"
        )

        if not result.success:
            return {
                'success': False,
                'result': None,
                'error': result.error,
                'workflow_context': ctx
            }

        # 匹配方案ID
        plan_description = session_params.get('plan_description', '')
        exact_rain_time = ctx.get('exact_rain_time')

        plan_id = self._match_plan_id(result.data, plan_description, exact_rain_time)
        ctx['plan_id'] = plan_id
        ctx['results']['plan_id'] = plan_id

        if not plan_id:
            return {
                'success': False,
                'result': None,
                'error': '未找到匹配的人工预报方案',
                'workflow_context': ctx
            }

        logger.info(f"匹配到方案ID: {plan_id}")

        return {
            'success': True,
            'result': {'plan_id': plan_id, 'plan_list': result.data},
            'workflow_context': ctx
        }

    async def _step_6_get_result(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤6: 获取人工预报结果"""
        plan_id = ctx.get('plan_id')

        if not plan_id:
            return {
                'success': False,
                'result': None,
                'error': '无有效的方案ID',
                'workflow_context': ctx
            }

        result = await registry.execute("get_tjdata_result", plan_code=plan_id)

        if result.success:
            ctx['results']['manual_forecast_result'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_7_extract_result(self, ctx: Dict, session_params: Dict) -> Dict[str, Any]:
        """步骤7: 结果信息提取整理"""
        forecast_target = session_params.get('forecast_target', {'type': 'basin', 'name': '全流域'})
        forecast_data = ctx['results'].get('manual_forecast_result')

        extracted_result = self._extract_forecast_result(forecast_target, forecast_data)
        ctx['results']['extracted_result'] = extracted_result

        return {
            'success': True,
            'result': extracted_result,
            'workflow_context': ctx
        }


# 自动注册工作流
_get_manualforecast_result_workflow = GetManualForecastResultWorkflow()
register_workflow(_get_manualforecast_result_workflow)
