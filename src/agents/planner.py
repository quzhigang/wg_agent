"""
Planner - 规划调度器
负责分析用户意图、匹配工作流、制定执行计划
"""

from typing import Dict, Any, List, Optional
import json
import uuid
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..models.database import SavedWorkflow, SessionLocal
from ..config.logging_config import get_logger
from ..config.llm_prompt_logger import log_llm_call
from .state import AgentState, PlanStep, StepStatus, OutputType, IntentCategory, BusinessSubIntent

logger = get_logger(__name__)


class IntentAnalysis(BaseModel):
    """意图分析结果"""
    intent: str = Field(..., description="用户意图类别")
    confidence: float = Field(..., description="置信度 0-1")
    entities: Dict[str, Any] = Field(default_factory=dict, description="提取的实体")
    requires_data_query: bool = Field(default=False, description="是否需要数据查询")
    requires_model_call: bool = Field(default=False, description="是否需要调用模型")
    output_type: str = Field(default="text", description="建议的输出类型")


class TaskPlan(BaseModel):
    """任务执行计划"""
    steps: List[PlanStep] = Field(..., description="执行步骤列表")
    estimated_time_seconds: int = Field(default=30, description="预估执行时间")
    output_type: str = Field(default="text", description="输出类型")


# 意图分析提示词（三大类分类）
INTENT_ANALYSIS_PROMPT = """你是卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

## 意图分类体系（三大类）

### 第1类：chat（一般对话/闲聊）
- 问候、感谢、告别、闲聊
- 询问助手信息（你是谁、你能做什么等）
- 与流域业务无关的日常对话

### 第2类：knowledge（固有知识查询）
以下知识库范围内的问题属于此类：
- catchment_basin(流域概况)：卫共流域概况、流域各节点控制面积、流域内行政区划等
- water_project(水利工程)：水库、河道、闸站、蓄滞洪区、险工险段、南水北调工程、各河段防洪标准、工程现场照片等
- monitor_site(监测站点)：雨量站、水库和河道水文站、视频监测、取水监测、安全监测、AI监测等站点信息，且包含这些水利工程的基本参数信息
- history_flood(历史洪水)："21.7"、"23.7"等典型历史洪水的全要素信息、发生过程和受灾情况
- flood_preplan(防洪预案)：水库汛期调度运用计划、蓄滞洪区运用预案、流域和河道防洪预案等
- system_function(系统功能)：防洪"四预"系统的功能介绍、操作使用手册、系统api接口等
- business_workflow(业务流程)：防洪"四预"系统的业务操作流程信息，包括数据查询、预报预演等业务，包括调用接口和顺序。
- hydro_model(专业模型)：水利专业模型简介、模型类别、模型编码、模型算法、模型原理等
- catchment_planning(防洪规划)：海河流域防洪规划、防洪形势、暴雨洪水、防洪工程体系等
- project_designplan(工程治理)：水库、河道和蓄滞洪区等水利工程的设计治理方案报告

### 第3类：business（业务相关）
需进一步细分为以下子类：
- data_query: 监测数据查询（水情、雨情、水位、流量等实时或历史数据）
- flood_forecast: 洪水预报（进行预报、查询预报结果、预警信息）
- flood_simulation: 洪水预演（进行预演、查询预演结果）
- emergency_plan: 预案生成（防洪应急预案）
- damage_assessment: 灾损评估、避险转移
- other: 其他业务操作

## 上下文信息
对话历史摘要: {context_summary}

最近对话:
{chat_history}

## 用户当前消息
{user_message}

## 输出要求
请分析用户意图，返回JSON格式:

**如果是 chat（一般对话/闲聊），直接生成回复：**
{{
    "intent_category": "chat",
    "confidence": 0.95,
    "direct_response": "你的友好回复内容（控制在100字以内）"
}}

**如果是 knowledge（固有知识查询）：**
{{
    "intent_category": "knowledge",
    "confidence": 0.95,
    "target_kbs": ["知识库id1", "知识库id2"],
    "entities": {{"关键词": "值"}},
    "needs_kb_search": true,
    "needs_web_search": false
}}
注意：
- target_kbs从以下知识库id中选择相关的：catchment_basin, water_project, monitor_site, history_flood, flood_preplan, system_function, hydro_model, catchment_planning, project_designplan
- needs_kb_search和needs_web_search的判断规则：
  1. 知识库能完全回答（如卫共流域概况、水库基本信息、历史洪水记录、规划内容等静态信息）：needs_kb_search=true, needs_web_search=false
  2. 知识库完全不能回答的情况，needs_kb_search=false, needs_web_search=true：
     - 询问具体年份的实际执行情况、完成情况、进展（如"2025年完成了哪些工程"）
     - 询问最新新闻、动态、政策变化
     - 询问天气预报、气象信息
     - 询问其他流域、非水利知识
  3. 知识库部分能回答，需网络补充（如某水库最新运行状态、流域近期政策解读）：needs_kb_search=true, needs_web_search=true

**如果是 business（业务相关）：**
{{
    "intent_category": "business",
    "business_sub_intent": "data_query/flood_forecast/flood_simulation/emergency_plan/damage_assessment/other",
    "confidence": 0.95,
    "entities": {{"站点": "xxx", "时间": "xxx"}},
    "output_type": "text 或 web_page"
}}

注意:
- 对于chat类，需友好回复并简要介绍能力
- 如果涉及图表展示，output_type应为"web_page"
"""

# 计划生成提示词
PLAN_GENERATION_PROMPT = """你是卫共流域数字孪生系统的任务规划器，负责制定执行计划。

## 可用工具
{available_tools}

## 可用工作流
{available_workflows}

## 相关知识和业务流程参考
{rag_context}

## 用户意图
意图类别: {intent}
提取实体: {entities}

## 用户消息
{user_message}

## 输出要求
请生成执行计划，返回JSON格式:
{{
    "steps": [
        {{
            "step_id": 1,
            "description": "步骤描述",
            "tool_name": "工具名称（如果需要）",
            "tool_args": {{"参数": "值"}},
            "dependencies": [],
            "is_async": false
        }}
    ],
    "estimated_time_seconds": 30,
    "output_type": "text 或 web_page"
}}

规划原则:
1. 步骤应该清晰、可执行
2. 正确设置步骤间的依赖关系
3. 耗时操作（如模型调用）应标记为异步
4. 最后一步不需要指定工具，系统会自动生成响应
5. 只使用可用工具列表中存在的工具名称，不要使用不存在的工具如"generate_response"
6. 参考"相关知识和业务流程参考"中的信息，优化执行计划的步骤和工具选择
"""


# 快速意图识别关键词（不需要调用LLM）
QUICK_CHAT_KEYWORDS = [
    # 问候语
    "你好", "您好", "hi", "hello", "嗨", "早上好", "下午好", "晚上好", "早安", "晚安",
    # 感谢语
    "谢谢", "感谢", "多谢", "thanks", "thank you",
    # 告别语
    "再见", "拜拜", "bye", "goodbye", "回见",
    # 简单问答
    "你是谁", "你叫什么", "你能做什么", "你会什么", "介绍一下你自己",
    "你多大", "几岁", "年龄", "生日",
    # 闲聊
    "今天天气", "吃了吗", "在吗", "忙吗", "怎么样", "好吗", "还好吗",
    "干嘛", "干什么", "做什么", "聊聊", "无聊", "开心", "高兴", "难过"
]


class Planner:
    """规划调度器"""
    
    def __init__(self):
        """初始化规划器"""
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_api_base,
            model=settings.openai_model_name,
            temperature=0.3  # 规划任务使用较低温度
        )
        self.json_parser = JsonOutputParser()
        
        # 意图分析链
        self.intent_prompt = ChatPromptTemplate.from_template(INTENT_ANALYSIS_PROMPT)
        self.intent_chain = self.intent_prompt | self.llm | self.json_parser
        
        # 计划生成链
        self.plan_prompt = ChatPromptTemplate.from_template(PLAN_GENERATION_PROMPT)
        self.plan_chain = self.plan_prompt | self.llm | self.json_parser
        
        logger.info("Planner初始化完成")
    
    def _is_quick_chat(self, message: str) -> bool:
        """
        快速判断是否为一般闲聊（不需要调用LLM）
        
        Args:
            message: 用户消息
            
        Returns:
            是否为一般闲聊
        """
        message_lower = message.lower().strip()
        
        # 检查是否包含业务关键词（如果包含则不是闲聊）
        business_keywords = [
            "水位", "雨量", "流量", "洪水", "预报", "预演", "预案", 
            "监测", "站点", "流域", "卫共", "河道", "水库", "闸门",
            "降雨", "汛期", "防洪", "灾损", "淹没", "模型", "方案",
            "查询", "数据", "统计", "分析", "报告"
        ]
        for keyword in business_keywords:
            if keyword in message_lower:
                return False
        
        # 消息较短（<=15字符）且不包含业务关键词，很可能是闲聊
        if len(message_lower) <= 15:
            return True
        
        # 检查闲聊关键词
        for keyword in QUICK_CHAT_KEYWORDS:
            if keyword in message_lower:
                return True
        
        return False
    
    async def analyze_intent(self, state: AgentState) -> Dict[str, Any]:
        """
        分析用户意图（三大类分类）

        Args:
            state: 当前智能体状态

        Returns:
            包含意图分析结果的状态更新
        """
        logger.info(f"开始分析用户意图: {state['user_message'][:50]}...")

        try:
            # 格式化聊天历史
            chat_history_str = self._format_chat_history(state.get('chat_history', []))

            # 准备上下文变量
            context_vars = {
                "context_summary": state.get('context_summary') or "无",
                "chat_history": chat_history_str or "无",
                "user_message": state['user_message']
            }

            # 调用意图分析链
            result = await self.intent_chain.ainvoke(context_vars)

            # 记录LLM调用日志
            full_prompt = INTENT_ANALYSIS_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="意图分析",
                module_name="Planner.analyze_intent",
                prompt_template_name="INTENT_ANALYSIS_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=str(result)
            )

            logger.info(f"意图分析结果: {result}")

            intent_category = result.get("intent_category", "chat")

            # 第1类：chat - 一般对话
            if intent_category == "chat":
                return {
                    "intent_category": IntentCategory.CHAT.value,
                    "intent": "general_chat",  # 兼容旧字段
                    "intent_confidence": result.get("confidence", 0.95),
                    "direct_response": result.get("direct_response"),
                    "is_quick_chat": True,
                    "next_action": "quick_respond"
                }

            # 第2类：knowledge - 固有知识查询
            if intent_category == "knowledge":
                return {
                    "intent_category": IntentCategory.KNOWLEDGE.value,
                    "intent": "knowledge_qa",  # 兼容旧字段
                    "intent_confidence": result.get("confidence", 0.9),
                    "entities": result.get("entities", {}),
                    "target_kbs": result.get("target_kbs", []),  # 目标知识库列表
                    "needs_kb_search": result.get("needs_kb_search", True),
                    "needs_web_search": result.get("needs_web_search", False),
                    "next_action": "knowledge_rag"  # 直接走知识库检索流程
                }

            # 第3类：business - 业务相关
            if intent_category == "business":
                sub_intent = result.get("business_sub_intent", "other")
                return {
                    "intent_category": IntentCategory.BUSINESS.value,
                    "business_sub_intent": sub_intent,
                    "intent": sub_intent,  # 兼容旧字段
                    "intent_confidence": result.get("confidence", 0.9),
                    "entities": result.get("entities", {}),
                    "output_type": result.get("output_type", "text"),
                    "next_action": "business_match"  # 先匹配业务流程模板
                }

            # 默认当作闲聊处理
            return {
                "intent_category": IntentCategory.CHAT.value,
                "intent": "general_chat",
                "intent_confidence": 0.5,
                "is_quick_chat": True,
                "next_action": "quick_respond"
            }

        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {
                "intent_category": IntentCategory.CHAT.value,
                "intent": "general_chat",
                "intent_confidence": 0.0,
                "error": f"意图分析失败: {str(e)}"
            }
    
    async def check_workflow_match(self, state: AgentState) -> Dict[str, Any]:
        """
        检查是否匹配预定义工作流（用于第3类业务场景）

        通过向量检索匹配预制业务流程模板

        Args:
            state: 当前智能体状态

        Returns:
            包含工作流匹配结果的状态更新
        """
        logger.info("检查业务流程模板匹配...")

        intent_category = state.get('intent_category')
        sub_intent = state.get('business_sub_intent')

        # 只对业务类意图进行模板匹配
        if intent_category != IntentCategory.BUSINESS.value:
            return {"matched_workflow": None, "workflow_from_template": False}

        try:
            # 1. 尝试通过向量检索匹配业务流程模板
            from ..rag.retriever import get_rag_retriever
            rag_retriever = get_rag_retriever()

            # 在 business_workflow 知识库中检索
            workflow_docs = await rag_retriever.retrieve(
                query=state['user_message'],
                top_k=3,
                category="business_workflow"
            )

            # 检查是否有高置信度匹配
            if workflow_docs and len(workflow_docs) > 0:
                top_doc = workflow_docs[0]
                score = top_doc.get('score', 0)

                # 置信度阈值 0.75
                if score >= 0.75:
                    workflow_name = top_doc.get('metadata', {}).get('workflow_name')
                    if workflow_name:
                        logger.info(f"向量匹配到业务流程模板: {workflow_name}, 置信度: {score}")
                        return {
                            "matched_workflow": workflow_name,
                            "workflow_from_template": True,
                            "retrieved_documents": workflow_docs,
                            "next_action": "execute"
                        }

            # 2. 基于子意图的静态映射（备选方案）
            workflow_mapping = {
                'flood_forecast': 'flood_forecast_workflow',
                'flood_simulation': 'flood_simulation_workflow',
                'emergency_plan': 'emergency_plan_workflow',
                'damage_assessment': 'damage_assessment_workflow',
                'data_query': None  # 数据查询通常需要动态规划
            }

            matched = workflow_mapping.get(sub_intent)
            if matched:
                # 检查工作流是否已注册
                from ..workflows.registry import get_workflow_registry
                registry = get_workflow_registry()
                if registry.has_workflow(matched):
                    logger.info(f"静态映射到工作流: {matched}")
                    return {
                        "matched_workflow": matched,
                        "workflow_from_template": True,
                        "next_action": "execute"
                    }

        except Exception as e:
            logger.warning(f"工作流模板匹配失败: {e}")

        # 3. 尝试匹配自动保存的流程
        saved_match = self._match_saved_workflow(state)
        if saved_match:
            return saved_match

        # 未匹配到模板，需要动态规划
        logger.info("未匹配到业务流程模板，将进行动态规划")
        return {
            "matched_workflow": None,
            "workflow_from_template": False,
            "next_action": "dynamic_plan"
        }
    
    async def generate_plan(self, state: AgentState) -> Dict[str, Any]:
        """
        生成执行计划
        
        Args:
            state: 当前智能体状态
            
        Returns:
            包含执行计划的状态更新
        """
        logger.info("开始生成执行计划...")
        
        try:
            # 1. 执行RAG检索，获取相关知识和业务流程参考
            rag_context = "无相关知识"
            rag_doc_count = 0
            try:
                from ..rag.retriever import get_rag_retriever
                rag_retriever = get_rag_retriever()
                rag_result = await rag_retriever.get_relevant_context(
                    user_message=state['user_message'],
                    intent=state.get('intent'),
                    max_length=3000
                )
                rag_context = rag_result.get('context', '无相关知识')
                rag_doc_count = rag_result.get('document_count', 0)
                logger.info(f"计划生成RAG检索完成，获取到 {rag_doc_count} 条相关文档")
            except Exception as rag_error:
                logger.warning(f"计划生成RAG检索失败: {rag_error}")
            
            # 2. 获取可用工具描述
            available_tools = self._get_available_tools_description()
            
            # 3. 获取可用工作流描述
            available_workflows = self._get_available_workflows_description()
            
            # 4. 准备上下文变量
            plan_context_vars = {
                "available_tools": available_tools,
                "available_workflows": available_workflows,
                "rag_context": rag_context,
                "intent": state.get('intent', 'unknown'),
                "entities": state.get('entities', {}),
                "user_message": state['user_message']
            }
            
            # 调用计划生成链（包含RAG上下文）
            result = await self.plan_chain.ainvoke(plan_context_vars)
            
            # 记录LLM调用日志
            full_prompt = PLAN_GENERATION_PROMPT.format(**plan_context_vars)
            log_llm_call(
                step_name="计划生成",
                module_name="Planner.generate_plan",
                prompt_template_name="PLAN_GENERATION_PROMPT",
                context_variables=plan_context_vars,
                full_prompt=full_prompt,
                response=str(result)
            )
            
            # 解析步骤
            steps = []
            for step_data in result.get('steps', []):
                step = PlanStep(
                    step_id=step_data.get('step_id', len(steps) + 1),
                    description=step_data.get('description', ''),
                    tool_name=step_data.get('tool_name'),
                    tool_args=step_data.get('tool_args'),
                    dependencies=step_data.get('dependencies', []),
                    status=StepStatus.PENDING,
                    is_async=step_data.get('is_async', False)
                )
                steps.append(step.model_dump())
            
            # 输出执行计划详情
            logger.info(f"生成了{len(steps)}个执行步骤")
            logger.info("=" * 60)
            logger.info("执行计划:")
            for step in steps:
                step_id = step.get('step_id', '?')
                description = step.get('description', '')
                tool_name = step.get('tool_name', '无')
                logger.info(f"  步骤{step_id}: {description} (工具: {tool_name})")
            logger.info("=" * 60)
            logger.info("")  # 空行

            # 自动保存动态生成的流程
            self._save_dynamic_plan(state, steps, result.get('output_type', 'text'))

            return {
                "plan": steps,
                "current_step_index": 0,
                "output_type": result.get('output_type', 'text'),
                "next_action": "execute"
            }
            
        except Exception as e:
            logger.error(f"计划生成失败: {e}")
            # 生成默认的简单计划
            default_plan = [
                PlanStep(
                    step_id=1,
                    description="直接回答用户问题",
                    tool_name=None,
                    tool_args=None,
                    dependencies=[],
                    status=StepStatus.PENDING
                ).model_dump()
            ]
            return {
                "plan": default_plan,
                "current_step_index": 0,
                "output_type": "text",
                "next_action": "execute",
                "error": f"计划生成失败，使用默认计划: {str(e)}"
            }
    
    def _format_chat_history(self, chat_history: List[Dict[str, str]], max_turns: int = 5) -> str:
        """格式化聊天历史"""
        if not chat_history:
            return ""
        
        recent = chat_history[-max_turns * 2:]  # 最近N轮对话
        formatted = []
        for msg in recent:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def _get_available_tools_description(self) -> str:
        """获取可用工具的描述（从工具注册表动态获取）"""
        from ..tools.registry import get_tool_registry
        
        registry = get_tool_registry()
        
        # 获取所有已注册工具的描述
        tools_desc = registry.get_tools_description()
        
        if tools_desc:
            return tools_desc
        
        # 如果注册表为空，返回基础工具描述
        return """
1. search_knowledge - 搜索知识库，查询流域相关的背景知识、专业知识等信息
   参数: query(查询内容), top_k(返回数量，默认5)
"""
    
    def _get_available_workflows_description(self) -> str:
        """获取可用工作流的描述"""
        # TODO: 从workflows模块动态获取
        return """
1. flood_forecast_workflow - 洪水预报工作流
   触发条件: 用户询问洪水预报相关问题

2. flood_simulation_workflow - 洪水预演工作流
   触发条件: 用户要求进行洪水模拟

3. emergency_plan_workflow - 应急预案工作流
   触发条件: 用户需要生成防洪预案

4. latest_flood_forecast_query - 最新洪水预报结果查询
   触发条件: 用户询问最新预报结果
"""

    def _match_saved_workflow(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """匹配自动保存的流程"""
        try:
            db = SessionLocal()
            sub_intent = state.get('business_sub_intent')

            # 查询同类子意图的已保存流程
            saved = db.query(SavedWorkflow).filter(
                SavedWorkflow.is_active == True,
                SavedWorkflow.sub_intent == sub_intent
            ).order_by(SavedWorkflow.use_count.desc()).first()

            if saved:
                # 更新使用次数
                saved.use_count += 1
                db.commit()

                logger.info(f"匹配到已保存流程: {saved.name}")
                return {
                    "matched_workflow": None,
                    "workflow_from_template": False,
                    "saved_workflow_id": saved.id,
                    "plan": json.loads(saved.plan_steps),
                    "current_step_index": 0,
                    "output_type": saved.output_type,
                    "next_action": "execute"
                }
            db.close()
        except Exception as e:
            logger.warning(f"匹配已保存流程失败: {e}")
        return None

    def _save_dynamic_plan(self, state: AgentState, steps: List[Dict], output_type: str):
        """保存动态生成的流程"""
        if len(steps) < 2:
            return  # 步骤太少不保存

        try:
            db = SessionLocal()
            sub_intent = state.get('business_sub_intent', 'other')
            user_msg = state.get('user_message', '')[:100]

            workflow = SavedWorkflow(
                id=str(uuid.uuid4()),
                name=f"auto_{sub_intent}_{uuid.uuid4().hex[:6]}",
                description=f"自动保存: {user_msg}",
                trigger_pattern=user_msg,
                intent_category=state.get('intent_category', 'business'),
                sub_intent=sub_intent,
                entities_pattern=json.dumps(state.get('entities', {}), ensure_ascii=False),
                plan_steps=json.dumps(steps, ensure_ascii=False),
                output_type=output_type,
                source="auto"
            )
            db.add(workflow)
            db.commit()
            db.close()
            logger.info(f"已自动保存流程: {workflow.name}")
        except Exception as e:
            logger.warning(f"保存动态流程失败: {e}")


# 创建全局Planner实例
_planner_instance: Optional[Planner] = None


def get_planner() -> Planner:
    """获取Planner单例"""
    global _planner_instance
    if _planner_instance is None:
        _planner_instance = Planner()
    return _planner_instance


async def planner_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph节点函数 - 规划节点

    执行意图分析，根据三大类分类决定后续流程：
    - chat: 直接返回回复
    - knowledge: 走知识库检索流程
    - business: 先匹配模板，未匹配则动态规划
    """
    planner = get_planner()

    # 1. 分析意图（三大类分类）
    intent_result = await planner.analyze_intent(state)

    intent_category = intent_result.get('intent_category')

    # 第1类：chat - 直接返回
    if intent_category == IntentCategory.CHAT.value:
        logger.info("意图类别: chat，直接返回回复")
        return intent_result

    # 第2类：knowledge - 直接走知识库检索
    if intent_category == IntentCategory.KNOWLEDGE.value:
        logger.info("意图类别: knowledge，走知识库检索流程")
        return intent_result

    # 第3类：business - 先匹配模板
    if intent_category == IntentCategory.BUSINESS.value:
        logger.info(f"意图类别: business，子意图: {intent_result.get('business_sub_intent')}")

        # 合并意图结果到临时状态
        temp_state = dict(state)
        temp_state.update(intent_result)

        # 检查业务流程模板匹配
        workflow_result = await planner.check_workflow_match(temp_state)

        # 如果匹配到模板，直接执行
        if workflow_result.get('matched_workflow'):
            logger.info(f"匹配到业务流程模板: {workflow_result.get('matched_workflow')}")
            return {**intent_result, **workflow_result}

        # 未匹配到模板，进行动态规划（先检索知识库辅助规划）
        logger.info("未匹配到模板，进行动态规划")
        temp_state.update(workflow_result)
        plan_result = await planner.generate_plan(temp_state)
        return {**intent_result, **workflow_result, **plan_result}

    # 默认返回意图结果
    return intent_result
