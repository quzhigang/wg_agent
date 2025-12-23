"""
Planner - 规划调度器
负责分析用户意图、匹配工作流、制定执行计划
"""

from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field

from ..config.settings import settings
from ..config.logging_config import get_logger
from .state import AgentState, PlanStep, StepStatus, OutputType

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


# 意图分析提示词（带直接回复功能）
INTENT_ANALYSIS_PROMPT = """你是卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

## 用户意图类别
1. general_chat - 一般对话、闲聊（如问候、感谢、闲聊、询问你的信息等）
2. knowledge_qa - 流域知识问答（关于流域概况、水利设施、防洪知识等）
3. data_query - 数据查询（水雨情、水位、流量等实时或历史数据）
4. flood_forecast - 洪水预报（调用预报模型）
5. flood_simulation - 洪水预演（模拟不同场景）
6. emergency_plan - 预案生成（防洪应急预案）
7. damage_assessment - 灾损评估

## 上下文信息
对话历史摘要: {context_summary}

最近对话:
{chat_history}

## 用户当前消息
{user_message}

## 输出要求
请分析用户意图，返回JSON格式:

**如果是 general_chat（一般对话/闲聊），请直接生成回复内容：**
{{
    "intent": "general_chat",
    "confidence": 0.95,
    "direct_response": "你的友好回复内容（控制在100字以内）",
    "output_type": "text"
}}

**如果是其他业务意图，返回：**
{{
    "intent": "意图类别",
    "confidence": 0.95,
    "entities": {{"提取的关键实体": "值"}},
    "requires_data_query": true/false,
    "requires_model_call": true/false,
    "output_type": "text 或 web_page"
}}

注意:
- 对于一般对话，你需要友好地回复用户，可以简要介绍自己的能力（流域介绍、工程信息查询、实时水雨情查询、洪水预报预演及应急预案生成等）
- 如果涉及图表展示（如水位趋势图、雨量分布图等），output_type应为"web_page"
- 如果只是简单文字回答，output_type应为"text"
"""

# 计划生成提示词
PLAN_GENERATION_PROMPT = """你是卫共流域数字孪生系统的任务规划器，负责制定执行计划。

## 可用工具
{available_tools}

## 可用工作流
{available_workflows}

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
4. 最后一步通常是"生成响应"
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
        分析用户意图
        
        Args:
            state: 当前智能体状态
            
        Returns:
            包含意图分析结果的状态更新
        """
        logger.info(f"开始分析用户意图: {state['user_message'][:50]}...")
        
        try:
            # 格式化聊天历史
            chat_history_str = self._format_chat_history(state.get('chat_history', []))
            
            # 调用意图分析链
            result = await self.intent_chain.ainvoke({
                "context_summary": state.get('context_summary') or "无",
                "chat_history": chat_history_str or "无",
                "user_message": state['user_message']
            })
            
            logger.info(f"意图分析结果: {result}")
            
            intent = result.get("intent", "general_chat")
            
            # 如果是一般对话且有直接回复，标记为快速响应
            if intent == "general_chat" and result.get("direct_response"):
                logger.info("意图为一般对话，使用直接回复")
                return {
                    "intent": "general_chat",
                    "intent_confidence": result.get("confidence", 0.95),
                    "output_type": "text",
                    "direct_response": result.get("direct_response"),
                    "is_quick_chat": True,
                    "next_action": "quick_respond"
                }
            
            return {
                "intent": intent,
                "intent_confidence": result.get("confidence", 0.5),
                "output_type": result.get("output_type", "text"),
                "entities": result.get("entities", {})
            }
            
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return {
                "intent": "general_chat",
                "intent_confidence": 0.0,
                "error": f"意图分析失败: {str(e)}"
            }
    
    async def check_workflow_match(self, state: AgentState) -> Dict[str, Any]:
        """
        检查是否匹配预定义工作流
        
        Args:
            state: 当前智能体状态
            
        Returns:
            包含工作流匹配结果的状态更新
        """
        # TODO: 从workflows模块导入工作流注册表
        # 这里先返回空匹配
        logger.info("检查工作流匹配...")
        
        # 根据意图进行简单匹配
        intent = state.get('intent', '')
        
        workflow_mapping = {
            'flood_forecast': 'flood_forecast_workflow',
            'flood_simulation': 'flood_simulation_workflow',
            'emergency_plan': 'emergency_plan_workflow',
            'damage_assessment': 'damage_assessment_workflow'
        }
        
        matched = workflow_mapping.get(intent)
        
        if matched:
            logger.info(f"匹配到工作流: {matched}")
            return {
                "matched_workflow": matched,
                "next_action": "execute"  # 有匹配的工作流，直接执行
            }
        
        return {
            "matched_workflow": None,
            "next_action": "plan"  # 没有匹配，需要动态规划
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
            # 获取可用工具描述
            available_tools = self._get_available_tools_description()
            
            # 获取可用工作流描述
            available_workflows = self._get_available_workflows_description()
            
            # 调用计划生成链
            result = await self.plan_chain.ainvoke({
                "available_tools": available_tools,
                "available_workflows": available_workflows,
                "intent": state.get('intent', 'unknown'),
                "entities": state.get('entities', {}),
                "user_message": state['user_message']
            })
            
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
            
            logger.info(f"生成了{len(steps)}个执行步骤")
            
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
        """获取可用工具的描述"""
        # TODO: 从tools模块动态获取
        return """
1. query_water_level - 查询水位数据
   参数: station_id(测站ID), start_time(开始时间), end_time(结束时间)

2. query_rainfall - 查询雨量数据
   参数: station_id(测站ID), start_time(开始时间), end_time(结束时间)

3. query_flow - 查询流量数据
   参数: station_id(测站ID), start_time(开始时间), end_time(结束时间)

4. run_flood_forecast - 运行洪水预报模型
   参数: forecast_time(预报时间), scenario(场景)

5. search_knowledge - 搜索知识库
   参数: query(查询内容), top_k(返回数量)

6. generate_web_page - 生成Web页面
   参数: page_type(页面类型), data(数据内容)
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
    
    执行意图分析、工作流匹配和计划生成
    """
    planner = get_planner()
    
    # 1. 分析意图（LLM会判断是否为闲聊，如果是闲聊会直接返回回复）
    intent_result = await planner.analyze_intent(state)
    state.update(intent_result)
    
    # 如果意图分析已经返回了直接回复（一般对话），直接跳转到快速响应
    if intent_result.get('is_quick_chat') and intent_result.get('direct_response'):
        logger.info("LLM判断为一般对话，使用直接回复")
        return state
    
    # 2. 检查工作流匹配
    workflow_result = await planner.check_workflow_match(state)
    state.update(workflow_result)
    
    # 3. 如果没有匹配工作流，生成动态计划
    if not state.get('matched_workflow'):
        plan_result = await planner.generate_plan(state)
        state.update(plan_result)
    
    return state
