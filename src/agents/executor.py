"""
Executor - 任务执行器
负责执行计划中的各个步骤，调用工具，处理异步任务
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import time

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..config.settings import settings
from ..config.logging_config import get_logger
from .state import AgentState, PlanStep, ExecutionResult, StepStatus

logger = get_logger(__name__)


class Executor:
    """任务执行器"""
    
    def __init__(self):
        """初始化执行器"""
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_model_name,
            temperature=0.7
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
        
        logger.info(f"执行步骤 {step_id}: {description}")
        start_time = time.time()
        
        try:
            # 如果没有指定工具，使用LLM直接处理
            if not tool_name:
                output = await self._execute_with_llm(description, state)
            else:
                # 查找并执行工具
                output = await self._execute_tool(tool_name, tool_args, state)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            logger.info(f"步骤 {step_id} 执行成功，耗时 {execution_time}ms")
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
        
        # 执行工具（支持同步和异步）
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**tool_args)
        else:
            result = tool_func(**tool_args)
        
        return result
    
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
        prompt = ChatPromptTemplate.from_template("""你是卫共流域数字孪生系统的智能助手。

## 任务
{task_description}

## 用户原始消息
{user_message}

## 已有执行结果
{execution_results}

## 检索到的知识
{retrieved_documents}

请根据以上信息完成任务，给出清晰、准确的回答。
""")
        
        chain = prompt | self.llm
        
        # 格式化已有结果
        results_str = self._format_execution_results(state.get('execution_results', []))
        docs_str = self._format_retrieved_documents(state.get('retrieved_documents', []))
        
        response = await chain.ainvoke({
            "task_description": task_description,
            "user_message": state.get('user_message', ''),
            "execution_results": results_str or "无",
            "retrieved_documents": docs_str or "无"
        })
        
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
        
        return "\n".join(formatted)
    
    def _format_retrieved_documents(self, documents: List[Dict[str, Any]]) -> str:
        """格式化检索到的文档"""
        if not documents:
            return ""
        
        formatted = []
        for i, doc in enumerate(documents[:5], 1):  # 最多5个
            content = doc.get('content', '')[:500]  # 截断
            source = doc.get('source', '未知来源')
            formatted.append(f"[{i}] {source}: {content}")
        
        return "\n\n".join(formatted)


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
