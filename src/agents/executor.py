"""
Executor - 任务执行器
负责执行计划中的各个步骤，调用工具，处理异步任务
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import time
import re

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import settings
from ..config.logging_config import get_logger
from ..config.llm_prompt_logger import log_llm_call
from .state import AgentState, PlanStep, ExecutionResult, StepStatus

logger = get_logger(__name__)


class Executor:
    """任务执行器"""

    def __init__(self):
        """初始化执行器"""
        # 思考模式配置（用于Qwen3等模型，非流式调用需设置为false）
        extra_body = {"enable_thinking": settings.llm_enable_thinking}

        # 执行器LLM
        executor_cfg = settings.get_executor_config()
        self.llm = ChatOpenAI(
            api_key=executor_cfg["api_key"],
            base_url=executor_cfg["api_base"],
            model=executor_cfg["model"],
            temperature=executor_cfg["temperature"],
            model_kwargs={"extra_body": extra_body}
        )
        
        # 工具注册表 - 将在tools模块实现后动态加载
        self.tool_registry: Dict[str, callable] = {}
        
        # 异步任务回调
        self.async_callbacks: Dict[str, callable] = {}
        
        logger.info("Executor初始化完成")
    
    def register_tool(self, name: str, func: callable):
        """注册工具"""
        self.tool_registry[name] = func
        logger.info(f"注册工具: {name}")
    
    def register_tools(self, tools: Dict[str, callable]):
        """批量注册工具"""
        self.tool_registry.update(tools)
        logger.info(f"批量注册了{len(tools)}个工具")
    
    async def execute_step(self, step: Dict[str, Any], state: AgentState) -> ExecutionResult:
        """
        执行单个步骤
        
        Args:
            step: 步骤信息（序列化的PlanStep）
            state: 当前智能体状态
            
        Returns:
            执行结果
        """
        step_id = step.get('step_id', 0)
        tool_name = step.get('tool_name')
        tool_args = step.get('tool_args', {})
        description = step.get('description', '')
        
        # 解析参数中的变量占位符 (例如: $$step_1.data[0].stcd$$)
        resolved_args = self._resolve_variables(tool_args, state)
        
        logger.info(f"执行步骤 {step_id}: {description}")
        if tool_name:
            logger.info(f"工具名称: {tool_name}, 原始参数: {tool_args}")
            if resolved_args != tool_args:
                logger.info(f"解析后参数: {resolved_args}")
        
        start_time = time.time()
        
        try:
            # 如果没有指定工具，使用LLM直接处理
            if not tool_name:
                output = await self._execute_with_llm(description, state)
            else:
                # 查找并执行工具
                output = await self._execute_tool(tool_name, resolved_args, state)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"步骤 {step_id} 执行成功，耗时 {execution_time}ms")
            logger.info(f"步骤 {step_id} 执行结果: {output}")
            logger.info("")  # 空行分隔
            
            return ExecutionResult(
                step_id=step_id,
                success=True,
                output=output,
                error=None,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"步骤 {step_id} 执行失败: {e}")
            logger.info("")  # 空行分隔
            
            return ExecutionResult(
                step_id=step_id,
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=execution_time
            )
    
    async def _execute_tool(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any],
        state: AgentState
    ) -> Any:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            state: 当前状态
            
        Returns:
            工具执行结果
        """
        if tool_name not in self.tool_registry:
            # 尝试动态加载工具
            tool_func = await self._load_tool(tool_name)
            if not tool_func:
                raise ValueError(f"未找到工具: {tool_name}")
            self.tool_registry[tool_name] = tool_func
        
        tool_func = self.tool_registry[tool_name]

        # 转换参数类型（处理字符串形式的布尔值）
        tool_args = self._convert_arg_types(tool_args)

        # 执行工具（支持同步和异步）
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**tool_args)
        else:
            result = tool_func(**tool_args)
        
        return result

    def _convert_arg_types(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """转换参数类型，处理字符串形式的布尔值"""
        converted = {}
        for key, value in args.items():
            if isinstance(value, str):
                if value.lower() == 'true':
                    converted[key] = True
                elif value.lower() == 'false':
                    converted[key] = False
                else:
                    converted[key] = value
            else:
                converted[key] = value
        return converted

    async def _load_tool(self, tool_name: str) -> Optional[callable]:
        """
        动态加载工具
        
        从全局工具注册表中加载工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具函数或None
        """
        logger.info(f"尝试从工具注册表加载工具: {tool_name}")
        
        try:
            from ..tools.registry import get_tool_registry
            
            registry = get_tool_registry()
            
            # 检查工具是否存在
            if registry.has_tool(tool_name):
                tool_func = registry.get_tool_function(tool_name)
                if tool_func:
                    logger.info(f"成功加载工具: {tool_name}")
                    return tool_func
            
            logger.warning(f"工具注册表中未找到工具: {tool_name}")
            return None
            
        except Exception as e:
            logger.error(f"加载工具 {tool_name} 时发生错误: {e}")
            return None
    
    async def _execute_with_llm(self, task_description: str, state: AgentState) -> str:
        """
        使用LLM执行任务（无工具调用）
        
        Args:
            task_description: 任务描述
            state: 当前状态
            
        Returns:
            LLM生成的结果
        """
        prompt_template = """你是卫共流域数字孪生系统的智能助手。

## 任务
{task_description}

## 用户原始消息
{user_message}

## 已有执行结果
{execution_results}

## 检索到的知识
{retrieved_documents}

请根据以上信息完成任务，给出清晰、准确的回答。
"""
        prompt = ChatPromptTemplate.from_template(prompt_template)
        
        chain = prompt | self.llm
        
        # 格式化已有结果
        results_str = self._format_execution_results(state.get('execution_results', []))
        docs_str = self._format_retrieved_documents(state.get('retrieved_documents', []))
        
        # 准备上下文变量
        context_vars = {
            "task_description": task_description,
            "user_message": state.get('user_message', ''),
            "execution_results": results_str or "无",
            "retrieved_documents": docs_str or "无"
        }
        
        import time
        _start = time.time()
        response = await chain.ainvoke(context_vars)
        _elapsed = time.time() - _start

        # 记录LLM调用日志
        full_prompt = prompt_template.format(**context_vars)
        log_llm_call(
            step_name="任务执行(LLM)",
            module_name="Executor._execute_with_llm",
            prompt_template_name="EXECUTOR_LLM_PROMPT",
            context_variables=context_vars,
            full_prompt=full_prompt,
            response=response.content,
            elapsed_time=_elapsed
        )
        
        return response.content
    
    async def execute_async_task(
        self,
        task_type: str,
        params: Dict[str, Any],
        state: AgentState
    ) -> str:
        """
        启动异步任务
        
        Args:
            task_type: 任务类型
            params: 任务参数
            state: 当前状态
            
        Returns:
            异步任务ID
        """
        from uuid import uuid4
        
        task_id = str(uuid4())
        logger.info(f"启动异步任务: {task_type}, ID: {task_id}")
        
        # TODO: 实际的异步任务处理将在async_tasks模块实现
        # 这里返回任务ID，后续通过轮询或WebSocket获取结果
        
        return task_id
    
    async def check_async_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        检查异步任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        # TODO: 从async_tasks模块获取任务状态
        return {
            "task_id": task_id,
            "status": "pending",
            "result": None
        }
    
    async def handle_retry(
        self,
        step: Dict[str, Any],
        error: str,
        state: AgentState
    ) -> Dict[str, Any]:
        """
        处理步骤重试
        
        Args:
            step: 失败的步骤
            error: 错误信息
            state: 当前状态
            
        Returns:
            重试决策
        """
        retry_count = step.get('retry_count', 0)
        max_retries = settings.task_max_retries
        
        if retry_count >= max_retries:
            logger.warning(f"步骤 {step.get('step_id')} 已达到最大重试次数")
            return {
                "should_retry": False,
                "action": "fallback",
                "message": f"步骤执行失败，已重试{retry_count}次"
            }
        
        # 增加重试计数
        step['retry_count'] = retry_count + 1
        
        # 等待后重试
        await asyncio.sleep(settings.task_retry_delay_seconds)
        
        return {
            "should_retry": True,
            "action": "retry",
            "message": f"正在进行第{retry_count + 1}次重试"
        }
    
    def _format_execution_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化执行结果"""
        if not results:
            return ""
        
        formatted = []
        for r in results:
            step_id = r.get('step_id', '?')
            success = "成功" if r.get('success') else "失败"
            output = r.get('output', '')
            if isinstance(output, dict):
                output = str(output)[:500]  # 截断长输出
            formatted.append(f"步骤{step_id} ({success}): {output}")
        
        return "".join(formatted)
    
    def _format_retrieved_documents(self, documents: List[Dict[str, Any]]) -> str:
        """格式化检索到的文档"""
        if not documents:
            return ""
        
        formatted = []
        for i, doc in enumerate(documents[:5], 1):  # 最多5个
            content = doc.get('content', '')[:500]  # 截断
            source = doc.get('source', '未知来源')
            formatted.append(f"[{i}] {source}: {content}")
        
        return "".join(formatted)

    def _resolve_variables(self, args: Any, state: AgentState) -> Any:
        """
        递归解析参数中的变量占位符
        支持格式: 
        - $$step_1.data.xxx$$, $$step_2.output.data[0].id$$ 等（双美元符号）
        - {{step_1.data.xxx}}, {{step_2.data[0].stcd}} 等（双花括号，LLM有时会使用这种格式）
        """
        if isinstance(args, str):
            # 支持 $$...$$ 格式
            if args.startswith("$$") and args.endswith("$$"):
                var_path = args[2:-2]
                return self._get_value_by_path(var_path, state)
            # 支持 {{...}} 格式（LLM有时会使用这种格式）
            if args.startswith("{{") and args.endswith("}}"):
                var_path = args[2:-2]
                return self._get_value_by_path(var_path, state)
            return args
        elif isinstance(args, dict):
            return {k: self._resolve_variables(v, state) for k, v in args.items()}
        elif isinstance(args, list):
            return [self._resolve_variables(v, state) for v in args]
        return args

    def _get_value_by_path(self, path: str, state: AgentState) -> Any:
        """根据路径从状态中获取值"""
        # 使用正则提取步骤ID和后续路径
        # 支持多种格式：
        # - step_2[0].stcd, STEP_2[0].stcd, 2.data[0].stcd（LLM有时会省略step_前缀或使用大写）
        # - PREV[1].data[0].stcd（PREV[n]表示前n步的结果，PREV[1]表示上一步）

        execution_results = state.get('execution_results', [])
        current_step_index = state.get('current_step_index', 0)

        # 处理 PREV[n] 格式
        prev_match = re.match(r"[Pp][Rr][Ee][Vv]\[(\d+)\]((?:[\.\[].*)?$)", path)
        if prev_match:
            prev_offset = int(prev_match.group(1))
            remaining_path = prev_match.group(2)
            # PREV[1] 表示上一步，即 current_step_index - 1 对应的步骤
            # 但 execution_results 是按执行顺序存储的，所以取倒数第 prev_offset 个
            if len(execution_results) >= prev_offset:
                target_result = execution_results[-prev_offset]
                return self._extract_value_from_result(target_result, remaining_path)
            else:
                logger.warning(f"PREV[{prev_offset}] 超出已执行步骤范围")
                return None

        # 处理 step_X 格式
        match = re.match(r"(?:[Ss][Tt][Ee][Pp]_)?(\d+)((?:[\.\[].*)?$)", path)
        if not match:
            return None

        step_id_str = match.group(1)
        remaining_path = match.group(2)

        try:
            target_step_id = int(step_id_str)

            # 查找对应步骤的结果（从后往前查找，确保获取当前轮次的结果）
            target_result = next((r for r in reversed(execution_results) if r.get('step_id') == target_step_id), None)

            if not target_result:
                logger.warning(f"未找到步骤 {target_step_id} 的执行结果")
                return None

            return self._extract_value_from_result(target_result, remaining_path)
        except Exception as e:
            logger.error(f"解析路径 {path} 出错: {e}")
            return None

    def _extract_value_from_result(self, target_result: Dict, remaining_path: str) -> Any:
        """从执行结果中提取值"""
        # 获取 output (这是一个 ToolResult 字典，包含 success, data, error 等)
        current_val = target_result.get('output')

        if not remaining_path:
            return current_val

        # 兼容性处理：如果 output 是 ToolResult 结构且包含 data 字段
        # 如果路径不是明确请求 data 或以 .data 开头，我们默认进入 data
        if isinstance(current_val, dict) and 'data' in current_val:
            if not (remaining_path.startswith('.data.') or remaining_path == '.data' or remaining_path.startswith('.data[')):
                current_val = current_val.get('data')

        # 常见字段别名映射（LLM可能使用不同的名称）
        alias_map = {
            'result_code': 'stcd', 'code': 'stcd', 'station_code': 'stcd',
            'result_name': 'stnm', 'name': 'stnm', 'station_name': 'stnm',
        }
        # 检查路径中是否有别名需要替换
        for alias, real in alias_map.items():
            remaining_path = remaining_path.replace(f'.{alias}', f'.{real}')

        # 处理剩余路径（属性访问 .xxx 和索引访问 [idx]）
        ops = re.findall(r"\.([^.\[\]]+)|\[(\d+)\]", remaining_path)

        for attr, index in ops:
            if current_val is None:
                return None

            if attr: # 普通属性
                if isinstance(current_val, dict):
                    current_val = current_val.get(attr)
                elif hasattr(current_val, attr):
                    current_val = getattr(current_val, attr)
                else:
                    return None
            elif index: # 索引
                idx = int(index)
                if isinstance(current_val, (list, tuple)) and len(current_val) > idx:
                    current_val = current_val[idx]
                else:
                    return None

        return current_val


# 创建全局Executor实例
_executor_instance: Optional[Executor] = None


def get_executor() -> Executor:
    """获取Executor单例"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = Executor()
    return _executor_instance


async def executor_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph节点函数 - 执行节点
    
    执行当前计划步骤
    """
    executor = get_executor()
    
    plan = state.get('plan', [])
    current_index = state.get('current_step_index', 0)
    
    if current_index >= len(plan):
        logger.info("所有步骤执行完成")
        return {
            "next_action": "respond"
        }
    
    # 获取当前步骤
    current_step = plan[current_index]
    
    # 检查依赖是否满足
    dependencies = current_step.get('dependencies', [])
    execution_results = state.get('execution_results', [])
    completed_ids = {r.get('step_id') for r in execution_results if r.get('success')}
    
    if not all(dep_id in completed_ids for dep_id in dependencies):
        logger.warning(f"步骤 {current_step.get('step_id')} 的依赖未满足")
        # 跳过当前步骤或等待
        return {
            "error": "依赖步骤未完成",
            "should_retry": True
        }
    
    # 执行步骤
    result = await executor.execute_step(current_step, state)
    
    # 更新步骤状态
    current_step['status'] = StepStatus.COMPLETED.value if result.success else StepStatus.FAILED.value
    plan[current_index] = current_step
    
    # 处理执行失败
    if not result.success:
        retry_decision = await executor.handle_retry(current_step, result.error, state)
        
        if retry_decision['should_retry']:
            return {
                "plan": plan,
                "should_retry": True,
                "error": result.error
            }
        else:
            # 失败后继续下一步或结束
            return {
                "plan": plan,
                "current_step_index": current_index + 1,
                "execution_results": [result.model_dump()],
                "error": result.error,
                "next_action": "execute" if current_index + 1 < len(plan) else "respond"
            }
    
    # 执行成功，继续下一步
    next_index = current_index + 1
    has_more_steps = next_index < len(plan)
    
    # 检查是否有异步任务需要等待
    if current_step.get('is_async') and result.output:
        # 异步任务返回任务ID
        return {
            "plan": plan,
            "current_step_index": next_index,
            "execution_results": [result.model_dump()],
            "async_task_ids": [result.output],
            "next_action": "wait_async"
        }
    
    return {
        "plan": plan,
        "current_step_index": next_index,
        "execution_results": [result.model_dump()],
        "next_action": "execute" if has_more_steps else "respond"
    }
