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
from .planner import planner_node, get_planner
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


def should_continue(state: AgentState) -> Literal["plan", "execute", "respond", "wait_async", "end"]:
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
    工作流执行节点
    
    如果匹配到预定义工作流，执行固定工作流
    """
    logger.info("检查工作流执行...")
    
    matched_workflow = state.get('matched_workflow')
    
    if not matched_workflow:
        # 没有匹配的工作流，跳过
        return {}
    
    logger.info(f"执行工作流: {matched_workflow}")
    
    # TODO: 从workflows模块获取工作流定义并执行
    # from ..workflows import execute_workflow
    # result = await execute_workflow(matched_workflow, state)
    
    # 工作流执行后，更新计划
    # 这里返回工作流生成的执行计划
    return {
        "next_action": "execute"
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
    规划节点路由函数（三大类分类）

    根据意图类别决定下一步走向：
    - chat: 快速对话
    - knowledge: 知识库检索
    - business: 业务执行（模板或动态规划）
    """
    intent_category = state.get('intent_category')
    next_action = state.get('next_action')

    # 第1类：chat - 快速对话
    if intent_category == IntentCategory.CHAT.value or next_action == 'quick_respond':
        return "quick_chat"

    # 第2类：knowledge - 知识库检索
    if intent_category == IntentCategory.KNOWLEDGE.value or next_action == 'knowledge_rag':
        return "knowledge_rag"

    # 第3类：business - 业务执行
    if intent_category == IntentCategory.BUSINESS.value:
        # 匹配到模板，直接执行
        if state.get('matched_workflow'):
            return "workflow"
        # 未匹配，走动态规划后执行
        return "execute"

    # 默认走知识库检索
    return "knowledge_rag"


def create_agent_graph() -> StateGraph:
    """
    创建智能体状态图（三大类分类架构）

    流程：
    - 第1类 chat: plan → quick_chat → END
    - 第2类 knowledge: plan → knowledge_rag → respond → END
    - 第3类 business:
        - 匹配模板: plan → workflow → execute → respond → END
        - 动态规划: plan → execute → respond → END

    Returns:
        配置好的StateGraph实例
    """
    logger.info("创建智能体状态图...")

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("plan", planner_node)
    workflow.add_node("quick_chat", quick_chat_node)
    workflow.add_node("knowledge_rag", knowledge_rag_node)  # 新增：知识库检索节点
    workflow.add_node("workflow", workflow_executor_node)
    workflow.add_node("execute", executor_node)
    workflow.add_node("wait_async", async_wait_node)
    workflow.add_node("respond", controller_node)

    # 设置入口点
    workflow.set_entry_point("plan")

    # 添加条件边 - 规划后的三大类路由
    workflow.add_conditional_edges(
        "plan",
        plan_router,
        {
            "quick_chat": "quick_chat",      # 第1类：chat
            "knowledge_rag": "knowledge_rag", # 第2类：knowledge
            "workflow": "workflow",           # 第3类：business（模板匹配）
            "execute": "execute"              # 第3类：business（动态规划）
        }
    )

    # 快速对话直接结束
    workflow.add_edge("quick_chat", END)

    # 知识库检索后直接响应
    workflow.add_edge("knowledge_rag", "respond")

    # 工作流后进入执行
    workflow.add_edge("workflow", "execute")

    # 执行节点的条件路由
    workflow.add_conditional_edges(
        "execute",
        should_continue,
        {
            "execute": "execute",
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
                    # 规划节点 - 发送意图识别结果
                    intent = node_output.get('intent')
                    confidence = node_output.get('intent_confidence', 0)
                    
                    if intent:
                        yield {
                            "type": "intent",
                            "node": node_name,
                            "intent": intent,
                            "confidence": confidence,
                            "progress": progress,
                            "state": {
                                "intent": intent,
                                "current_step": 0,
                                "total_steps": 0,
                                "next_action": node_output.get('next_action')
                            }
                        }
                    
                    # 如果有执行计划，发送计划事件
                    plan = node_output.get('plan', [])
                    if plan:
                        yield {
                            "type": "plan",
                            "node": node_name,
                            "steps": [
                                {
                                    "step_id": step.get('step_id', i+1),
                                    "description": step.get('description', ''),
                                    "tool_name": step.get('tool_name')
                                }
                                for i, step in enumerate(plan)
                            ],
                            "progress": progress,
                            "state": {
                                "intent": intent,
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
                        
                        # 发送步骤开始事件
                        if step_id not in sent_steps:
                            yield {
                                "type": "step_start",
                                "node": node_name,
                                "step_id": step_id,
                                "description": current_step.get('description', ''),
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
                            yield {
                                "type": "step_end",
                                "node": node_name,
                                "step_id": result_step_id,
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
