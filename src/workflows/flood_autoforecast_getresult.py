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
    1. 登录系统获取认证token - 调用login_basin_system工具
    2. 解析会话参数 - 提取预报对象
    3. 进行自动预报 - 调用auto_forcast工具
    4. 监视自动预报计算进度 - 每5秒调用一次model_plan_detail工具
    5. 获取最新洪水自动预报结果 - 调用get_tjdata_result工具
    6. 结果信息提取整理 - 提取主要预报结果数据

    注意：Web页面生成由Controller统一处理，通过模板向量化检索+LLM匹配实现
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
                name="登录系统获取认证token",
                description="调用login_basin_system工具登录卫共流域数字孪生系统，获取访问令牌用于后续接口调用鉴权",
                tool_name="login_basin_system",
                tool_args_template={},
                depends_on=[],
                is_async=False,
                output_key="auth_token"
            ),
            WorkflowStep(
                step_id=2,
                name="解析会话参数",
                description="从用户会话中提取预报对象，如果请求全流域洪水预报结果则输出全流域，如果请求指定水库水文站点蓄滞洪区预报结果则输出其中文名称",
                tool_name=None,  # 无需调用工具，由LLM解析
                tool_args_template=None,
                depends_on=[1],
                is_async=False,
                output_key="forecast_target"
            ),
            WorkflowStep(
                step_id=3,
                name="进行自动预报",
                description="调用auto_forcast工具创建洪水自动预报模型方案并进行计算",
                tool_name="auto_forcast",
                tool_args_template={},  # 无需输入参数
                depends_on=[2],
                is_async=True,
                output_key="auto_forcast_result"
            ),
            WorkflowStep(
                step_id=4,
                name="监视自动预报计算进度",
                description="每5秒调用一次model_plan_detail工具，方案编码固定为model_auto，当state字段值为'已完成'时进行步骤5",
                tool_name="model_plan_detail",
                tool_args_template={"plan_code": "model_auto"},
                depends_on=[3],
                is_async=False,
                output_key="plan_detail"
            ),
            WorkflowStep(
                step_id=5,
                name="获取最新洪水自动预报结果",
                description="调用get_tjdata_result工具获取自动预报方案结果，包含水库、河道断面、蓄滞洪区洪水结果",
                tool_name="get_tjdata_result",
                tool_args_template={"plan_code": "model_auto"},  # 固定采用model_auto
                depends_on=[4],
                is_async=False,
                output_key="auto_forecast_result"
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

            # 步骤2: 解析会话参数 - 提取预报对象
            forecast_target = self._parse_forecast_target(user_message, params, entities)
            results['forecast_target'] = forecast_target
            logger.info(f"解析到预报对象: {forecast_target}")

            execution_results.append({
                'step_id': 2,
                'step_name': '解析会话参数',
                'tool_name': None,
                'success': True,
                'execution_time_ms': 0,
                'data': forecast_target,
                'error': None
            })

            # 步骤3: 进行自动预报
            logger.info("执行步骤3: 进行自动预报")
            start_time = time.time()
            
            # 调用auto_forcast工具，无需参数
            result = await registry.execute("auto_forcast")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 3,
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
            
            # 步骤4: 监视自动预报计算进度
            logger.info("执行步骤4: 监视自动预报计算进度")
            
            # 获取预计计算时间
            expect_seconds = 60  # 默认60秒
            if isinstance(result.data, dict) and result.data.get('expect_seconds'):
                try:
                    expect_seconds = int(result.data.get('expect_seconds', 60))
                except (ValueError, TypeError):
                    expect_seconds = 60
            
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
                'step_id': 4,
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
            
            # 步骤5: 获取最新洪水自动预报结果
            logger.info("执行步骤5: 获取最新洪水自动预报结果")
            start_time = time.time()
            
            # 调用get_tjdata_result工具，plan_code固定为"model_auto"
            result = await registry.execute("get_tjdata_result", plan_code="model_auto")
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            step_result = {
                'step_id': 5,
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

            logger.info("进行洪水自动预报并查询结果工作流执行完成")

            return {
                "execution_results": execution_results,
                "workflow_results": results,
                "output_type": self.output_type,
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
    
    def _parse_forecast_target(self, user_message: str, params: Dict[str, Any], entities: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        解析预报对象，支持多对象查询

        Args:
            user_message: 用户消息
            params: 提取的参数（extracted_params）
            entities: 意图分析提取的实体（entities字段）

        Returns:
            预报对象信息，包含 targets 列表支持多对象
        """
        entities = entities or {}

        # 优先从entities中获取对象信息
        object_name = entities.get("object", "")
        object_type = entities.get("object_type", "")

        # 检查是否有多个对象（用逗号、顿号、"和"分隔）
        import re
        object_names = []
        object_types = []

        if object_name:
            # 分割多个对象名称
            object_names = re.split(r'[,，、和]', object_name)
            object_names = [name.strip() for name in object_names if name.strip()]

        if object_type:
            # 分割多个对象类型
            object_types = re.split(r'[,，、和]', object_type)
            object_types = [t.strip() for t in object_types if t.strip()]

        # 如果没有从entities获取到，尝试从用户消息中提取
        if not object_names:
            # 尝试提取水库名称
            reservoir_names = re.findall(r'([\u4e00-\u9fa5]+水库)', user_message)
            # 尝试提取站点名称
            station_names = re.findall(r'([\u4e00-\u9fa5]+站)', user_message)
            # 尝试提取蓄滞洪区名称
            detention_names = re.findall(r'([\u4e00-\u9fa5]+蓄滞洪区)', user_message)

            object_names = reservoir_names + station_names + detention_names

        # 如果仍然没有对象，返回全流域
        if not object_names:
            return {
                "type": "basin",
                "name": "全流域",
                "id": None,
                "targets": [{"type": "basin", "name": "全流域", "id": None}]
            }

        # 解析每个对象的类型
        targets = []
        for i, name in enumerate(object_names):
            obj_type = object_types[i] if i < len(object_types) else None
            target = self._parse_single_target(name, obj_type, user_message)
            targets.append(target)

        # 如果只有一个对象，保持向后兼容
        if len(targets) == 1:
            result = targets[0].copy()
            result["targets"] = targets
            return result

        # 多个对象
        return {
            "type": "multiple",
            "name": "、".join([t["name"] for t in targets]),
            "id": None,
            "targets": targets
        }

    def _parse_single_target(self, name: str, obj_type: str, user_message: str) -> Dict[str, Any]:
        """
        解析单个预报对象

        Args:
            name: 对象名称
            obj_type: 对象类型（可能为None）
            user_message: 用户消息

        Returns:
            单个预报对象信息
        """
        target = {
            "type": "basin",
            "name": name,
            "id": None
        }

        # 根据名称或类型判断对象类型
        if obj_type == "水库" or "水库" in name:
            target["type"] = "reservoir"
        elif obj_type in ["站点", "水文站", "站", "监测站点"] or "站" in name:
            target["type"] = "station"
        elif obj_type == "蓄滞洪区" or "蓄滞洪区" in name or "滞洪区" in name:
            target["type"] = "detention_basin"
        elif obj_type == "闸" or "闸" in name:
            target["type"] = "gate"

        return target

    def _extract_name_from_message(self, message: str, suffix: str) -> str:
        """
        从用户消息中提取带有指定后缀的名称

        Args:
            message: 用户消息
            suffix: 后缀（如"水库"、"站"、"蓄滞洪区"）

        Returns:
            提取的名称，如果未找到则返回空字符串
        """
        import re
        # 匹配中文名称+后缀的模式
        pattern = rf'([\u4e00-\u9fa5]+{suffix})'
        match = re.search(pattern, message)
        if match:
            return match.group(1)
        return ""
    
    def _extract_forecast_result(
        self,
        forecast_target: Dict[str, Any],
        forecast_data: Any
    ) -> Dict[str, Any]:
        """
        根据预报对象提取相关结果数据，支持多对象查询

        Args:
            forecast_target: 预报对象（可能包含多个targets）
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
        targets = forecast_target.get("targets", [])

        # 多对象查询
        if target_type == "multiple" and targets:
            extracted["summary"] = f"{target_name}洪水预报结果"
            extracted["data"] = {"results": []}

            for target in targets:
                single_data = self._extract_single_target_data(target, forecast_data)
                extracted["data"]["results"].append({
                    "target": target,
                    "data": single_data
                })

            return extracted

        # 单对象查询（向后兼容）
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

    def _extract_single_target_data(self, target: Dict[str, Any], forecast_data: Any) -> Dict[str, Any]:
        """
        提取单个对象的预报数据

        Args:
            target: 单个预报对象
            forecast_data: 完整的预报数据

        Returns:
            该对象的预报数据
        """
        target_type = target.get("type", "basin")
        target_name = target.get("name", "")

        if target_type == "basin":
            return forecast_data
        elif target_type == "reservoir":
            return self._extract_reservoir_data(forecast_data, target_name)
        elif target_type == "station":
            return self._extract_station_data(forecast_data, target_name)
        elif target_type == "detention_basin":
            return self._extract_detention_data(forecast_data, target_name)
        elif target_type == "gate":
            # 闸站数据也从河道断面中提取
            return self._extract_station_data(forecast_data, target_name)

        return {"message": f"未找到{target_name}的预报数据"}
    
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
        logger.info("初始化自动预报工作流执行环境")

        user_message = state.get('user_message', '')
        params = state.get('extracted_params', {})
        entities = state.get('entities', {})

        # 解析预报对象
        forecast_target = self._parse_forecast_target(user_message, params, entities)

        return {
            'workflow_context': {
                'forecast_target': forecast_target,
                'auth_token': None,  # 将在步骤1中获取
                'results': {},
                'expect_seconds': 60,
                'max_poll_count': 0,
                'poll_count': 0,
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
        forecast_target = ctx.get('forecast_target', {})
        results = ctx.get('results', {})

        # 步骤索引到步骤ID的映射（步骤ID从1开始）
        step_id = step_index + 1

        logger.info(f"执行自动预报工作流步骤 {step_id}")

        try:
            if step_id == 1:
                return await self._step_1_login(ctx, registry)
            elif step_id == 2:
                return await self._step_2_parse_params(ctx, forecast_target)
            elif step_id == 3:
                return await self._step_3_start_auto_forecast(ctx, registry)
            elif step_id == 4:
                return await self._step_4_poll_status(ctx, registry)
            elif step_id == 5:
                return await self._step_5_get_result(ctx, registry)
            elif step_id == 6:
                return await self._step_6_extract_result(ctx, forecast_target)
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
        forecast_target = ctx.get('forecast_target', {})

        logger.info("自动预报工作流执行完成，生成最终响应")

        return {
            'workflow_status': 'completed',
            'output_type': self.output_type,
            'forecast_target': forecast_target,
            'extracted_result': results.get('extracted_result'),
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

    async def _step_2_parse_params(self, ctx: Dict, forecast_target: Dict) -> Dict[str, Any]:
        """步骤2: 解析会话参数"""
        ctx['results']['forecast_target'] = forecast_target
        logger.info(f"解析到预报对象: {forecast_target}")

        return {
            'success': True,
            'result': forecast_target,
            'workflow_context': ctx
        }

    async def _step_3_start_auto_forecast(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤3: 进行自动预报"""
        result = await registry.execute("auto_forcast")

        if result.success:
            ctx['results']['auto_forcast_result'] = result.data
            logger.info("自动预报已启动")

            # 获取预计计算时间
            expect_seconds = 60
            if isinstance(result.data, dict) and result.data.get('expect_seconds'):
                try:
                    expect_seconds = int(result.data.get('expect_seconds', 60))
                except (ValueError, TypeError):
                    expect_seconds = 60

            ctx['expect_seconds'] = expect_seconds
            ctx['max_poll_count'] = expect_seconds // 5 + 30

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_4_poll_status(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤4: 监视自动预报计算进度"""
        max_poll_count = ctx.get('max_poll_count', 42)

        poll_count = 0
        plan_completed = False
        final_state = None

        while poll_count < max_poll_count:
            poll_count += 1

            # 等待5秒
            await asyncio.sleep(5)

            # 查询状态
            detail_result = await registry.execute("model_plan_detail", plan_code="model_auto")

            if detail_result.success and detail_result.data:
                detail_data = detail_result.data
                current_state = detail_data.get('state', '')

                logger.info(f"自动预报计算进度查询 ({poll_count}/{max_poll_count}): state={current_state}")

                if current_state == '已完成':
                    plan_completed = True
                    final_state = current_state
                    break
                elif current_state in ['待计算', '计算错误']:
                    final_state = current_state
                else:
                    final_state = current_state
            else:
                logger.warning(f"查询自动预报进度失败: {detail_result.error}")

        ctx['poll_count'] = poll_count
        ctx['plan_completed'] = plan_completed
        ctx['results']['plan_detail'] = {'state': final_state, 'request_count': poll_count}

        if not plan_completed and final_state in ['待计算', '计算错误']:
            return {
                'success': False,
                'result': {'final_state': final_state, 'request_count': poll_count},
                'error': f"自动预报计算失败，状态: {final_state}",
                'workflow_context': ctx
            }

        return {
            'success': plan_completed,
            'result': {'final_state': final_state, 'request_count': poll_count},
            'error': None if plan_completed else f"计算未完成，最终状态: {final_state}",
            'workflow_context': ctx
        }

    async def _step_5_get_result(self, ctx: Dict, registry) -> Dict[str, Any]:
        """步骤5: 获取最新洪水自动预报结果"""
        result = await registry.execute("get_tjdata_result", plan_code="model_auto")

        if result.success:
            ctx['results']['auto_forecast_result'] = result.data

        return {
            'success': result.success,
            'result': result.data if result.success else None,
            'error': result.error if not result.success else None,
            'workflow_context': ctx
        }

    async def _step_6_extract_result(self, ctx: Dict, forecast_target: Dict) -> Dict[str, Any]:
        """步骤6: 结果信息提取整理"""
        forecast_data = ctx['results'].get('auto_forecast_result')
        extracted_result = self._extract_forecast_result(forecast_target, forecast_data)
        ctx['results']['extracted_result'] = extracted_result

        return {
            'success': True,
            'result': extracted_result,
            'workflow_context': ctx
        }


# 自动注册工作流
_flood_autoforecast_getresult_workflow = FloodAutoForecastGetResultWorkflow()
register_workflow(_flood_autoforecast_getresult_workflow)
