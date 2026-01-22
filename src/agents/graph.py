"""
LangGraph状态图定义
整合Planner、Executor、Controller，构建完整的智能体工作流
"""

from typing import Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from ..config.logging_config import get_logger
from ..config.settings import settings
from ..config.llm_prompt_logger import start_session, end_session
from .state import AgentState, create_initial_state, OutputType, IntentCategory
from .planner import planner_node, sub_intent_node, workflow_match_node, get_planner
from .executor import executor_node, get_executor
from .controller import controller_node, get_controller
from ..rag.retriever import get_rag_retriever
from ..tools.mcp_websearch import mcp_web_search, is_mcp_websearch_enabled

logger = get_logger(__name__)


# 快速对话提示词模板
QUICK_CHAT_PROMPT = """你是卫共流域数字孪生系统的智能助手"小卫"。

你的职责是：
1. 友好地与用户进行日常对话
2. 简要介绍自己的能力（流域介绍、工程查询、水雨情查询、洪水预报、洪水预演等）
3. 简要引导用户提出与流域相关的问题

用户消息: {user_message}

请用简洁友好的语气回复用户，回复不要太长（控制在100字以内）。"""


def should_continue(state: AgentState) -> Literal["plan", "execute", "workflow", "respond", "wait_async", "end"]:
    """
    路由函数：决定下一步动作

    Args:
        state: 当前状态

    Returns:
        下一步动作
    """
    next_action = state.get('next_action', 'plan')

    # 检查是否有致命错误
    if state.get('error') and not state.get('should_retry'):
        # 有错误且不需要重试，直接生成响应
        return "respond"

    # 检查重试
    if state.get('should_retry'):
        return "execute"

    # 支持 workflow 节点的循环执行
    if next_action == 'workflow':
        return "workflow"

    return next_action


async def rag_retrieval_node(state: AgentState) -> Dict[str, Any]:
    """
    RAG检索节点（用于业务场景的辅助检索）

    当RAG检索失败或无法获取到信息时，会尝试使用网络搜索作为备选方案。
    """
    logger.info("执行RAG检索...")

    intent_category = state.get('intent_category', '')
    user_message = state.get('user_message', '')

    retrieved_docs = []
    retrieval_source = "rag"

    try:
        rag_retriever = get_rag_retriever()
        retrieved_docs = await rag_retriever.retrieve(
            query=user_message,
            top_k=5
        )
        logger.info(f"RAG检索完成，获取到 {len(retrieved_docs)} 条结果")

    except Exception as e:
        logger.error(f"RAG检索异常: {e}")

    # RAG无结果时尝试网络搜索
    if not retrieved_docs and is_mcp_websearch_enabled():
        logger.info("RAG无结果，尝试网络搜索...")
        try:
            web_results = await mcp_web_search(user_message, max_results=5)
            if web_results:
                retrieved_docs = [
                    {
                        'content': r.get('content', r.get('snippet', '')),
                        'metadata': {
                            'category': '网络搜索',
                            'source': r.get('url', r.get('link', '')),
                            'title': r.get('title', '')
                        }
                    }
                    for r in web_results
                ]
                retrieval_source = "mcp_websearch"
        except Exception as e:
            logger.error(f"网络搜索异常: {e}")

    return {
        "retrieved_documents": retrieved_docs,
        "retrieval_source": retrieval_source
    }


async def knowledge_rag_node(state: AgentState) -> Dict[str, Any]:
    """
    知识库检索节点（第2类：固有知识查询专用）

    根据意图分析结果决定是否进行知识库检索和网络搜索
    """
    user_message = state.get('user_message', '')
    # 优先使用补全后的查询，如果没有则使用原始消息
    search_query = state.get('rewritten_query') or user_message
    target_kbs = state.get('target_kbs', [])
    needs_kb_search = state.get('needs_kb_search', True)
    needs_web_search = state.get('needs_web_search', False)
    retrieved_docs = []
    retrieval_source = None

    logger.info(f"知识库检索: {search_query[:30]}... (KB={needs_kb_search}, Web={needs_web_search})")

    try:
        # 1. 知识库检索（如果需要）
        if needs_kb_search:
            rag_retriever = get_rag_retriever()
            retrieved_docs = await rag_retriever.retrieve(
                query=search_query,
                top_k=5,
                target_kbs=target_kbs
            )
            if retrieved_docs:
                retrieval_source = "rag"

        # 2. 网络搜索（如果需要）
        if needs_web_search and is_mcp_websearch_enabled():
            logger.info("执行网络搜索...")
            try:
                web_results = await mcp_web_search(search_query, max_results=5)
                if web_results:
                    web_docs = [
                        {
                            'content': r.get('content', r.get('snippet', '')),
                            'metadata': {
                                'category': '网络搜索',
                                'source': r.get('url', r.get('link', '')),
                                'title': r.get('title', '')
                            },
                            'score': 0.8
                        }
                        for r in web_results
                    ]
                    logger.info(f"网络搜索完成，获取到 {len(web_docs)} 条结果")
                    # 合并结果：网络搜索结果在前
                    retrieved_docs = web_docs + retrieved_docs
                    retrieval_source = "web_search" if not needs_kb_search else "rag+web_search"
            except Exception as e:
                logger.error(f"网络搜索异常: {e}")

        return {
            "retrieved_documents": retrieved_docs,
            "retrieval_source": retrieval_source,
            "next_action": "respond"
        }

    except Exception as e:
        logger.error(f"知识库检索异常: {e}")
        return {
            "retrieved_documents": [],
            "retrieval_source": None,
            "error": f"知识库检索失败: {str(e)}",
            "next_action": "respond"
        }


async def workflow_executor_node(state: AgentState) -> Dict[str, Any]:
    """
    工作流执行节点（支持单步执行模式）

    执行模式：
    1. 单步执行模式（supports_step_execution=True）：
       - 每次执行一个步骤，返回后让图循环
       - 支持流式显示每个步骤的进度
       - 为后续错误回滚和替代方案提供基础
    2. 批量执行模式（supports_step_execution=False）：
       - 一次性执行所有步骤
       - 适用于简单工作流或不需要流式显示的场景
    """
    from ..workflows.registry import get_workflow_registry
    import time

    logger.info("检查工作流执行...")

    matched_workflow = state.get('matched_workflow')

    if not matched_workflow:
        # 没有匹配的工作流，跳过
        return {}

    logger.info(f"执行工作流: {matched_workflow}")

    # 从工作流注册表获取工作流实例
    workflow_registry = get_workflow_registry()
    workflow = workflow_registry.get_workflow(matched_workflow)

    if not workflow:
        logger.error(f"未找到工作流: {matched_workflow}")
        return {
            "error": f"未找到工作流: {matched_workflow}",
            "next_action": "respond"
        }

    try:
        # 检查是否支持单步执行模式
        if workflow.supports_step_execution:
            return await _execute_workflow_step(workflow, state)
        else:
            # 批量执行模式（保持原有逻辑）
            logger.info(f"开始批量执行工作流: {workflow.name}")
            result = await workflow.execute(state)
            logger.info(f"工作流 {workflow.name} 执行完成")
            return result

    except Exception as e:
        logger.error(f"工作流 {matched_workflow} 执行异常: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": f"工作流执行异常: {str(e)}",
            "next_action": "respond"
        }


async def _execute_workflow_step(workflow, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    执行工作流的单个步骤

    Args:
        workflow: 工作流实例
        state: 当前状态

    Returns:
        更新后的状态
    """
    import time
    import asyncio

    # 步骤执行最小时间间隔（毫秒），防止接口调用过快导致后台服务卡顿
    MIN_STEP_INTERVAL_MS = 200

    current_step_index = state.get('current_step_index', 0)
    plan = state.get('plan', [])
    execution_results = state.get('execution_results', [])
    workflow_context = state.get('workflow_context', {})

    total_steps = len(plan)

    # 检查是否需要初始化（第一步执行前）
    if current_step_index == 0 and not workflow_context:
        logger.info(f"初始化工作流 {workflow.name} 执行环境")
        init_result = await workflow.prepare_execution(state)
        workflow_context = init_result.get('workflow_context', {})
        # 初始化完成后，返回初始化结果，让状态更新后再执行第一步
        # 这样可以确保 workflow_context 被正确保存到状态中
        return {
            'workflow_context': workflow_context,
            'workflow_status': init_result.get('workflow_status', 'running'),
            'current_step_index': 0,  # 保持在第一步
            'next_action': 'workflow'  # 继续执行工作流
        }

    # 检查是否已完成所有步骤
    if current_step_index >= total_steps:
        logger.info(f"工作流 {workflow.name} 所有步骤已完成，执行收尾")
        final_result = await workflow.finalize_execution(state)
        return {
            **final_result,
            'workflow_completed': True,
            'next_action': 'respond'
        }

    # 获取当前步骤信息
    current_step = plan[current_step_index]
    step_id = current_step.get('step_id', current_step_index + 1)
    step_name = current_step.get('name', current_step.get('description', f'步骤{step_id}'))

    logger.info(f"执行工作流 {workflow.name} 步骤 {step_id}/{total_steps}: {step_name}")

    # 记录步骤开始时间
    start_time = time.time()

    try:
        # 执行单个步骤
        step_result = await workflow.execute_step(state, current_step_index)

        # 计算执行时间
        execution_time_ms = int((time.time() - start_time) * 1000)

        # 确保步骤执行满足最小时间间隔，防止接口调用过快
        if execution_time_ms < MIN_STEP_INTERVAL_MS:
            wait_time_ms = MIN_STEP_INTERVAL_MS - execution_time_ms
            await asyncio.sleep(wait_time_ms / 1000.0)

        # 构建步骤执行结果
        step_execution_result = {
            'step_id': step_id,
            'step_name': step_name,
            'tool_name': current_step.get('tool_name'),
            'success': step_result.get('success', True),
            'execution_time_ms': execution_time_ms,
            'result': step_result.get('result'),
            'error': step_result.get('error')
        }

        # 注意：execution_results 使用 Annotated[..., add]，LangGraph 会自动累加
        # 因此只需返回新增的步骤结果，不需要手动拼接完整列表
        new_step_results = [step_execution_result]

        # 更新工作流上下文
        new_workflow_context = {
            **workflow_context,
            **step_result.get('workflow_context', {})
        }

        # 检查步骤是否成功
        if not step_result.get('success', True):
            logger.warning(f"步骤 {step_id} 执行失败: {step_result.get('error')}")
            # 步骤失败，可以在这里添加重试或替代方案逻辑
            # 目前直接继续下一步或终止

        # 检查工作流是否提前完成
        if step_result.get('workflow_completed', False):
            logger.info(f"工作流 {workflow.name} 提前完成")
            return {
                'execution_results': new_step_results,
                'workflow_context': new_workflow_context,
                'current_step_index': total_steps,  # 标记为完成
                'workflow_completed': True,
                'next_action': 'respond',
                **step_result.get('final_state', {})
            }

        # 返回更新后的状态，继续下一步
        next_step_index = current_step_index + 1
        is_last_step = next_step_index >= total_steps

        # 如果是最后一步，调用 finalize_execution 获取最终状态（包括 generated_page_url）
        if is_last_step:
            logger.info(f"工作流 {workflow.name} 最后一步执行完成，执行收尾")
            # 构建临时状态用于 finalize_execution
            temp_state = {
                **state,
                'workflow_context': new_workflow_context,
                'current_step_index': next_step_index
            }
            final_result = await workflow.finalize_execution(temp_state)
            return {
                'execution_results': new_step_results,
                'workflow_context': new_workflow_context,
                'current_step_index': next_step_index,
                'workflow_completed': True,
                'next_action': 'respond',
                # 合并 finalize_execution 的结果（包括 generated_page_url, extracted_result 等）
                **{k: v for k, v in final_result.items()
                   if k not in ['workflow_context', 'current_step_index', 'workflow_completed', 'next_action']},
                # 传递步骤结果中的其他状态
                **{k: v for k, v in step_result.items()
                   if k not in ['success', 'result', 'error', 'workflow_context', 'workflow_completed', 'final_state']}
            }

        return {
            'execution_results': new_step_results,
            'workflow_context': new_workflow_context,
            'current_step_index': next_step_index,
            'workflow_completed': False,
            'next_action': 'workflow',  # 继续执行下一步
            # 传递步骤结果中的其他状态
            **{k: v for k, v in step_result.items()
               if k not in ['success', 'result', 'error', 'workflow_context', 'workflow_completed', 'final_state']}
        }

    except Exception as e:
        logger.error(f"步骤 {step_id} 执行异常: {e}")
        import traceback
        traceback.print_exc()

        execution_time_ms = int((time.time() - start_time) * 1000)

        # 记录失败的步骤
        step_execution_result = {
            'step_id': step_id,
            'step_name': step_name,
            'tool_name': current_step.get('tool_name'),
            'success': False,
            'execution_time_ms': execution_time_ms,
            'result': None,
            'error': str(e)
        }

        # 注意：execution_results 使用 Annotated[..., add]，只返回新增的步骤结果
        new_step_results = [step_execution_result]

        return {
            'execution_results': new_step_results,
            'workflow_context': workflow_context,
            'current_step_index': current_step_index + 1,
            'error': f"步骤 {step_id} 执行异常: {str(e)}",
            'next_action': 'respond'
        }


async def quick_chat_node(state: AgentState) -> Dict[str, Any]:
    """
    快速对话节点
    
    对于一般闲聊，直接使用意图分析时LLM已生成的回复，不再调用LLM
    """
    logger.info("执行快速对话响应...")
    
    # 直接使用意图分析时LLM已生成的直接回复
    direct_response = state.get('direct_response')
    if direct_response:
        logger.info("使用意图分析时生成的直接回复，跳过LLM调用")
        return {
            "final_response": direct_response,
            "output_type": OutputType.TEXT.value,
            "next_action": "end"
        }
    
    # 兜底：如果没有直接回复，返回默认回复（不再调用LLM，避免额外耗时）
    logger.warning("未找到直接回复，使用默认回复")
    return {
        "final_response": "你好！我是卫共流域数字孪生系统的智能助手小卫，有什么可以帮助您的吗？",
        "output_type": OutputType.TEXT.value,
        "next_action": "end"
    }


async def async_wait_node(state: AgentState) -> Dict[str, Any]:
    """
    异步任务等待节点
    
    等待异步任务完成
    """
    import asyncio
    from ..config.settings import settings
    
    logger.info("等待异步任务...")
    
    async_task_ids = state.get('async_task_ids', [])
    pending_results = state.get('pending_async_results', {})
    
    if not async_task_ids:
        return {"next_action": "respond"}
    
    executor = get_executor()
    max_wait_time = 60  # 最大等待60秒
    poll_interval = settings.task_polling_interval_seconds
    
    elapsed = 0
    while elapsed < max_wait_time:
        all_completed = True
        
        for task_id in async_task_ids:
            if task_id not in pending_results:
                status = await executor.check_async_task_status(task_id)
                
                if status['status'] == 'completed':
                    pending_results[task_id] = status['result']
                elif status['status'] == 'failed':
                    pending_results[task_id] = {'error': status.get('error', '任务失败')}
                else:
                    all_completed = False
        
        if all_completed:
            break
        
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    
    # 检查是否超时
    if elapsed >= max_wait_time:
        logger.warning("异步任务等待超时")
        return {
            "pending_async_results": pending_results,
            "error": "异步任务等待超时",
            "next_action": "respond"
        }
    
    return {
        "pending_async_results": pending_results,
        "next_action": "respond"
    }


def plan_router(state: AgentState) -> str:
    """
    规划节点路由函数（第1阶段：意图分类后的路由）

    根据意图类别决定下一步走向：
    - chat: 快速对话
    - knowledge: 知识库检索
    - business: 进入第2阶段子意图分类
    """
    intent_category = state.get('intent_category')
    next_action = state.get('next_action')

    # 第1类：chat - 快速对话
    if intent_category == IntentCategory.CHAT.value or next_action == 'quick_respond':
        return "quick_chat"

    # 第2类：knowledge - 知识库检索
    if intent_category == IntentCategory.KNOWLEDGE.value or next_action == 'knowledge_rag':
        return "knowledge_rag"

    # 第3类：business - 进入第2阶段子意图分类
    if intent_category == IntentCategory.BUSINESS.value or next_action == 'sub_intent':
        return "sub_intent"

    # 默认走知识库检索
    return "knowledge_rag"


def sub_intent_router(state: AgentState) -> str:
    """
    子意图分类节点路由函数（第2阶段完成后的路由）

    始终进入第3阶段工作流匹配
    """
    return "workflow_match"


def workflow_match_router(state: AgentState) -> str:
    """
    工作流匹配节点路由函数（第3阶段完成后的路由）

    根据匹配结果决定下一步：
    - 匹配到模板: workflow
    - 未匹配（动态规划）: execute
    """
    # 匹配到模板，直接执行
    if state.get('matched_workflow') or state.get('saved_workflow_id'):
        return "workflow"
    # 未匹配，走动态规划后执行
    return "execute"


def create_agent_graph() -> StateGraph:
    """
    创建智能体状态图（三阶段意图识别架构）

    流程：
    - 第1类 chat: plan → quick_chat → END
    - 第2类 knowledge: plan → knowledge_rag → respond → END
    - 第3类 business:
        - plan → sub_intent → workflow_match → workflow → respond → END (模板匹配)
        - plan → sub_intent → workflow_match → execute → respond → END (动态规划)

    Returns:
        配置好的StateGraph实例
    """
    logger.info("创建智能体状态图...")

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("plan", planner_node)                    # 第1阶段：意图分类
    workflow.add_node("sub_intent", sub_intent_node)           # 第2阶段：子意图分类
    workflow.add_node("workflow_match", workflow_match_node)   # 第3阶段：工作流匹配
    workflow.add_node("quick_chat", quick_chat_node)
    workflow.add_node("knowledge_rag", knowledge_rag_node)
    workflow.add_node("workflow", workflow_executor_node)
    workflow.add_node("execute", executor_node)
    workflow.add_node("wait_async", async_wait_node)
    workflow.add_node("respond", controller_node)

    # 设置入口点
    workflow.set_entry_point("plan")

    # 添加条件边 - 第1阶段：意图分类后的路由
    workflow.add_conditional_edges(
        "plan",
        plan_router,
        {
            "quick_chat": "quick_chat",      # 第1类：chat
            "knowledge_rag": "knowledge_rag", # 第2类：knowledge
            "sub_intent": "sub_intent"        # 第3类：business → 进入第2阶段
        }
    )

    # 第2阶段：子意图分类后进入第3阶段
    workflow.add_edge("sub_intent", "workflow_match")

    # 添加条件边 - 第3阶段：工作流匹配后的路由
    workflow.add_conditional_edges(
        "workflow_match",
        workflow_match_router,
        {
            "workflow": "workflow",   # 模板匹配
            "execute": "execute"      # 动态规划
        }
    )

    # 快速对话直接结束
    workflow.add_edge("quick_chat", END)

    # 知识库检索后直接响应
    workflow.add_edge("knowledge_rag", "respond")

    # 工作流节点的条件路由（工作流执行完成后根据 next_action 决定下一步）
    workflow.add_conditional_edges(
        "workflow",
        should_continue,
        {
            "workflow": "workflow",    # 单步执行模式：继续执行下一步
            "execute": "execute",      # 工作流需要额外执行步骤
            "wait_async": "wait_async", # 等待异步任务
            "respond": "respond",       # 工作流执行完成，直接响应
            "plan": "plan",
            "end": END
        }
    )

    # 执行节点的条件路由
    workflow.add_conditional_edges(
        "execute",
        should_continue,
        {
            "execute": "execute",
            "workflow": "workflow",    # 支持从 execute 返回 workflow
            "wait_async": "wait_async",
            "respond": "respond",
            "plan": "plan",
            "end": END
        }
    )

    # 异步等待后生成响应
    workflow.add_edge("wait_async", "respond")

    # 响应节点结束
    workflow.add_edge("respond", END)

    logger.info("智能体状态图创建完成")

    return workflow


# 全局图实例
_graph_instance: Optional[StateGraph] = None
_compiled_graph = None


def reset_agent_graph():
    """重置智能体图（用于热重载）"""
    global _graph_instance, _compiled_graph
    _graph_instance = None
    _compiled_graph = None
    logger.info("智能体图已重置")


def get_agent_graph():
    """获取编译后的智能体图"""
    global _graph_instance, _compiled_graph
    
    if _compiled_graph is None:
        _graph_instance = create_agent_graph()
        # 使用内存检查点保存器
        memory = MemorySaver()
        _compiled_graph = _graph_instance.compile(checkpointer=memory)
        logger.info("智能体图编译完成")
    
    return _compiled_graph


async def run_agent(
    conversation_id: str,
    user_message: str,
    user_id: Optional[str] = None,
    chat_history: Optional[list] = None,
    context_summary: Optional[str] = None
) -> Dict[str, Any]:
    """
    运行智能体（非流式）
    
    Args:
        conversation_id: 会话ID
        user_message: 用户消息
        user_id: 用户ID
        chat_history: 聊天历史
        context_summary: 上下文摘要
        
    Returns:
        智能体响应
    """
    logger.info(f"运行智能体 - 会话: {conversation_id}")
    
    # 开始LLM提示词日志会话
    start_session(conversation_id, user_message)
    
    # 创建初始状态
    initial_state = create_initial_state(
        conversation_id=conversation_id,
        user_message=user_message,
        user_id=user_id,
        chat_history=chat_history,
        context_summary=context_summary
    )
    
    # 获取编译后的图
    graph = get_agent_graph()
    
    # 配置
    config = {
        "configurable": {
            "thread_id": conversation_id
        }
    }
    
    try:
        # 非流式执行
        final_state = await graph.ainvoke(initial_state, config)
        
        # 结束LLM提示词日志会话
        end_session()
        
        return {
            "conversation_id": conversation_id,
            "response": final_state.get('final_response', ''),
            "output_type": final_state.get('output_type', 'text'),
            "page_url": final_state.get('generated_page_url'),
            "page_task_id": final_state.get('page_task_id'),
            "page_generating": final_state.get('page_generating', False),
            "execution_steps": [
                {
                    "step_id": r.get('step_id'),
                    "success": r.get('success'),
                    "execution_time_ms": r.get('execution_time_ms')
                }
                for r in final_state.get('execution_results', [])
            ],
            "intent": final_state.get('intent'),
            "error": final_state.get('error')
        }
            
    except Exception as e:
        logger.error(f"智能体执行失败: {e}")
        return {
            "conversation_id": conversation_id,
            "response": f"抱歉，处理您的请求时遇到了问题: {str(e)}",
            "output_type": "text",
            "error": str(e)
        }


async def run_agent_stream(
    conversation_id: str,
    user_message: str,
    user_id: Optional[str] = None,
    chat_history: Optional[list] = None,
    context_summary: Optional[str] = None
):
    """
    流式运行智能体
    
    Args:
        conversation_id: 会话ID
        user_message: 用户消息
        user_id: 用户ID
        chat_history: 聊天历史
        context_summary: 上下文摘要
        
    Yields:
        执行事件，包含以下类型:
        - type: "intent" - 意图识别结果
        - type: "rag" - RAG检索结果
        - type: "plan" - 执行计划
        - type: "step_start" - 步骤开始
        - type: "step_end" - 步骤完成
        - type: "step" - 通用步骤进度
        - node: "final" - 最终响应
        - node: "error" - 错误
    """
    logger.info(f"流式运行智能体 - 会话: {conversation_id}")
    
    # 开始LLM提示词日志会话
    start_session(conversation_id, user_message)
    
    # 创建初始状态
    initial_state = create_initial_state(
        conversation_id=conversation_id,
        user_message=user_message,
        user_id=user_id,
        chat_history=chat_history,
        context_summary=context_summary
    )
    
    # 获取编译后的图
    graph = get_agent_graph()
    
    # 配置
    config = {
        "configurable": {
            "thread_id": conversation_id
        }
    }
    
    controller = get_controller()
    
    # 用于跟踪已发送的步骤
    sent_steps = set()
    last_step_index = -1
    
    try:
        async for event in graph.astream(initial_state, config):
            # 获取当前节点和状态
            for node_name, node_output in event.items():
                # 格式化流式响应
                progress = await controller.format_streaming_response(node_output)

                # 根据节点类型发送不同的事件
                if node_name == "plan":
                    # 第1阶段：意图分类节点
                    intent = node_output.get('intent')
                    confidence = node_output.get('intent_confidence', 0)
                    intent_category = node_output.get('intent_category', '')

                    # 调试日志
                    logger.info(f"[DEBUG] plan节点输出: intent={intent}, intent_category={intent_category}")

                    if intent_category:
                        yield {
                            "type": "intent_stage",
                            "node": node_name,
                            "stage": 1,
                            "stage_name": "intent_category",
                            "stage_label": "意图类别",
                            "intent_category": intent_category,
                            "confidence": confidence,
                            "progress": progress,
                            "state": {
                                "intent": intent,
                                "current_step": 0,
                                "total_steps": 0,
                                "next_action": node_output.get('next_action')
                            }
                        }

                elif node_name == "sub_intent":
                    # 第2阶段：子意图分类节点
                    business_sub_intent = node_output.get('business_sub_intent', '')

                    logger.info(f"[DEBUG] sub_intent节点输出: business_sub_intent={business_sub_intent}")

                    if business_sub_intent:
                        yield {
                            "type": "intent_stage",
                            "node": node_name,
                            "stage": 2,
                            "stage_name": "business_sub_intent",
                            "stage_label": "业务子意图",
                            "business_sub_intent": business_sub_intent,
                            "progress": progress,
                            "state": {
                                "intent": node_output.get('intent'),
                                "current_step": 0,
                                "total_steps": 0,
                                "next_action": node_output.get('next_action')
                            }
                        }

                elif node_name == "workflow_match":
                    # 第3阶段：工作流匹配节点
                    matched_workflow = node_output.get('matched_workflow') or node_output.get('saved_workflow_name') or ''
                    business_sub_intent = node_output.get('business_sub_intent') or node_output.get('intent') or ''
                    plan = node_output.get('plan', [])

                    logger.info(f"[DEBUG] workflow_match节点输出: matched_workflow={matched_workflow}, business_sub_intent={business_sub_intent}, plan_steps={len(plan)}")

                    yield {
                        "type": "intent_stage",
                        "node": node_name,
                        "stage": 3,
                        "stage_name": "workflow_match",
                        "stage_label": "工作流匹配",
                        "matched_workflow": matched_workflow,
                        "business_sub_intent": business_sub_intent,  # 传递子意图供前端显示
                        "progress": progress,
                        "state": {
                            "intent": node_output.get('intent'),
                            "current_step": 0,
                            "total_steps": len(plan),
                            "next_action": node_output.get('next_action')
                        }
                    }

                    # 如果有执行计划（动态规划），发送计划事件
                    if plan:
                        yield {
                            "type": "plan",
                            "node": node_name,
                            "steps": [
                                {
                                    "step_id": step.get('step_id', i+1),
                                    "description": step.get('name', step.get('description', '')),
                                    "tool_name": step.get('tool_name')
                                }
                                for i, step in enumerate(plan)
                            ],
                            "progress": progress,
                            "state": {
                                "intent": node_output.get('intent'),
                                "current_step": 0,
                                "total_steps": len(plan),
                                "next_action": node_output.get('next_action')
                            }
                        }

                elif node_name == "knowledge_rag":
                    # 知识库检索节点
                    retrieved_docs = node_output.get('retrieved_documents', [])
                    retrieval_source = node_output.get('retrieval_source', 'rag')

                    yield {
                        "type": "rag",
                        "node": node_name,
                        "doc_count": len(retrieved_docs),
                        "source": retrieval_source,
                        "progress": progress,
                        "state": {
                            "intent": node_output.get('intent'),
                            "intent_category": node_output.get('intent_category'),
                            "current_step": 0,
                            "total_steps": 0,
                            "next_action": node_output.get('next_action')
                        }
                    }
                
                elif node_name == "execute":
                    # 执行节点 - 发送步骤执行状态
                    current_step_index = node_output.get('current_step_index', 0)
                    plan = node_output.get('plan', [])
                    execution_results = node_output.get('execution_results', [])
                    
                    # 检查是否有新步骤开始
                    if current_step_index > last_step_index and current_step_index < len(plan):
                        current_step = plan[current_step_index]
                        step_id = current_step.get('step_id', current_step_index + 1)
                        step_name = current_step.get('name', current_step.get('description', f'步骤{step_id}'))

                        # 发送步骤开始事件
                        if step_id not in sent_steps:
                            yield {
                                "type": "step_start",
                                "node": node_name,
                                "step_id": step_id,
                                "name": step_name,  # 简短名称
                                "description": step_name,  # 前端会添加步骤编号前缀
                                "tool_name": current_step.get('tool_name'),
                                "progress": progress,
                                "state": {
                                    "intent": node_output.get('intent'),
                                    "current_step": current_step_index,
                                    "total_steps": len(plan),
                                    "next_action": node_output.get('next_action')
                                }
                            }
                            sent_steps.add(step_id)

                        last_step_index = current_step_index

                    # 检查是否有步骤完成
                    for result in execution_results:
                        result_step_id = result.get('step_id')
                        if result_step_id and f"done_{result_step_id}" not in sent_steps:
                            result_step_name = result.get('step_name', f'步骤{result_step_id}')
                            yield {
                                "type": "step_end",
                                "node": node_name,
                                "step_id": result_step_id,
                                "name": result_step_name,  # 简短名称
                                "description": result_step_name,  # 前端会添加步骤编号前缀
                                "success": result.get('success', False),
                                "result_summary": str(result.get('result', ''))[:200] if result.get('result') else '',
                                "execution_time_ms": result.get('execution_time_ms', 0),
                                "progress": progress,
                                "state": {
                                    "intent": node_output.get('intent'),
                                    "current_step": current_step_index,
                                    "total_steps": len(plan),
                                    "next_action": node_output.get('next_action')
                                }
                            }
                            sent_steps.add(f"done_{result_step_id}")
                
                elif node_name == "quick_chat":
                    # 快速对话节点 - 直接发送最终响应
                    if node_output.get('final_response'):
                        # 结束LLM提示词日志会话
                        end_session()
                        yield {
                            "node": "final",
                            "response": node_output.get('final_response'),
                            "output_type": node_output.get('output_type', 'text'),
                            "page_url": node_output.get('generated_page_url'),
                            "page_task_id": node_output.get('page_task_id'),
                            "page_generating": node_output.get('page_generating', False)
                        }

                elif node_name == "respond":
                    # 响应节点 - 发送最终响应
                    if node_output.get('final_response'):
                        # 结束LLM提示词日志会话
                        end_session()
                        yield {
                            "node": "final",
                            "response": node_output.get('final_response'),
                            "output_type": node_output.get('output_type', 'text'),
                            "page_url": node_output.get('generated_page_url'),
                            "page_task_id": node_output.get('page_task_id'),
                            "page_generating": node_output.get('page_generating', False)
                        }

                elif node_name == "workflow":
                    # 工作流节点 - 发送步骤完成事件（前端自动处理闪烁）
                    current_step_index = node_output.get('current_step_index', 0)
                    plan = node_output.get('plan', [])
                    execution_results = node_output.get('execution_results', [])

                    # 发送步骤完成事件
                    for result in execution_results:
                        result_step_id = result.get('step_id')
                        if result_step_id and f"done_{result_step_id}" not in sent_steps:
                            result_step_name = result.get('step_name', f'步骤{result_step_id}')
                            yield {
                                "type": "step_end",
                                "node": node_name,
                                "step_id": result_step_id,
                                "name": result_step_name,
                                "description": result_step_name,
                                "success": result.get('success', False),
                                "result_summary": str(result.get('result', ''))[:200] if result.get('result') else '',
                                "execution_time_ms": result.get('execution_time_ms', 0),
                                "progress": progress,
                                "state": {
                                    "intent": node_output.get('intent'),
                                    "current_step": current_step_index,
                                    "total_steps": len(plan),
                                    "next_action": node_output.get('next_action')
                                }
                            }
                            sent_steps.add(f"done_{result_step_id}")

                    # 更新 last_step_index
                    if current_step_index > last_step_index:
                        last_step_index = current_step_index

                else:
                    # 其他节点 - 发送通用进度
                    yield {
                        "type": "step",
                        "node": node_name,
                        "progress": progress,
                        "state": {
                            "intent": node_output.get('intent'),
                            "current_step": node_output.get('current_step_index', 0),
                            "total_steps": len(node_output.get('plan', [])),
                            "next_action": node_output.get('next_action')
                        }
                    }
                
                # 如果是最终响应（兜底检查）
                if node_output.get('final_response') and node_name not in ['quick_chat', 'respond']:
                    yield {
                        "node": "final",
                        "response": node_output.get('final_response'),
                        "output_type": node_output.get('output_type', 'text'),
                        "page_url": node_output.get('generated_page_url'),
                        "page_task_id": node_output.get('page_task_id'),
                        "page_generating": node_output.get('page_generating', False)
                    }
                    
    except Exception as e:
        logger.error(f"流式执行失败: {e}")
        yield {
            "node": "error",
            "error": str(e)
        }
