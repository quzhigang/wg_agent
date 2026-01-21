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
        entities = state.get('entities', {})  # 获取意图分析提取的实体

        execution_results = []

        try:
            # 步骤1: 解析会话参数 - 提取预报对象和降雨大概起止时间
            logger.info("执行步骤1: 解析会话参数")
            parsed_params = self._parse_session_params(user_message, params, entities)
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
            # 注意：历史自动预报结果需要使用 get_history_autoforcast_res 接口
            # get_tjdata_result 接口对历史自动预报方案返回null
            logger.info("执行步骤5: 获取历史洪水自动预报结果")
            start_time = time.time()

            forecast_result = await registry.execute(
                "get_history_autoforcast_res",
                history_plan_id=history_plan_id
            )

            execution_time_ms = int((time.time() - start_time) * 1000)

            step_result = {
                'step_id': 5,
                'step_name': '获取历史洪水自动预报结果',
                'tool_name': 'get_history_autoforcast_res',
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

            # 记录返回数据的基本信息
            if forecast_result.data and isinstance(forecast_result.data, dict):
                logger.info(f"步骤5返回数据keys: {list(forecast_result.data.keys())}")
            elif not forecast_result.data:
                logger.warning("步骤5返回数据为空!")

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
    
    def _parse_session_params(self, user_message: str, params: Dict[str, Any], entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析会话参数，提取预报对象和降雨大概起止时间，支持多对象查询

        Args:
            user_message: 用户消息
            params: 提取的参数
            entities: 意图分析提取的实体

        Returns:
            解析后的参数
        """
        import re

        result = {
            "forecast_target": {
                "type": "basin",
                "name": "全流域",
                "id": None
            },
            "rain_start_time": "",
            "rain_end_time": ""
        }

        entities = entities or {}

        # 优先从entities中获取对象信息
        object_name = entities.get("object", "")
        object_type = entities.get("object_type", "")

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

        # 解析时间范围（前后增加几天余量）
        time_parsed = self._parse_time_range(user_message, params, entities)
        result["rain_start_time"] = time_parsed["start_time"]
        result["rain_end_time"] = time_parsed["end_time"]

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

    def _parse_time_range(self, user_message: str, params: Dict[str, Any], entities: Dict[str, Any]) -> Dict[str, str]:
        """
        解析时间范围，支持多种时间表达方式

        Args:
            user_message: 用户消息
            params: 提取的参数
            entities: 意图分析提取的实体

        Returns:
            包含 start_time 和 end_time 的字典
        """
        import re

        now = datetime.now()
        result = {"start_time": "", "end_time": ""}

        # 1. 优先使用params中的明确时间
        if params.get("start_time") and params.get("end_time"):
            try:
                st = datetime.fromisoformat(params.get("start_time").replace("Z", "+00:00"))
                ed = datetime.fromisoformat(params.get("end_time").replace("Z", "+00:00"))
                result["start_time"] = (st - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
                result["end_time"] = (ed + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
                return result
            except:
                pass

        # 2. 从entities中获取时间信息
        time_str = entities.get("time", "")

        # 合并用户消息和entities中的时间信息进行解析
        text_to_parse = f"{user_message} {time_str}"

        # 3. 尝试解析具体日期格式
        parsed_date = self._extract_date_from_text(text_to_parse, now)
        if parsed_date:
            # 找到具体日期，前后各加3天余量
            result["start_time"] = (parsed_date - timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            result["end_time"] = (parsed_date + timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            return result

        # 4. 处理相对时间描述
        if "上周" in text_to_parse:
            result["start_time"] = (now - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
            result["end_time"] = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        elif "上个月" in text_to_parse:
            # 上个月
            last_month = now.replace(day=1) - timedelta(days=1)
            result["start_time"] = last_month.replace(day=1).strftime("%Y-%m-%d 00:00:00")
            result["end_time"] = last_month.strftime("%Y-%m-%d 23:59:59")
        elif "今年汛期" in text_to_parse:
            # 汛期通常是6-9月
            year = now.year
            result["start_time"] = f"{year}-06-01 00:00:00"
            result["end_time"] = f"{year}-09-30 23:59:59"
        elif "去年汛期" in text_to_parse:
            year = now.year - 1
            result["start_time"] = f"{year}-06-01 00:00:00"
            result["end_time"] = f"{year}-09-30 23:59:59"
        else:
            # 5. 尝试匹配月份
            month_match = re.search(r'(\d{1,2})月', text_to_parse)
            if month_match:
                month = int(month_match.group(1))
                # 判断是今年还是去年的月份
                year = now.year
                if month > now.month:
                    # 如果月份大于当前月份，说明是去年的
                    year = now.year - 1

                # 返回整个月的时间范围
                if month == 12:
                    end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
                else:
                    end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)

                result["start_time"] = f"{year}-{month:02d}-01 00:00:00"
                result["end_time"] = end_date.strftime("%Y-%m-%d %H:%M:%S")
            else:
                # 默认查询最近30天
                result["start_time"] = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
                result["end_time"] = now.strftime("%Y-%m-%d %H:%M:%S")

        return result

    def _extract_date_from_text(self, text: str, now: datetime) -> datetime:
        """
        从文本中提取具体日期

        支持格式：
        - X月X日、X月X号
        - XXXX年X月X日
        - X-X、X/X（月-日）
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
            # 推断年份：如果日期在当前日期之后，则认为是去年
            year = now.year
            try:
                target_date = datetime(year, month, day)
                if target_date > now:
                    # 日期在未来，说明是去年的
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

        # 模式4: X-X 或 X/X（假设是月-日）
        pattern4 = r'(\d{1,2})[-/](\d{1,2})'
        match = re.search(pattern4, text)
        if match:
            month, day = int(match.group(1)), int(match.group(2))
            if 1 <= month <= 12 and 1 <= day <= 31:
                year = now.year
                try:
                    target_date = datetime(year, month, day)
                    if target_date > now:
                        year = now.year - 1
                        target_date = datetime(year, month, day)
                    return target_date
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
            具体降雨起止时间，格式为 {"start_time": "...", "end_time": "..."}
        """
        result = {
            "start_time": "",
            "end_time": ""
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
                time_array = rain_data.get("t") or rain_data.get("time") or rain_data.get("times")
                value_array = (rain_data.get("v") or rain_data.get("value") or
                              rain_data.get("values") or rain_data.get("p") or
                              rain_data.get("rain") or rain_data.get("rainfall") or
                              rain_data.get("drp"))

                if isinstance(time_array, list) and isinstance(value_array, list):
                    logger.info(f"_analyze_rain_time: 检测到并行数组格式: 时间数组长度={len(time_array)}, 值数组长度={len(value_array)}")
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

            result["start_time"] = time_series[start_idx][0]
            result["end_time"] = time_series[end_idx][0]

            # 计算主要降雨时段的总降雨量
            total_rain = sum(time_series[i][1] for i in range(start_idx, end_idx + 1))
            logger.info(f"_analyze_rain_time: 分析成功，降雨时间段: {result['start_time']} ~ {result['end_time']}, "
                       f"时间点数量: {end_idx - start_idx + 1}, 总降雨量: {total_rain:.2f}mm")

        except Exception as e:
            logger.warning(f"_analyze_rain_time: 分析降雨时间失败: {e}", exc_info=True)

        return result

    def _find_matching_plan_id(self, plan_list: Any, rain_end_time: str) -> str:
        """
        从历史自动预报方案清单中找到匹配的方案ID
        寻找与降雨结束时间最接近且超过的预报开始时间对应的方案ID

        API返回格式:
        {
            "model_auto_20240911180000": ["2024/09/11 18:00:00", "2024/09/14 18:00:00", "14.6"],
            ...
        }
        键是方案ID，值是数组 [预报开始时间, 预报结束时间, 总降雨量]

        Args:
            plan_list: 历史预报方案清单
            rain_end_time: 降雨结束时间

        Returns:
            匹配的方案ID
        """
        if not plan_list:
            logger.warning("历史预报方案清单为空")
            return ""

        logger.info(f"历史预报方案清单类型: {type(plan_list).__name__}, 数据预览: {str(plan_list)[:500]}")

        try:
            # 解析降雨结束时间
            if rain_end_time:
                target_time = datetime.strptime(rain_end_time, "%Y-%m-%d %H:%M:%S")
            else:
                target_time = datetime.now()

            logger.info(f"目标降雨结束时间: {target_time}")

            best_plan_id = ""
            min_diff = float('inf')

            # 处理实际API返回的字典格式: {plan_id: [start_time, end_time, rainfall], ...}
            if isinstance(plan_list, dict):
                for plan_id, plan_info in plan_list.items():
                    # 跳过非方案数据的键
                    if plan_id in ["success", "message", "code", "data"]:
                        continue

                    if isinstance(plan_info, list) and len(plan_info) >= 2:
                        # plan_info = [预报开始时间, 预报结束时间, 总降雨量]
                        forecast_start = plan_info[0]

                        if forecast_start:
                            try:
                                # 处理可能的日期格式: "2024/09/11 18:00:00" 或 "2024-09-11 18:00:00"
                                forecast_start_clean = forecast_start.replace("/", "-").replace("\\", "-")
                                plan_time = datetime.strptime(forecast_start_clean, "%Y-%m-%d %H:%M:%S")

                                # 找到超过降雨结束时间且差距最小的方案
                                if plan_time >= target_time:
                                    diff = (plan_time - target_time).total_seconds()
                                    if diff < min_diff:
                                        min_diff = diff
                                        best_plan_id = str(plan_id)
                                        logger.info(f"找到候选方案: {plan_id}, 预报开始时间: {plan_time}, 差距: {diff}秒")
                            except Exception as e:
                                logger.warning(f"解析方案 {plan_id} 的时间失败: {forecast_start}, 错误: {e}")
                                continue

                # 如果没找到超过的，取最接近的（时间最近的）
                if not best_plan_id and plan_list:
                    # 找到时间最接近目标时间的方案（不管是之前还是之后）
                    min_abs_diff = float('inf')
                    for plan_id, plan_info in plan_list.items():
                        if plan_id in ["success", "message", "code", "data"]:
                            continue
                        if isinstance(plan_info, list) and len(plan_info) >= 2:
                            forecast_start = plan_info[0]
                            if forecast_start:
                                try:
                                    forecast_start_clean = forecast_start.replace("/", "-").replace("\\", "-")
                                    plan_time = datetime.strptime(forecast_start_clean, "%Y-%m-%d %H:%M:%S")
                                    abs_diff = abs((plan_time - target_time).total_seconds())
                                    if abs_diff < min_abs_diff:
                                        min_abs_diff = abs_diff
                                        best_plan_id = str(plan_id)
                                except:
                                    continue
                    logger.info(f"未找到超过目标时间的方案，选择最接近的方案: {best_plan_id}")

            # 兼容旧格式: [{planId: ..., forecastStart: ...}, ...]
            elif isinstance(plan_list, list):
                for plan in plan_list:
                    if isinstance(plan, dict):
                        plan_id = plan.get("planId") or plan.get("plan_id") or plan.get("id")
                        forecast_start = plan.get("forecastStart") or plan.get("start_time")

                        if forecast_start:
                            try:
                                plan_time = datetime.strptime(forecast_start, "%Y-%m-%d %H:%M:%S")
                                if plan_time >= target_time:
                                    diff = (plan_time - target_time).total_seconds()
                                    if diff < min_diff:
                                        min_diff = diff
                                        best_plan_id = str(plan_id)
                            except:
                                continue

                if not best_plan_id and plan_list:
                    best_plan_id = str(plan_list[0].get("planId") or plan_list[0].get("plan_id") or plan_list[0].get("id") or "")

            logger.info(f"最终选择的方案ID: {best_plan_id}")
            return best_plan_id

        except Exception as e:
            logger.warning(f"查找匹配方案ID失败: {e}", exc_info=True)
            return ""
    
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
                "summary": f"{'、'.join(target_names)}历史洪水自动预报结果",
                "data": {"targets": targets_data},
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

        elif target_type == "gate":
            gate_data = self._extract_station_data(forecast_data, target_name)
            extracted["summary"] = f"{target_name}历史洪水预报结果"
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
                    # 也检查 SectionName 字段
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
                    # 也检查 Name 字段
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
        logger.info("初始化历史自动预报结果查询工作流执行环境")

        user_message = state.get('user_message', '')
        params = state.get('extracted_params', {})
        entities = state.get('entities', {})

        # 解析会话参数
        parsed_params = self._parse_session_params(user_message, params, entities)

        return {
            'workflow_context': {
                'parsed_params': parsed_params,
                'results': {},
                'exact_rain_time': None,
                'history_plan_id': None
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
        parsed_params = ctx.get('parsed_params', {})
        results = ctx.get('results', {})

        # 步骤索引到步骤ID的映射（步骤ID从1开始）
        step_id = step_index + 1

        logger.info(f"执行历史自动预报结果查询工作流步骤 {step_id}")

        try:
            if step_id == 1:
                return await self._step_1_parse_params(ctx, parsed_params)
            elif step_id == 2:
                return await self._step_2_get_history_rain(ctx, parsed_params, registry)
            elif step_id == 3:
                return await self._step_3_analyze_rain_time(ctx)
            elif step_id == 4:
                return await self._step_4_get_plan_id(ctx, registry)
            elif step_id == 5:
                return await self._step_5_get_result(ctx, registry)
            elif step_id == 6:
                return await self._step_6_extract_result(ctx, parsed_params)
            elif step_id == 7:
                return await self._step_7_generate_page(ctx, parsed_params, registry)
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
        parsed_params = ctx.get('parsed_params', {})
        forecast_target = parsed_params.get('forecast_target', {})

        logger.info("历史自动预报结果查询工作流执行完成，生成最终响应")

        return {
            'workflow_status': 'completed',
            'output_type': self.output_type,
            'generated_page_url': results.get('report_page_url'),
            'forecast_target': forecast_target,
            'history_plan_id': ctx.get('history_plan_id'),
            'extracted_result': results.get('extracted_result'),
            'next_action': 'respond'
        }

    # ==================== 各步骤的具体实现 ====================

    async def _step_1_parse_params(self, ctx: Dict, parsed_params: Dict) -> Dict[str, Any]:
        """步骤1: 解析会话参数"""
        ctx['results']['parsed_params'] = parsed_params
        ctx['results']['forecast_target'] = parsed_params.get('forecast_target', {})
        ctx['results']['rain_start_time'] = parsed_params.get('rain_start_time', '')
        ctx['results']['rain_end_time'] = parsed_params.get('rain_end_time', '')

        logger.info(f"解析到预报对象: {ctx['results']['forecast_target']}")
        logger.info(f"解析到降雨时间范围: {ctx['results']['rain_start_time']} - {ctx['results']['rain_end_time']}")

        return {
            'success': True,
            'result': parsed_params,
            'workflow_context': ctx
        }

    async def _step_2_get_history_rain(self, ctx: Dict, parsed_params: Dict, registry) -> Dict[str, Any]:
        """步骤2: 获取历史面雨量过程"""
        rain_start_time = parsed_params.get('rain_start_time', '')
        rain_end_time = parsed_params.get('rain_end_time', '')

        if not rain_start_time or not rain_end_time:
            return {
                'success': False,
                'result': None,
                'error': '未提供降雨时间范围',
                'workflow_context': ctx
            }

        result = await registry.execute(
            "forecast_rain_ecmwf_avg",
            st=rain_start_time,
            ed=rain_end_time
        )

        if result.success:
            ctx['results']['rain_process'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_3_analyze_rain_time(self, ctx: Dict) -> Dict[str, Any]:
        """步骤3: 获取具体降雨起止时间"""
        rain_process = ctx['results'].get('rain_process')

        if not rain_process:
            return {
                'success': False,
                'result': None,
                'error': '无降雨过程数据',
                'workflow_context': ctx
            }

        exact_rain_time = self._analyze_rain_time(rain_process)
        ctx['exact_rain_time'] = exact_rain_time
        ctx['results']['exact_rain_time'] = exact_rain_time

        logger.info(f"分析得到具体降雨时间: {exact_rain_time}")

        return {
            'success': True,
            'result': exact_rain_time,
            'workflow_context': ctx
        }

    async def _step_4_get_plan_id(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤4: 获取历史洪水自动预报方案ID"""
        result = await registry.execute("get_history_autoforcast_list")

        if not result.success:
            return {
                'success': False,
                'result': None,
                'error': result.error,
                'workflow_context': ctx
            }

        # 从清单中找到匹配的方案ID
        exact_rain_time = ctx.get('exact_rain_time', {})
        history_plan_id = self._find_matching_plan_id(
            result.data,
            exact_rain_time.get('end_time', '')
        )
        ctx['history_plan_id'] = history_plan_id
        ctx['results']['history_plan_id'] = history_plan_id

        logger.info(f"找到匹配的历史预报方案ID: {history_plan_id}")

        return {
            'success': bool(history_plan_id),
            'result': {'history_plan_id': history_plan_id, 'plan_list': result.data},
            'error': None if history_plan_id else '未找到匹配的历史预报方案',
            'workflow_context': ctx
        }

    async def _step_5_get_result(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤5: 获取历史洪水自动预报结果"""
        history_plan_id = ctx.get('history_plan_id')

        if not history_plan_id:
            return {
                'success': False,
                'result': None,
                'error': '无有效的历史方案ID',
                'workflow_context': ctx
            }

        # 使用 get_history_autoforcast_res 接口获取历史自动预报结果
        result = await registry.execute(
            "get_history_autoforcast_res",
            history_plan_id=history_plan_id
        )

        if result.success:
            ctx['results']['history_forecast_result'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_6_extract_result(self, ctx: Dict, parsed_params: Dict) -> Dict[str, Any]:
        """步骤6: 结果信息提取整理"""
        forecast_target = parsed_params.get('forecast_target', {'type': 'basin', 'name': '全流域'})
        forecast_data = ctx['results'].get('history_forecast_result')

        extracted_result = self._extract_forecast_result(forecast_target, forecast_data)
        ctx['results']['extracted_result'] = extracted_result

        return {
            'success': True,
            'result': extracted_result,
            'workflow_context': ctx
        }

    async def _step_7_generate_page(self, ctx: Dict, parsed_params: Dict, registry) -> Dict[str, Any]:
        """步骤7: 采用合适的Web页面模板进行结果输出"""
        forecast_target = parsed_params.get('forecast_target', {'type': 'basin', 'name': '全流域'})
        extracted_result = ctx['results'].get('extracted_result')

        template = self._select_template(forecast_target)

        page_result = await registry.execute(
            "generate_report_page",
            report_type="history_forecast",
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
_history_auto_forecast_workflow = GetHistoryAutoForecastResultWorkflow()
register_workflow(_history_auto_forecast_workflow)
