"""
LangGraph状态图定义
整合Planner、Executor、Controller，构建完整的智能体工作流
"""

from typing import Dict, Any, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from ..config.logging_config import get_logger
from .state import AgentState, create_initial_state
from .planner import planner_node, get_planner
from .executor import executor_node, get_executor
from .controller import controller_node, get_controller

logger = get_logger(__name__)


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
    RAG检索节点
    
    根据用户问题和意图，从知识库中检索相关文档
    """
    logger.info("执行RAG检索...")
    
    # TODO: 实现完整的RAG检索逻辑
    # 这里预留接口，后续在rag模块实现
    
    intent = state.get('intent', '')
    
    # 只对知识问答类意图进行检索
    if intent in ['knowledge_qa', 'general_chat']:
        # 模拟检索结果
        retrieved_docs = []
        
        # TODO: 调用ChromaDB检索
        # from ..rag import search_knowledge
        # retrieved_docs = await search_knowledge(state['user_message'])
        
        return {
            "retrieved_documents": retrieved_docs
        }
    
    return {"retrieved_documents": []}


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


def create_agent_graph() -> StateGraph:
    """
    创建智能体状态图
    
    Returns:
        配置好的StateGraph实例
    """
    logger.info("创建智能体状态图...")
    
    # 创建状态图
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("plan", planner_node)
    workflow.add_node("rag", rag_retrieval_node)
    workflow.add_node("workflow", workflow_executor_node)
    workflow.add_node("execute", executor_node)
    workflow.add_node("wait_async", async_wait_node)
    workflow.add_node("respond", controller_node)
    
    # 设置入口点
    workflow.set_entry_point("plan")
    
    # 添加条件边
    workflow.add_conditional_edges(
        "plan",
        lambda state: "workflow" if state.get('matched_workflow') else "rag",
        {
            "workflow": "workflow",
            "rag": "rag"
        }
    )
    
    # RAG后进入执行
    workflow.add_edge("rag", "execute")
    
    # 工作流后进入执行
    workflow.add_edge("workflow", "execute")
    
    # 执行节点的条件路由
    workflow.add_conditional_edges(
        "execute",
        should_continue,
        {
            "execute": "execute",  # 继续执行下一步
            "wait_async": "wait_async",  # 等待异步任务
            "respond": "respond",  # 生成响应
            "plan": "plan",  # 重新规划（很少用）
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
        
        return {
            "conversation_id": conversation_id,
            "response": final_state.get('final_response', ''),
            "output_type": final_state.get('output_type', 'text'),
            "page_url": final_state.get('generated_page_url'),
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
        执行事件
    """
    logger.info(f"流式运行智能体 - 会话: {conversation_id}")
    
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
    
    try:
        async for event in graph.astream(initial_state, config):
            # 获取当前节点和状态
            for node_name, node_output in event.items():
                # 格式化流式响应
                progress = await controller.format_streaming_response(node_output)
                
                yield {
                    "node": node_name,
                    "progress": progress,
                    "state": {
                        "intent": node_output.get('intent'),
                        "current_step": node_output.get('current_step_index', 0),
                        "total_steps": len(node_output.get('plan', [])),
                        "next_action": node_output.get('next_action')
                    }
                }
                
                # 如果是最终响应，发送完整内容
                if node_output.get('final_response'):
                    yield {
                        "node": "final",
                        "response": node_output.get('final_response'),
                        "output_type": node_output.get('output_type', 'text'),
                        "page_url": node_output.get('generated_page_url')
                    }
                    
    except Exception as e:
        logger.error(f"流式执行失败: {e}")
        yield {
            "node": "error",
            "error": str(e)
        }
