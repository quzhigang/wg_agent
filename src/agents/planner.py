"""
Planner - 规划调度器
负责分析用户意图、匹配工作流、制定执行计划
"""

from typing import Dict, Any, List, Optional
import json
import uuid
import asyncio
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


# 1、意图分析提示词（三大类分类，简化版 - 移除business子意图详细分类）
INTENT_ANALYSIS_PROMPT = """你是河南省卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

## 意图分类体系（三大类）

### 第1类：chat（一般对话/闲聊）
- 问候、感谢、告别、闲聊
- 询问助手信息（你是谁、你能做什么等）
- 与流域业务无关的日常对话

### 第2类：knowledge（固有知识查询）
查询静态的、固有的知识信息，包括：
- catchment_basin(流域概况)：卫共流域概况、流域各节点控制面积、流域内行政区划等
- water_project(水利工程)：水库、河道、闸站、蓄滞洪区、险工险段、南水北调工程、各河段防洪标准、工程现场照片等
- monitor_site(监测站点)：雨量站、水库和河道水文站、视频监测、取水监测、安全监测、AI监测等站点信息，且包含这些水利工程的基本参数信息
- history_flood(历史洪水)："21.7"、"23.7"等典型历史洪水信息、发生过程和受灾情况
- flood_preplan(防洪预案)：水库汛期调度运用计划、蓄滞洪区运用预案、流域和河道防洪预案等
- system_function(系统功能)：防洪"四预"系统的功能介绍、操作使用手册、系统api接口等
- business_workflow(业务流程)：防洪"四预"系统的业务操作流程信息，包括数据查询、预报预演等业务，包括调用接口和顺序
- hydro_model(专业模型)：水利专业模型简介、模型类别、模型编码、模型算法、模型原理等
- catchment_planning(防洪规划)：海河流域防洪规划、防洪形势、暴雨洪水、防洪工程体系等
- project_designplan(工程治理)：水库、河道和蓄滞洪区等水利工程的设计治理方案报告

### 第3类：business（业务操作）
涉及动态数据查询或业务操作，包括：
- 实时数据查询：当前水位、当前雨情、最新流量、实时监测数据、历时某时间的数据等
- 洪水预报：启动预报、查询预报结果、预警信息
- 洪水预演：启动预演、查询预演结果
- 预案生成、灾损评估等业务操作

**区分要点（knowledge vs business）：**
- "XX水库设计库容多少" → knowledge（固有属性）
- "XX水库当前水位和库容" → business（实时数据）
- "未来洪水预报" → business（预报结果）
- "历史洪水最高水位与当前水位对比" → business（包含实时数据，优先归为business）
- "21.7洪水水位是否超过防洪高水位" → knowledge（纯历史数据与固有参数对比）
- "21.7洪水水位和当前水位哪个大" → business（涉及当前实时数据）

**核心原则**：1、只要问题中涉及"当前"、"实时"、"最新"等动态数据需求，整体归类为business；2、即包含固有知识查询，又包含业务的混合问题，归类为business

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
    "direct_response": "你的友好回复内容（控制在100字以内）",
    "is_greeting": true/false
}}
注意：is_greeting仅在用户打招呼（你好、您好、hi、hello等）或询问"你是谁"、"介绍一下你自己"等自我介绍场景时为true。
- 当is_greeting=true时，回复需包含自我介绍："您好！我是卫共流域数字孪生系统的智能助手小卫，..."
- 当is_greeting=false时（如感谢、告别、闲聊等），直接回复，不要加自我介绍

**如果是 knowledge（固有知识查询）：**
{{
    "intent_category": "knowledge",
    "confidence": 0.95,
    "target_kbs": ["知识库id1", "知识库id2"],
    "entities": {{"关键词": "值"}},
    "needs_kb_search": true,
    "needs_web_search": false,
    "rewritten_query": "结合对话历史补全后的完整查询语句"
}}
注意：rewritten_query字段非常重要！如果用户消息存在省略（如"小南海呢？"），必须结合对话历史补全为完整查询（如"小南海水库的流域面积"）。如果用户消息已经完整，则直接复制用户消息。
注意：
- target_kbs从以下知识库id中选择相关的：catchment_basin, water_project, monitor_site, history_flood, flood_preplan, system_function, hydro_model, catchment_planning, project_designplan
- needs_kb_search和needs_web_search的判断规则：
  1. 知识库能完全回答（如卫共流域概况、水库基本信息、历史洪水记录、规划内容等静态信息）：needs_kb_search=true, needs_web_search=false
  2. 知识库完全不能回答的情况，needs_kb_search=false, needs_web_search=true：
     - 询问具体年份的实际执行情况、完成情况、进展（如"2025年完成了哪些工程"）
     - 询问最新新闻、动态、政策变化
     - 询问其他流域、非水利知识
  3. 知识库部分能回答，需网络补充，或无法确定知识库是否有完整答案的情况：needs_kb_search=true, needs_web_search=true

**如果是 business（业务操作）：**
{{
    "intent_category": "business",
    "confidence": 0.95,
    "entities": {{
        "object": "对象名称",
        "object_type": "对象类型或null",
        "action": "要执行的操作",
        "time": "时间范围或null"
    }},
    "target_kbs": ["需要参考的知识库id列表"]
}}

**entities字段说明：**
- object: 操作对象的名称，可以是：
  - 具体站点/水库/河道/工程名称（如"修武站"、"盘石头水库"、"卫河"、"盐土庄闸"）
  - 业务事件名称（如"洪水预报"、"预演方案"）
  - 区域名称（如"卫共流域"、"新乡市"）
- object_type: 对象的类型，如果能明确判断则填写，否则填null。
- action: 用户想要执行的具体操作（如"查询当前水位"、"启动预报"、"对比分析"）
- time: 时间范围（如"当前"、"最近24小时"、"2023年7月"），无时间要求则填null

**示例：**
- "盘石头水库实时水情" → {{"object": "盘石头水库", "object_type": "水库", "action": "查询实时水情", "time": "当前"}}

注意：
- business类只需识别类别和提取实体，具体业务子意图和工作流将在下一阶段确定
- 如果无法确定object_type，一定要填null，不要猜测！后续阶段会通过数据库和知识库查询补全
- target_kbs用于辅助计划生成阶段的知识库检索，从以下知识库id中选择相关的：catchment_basin, water_project, monitor_site, history_flood, flood_preplan, system_function, business_workflow, hydro_model, catchment_planning, project_designplan
- 根据问题涉及的内容选择相关知识库，如涉及历史洪水则包含history_flood，涉及水库信息则包含water_project
"""

# 2、业务子意图分类提示词（第3类business触发，在工作流匹配之前执行，第2阶段）
BUSINESS_SUB_INTENT_PROMPT = """你是河南省卫共流域数字孪生系统的业务意图分类器，负责对业务类意图进行细分。

## 用户消息
{user_message}

## 提取的实体
{entities}

## 业务子意图分类体系

### data_query（监测数据查询）
- 仅查询当前/实时水位、流量、雨量、视频、工情等监测数据
- 仅查询历史某时间的监测数据
- 特点：单一数据查询，不涉及对比、分析、判断
- 示例："盘石头水库当前水位"、"修武站2024年7月14日 8点流量"、"最近24小时雨量"
- 反例（复合问题不属于data_query）：
  - 复合问题："当前水位超过设计水位了吗" → 除了查询当前水位外，还要查询设计水位并进行对比分析，归为other

### flood_forecast（洪水预报）
- 启动洪水预报计算
- 查询预报结果
- 预警信息查询
- 示例："未来洪水预报"、"启动自动预报"、"最新预报结果"

### flood_simulation（洪水预演）
- 启动洪水预演/模拟
- 查询预演结果
- 淹没分析
- 示例："启动洪水预演"、"模拟洪水淹没范围"

### emergency_plan（预案生成）
- 生成防洪预案
- 调度方案制定
- 示例："生成防洪预案"、"制定调度方案"

### damage_assessment（灾损评估）
- 灾害损失评估
- 避险转移分析
- 受灾人口统计
- 示例："评估洪水损失"、"避险转移方案"

### other（其他业务操作）
- 不属于以上类别的业务操作
- 复合问题：需要多步骤处理的问题，如同时涉及实时数据查询和固有属性查询、对比
- 示例：
  - "盘石头水库当前水位超过设计水位了吗" → 需要查实时水位 + 查设计水位 + 对比
  - "小南海水库当前水位超过预报水位了吗" → 需要查实时水位 + 查预报水位 + 对比

## 输出要求
返回JSON格式：
{{
    "business_sub_intent": "子意图类别（data_query/flood_forecast/flood_simulation/emergency_plan/damage_assessment/other）",
    "confidence": 0.95,
    "reason": "分类理由"
}}

## 分类规则
1. 涉及"当前"、"实时"、"最新"、"水情"、"雨情"、"工情"、"视频"、"AI监测"、"无人机监测"等监测数据查询，且不涉及对比、判断 → data_query
2. 涉及"预报"、"预测"、"未来洪水" → flood_forecast
3. 涉及"预演"、"模拟" → flood_simulation
4. 涉及"预案"、"调度方案" → emergency_plan
5. 涉及"损失"、"灾损"、"转移" → damage_assessment
6. 复合问题和无法明确归类 → other

**关键判断：data_query vs other**
- data_query：纯粹的数据查询，如"当前水位多少"、"实时流量"
- other：涉及对比或判断的复合问题，如"当前水位超过设计水位了吗"、"水位是否达到警戒线"
"""

# 3、预定义工作流按子意图分类（用于工作流匹配阶段）
PREDEFINED_WORKFLOWS_BY_SUB_INTENT = {
    "data_query": """
暂无预定义的数据查询工作流模板，请检查已保存的动态工作流或进行动态规划。
""",
    "flood_forecast": """
1. get_auto_forecast_result - 查询最新自动预报结果
   适用场景：用户询问流域、水库、站点的未来洪水预报情况，且未指定启动新预报
   适用对象类型：洪水预报
   示例："未来几天流域洪水情况"、"最新预报结果"、"水库预报水位"

2. get_history_autoforecast_result - 查询历史自动预报结果
   适用场景：用户询问过去某次自动预报的结果
   适用对象类型：洪水预报
   示例："上次自动预报结果"、"历史预报记录"

3. flood_autoforecast_getresult - 启动自动洪水预报并获取结果
   适用场景：用户明确要求启动/执行一次新的自动预报计算
   适用对象类型：洪水预报
   示例："启动自动预报"、"执行一次预报"、"运行预报模型"

4. get_manual_forecast_result - 查询人工预报结果
   适用场景：用户询问人工/手动预报的结果
   适用对象类型：洪水预报
   示例："人工预报结果"、"手动预报情况"

5. flood_manualforecast_getresult - 启动人工洪水预报并获取结果
   适用场景：用户要求启动人工预报，通常需要指定降雨条件
   适用对象类型：洪水预报
   示例："按照XX降雨条件进行预报"、"自定义雨量预报"
""",
    "flood_simulation": """
暂无预定义的洪水预演工作流模板，请检查已保存的动态工作流或进行动态规划。
""",
    "emergency_plan": """
暂无预定义的预案生成工作流模板，请检查已保存的动态工作流或进行动态规划。
""",
    "damage_assessment": """
暂无预定义的灾损评估工作流模板，请检查已保存的动态工作流或进行动态规划。
""",
    "other": """
暂无预定义工作流模板，请检查已保存的动态工作流或进行动态规划。
"""
}

# 4、业务工作流匹配提示词（第3阶段，仅business类触发，根据子意图提供相应工作流）
WORKFLOW_SELECT_PROMPT = """你是河南省卫共流域数字孪生系统的业务流程选择器，负责从可用工作流中选择最匹配的一个。

## 输入信息
- 用户消息：{user_message}
- 实体：{entities}
- 子意图：{business_sub_intent}

## 可用的预定义工作流
{predefined_workflows}

## 可用的已保存工作流
{saved_workflows}

## 匹配规则

1. **data_query子意图必须严格匹配数据来源**
   - 数据来源由entities中的object_type字段确定
   - 工作流的数据来源必须与object_type完全对应
   - 如：object_type为"水库水文站"，只能匹配水库水文站数据来源的工作流

2. **工作流必须完全覆盖用户需求**
   - 只有完全满足用户需求才能匹配
   - 部分满足视为不匹配，返回null交给动态规划

3. **无可用工作流时返回null**

## 输出格式
返回JSON：
{{
    "matched_workflow": null或"预定义工作流名称",
    "saved_workflow_id": null或"已保存工作流的UUID",
    "output_type": "text或web_page"
}}

注意：matched_workflow填预定义工作流名称，saved_workflow_id填已保存工作流的UUID，两者不要混淆。
"""

# 5、动态计划生成提示词
PLAN_GENERATION_PROMPT = """你是河南省卫共流域数字孪生系统的任务规划器，负责制定执行计划。

## 可用工具
{available_tools}

## 业务流程参考（仅供规划参考）
{rag_context}

## 用户意图
意图类别: {intent}
提取实体: {entities}
目标知识库: {target_kbs}

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
            "tool_args": {{"参数": "值", "布尔参数": true}},
            "dependencies": [],
            "is_async": false
        }}
    ],
    "estimated_time_seconds": 30,
    "output_type": "text 或 web_page"
}}

**重要：tool_args中的布尔类型参数必须使用JSON布尔值true/false，不要使用字符串"true"/"false"**

**步骤间参数传递（重要）：**
- 当后续步骤需要使用前面步骤的结果时，使用占位符格式：$$step_N.字段名$$
- 例如：步骤2返回 {{"data": {{"stcd": "31005650"}}}}，步骤3要使用stcd，应写：$$step_2.stcd$$
- 常用字段：stcd（站点编码）、stnm（站点名称）、data（数据对象）
- 错误示例：$$STEP_2.result_code$$（result_code不存在）
- 正确示例：$$step_2.stcd$$（直接使用返回数据中的字段名）

规划原则:
1. 步骤应该清晰、可执行
2. 正确设置步骤间的依赖关系
3. 耗时操作（如模型调用）应标记为异步
4. 最后一步不需要指定工具，系统会自动生成响应
5. 参考"业务流程参考"中的信息

**知识库检索规划（重要）：**
- 如果用户问题需要知识库中的信息（如历史洪水数据、水库特征参数、防洪标准等），必须在计划中添加"search_knowledge"工具调用步骤
- search_knowledge工具参数：{{"query": "检索关键词", "target_kbs": ["知识库id列表"]}}
- 目标知识库应根据问题内容选择，参考上面的"目标知识库"字段
- 知识库检索步骤应安排在需要该信息的步骤之前
- 例如：查询历史洪水水位需要先search_knowledge检索history_flood，再进行数据处理
"""

# 6、工作流模板化生成提示词（将具体执行计划抽象为通用模板）
WORKFLOW_TEMPLATE_PROMPT = """你是一个工作流模板生成器，需要将具体的执行计划抽象为通用的业务工作流模板。

## 原始用户消息
{user_message}

## 提取的实体
{entities}

## 业务子意图
{business_sub_intent}

## 执行计划步骤
{plan_steps}

## 任务
请将上述具体的执行计划抽象为一个通用的业务工作流模板，使其可以复用于同类业务场景。

## 输出要求
返回JSON格式：
{{
    "workflow_name": "简短的工作流名称（英文，如 query_reservoir_realtime_water_level）",
    "display_name": "中文简称（4-10字，如"水库实时水位查询"、"河道水情查询"）",
    "description": "工作流的通用描述（中文，不要包含具体名称，描述对象类型和业务场景）",
    "trigger_pattern": "触发模式描述（中文，用于匹配用户意图，如果是监测数据查询子意图，必须强调适用的数据来源）",
    "template_steps": [
        {{
            "step_id": 1,
            "description": "步骤描述",
            "tool_name": "工具名称",
            "tool_args_template": {{"参数名": "值"}}
        }}
    ],
    "required_entities": ["对象", "对象类型"]
}}

## 占位符规则

**用户输入的实体（使用双花括号）：**
- {{{{对象}}}}：操作对象名称（站点名、水库名等）
- {{{{对象类型}}}}：对象的类型或数据来源
- {{{{时间}}}}：时间范围

**步骤间数据传递（使用$$符号）：**
- $$step_N.字段名$$：引用第N步的输出字段
- 例如：步骤2返回stcd，步骤3使用 {{"stcd": "$$step_2.stcd$$"}}

**示例：**
- 步骤2：{{"object": "{{{{对象}}}}", "object_type": "{{{{对象类型}}}}"}}
- 步骤3：{{"stcd": "$$step_2.stcd$$"}}

注意：
1. 去除所有具体值，保留通用结构
2. 严格区分用户输入占位符和步骤间传递占位符
3. 如果是监测数据查询子意图，强调数据来源匹配
"""

# 7、对象类型(或数据来源)合成提示词（用于RAG检索后合成对象类型）
OBJECT_TYPE_SYNTHESIS_PROMPT = """你是卫共流域数字孪生系统的实体识别助手，负责根据检索到的信息确定对象的类型。

## 用户消息
{user_message}

## 待识别对象
对象名称：{object_name}

## 数据库查询结果
{db_result}

## 知识库检索结果
{rag_context}

## 任务
根据以上信息，确定对象的类型。

## 输出要求
返回JSON格式：
{{
    "object": "对象名称",
    "object_type": "对象类型",
    "stcd": "站点编码（如果有）",
    "confidence": 0.9,
    "source": "类型来源：db/rag/infer",
    "reason": "判断依据"
}}

## 对象类型选项
- 站点类：水库水文站、河道水文站、雨量站、闸站监测、AI监测站点、工程安全监测、取水监测、墒情站
- 工程类：水库、河道、蓄滞洪区、闸站
- 业务类：洪水预报、洪水预演、预案生成、灾损评估
- 区域类：流域、行政区
- 其他：unknown（如果无法确定）

## 判断规则
1. 优先使用数据库查询结果中的station_type字段
2. 如果数据库无结果，根据知识库检索内容推断
3. 如果名称中包含"水库"且无其他信息，推断为"水库水文站"
4. 如果名称中包含"站"但无法确定类型，设为"unknown"
5. 对于"洪水预报"、"预演"等业务名词，直接设置对应业务类型
"""

# 8、工具筛选提示词（第一阶段，根据摘要筛选需要的工具）
TOOL_SELECTION_PROMPT = """你是河南省卫共流域数字孪生系统的工具选择助手，负责根据用户需求筛选需要的工具。

## 用户消息
{user_message}

## 业务子意图
{business_sub_intent}

## 提取的实体
{entities}

## 可用工具摘要
{tools_summary}

## 任务
从上述工具中选择完成任务所需的工具。

## 输出要求
返回JSON格式：
{{
    "selected_tools": ["工具名称1", "工具名称2", ...],
    "reason": "选择理由（简短说明为什么选择这些工具）"
}}

## 选择原则
1. 根据用户意图和实体信息，选择最相关的工具
2. 通常选择2-6个工具即可完成任务，不要贪多
3. 如果需要查询站点编码，必须包含 lookup_station_code
4. 如果需要知识库检索，必须包含 search_knowledge
5. 根据数据类型选择对应的查询工具：
   - 水库水情 → query_reservoir_last, query_reservoir_process
   - 河道水情 → query_river_last, query_river_process
   - 雨量数据 → query_rain_process, query_rain_statistics, query_rain_sum
   - AI监测 → query_ai_water_last, query_ai_rain_last 等
6. 如果不确定需要哪个工具，可以多选几个相关的
"""

class Planner:
    """规划调度器"""

    def __init__(self):
        """初始化规划器"""
        self.json_parser = JsonOutputParser()

        # 思考模式配置（用于Qwen3等模型，非流式调用需设置为false）
        extra_body = {"enable_thinking": settings.llm_enable_thinking}

        # 意图识别LLM
        intent_cfg = settings.get_intent_config()
        intent_llm = ChatOpenAI(
            api_key=intent_cfg["api_key"],
            base_url=intent_cfg["api_base"],
            model=intent_cfg["model"],
            temperature=intent_cfg["temperature"],
            model_kwargs={"extra_body": extra_body}
        )
        self.intent_prompt = ChatPromptTemplate.from_template(INTENT_ANALYSIS_PROMPT)
        self.intent_chain = self.intent_prompt | intent_llm | self.json_parser

        # 工作流匹配LLM
        workflow_cfg = settings.get_workflow_config()
        workflow_llm = ChatOpenAI(
            api_key=workflow_cfg["api_key"],
            base_url=workflow_cfg["api_base"],
            model=workflow_cfg["model"],
            temperature=workflow_cfg["temperature"],
            model_kwargs={"extra_body": extra_body}
        )
        self.workflow_select_prompt = ChatPromptTemplate.from_template(WORKFLOW_SELECT_PROMPT)
        self.workflow_select_chain = self.workflow_select_prompt | workflow_llm | self.json_parser

        # 计划生成LLM
        plan_cfg = settings.get_plan_config()
        plan_llm = ChatOpenAI(
            api_key=plan_cfg["api_key"],
            base_url=plan_cfg["api_base"],
            model=plan_cfg["model"],
            temperature=plan_cfg["temperature"],
            model_kwargs={"extra_body": extra_body}
        )
        self.plan_prompt = ChatPromptTemplate.from_template(PLAN_GENERATION_PROMPT)
        self.plan_chain = self.plan_prompt | plan_llm | self.json_parser

        # 工作流模板化LLM（复用workflow配置）
        self.workflow_template_prompt = ChatPromptTemplate.from_template(WORKFLOW_TEMPLATE_PROMPT)
        self.workflow_template_chain = self.workflow_template_prompt | workflow_llm | self.json_parser

        # 对象类型合成LLM（复用意图识别配置，保持一致性）
        self.object_type_prompt = ChatPromptTemplate.from_template(OBJECT_TYPE_SYNTHESIS_PROMPT)
        self.object_type_chain = self.object_type_prompt | intent_llm | self.json_parser

        # 业务子意图分类LLM（复用意图识别配置，保持一致性）
        self.sub_intent_prompt = ChatPromptTemplate.from_template(BUSINESS_SUB_INTENT_PROMPT)
        self.sub_intent_chain = self.sub_intent_prompt | intent_llm | self.json_parser

        # 工具筛选LLM（独立配置）
        tool_select_cfg = settings.get_tool_select_config()
        tool_select_llm = ChatOpenAI(
            api_key=tool_select_cfg["api_key"],
            base_url=tool_select_cfg["api_base"],
            model=tool_select_cfg["model"],
            temperature=tool_select_cfg["temperature"],
            model_kwargs={"extra_body": extra_body}
        )
        self.tool_select_prompt = ChatPromptTemplate.from_template(TOOL_SELECTION_PROMPT)
        self.tool_select_chain = self.tool_select_prompt | tool_select_llm | self.json_parser

        # 保存intent_llm引用，供多类型站点选择等场景使用
        self.intent_llm = intent_llm

        logger.info("Planner初始化完成")

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
            import time
            _start = time.time()
            result = await self.intent_chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = INTENT_ANALYSIS_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="意图分析",
                module_name="Planner.analyze_intent",
                prompt_template_name="INTENT_ANALYSIS_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=str(result),
                elapsed_time=_elapsed
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
                # 获取补全后的查询，如果没有则使用原始消息
                rewritten_query = result.get("rewritten_query") or state['user_message']
                return {
                    "intent_category": IntentCategory.KNOWLEDGE.value,
                    "intent": "knowledge_qa",  # 兼容旧字段
                    "intent_confidence": result.get("confidence", 0.9),
                    "entities": result.get("entities", {}),
                    "target_kbs": result.get("target_kbs", []),  # 目标知识库列表
                    "needs_kb_search": result.get("needs_kb_search", True),
                    "needs_web_search": result.get("needs_web_search", False),
                    "rewritten_query": rewritten_query,  # 补全后的查询
                    "next_action": "knowledge_rag"  # 直接走知识库检索流程
                }

            # 第3类：business - 业务相关（只识别类别，不细分子意图）
            if intent_category == "business":
                return {
                    "intent_category": IntentCategory.BUSINESS.value,
                    "intent": "business",  # 兼容旧字段
                    "intent_confidence": result.get("confidence", 0.9),
                    "entities": result.get("entities", {}),
                    "target_kbs": result.get("target_kbs", []),  # 业务场景需要参考的知识库
                    "next_action": "business_match"  # 进入第2阶段：工作流选择
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

    async def _llm_select_station_type(self, object_name: str, user_message: str, candidate_types: List[str]) -> Optional[str]:
        """
        当数据库返回多种站点类型时，使用LLM根据对话意图选择最可能的类型

        Args:
            object_name: 对象名称
            user_message: 用户原始消息
            candidate_types: 候选类型列表

        Returns:
            最可能的类型，如果判断失败返回None
        """
        try:
            import time

            # 构建提示词
            prompt = f"""根据用户的对话意图，判断"{object_name}"最可能是哪种类型的监测站点。

## 用户消息
{user_message}

## 候选类型（数据库查询到的）
{', '.join(candidate_types)}

## 所有监测站点类型参考
- 水库水文站：监测水库水位、入库流量、出库流量等
- 河道水文站：监测河道水位、流量等水情信息
- 雨量站：监测降雨量
- 闸站监测：监测闸门开度、过闸流量等
- AI监测站点：AI视频监测
- 工程安全监测：监测工程结构安全
- 取水监测：监测取水量
- 墒情站：监测土壤墒情

## 判断规则
1. "水情"、"水位"、"流量"相关查询 → 优先选择"河道水文站"或"水库水文站"
2. "雨量"、"降雨"相关查询 → 选择"雨量站"
3. "闸门"、"开度"相关查询 → 选择"闸站监测"
4. "墒情"、"土壤"相关查询 → 选择"墒情站"
5. 如果用户没有明确指定，根据常见业务场景推断（水情查询最常见的是河道水文站）

请直接返回最可能的类型名称（必须是候选类型之一），不要解释："""

            _start = time.time()
            response = await self.intent_llm.ainvoke(prompt)
            _elapsed = time.time() - _start

            result_text = response.content.strip() if hasattr(response, 'content') else str(response).strip()

            # 记录日志
            log_llm_call(
                step_name="多类型站点选择",
                module_name="Planner._llm_select_station_type",
                prompt_template_name="STATION_TYPE_SELECT_PROMPT",
                context_variables={
                    "object_name": object_name,
                    "user_message": user_message,
                    "candidate_types": candidate_types
                },
                full_prompt=prompt,
                response=result_text,
                elapsed_time=_elapsed
            )

            # 验证返回的类型是否在候选列表中
            for candidate in candidate_types:
                if candidate in result_text or result_text in candidate:
                    logger.info(f"LLM选择站点类型: {result_text} (匹配: {candidate})")
                    return candidate

            logger.warning(f"LLM返回的类型'{result_text}'不在候选列表中: {candidate_types}")
            return None

        except Exception as e:
            logger.error(f"LLM选择站点类型失败: {e}")
            return None

    async def _resolve_object_type(self, entities: Dict[str, Any], target_kbs: List[str], user_message: str, force: bool = False) -> Dict[str, Any]:
        """
        解析并补全对象类型

        流程：
        1. 检查 entities 中的 object_type 是否已有值（force=True时跳过此检查）
        2. 如果没有，调用 lookup_station_code 工具查询数据库
        3. 如果数据库查不到，进行 RAG 知识库检索
        4. 调用 LLM 合成对象和对象类型

        Args:
            entities: 意图识别提取的实体
            target_kbs: 目标知识库列表
            user_message: 用户原始消息
            force: 是否强制执行解析，忽略已有的object_type（用于data_query子意图）

        Returns:
            增强后的实体字典，包含 object_type 和可能的 stcd
        """
        enhanced_entities = dict(entities)
        object_name = entities.get('object')
        object_type = entities.get('object_type')

        # 如果已经有 object_type 且不是强制模式，直接返回
        if not force and object_type and object_type != 'null' and object_type.lower() != 'null':
            logger.info(f"对象类型已存在: {object_name} -> {object_type}")
            return enhanced_entities

        # 如果没有对象名称，无法查询
        if not object_name:
            logger.info("无对象名称，跳过类型解析")
            return enhanced_entities

        logger.info(f"开始解析对象类型: {object_name}")

        db_result = "未查询到数据库记录"
        rag_context = "未检索到相关知识"

        # 步骤1: 尝试数据库查询
        try:
            from ..tools.registry import get_tool_registry
            registry = get_tool_registry()
            lookup_tool = registry.get_tool('lookup_station_code')

            if lookup_tool:
                result = await lookup_tool.execute(
                    station_name=object_name,
                    exact_match=False
                )
                if result.success and result.data:
                    stations = result.data.get('stations', [])
                    if stations:
                        # 检查是否有多种不同类型
                        unique_types = list(set(s.get('type') for s in stations if s.get('type')))

                        if len(unique_types) == 1:
                            # 只有一种类型，直接使用
                            first_station = stations[0]
                            enhanced_entities['object_type'] = first_station.get('type')
                            enhanced_entities['stcd'] = first_station.get('stcd')
                            logger.info(f"数据库查询成功(单一类型): {object_name} -> {first_station.get('type')} (stcd: {first_station.get('stcd')})")
                            return enhanced_entities
                        else:
                            # 多种类型，需要LLM根据对话意图判断
                            logger.info(f"数据库返回多种类型: {unique_types}，需要LLM判断")
                            best_type = await self._llm_select_station_type(
                                object_name=object_name,
                                user_message=user_message,
                                candidate_types=unique_types
                            )
                            if best_type:
                                # 找到匹配类型的站点
                                matched_station = next((s for s in stations if s.get('type') == best_type), stations[0])
                                enhanced_entities['object_type'] = best_type
                                enhanced_entities['stcd'] = matched_station.get('stcd')
                                logger.info(f"LLM选择类型: {object_name} -> {best_type} (stcd: {matched_station.get('stcd')})")
                                return enhanced_entities
                            else:
                                # LLM判断失败，使用第一个结果
                                first_station = stations[0]
                                enhanced_entities['object_type'] = first_station.get('type')
                                enhanced_entities['stcd'] = first_station.get('stcd')
                                logger.warning(f"LLM选择失败，使用默认: {object_name} -> {first_station.get('type')}")
                                return enhanced_entities
                    else:
                        db_result = f"数据库中未找到名为'{object_name}'的站点"
                else:
                    db_result = f"数据库查询无结果: {result.data.get('message', '未知')}" if result.data else "查询失败"
        except Exception as e:
            logger.warning(f"数据库查询站点类型失败: {e}")
            db_result = f"数据库查询异常: {str(e)}"

        logger.info(f"数据库查询结果: {db_result}")

        # 步骤2: RAG知识库检索
        try:
            from ..rag.retriever import get_rag_retriever
            rag_retriever = get_rag_retriever()

            # 使用 monitor_site 知识库优先，如果 target_kbs 中有的话
            search_kbs = ['monitor_site']
            if target_kbs:
                # 添加用户指定的知识库
                for kb in target_kbs:
                    if kb not in search_kbs:
                        search_kbs.append(kb)

            rag_result = await rag_retriever.get_relevant_context(
                user_message=f"{object_name}是什么类型？属于什么站点或工程？",
                intent="identify_object_type",
                max_length=1000,
                target_kbs=search_kbs[:3]  # 最多检索3个知识库
            )
            rag_context = rag_result.get('context', '未检索到相关知识')
            doc_count = rag_result.get('document_count', 0)
            logger.info(f"RAG检索完成，获取到 {doc_count} 条相关文档")
        except Exception as e:
            logger.warning(f"RAG检索对象类型失败: {e}")
            rag_context = f"知识库检索异常: {str(e)}"

        # 步骤3: 调用LLM合成对象类型
        try:
            import time
            context_vars = {
                "user_message": user_message,
                "object_name": object_name,
                "db_result": db_result,
                "rag_context": rag_context
            }

            _start = time.time()
            result = await self.object_type_chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = OBJECT_TYPE_SYNTHESIS_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="对象类型合成",
                module_name="Planner._resolve_object_type",
                prompt_template_name="OBJECT_TYPE_SYNTHESIS_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=str(result),
                elapsed_time=_elapsed
            )

            logger.info(f"LLM对象类型合成结果: {result}")

            # 更新实体
            if result.get('object_type') and result.get('object_type') != 'unknown':
                enhanced_entities['object_type'] = result.get('object_type')
            if result.get('stcd'):
                enhanced_entities['stcd'] = result.get('stcd')

            logger.info(f"对象类型解析完成: {object_name} -> {enhanced_entities.get('object_type', 'unknown')}")

        except Exception as e:
            logger.error(f"LLM合成对象类型失败: {e}")
            # 尝试简单推断
            if '水库' in object_name:
                enhanced_entities['object_type'] = '水库水文站'
            elif '河' in object_name or '站' in object_name:
                enhanced_entities['object_type'] = 'unknown'

        return enhanced_entities

    async def _select_relevant_tools(
        self,
        user_message: str,
        business_sub_intent: str,
        entities: Dict[str, Any]
    ) -> List[str]:
        """
        第一阶段：根据任务筛选需要的工具

        Args:
            user_message: 用户消息
            business_sub_intent: 业务子意图
            entities: 提取的实体

        Returns:
            需要的工具名称列表
        """
        from ..tools.registry import get_tool_registry
        registry = get_tool_registry()

        # 获取工具摘要
        tools_summary = registry.get_tools_summary()

        context_vars = {
            "user_message": user_message,
            "business_sub_intent": business_sub_intent,
            "entities": json.dumps(entities, ensure_ascii=False),
            "tools_summary": tools_summary
        }

        try:
            import time
            _start = time.time()
            result = await self.tool_select_chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = TOOL_SELECTION_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="工具筛选",
                module_name="Planner._select_relevant_tools",
                prompt_template_name="TOOL_SELECTION_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=str(result),
                elapsed_time=_elapsed
            )

            selected_tools = result.get("selected_tools", [])
            logger.info(f"工具筛选结果: {selected_tools}，理由: {result.get('reason', '')}")

            # 确保基础工具被包含
            if entities.get('object') and "lookup_station_code" not in selected_tools:
                # 如果有对象名称但没有选择站点查询工具，添加它
                selected_tools.insert(0, "lookup_station_code")
                logger.info("自动添加 lookup_station_code 工具")

            return selected_tools

        except Exception as e:
            logger.warning(f"工具筛选失败，使用全量工具: {e}")
            # 降级：返回所有工具名称
            return registry.list_tools()

    async def classify_business_sub_intent(self, state: AgentState) -> Dict[str, Any]:
        """
        对业务类意图进行子意图分类

        在意图识别为第3类business后、工作流匹配之前执行

        Args:
            state: 当前智能体状态

        Returns:
            包含子意图分类结果的状态更新
        """
        logger.info("执行业务子意图分类...")

        try:
            user_message = state['user_message']
            entities = state.get('entities', {})

            context_vars = {
                "user_message": user_message,
                "entities": json.dumps(entities, ensure_ascii=False)
            }

            import time
            _start = time.time()
            result = await self.sub_intent_chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = BUSINESS_SUB_INTENT_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="业务子意图分类",
                module_name="Planner.classify_business_sub_intent",
                prompt_template_name="BUSINESS_SUB_INTENT_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=str(result),
                elapsed_time=_elapsed
            )

            logger.info(f"业务子意图分类结果: {result}")

            sub_intent = result.get("business_sub_intent", "other")
            confidence = result.get("confidence", 0.9)

            return {
                "business_sub_intent": sub_intent,
                "sub_intent_confidence": confidence,
                "sub_intent_reason": result.get("reason", "")
            }

        except Exception as e:
            logger.error(f"业务子意图分类失败: {e}")
            return {
                "business_sub_intent": "other",
                "sub_intent_confidence": 0.0,
                "error": f"子意图分类失败: {str(e)}"
            }

    async def check_workflow_match(self, state: AgentState) -> Dict[str, Any]:
        """
        检查是否匹配预定义工作流（用于第3类业务场景）

        通过LLM选择最匹配的业务工作流（第3阶段，使用已分类的子意图）

        Args:
            state: 当前智能体状态（包含已分类的business_sub_intent）

        Returns:
            包含工作流匹配结果的状态更新
        """
        logger.info("执行第3阶段：业务工作流选择...")

        intent_category = state.get('intent_category')

        # 只对业务类意图进行工作流选择
        if intent_category != IntentCategory.BUSINESS.value:
            return {"matched_workflow": None, "workflow_from_template": False}

        try:
            # 获取已分类的子意图（由上一阶段传入）
            business_sub_intent = state.get('business_sub_intent', 'other')
            logger.info(f"使用已分类的子意图: {business_sub_intent}")

            # 先解析对象类型（如果未知的话）
            entities = state.get('entities', {})
            target_kbs = state.get('target_kbs', [])
            user_message = state['user_message']

            # 检查是否需要解析对象类型
            object_type = entities.get('object_type')
            # 对于监测数据查询子意图，强制执行3步对象类型解析（因为意图识别缺乏知识，无法准确判断对象类型）
            if business_sub_intent == 'data_query':
                logger.info("监测数据查询子意图，强制执行对象类型解析...")
                enhanced_entities = await self._resolve_object_type(entities, target_kbs, user_message, force=True)
            elif not object_type or object_type == 'null' or (isinstance(object_type, str) and object_type.lower() == 'null'):
                logger.info("对象类型未知，开始解析...")
                enhanced_entities = await self._resolve_object_type(entities, target_kbs, user_message)
            else:
                enhanced_entities = entities
                logger.info(f"对象类型已知: {object_type}")

            # 根据子意图获取对应的预定义工作流
            predefined_workflows = PREDEFINED_WORKFLOWS_BY_SUB_INTENT.get(
                business_sub_intent,
                PREDEFINED_WORKFLOWS_BY_SUB_INTENT.get("other", "暂无预定义工作流模板")
            )
            logger.info(f"根据子意图 {business_sub_intent} 筛选预定义工作流")

            # 根据子意图获取已保存的动态工作流列表（使用向量检索）
            saved_workflows_desc = self._get_saved_workflows_description(
                sub_intent=business_sub_intent,
                user_message=user_message
            )
            logger.info(f"根据子意图 {business_sub_intent} 和用户消息进行工作流检索")

            # 使用LLM选择工作流（使用增强后的实体和已分类的子意图，以及筛选后的工作流）
            context_vars = {
                "user_message": user_message,
                "entities": json.dumps(enhanced_entities, ensure_ascii=False),
                "business_sub_intent": business_sub_intent,
                "predefined_workflows": predefined_workflows,
                "saved_workflows": saved_workflows_desc
            }

            import time
            _start = time.time()
            result = await self.workflow_select_chain.ainvoke(context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = WORKFLOW_SELECT_PROMPT.format(**context_vars)
            log_llm_call(
                step_name="工作流选择",
                module_name="Planner.check_workflow_match",
                prompt_template_name="WORKFLOW_SELECT_PROMPT",
                context_variables=context_vars,
                full_prompt=full_prompt,
                response=str(result),
                elapsed_time=_elapsed
            )

            logger.info(f"工作流选择结果: {result}")

            matched_workflow = result.get("matched_workflow")
            saved_workflow_id = result.get("saved_workflow_id")
            output_type = result.get("output_type", "text")

            # 第1优先级：检查预定义工作流模板
            if matched_workflow:
                from ..workflows.registry import get_workflow_registry
                registry = get_workflow_registry()
                if registry.has_workflow(matched_workflow):
                    logger.info(f"LLM选择工作流: {matched_workflow}")
                    return {
                        "matched_workflow": matched_workflow,
                        "workflow_from_template": True,
                        "intent": business_sub_intent,
                        "output_type": output_type,
                        "entities": enhanced_entities,  # 返回增强后的实体
                        "next_action": "execute"
                    }
                else:
                    logger.warning(f"工作流 {matched_workflow} 未注册")

            # 第2优先级：检查已保存的动态工作流
            if saved_workflow_id:
                saved_result = self._load_saved_workflow(
                    saved_workflow_id,
                    entities=enhanced_entities,  # 使用增强后的实体
                    user_message=user_message
                )
                if saved_result:
                    display_name = saved_result.get("saved_workflow_name", saved_workflow_id)
                    logger.info(f"匹配到已保存工作流: {display_name}")
                    saved_result.update({
                        "intent": business_sub_intent,
                        "entities": enhanced_entities,  # 返回增强后的实体
                    })
                    return saved_result

            # 未匹配到工作流，需要动态规划
            logger.info(f"未匹配到工作流，子意图: {business_sub_intent}，将进行动态规划")
            return {
                "matched_workflow": None,
                "workflow_from_template": False,
                "intent": business_sub_intent,
                "output_type": output_type,
                "entities": enhanced_entities,  # 返回增强后的实体
                "next_action": "dynamic_plan"
            }

        except Exception as e:
            logger.error(f"工作流选择失败: {e}")
            return {
                "matched_workflow": None,
                "workflow_from_template": False,
                "output_type": "text",
                "next_action": "dynamic_plan",
                "error": f"工作流选择失败: {str(e)}"
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
            # 获取业务子意图
            business_sub_intent = state.get('business_sub_intent', 'other')

            # 1. 仅对特定子意图检索业务流程知识库
            # 洪水预报、洪水预演、预案生成、灾损评估需要业务流程参考
            # 其他子意图（如data_query、other）不需要固定知识库检索
            sub_intents_need_kb = ['flood_forecast', 'flood_simulation', 'emergency_plan', 'damage_assessment']

            rag_context = "无相关业务流程参考"
            rag_doc_count = 0

            if business_sub_intent in sub_intents_need_kb:
                plan_target_kbs = ["business_workflow"]
                logger.info(f"子意图 {business_sub_intent} 需要业务流程参考，目标知识库: {plan_target_kbs}")

                # 执行RAG检索，获取业务流程参考
                try:
                    from ..rag.retriever import get_rag_retriever
                    rag_retriever = get_rag_retriever()
                    rag_result = await rag_retriever.get_relevant_context(
                        user_message=state['user_message'],
                        intent=state.get('intent'),
                        max_length=2000,
                        target_kbs=plan_target_kbs
                    )
                    rag_context = rag_result.get('context', '无相关业务流程参考')
                    rag_doc_count = rag_result.get('document_count', 0)
                    logger.info(f"计划生成RAG检索完成（知识库: {plan_target_kbs}），获取到 {rag_doc_count} 条业务流程参考")
                except Exception as rag_error:
                    logger.warning(f"计划生成RAG检索失败: {rag_error}")
            else:
                logger.info(f"子意图 {business_sub_intent} 不需要固定知识库检索，跳过RAG检索")

            # 2. 两阶段工具加载
            # 第一阶段：根据任务筛选需要的工具
            selected_tools = await self._select_relevant_tools(
                user_message=state['user_message'],
                business_sub_intent=business_sub_intent,
                entities=state.get('entities', {})
            )
            logger.info(f"筛选出 {len(selected_tools)} 个相关工具: {selected_tools}")

            # 第二阶段：只加载选中工具的详细描述
            from ..tools.registry import get_tool_registry
            registry = get_tool_registry()
            available_tools = registry.get_tools_description_by_names(selected_tools)

            # 3. 准备上下文变量
            # 从意图识别阶段获取目标知识库列表，供计划生成时参考
            target_kbs = state.get('target_kbs', [])
            if not target_kbs:
                target_kbs = ["water_project", "monitor_site"]

            plan_context_vars = {
                "available_tools": available_tools,
                "rag_context": rag_context,
                "intent": state.get('intent', 'unknown'),
                "entities": state.get('entities', {}),
                "target_kbs": target_kbs,  # 传递目标知识库，供LLM规划检索步骤
                "user_message": state['user_message']
            }
            
            # 调用计划生成链（包含RAG上下文）
            import time
            _start = time.time()
            result = await self.plan_chain.ainvoke(plan_context_vars)
            _elapsed = time.time() - _start

            # 记录LLM调用日志
            full_prompt = PLAN_GENERATION_PROMPT.format(**plan_context_vars)
            log_llm_call(
                step_name="计划生成",
                module_name="Planner.generate_plan",
                prompt_template_name="PLAN_GENERATION_PROMPT",
                context_variables=plan_context_vars,
                full_prompt=full_prompt,
                response=str(result),
                elapsed_time=_elapsed
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

            # 后台异步保存动态生成的流程（不阻塞主对话）
            asyncio.create_task(self._save_dynamic_plan(state, steps, result.get('output_type', 'text')))

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

    def _get_saved_workflows_description(self, sub_intent: str = None, user_message: str = None) -> str:
        """
        获取已保存的动态工作流描述（用于提示词）

        采用两阶段检索策略：
        1. 如果提供了 user_message，先使用向量检索粗筛 Top-K 个候选
        2. 否则按子意图从数据库查询

        Args:
            sub_intent: 业务子意图，如果提供则只返回该子意图相关的工作流
            user_message: 用户消息，用于向量检索
        """
        try:
            # 第一阶段：向量检索粗筛（如果提供了用户消息）
            if user_message:
                try:
                    from ..workflows.workflow_vector_index import get_workflow_vector_index
                    workflow_index = get_workflow_vector_index()

                    # 向量检索，按子意图过滤
                    vector_results = workflow_index.search(
                        query=user_message,
                        sub_intent=sub_intent,
                        top_k=5  # 使用默认的 Top-K 值
                    )

                    if vector_results:
                        logger.info(f"向量检索返回 {len(vector_results)} 个候选工作流")

                        # 格式化向量检索结果
                        descriptions = []
                        for result in vector_results:
                            display = result.get('display_name') or result.get('name')
                            score = result.get('score', 0)
                            desc = f"""- ID: {result.get('id')}
  名称: {result.get('name')}
  中文名: {display}
  描述: {result.get('description')}
  触发模式: {result.get('trigger_pattern')}
  相似度: {score:.3f}"""
                            descriptions.append(desc)

                        return "\n".join(descriptions)
                    else:
                        logger.info("向量检索无结果，回退到数据库查询")

                except Exception as vector_error:
                    logger.warning(f"向量检索失败，回退到数据库查询: {vector_error}")

            # 第二阶段：数据库查询（向量检索无结果或未提供用户消息时）
            db = SessionLocal()
            try:
                # 构建查询
                query = db.query(SavedWorkflow).filter(
                    SavedWorkflow.is_active == True
                )

                # 如果指定了子意图，则按子意图筛选
                if sub_intent:
                    query = query.filter(SavedWorkflow.sub_intent == sub_intent)

                saved_workflows = query.order_by(SavedWorkflow.use_count.desc()).limit(10).all()

                if not saved_workflows:
                    if sub_intent:
                        return f"暂无已保存的{sub_intent}类动态工作流"
                    return "暂无已保存的动态工作流"

                # 在 Session 关闭前提取所有需要的数据，提供更详细的匹配信息
                descriptions = []
                for wf in saved_workflows:
                    display = wf.display_name or wf.name  # 优先使用中文名
                    desc = f"""- ID: {wf.id}
  名称: {wf.name}
  中文名: {display}
  描述: {wf.description}
  触发模式: {wf.trigger_pattern}
  使用次数: {wf.use_count}"""
                    descriptions.append(desc)

                return "\n".join(descriptions)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"获取已保存工作流描述失败: {e}")
            if sub_intent:
                return f"暂无已保存的{sub_intent}类动态工作流"
            return "暂无已保存的动态工作流"

    def _load_saved_workflow(self, workflow_id: str, entities: Dict[str, Any] = None, user_message: str = None) -> Optional[Dict[str, Any]]:
        """
        根据ID加载已保存的工作流，并填充模板参数

        Args:
            workflow_id: 工作流ID
            entities: 用户实体（用于填充模板占位符）
            user_message: 用户原始消息（用于填充query等参数）
        """
        try:
            db = SessionLocal()
            try:
                saved = db.query(SavedWorkflow).filter(
                    SavedWorkflow.id == workflow_id,
                    SavedWorkflow.is_active == True
                ).first()

                if saved:
                    workflow_name = saved.name
                    display_name = saved.display_name or saved.name
                    workflow_id = saved.id
                    plan_steps = json.loads(saved.plan_steps)
                    output_type = saved.output_type

                    # 填充模板参数
                    plan_steps = self._fill_template_params(plan_steps, entities or {}, user_message or "")

                    # 更新使用次数
                    saved.use_count += 1
                    db.commit()

                    logger.info(f"加载已保存工作流: {display_name} ({workflow_name})")
                    return {
                        "matched_workflow": None,
                        "workflow_from_template": False,
                        "saved_workflow_id": workflow_id,
                        "saved_workflow_name": display_name,
                        "plan": plan_steps,
                        "current_step_index": 0,
                        "output_type": output_type,
                        "next_action": "execute"
                    }
                return None
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"加载已保存工作流失败: {e}")
        return None

    def _fill_template_params(self, plan_steps: List[Dict], entities: Dict[str, Any], user_message: str) -> List[Dict]:
        """
        填充工作流模板中的占位符参数

        支持的占位符格式：
        - {{对象}}、{{对象类型}}、{{时间}}等：从entities中获取值
        - $$step_N.xxx$$：引用前一步骤的结果（保持不变，由executor解析）
        """
        # 构建替换映射
        replacements = {}

        # 核心实体映射：object -> {{对象}}, object_type -> {{对象类型}}, time -> {{时间}}, action -> {{操作}}
        entity_mapping = {
            "object": "对象",
            "object_type": "对象类型",
            "time": "时间",
            "action": "操作"
        }

        for eng_key, cn_key in entity_mapping.items():
            value = entities.get(eng_key)
            if value and value != 'null' and value is not None:
                # 同时支持中文和英文占位符
                replacements[f"{{{{{cn_key}}}}}"] = str(value)   # {{对象}}
                replacements[f"{{{cn_key}}}"] = str(value)       # {对象}
                replacements[f"{{{{{eng_key}}}}}"] = str(value)  # {{object}}
                replacements[f"{{{eng_key}}}"] = str(value)      # {object}

        # 用户消息作为默认query
        replacements["{{query}}"] = user_message
        replacements["{query}"] = user_message

        filled_steps = []
        for step in plan_steps:
            new_step = step.copy()
            tool_args = step.get("tool_args") or step.get("tool_args_template") or {}

            if isinstance(tool_args, dict):
                new_args = {}
                for arg_key, arg_value in tool_args.items():
                    if isinstance(arg_value, str):
                        # 如果是 $$step_N.xxx$$ 格式的步骤间引用，保持不变
                        if arg_value.startswith("$$") and arg_value.endswith("$$"):
                            new_args[arg_key] = arg_value
                        else:
                            # 替换实体占位符
                            new_value = arg_value
                            for placeholder, replacement in replacements.items():
                                new_value = new_value.replace(placeholder, replacement)
                            # 如果仍是未替换的占位符，设为None（避免传入无效值）
                            if (new_value.startswith("{{") and new_value.endswith("}}")) or \
                               (new_value.startswith("{") and new_value.endswith("}") and len(new_value) > 2):
                                new_args[arg_key] = None
                            else:
                                new_args[arg_key] = new_value
                    else:
                        new_args[arg_key] = arg_value
                new_step["tool_args"] = new_args
            elif not tool_args:
                # 如果tool_args为空，根据工具类型填充默认参数
                tool_name = step.get("tool_name", "")
                if tool_name == "search_knowledge":
                    new_step["tool_args"] = {"query": user_message}

            filled_steps.append(new_step)

        return filled_steps

    def _match_saved_workflow(self, state: AgentState) -> Optional[Dict[str, Any]]:
        """匹配自动保存的流程"""
        try:
            db = SessionLocal()
            try:
                sub_intent = state.get('business_sub_intent')

                # 查询同类子意图的已保存流程
                saved = db.query(SavedWorkflow).filter(
                    SavedWorkflow.is_active == True,
                    SavedWorkflow.sub_intent == sub_intent
                ).order_by(SavedWorkflow.use_count.desc()).first()

                if saved:
                    # 在 Session 关闭前提取所有需要的数据
                    workflow_name = saved.name
                    workflow_id = saved.id
                    display_name = saved.display_name
                    plan_steps = json.loads(saved.plan_steps)
                    output_type = saved.output_type

                    # 更新使用次数
                    saved.use_count += 1
                    db.commit()

                    logger.info(f"匹配到已保存流程: {display_name or workflow_name}")
                    return {
                        "matched_workflow": None,
                        "workflow_from_template": False,
                        "saved_workflow_id": workflow_id,
                        "display_name": display_name,
                        "plan": plan_steps,
                        "current_step_index": 0,
                        "output_type": output_type,
                        "next_action": "execute"
                    }
                return None
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"匹配已保存流程失败: {e}")
        return None

    async def _save_dynamic_plan(self, state: AgentState, steps: List[Dict], output_type: str):
        """
        保存动态生成的流程为通用工作流模板

        使用LLM将具体的执行计划抽象为可复用的通用模板
        """
        if len(steps) < 2:
            return  # 步骤太少不保存

        try:
            sub_intent = state.get('business_sub_intent', 'other')
            user_msg = state.get('user_message', '')
            entities = state.get('entities', {})

            # 使用LLM生成通用工作流模板
            template_vars = {
                "user_message": user_msg,
                "entities": json.dumps(entities, ensure_ascii=False),
                "business_sub_intent": sub_intent,
                "plan_steps": json.dumps(steps, ensure_ascii=False, indent=2)
            }

            try:
                template_result = await self.workflow_template_chain.ainvoke(template_vars)
                logger.info(f"工作流模板化结果: {template_result}")

                workflow_name = template_result.get('workflow_name', f"auto_{sub_intent}_{uuid.uuid4().hex[:6]}")
                display_name = template_result.get('display_name', f"{sub_intent}工作流")
                description = template_result.get('description', f"自动保存的{sub_intent}类工作流")
                trigger_pattern = template_result.get('trigger_pattern', sub_intent)
                template_steps = template_result.get('template_steps', steps)
                required_entities = template_result.get('required_entities', [])

            except Exception as llm_error:
                logger.warning(f"LLM生成工作流模板失败，使用默认值: {llm_error}")
                workflow_name = f"auto_{sub_intent}_{uuid.uuid4().hex[:6]}"
                display_name = f"{sub_intent}工作流"
                description = f"自动保存的{sub_intent}类工作流"
                trigger_pattern = sub_intent
                template_steps = steps
                required_entities = list(entities.keys()) if entities else []

            # 检查是否已存在相同名称的工作流
            db = SessionLocal()
            try:
                existing = db.query(SavedWorkflow).filter(
                    SavedWorkflow.name == workflow_name,
                    SavedWorkflow.is_active == True
                ).first()

                if existing:
                    # 更新已有工作流的使用次数
                    existing.use_count += 1
                    db.commit()
                    logger.info(f"已存在相同工作流 {workflow_name}，更新使用次数")
                    return

                workflow = SavedWorkflow(
                    id=str(uuid.uuid4()),
                    name=workflow_name,
                    display_name=display_name,
                    description=description,
                    trigger_pattern=trigger_pattern,
                    intent_category=state.get('intent_category', 'business'),
                    sub_intent=sub_intent,
                    entities_pattern=json.dumps(required_entities, ensure_ascii=False),
                    plan_steps=json.dumps(template_steps, ensure_ascii=False),
                    output_type=output_type,
                    source="auto"
                )
                db.add(workflow)
                db.commit()
                logger.info(f"已自动保存通用工作流模板: {display_name} ({workflow_name})")

                # 自动索引到向量库
                try:
                    from ..workflows.workflow_vector_index import get_workflow_vector_index
                    workflow_index = get_workflow_vector_index()
                    workflow_data = {
                        "name": workflow_name,
                        "display_name": display_name,
                        "description": description,
                        "trigger_pattern": trigger_pattern,
                        "sub_intent": sub_intent
                    }
                    workflow_index.index_workflow(workflow.id, workflow_data)
                    logger.info(f"已将工作流 {display_name} 索引到向量库")
                except Exception as index_error:
                    logger.warning(f"工作流向量索引失败（不影响保存）: {index_error}")
            finally:
                db.close()
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

    三阶段意图分析：
    - 第1阶段：三大类分类（chat/knowledge/business）
    - 第2阶段：仅business类触发子意图分类
    - 第3阶段：工作流选择（使用子意图分类结果）

    流程：
    - chat: 直接返回回复
    - knowledge: 走知识库检索流程
    - business: 先子意图分类，再工作流选择，未匹配则动态规划
    """
    planner = get_planner()

    # 第1阶段：分析意图（三大类分类）
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

    # 第3类：business - 先子意图分类，再工作流选择
    if intent_category == IntentCategory.BUSINESS.value:
        logger.info("意图类别: business，进入第2阶段子意图分类")

        # 合并意图结果到临时状态
        temp_state = dict(state)
        temp_state.update(intent_result)

        # 第2阶段：子意图分类
        sub_intent_result = await planner.classify_business_sub_intent(temp_state)
        logger.info(f"子意图分类结果: {sub_intent_result.get('business_sub_intent')}")

        # 合并子意图分类结果
        temp_state.update(sub_intent_result)

        # 第3阶段：工作流选择（传入子意图分类结果）
        logger.info("进入第3阶段工作流选择")
        workflow_result = await planner.check_workflow_match(temp_state)

        # 如果匹配到工作流（预定义模板或已保存的动态工作流），直接执行
        if workflow_result.get('matched_workflow') or workflow_result.get('saved_workflow_id'):
            matched_name = workflow_result.get('matched_workflow') or workflow_result.get('saved_workflow_name') or workflow_result.get('saved_workflow_id')
            logger.info(f"匹配到工作流: {matched_name}，直接执行")
            return {**intent_result, **sub_intent_result, **workflow_result}

        # 未匹配到工作流，进行动态规划
        logger.info(f"未匹配工作流，子意图: {sub_intent_result.get('business_sub_intent')}，进行动态规划")
        temp_state.update(workflow_result)
        plan_result = await planner.generate_plan(temp_state)
        return {**intent_result, **sub_intent_result, **workflow_result, **plan_result}

    # 默认返回意图结果
    return intent_result
