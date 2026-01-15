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
  - 具体站点/水库/河道名称（如"修武站"、"盘石头水库"、"卫河"）
  - 业务事件名称（如"洪水预报"、"预演方案"）
  - 区域名称（如"卫共流域"、"新乡市"）
- object_type: 对象的类型，如果能明确判断则填写，否则填null。常见类型：
  - 站点类：水库水文站、河道水文站、雨量站、闸站监测、AI监测站点
  - 工程类：水库、河道、蓄滞洪区、闸站
  - 业务类：洪水预报、洪水预演、预案生成、灾损评估
  - 如果无法从用户消息中明确判断类型，必须填null（后续阶段会自动查询补全）
- action: 用户想要执行的具体操作（如"查询当前水位"、"启动预报"、"对比分析"）
- time: 时间范围（如"当前"、"最近24小时"、"2023年7月"），无时间要求则填null

**示例：**
- "修武站当前水位流量" → {{"object": "修武站", "object_type": null, "action": "查询水位流量", "time": "当前"}}
- "盘石头水库实时水情" → {{"object": "盘石头水库", "object_type": "水库水文站", "action": "查询实时水情", "time": "当前"}}
- "启动洪水预报" → {{"object": "洪水预报", "object_type": "洪水预报", "action": "启动", "time": null}}
- "查询最新自动预报结果" → {{"object": "自动预报", "object_type": "洪水预报", "action": "查询结果", "time": "最新"}}

注意：
- business类只需识别类别和提取实体，具体业务子意图和工作流将在下一阶段确定
- 如果无法确定object_type，一定要填null，不要猜测！后续阶段会通过数据库和知识库查询补全
- target_kbs用于辅助计划生成阶段的知识库检索，从以下知识库id中选择相关的：catchment_basin, water_project, monitor_site, history_flood, flood_preplan, system_function, business_workflow, hydro_model, catchment_planning, project_designplan
- 根据问题涉及的内容选择相关知识库，如涉及历史洪水则包含history_flood，涉及水库信息则包含water_project
"""

# 2、业务工作流选择提示词（第2阶段，仅business类触发）
WORKFLOW_SELECT_PROMPT = """你是河南省卫共流域数字孪生系统的业务流程选择器。

## 用户消息
{user_message}

## 提取的实体（含对象类型信息）
{entities}

## 【重要】对象类型匹配规则
在选择工作流之前，必须先检查实体中的object_type字段：
- 如果object_type为"水库水文站"或包含"水库"：只能匹配水库相关工作流（如query_reservoir_xxx）
- 如果object_type为"河道水文站"或包含"河道"：只能匹配河道相关工作流（如query_river_xxx）
- 如果object_type为"雨量站"：只能匹配雨量相关工作流
- 如果object_type为"洪水预报"相关：只能匹配预报类工作流
- 如果object_type为"洪水预演"相关：只能匹配预演类工作流
- **类型不匹配的工作流，即使功能相似，也必须视为覆盖率0%，禁止匹配！**

## 预定义工作流（模板）
以下是系统中已注册的业务工作流模板：

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

## 已保存的动态工作流
以下是之前对话中动态规划生成并保存的工作流，优先匹配这些已验证的流程：
{saved_workflows}

## 业务子意图分类
- data_query: 监测数据查询（当前水位、实时雨情、流量数据等）
- flood_forecast: 洪水预报相关（启动预报、查询预报结果）
- flood_simulation: 洪水预演相关（启动预演、查询预演结果）
- emergency_plan: 预案生成
- damage_assessment: 灾损评估、避险转移
- other: 其他业务操作

## 【核心】工作流匹配决策流程（必须严格按顺序执行）

**第零步：检查对象类型匹配**
首先检查entities中的object_type，筛选出类型匹配的候选工作流。类型不匹配的工作流直接排除，不进入后续评估。

**第一步：拆解用户问题的所有子需求**
将用户问题拆解为独立的子需求列表，每个子需求对应一个具体的数据获取或操作。

**第二步：逐一检查每个子需求的数据来源**
对每个子需求标注其数据来源类型：
- [知识库]：历史洪水数据、水库特征参数、防洪标准等静态信息
- [API调用]：当前/实时水位、流量等动态监测数据
- [模型计算]：预报、预演等需要启动计算的操作

**第三步：评估工作流覆盖度**
检查候选工作流能覆盖哪些子需求：
- 完全覆盖（100%）：工作流能满足所有子需求 → 可以匹配
- 部分覆盖（<100%）：工作流只能满足部分子需求 → **禁止匹配**
- 无覆盖（0%）：工作流与需求无关 → 不匹配

**第四步：做出最终决策**
- 只有"完全覆盖"才能返回工作流ID
- "部分覆盖"必须返回null，交给动态规划处理

## 输出要求
返回JSON格式（注意字段顺序，先分析后决策）：
{{
    "object_type_check": "对象类型检查结果，说明匹配或排除了哪些工作流",
    "sub_requirements": ["子需求1描述", "子需求2描述", ...],
    "coverage_analysis": "分析每个子需求的覆盖情况",
    "is_fully_covered": true/false,
    "business_sub_intent": "子意图类别",
    "matched_workflow": null或"工作流名称",
    "saved_workflow_id": null或"工作流ID",
    "output_type": "text 或 web_page",
    "reason": "最终决策理由"
}}

**关键规则：**
- 对象类型不匹配时，必须在object_type_check中说明，并将该工作流排除
- is_fully_covered=false时，matched_workflow和saved_workflow_id必须都为null
- 部分匹配=不匹配，宁可动态规划也不能返回只能满足部分需求的工作流

## 示例

**示例1（对象类型不匹配→排除）：**
用户问："修武站当前水位流量？"
实体：{{"object": "修武站", "object_type": "河道水文站", "action": "查询水位流量", "time": "当前"}}

正确输出：
{{
    "object_type_check": "修武站是河道水文站，query_reservoir_realtime_water_level是水库工作流，类型不匹配，排除",
    "sub_requirements": ["查询修武站当前水位流量[API调用]"],
    "coverage_analysis": "没有匹配河道水文站的已保存工作流",
    "is_fully_covered": false,
    "business_sub_intent": "data_query",
    "matched_workflow": null,
    "saved_workflow_id": null,
    "output_type": "web_page",
    "reason": "对象类型为河道水文站，无匹配的河道查询工作流，需动态规划"
}}

**示例2（对象类型匹配+完全覆盖→匹配）：**
用户问："盘石头水库当前水位是多少？"
实体：{{"object": "盘石头水库", "object_type": "水库水文站", "action": "查询水位", "time": "当前"}}

正确输出：
{{
    "object_type_check": "盘石头水库是水库水文站，与query_reservoir_realtime_water_level工作流类型匹配",
    "sub_requirements": ["查询当前实时水位[API调用]"],
    "coverage_analysis": "query_reservoir_realtime_water_level工作流完全满足这唯一的子需求，覆盖率100%",
    "is_fully_covered": true,
    "business_sub_intent": "data_query",
    "matched_workflow": null,
    "saved_workflow_id": "xxx-xxx-xxx",
    "output_type": "web_page",
    "reason": "对象类型匹配，工作流完全覆盖，可以匹配"
}}
"""

# 3、计划生成提示词
PLAN_GENERATION_PROMPT = """你是河南省卫共流域数字孪生系统的任务规划器，负责制定执行计划。

## 可用工具
{available_tools}

## 可用工作流
{available_workflows}

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
5. 只使用可用工具列表中存在的工具名称，不要使用不存在的工具如"generate_response"
6. 参考"业务流程参考"中的信息，了解类似业务的处理模式

**知识库检索规划（重要）：**
- 如果用户问题需要知识库中的信息（如历史洪水数据、水库特征参数、防洪标准等），必须在计划中添加"search_knowledge"工具调用步骤
- search_knowledge工具参数：{{"query": "检索关键词", "target_kbs": ["知识库id列表"]}}
- 目标知识库应根据问题内容选择，参考上面的"目标知识库"字段
- 知识库检索步骤应安排在需要该信息的步骤之前
- 例如：查询历史洪水水位需要先search_knowledge检索history_flood，再进行数据处理
"""

# 4、工作流模板化生成提示词（将具体执行计划抽象为通用模板）
WORKFLOW_TEMPLATE_PROMPT = """你是一个工作流模板生成器，需要将具体的执行计划抽象为通用的业务工作流模板。

## 原始用户消息
{user_message}

## 提取的实体
{entities}

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
    "trigger_pattern": "触发模式描述（中文，用于匹配用户意图，必须强调适用的对象类型）",
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
- {{{{对象类型}}}}：对象的类型
- {{{{时间}}}}：时间范围

**步骤间数据传递（使用$$符号）：**
- $$step_N.字段名$$：引用第N步的输出字段
- 例如：步骤2返回stcd，步骤3使用 {{"stcd": "$$step_2.stcd$$"}}

**示例：**
- 步骤2：{{"station_name": "{{{{对象}}}}", "station_type": "{{{{对象类型}}}}"}}
- 步骤3：{{"stcd": "$$step_2.stcd$$"}}

注意：
1. 去除所有具体值，保留通用结构
2. 严格区分用户输入占位符和步骤间传递占位符
3. 强调对象类型匹配
"""

# 5、对象类型合成提示词（用于RAG检索后合成对象类型）
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

    async def _resolve_object_type(self, entities: Dict[str, Any], target_kbs: List[str], user_message: str) -> Dict[str, Any]:
        """
        解析并补全对象类型

        流程：
        1. 检查 entities 中的 object_type 是否已有值
        2. 如果没有，调用 lookup_station_code 工具查询数据库
        3. 如果数据库查不到，进行 RAG 知识库检索
        4. 调用 LLM 合成对象和对象类型

        Args:
            entities: 意图识别提取的实体
            target_kbs: 目标知识库列表
            user_message: 用户原始消息

        Returns:
            增强后的实体字典，包含 object_type 和可能的 stcd
        """
        enhanced_entities = dict(entities)
        object_name = entities.get('object')
        object_type = entities.get('object_type')

        # 如果已经有 object_type，直接返回
        if object_type and object_type != 'null' and object_type.lower() != 'null':
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

    async def check_workflow_match(self, state: AgentState) -> Dict[str, Any]:
        """
        检查是否匹配预定义工作流（用于第3类业务场景）

        通过LLM选择最匹配的业务工作流（第2阶段）

        Args:
            state: 当前智能体状态

        Returns:
            包含工作流匹配结果的状态更新
        """
        logger.info("执行第2阶段：业务工作流选择...")

        intent_category = state.get('intent_category')

        # 只对业务类意图进行工作流选择
        if intent_category != IntentCategory.BUSINESS.value:
            return {"matched_workflow": None, "workflow_from_template": False}

        try:
            # 【新增】先解析对象类型（如果未知的话）
            entities = state.get('entities', {})
            target_kbs = state.get('target_kbs', [])
            user_message = state['user_message']

            # 检查是否需要解析对象类型
            object_type = entities.get('object_type')
            if not object_type or object_type == 'null' or (isinstance(object_type, str) and object_type.lower() == 'null'):
                logger.info("对象类型未知，开始解析...")
                enhanced_entities = await self._resolve_object_type(entities, target_kbs, user_message)
            else:
                enhanced_entities = entities
                logger.info(f"对象类型已知: {object_type}")

            # 获取已保存的动态工作流列表
            saved_workflows_desc = self._get_saved_workflows_description()

            # 使用LLM选择工作流（使用增强后的实体）
            context_vars = {
                "user_message": user_message,
                "entities": json.dumps(enhanced_entities, ensure_ascii=False),
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
            sub_intent = result.get("business_sub_intent", "other")
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
                        "business_sub_intent": sub_intent,
                        "intent": sub_intent,
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
                    logger.info(f"匹配到已保存工作流: {saved_workflow_id}")
                    saved_result.update({
                        "business_sub_intent": sub_intent,
                        "intent": sub_intent,
                        "entities": enhanced_entities,  # 返回增强后的实体
                    })
                    return saved_result

            # 未匹配到工作流，需要动态规划
            logger.info(f"未匹配到工作流，子意图: {sub_intent}，将进行动态规划")
            return {
                "matched_workflow": None,
                "workflow_from_template": False,
                "business_sub_intent": sub_intent,
                "intent": sub_intent,
                "output_type": output_type,
                "entities": enhanced_entities,  # 返回增强后的实体
                "next_action": "dynamic_plan"
            }

        except Exception as e:
            logger.error(f"工作流选择失败: {e}")
            return {
                "matched_workflow": None,
                "workflow_from_template": False,
                "business_sub_intent": "other",
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
            # 1. 计划生成阶段只检索业务流程知识库，用于了解可用的业务流程模式
            # 具体的业务知识（如历史洪水数据、水库参数等）应在计划执行阶段按需检索
            # 这样避免：1) 重复检索 2) 无关知识稀释规划注意力
            plan_target_kbs = ["business_workflow"]

            logger.info(f"计划生成阶段目标知识库: {plan_target_kbs}（仅检索业务流程参考）")

            # 2. 执行RAG检索，仅获取业务流程参考
            rag_context = "无相关业务流程参考"
            rag_doc_count = 0
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

            # 3. 获取可用工具描述
            available_tools = self._get_available_tools_description()

            # 4. 获取可用工作流描述
            available_workflows = self._get_available_workflows_description()

            # 5. 准备上下文变量
            # 从意图识别阶段获取目标知识库列表，供计划生成时参考
            target_kbs = state.get('target_kbs', [])
            if not target_kbs:
                target_kbs = ["water_project", "monitor_site"]

            plan_context_vars = {
                "available_tools": available_tools,
                "available_workflows": available_workflows,
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

    def _get_saved_workflows_description(self) -> str:
        """获取已保存的动态工作流描述（用于提示词）"""
        try:
            db = SessionLocal()
            try:
                saved_workflows = db.query(SavedWorkflow).filter(
                    SavedWorkflow.is_active == True
                ).order_by(SavedWorkflow.use_count.desc()).limit(10).all()

                if not saved_workflows:
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
  子意图: {wf.sub_intent}
  使用次数: {wf.use_count}"""
                    descriptions.append(desc)

                return "\n".join(descriptions)
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"获取已保存工作流描述失败: {e}")
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

    两阶段意图分析：
    - 第1阶段：三大类分类（chat/knowledge/business）
    - 第2阶段：仅business类触发工作流选择

    流程：
    - chat: 直接返回回复
    - knowledge: 走知识库检索流程
    - business: 第2阶段LLM选择工作流，未匹配则动态规划
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

    # 第3类：business - 第2阶段：LLM选择工作流
    if intent_category == IntentCategory.BUSINESS.value:
        logger.info("意图类别: business，进入第2阶段工作流选择")

        # 合并意图结果到临时状态
        temp_state = dict(state)
        temp_state.update(intent_result)

        # 第2阶段：LLM选择工作流
        workflow_result = await planner.check_workflow_match(temp_state)

        # 如果匹配到工作流（预定义模板或已保存的动态工作流），直接执行
        if workflow_result.get('matched_workflow') or workflow_result.get('saved_workflow_id'):
            matched_name = workflow_result.get('matched_workflow') or workflow_result.get('saved_workflow_id')
            logger.info(f"匹配到工作流: {matched_name}，直接执行")
            return {**intent_result, **workflow_result}

        # 未匹配到工作流，进行动态规划
        logger.info(f"未匹配工作流，子意图: {workflow_result.get('business_sub_intent')}，进行动态规划")
        temp_state.update(workflow_result)
        plan_result = await planner.generate_plan(temp_state)
        return {**intent_result, **workflow_result, **plan_result}

    # 默认返回意图结果
    return intent_result
