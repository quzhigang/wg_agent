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
- catchment_basin(流域概况)：卫共流域概况、流域面积、行政区划、防洪标准、水库等水利工程数量等
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
- "XX水库当前库容" → business（实时数据）
- "统计各水库当前库容总和" → business（实时数据+统计）
- "未来洪水预报" → business（预报结果）
- "历史洪水最高水位与当前水位对比" → business（包含实时数据）
- "21.7洪水水位是否超过防洪高水位" → knowledge（纯历史数据与固有参数对比）

**核心原则**：只要问题中涉及"当前"、"实时"、"最新"、"现在"等时间关键词，整体归类为business

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
  - 业务事件名称（如"洪水预报"、"预演方案"、"23.7洪水"）
  - 区域名称（如"卫共流域"、"新乡市"）
- object_type: 对象的类型，如果能明确判断则填写，否则填null
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
- 针对单个明确站点/对象的监测数据查询（当前/实时/历史某时刻）
- 直接查询水情数据，无需获取特征参数进行对比、判断

### flood_forecast（洪水预报）
- 启动洪水预报计算
- 查询预报结果
- 预警信息查询

### flood_simulation（洪水预演）
- 启动洪水预演/模拟
- 查询预演结果
- 淹没分析

### emergency_plan（预案生成）
- 生成防洪预案
- 调度方案制定

### damage_assessment（灾损评估）
- 灾害损失评估
- 避险转移分析
- 受灾人口统计

### other（其他业务操作）
- 查询对象为群体/不明确
- 需要多步处理（对比、统计、汇总、排序等）
- 需要获取特征参数（如防洪高水位、设计水位等）与实时数据进行对比判断
- 需要知识库检索辅助回答

## 输出要求
返回JSON格式：
{{
    "business_sub_intent": "子意图类别（data_query/flood_forecast/flood_simulation/emergency_plan/damage_assessment/other）",
    "confidence": 0.95,
    "reason": "分类理由"
}}

## 分类规则
1. 涉及"预报"、"预测"、"未来洪水" → flood_forecast
2. 涉及"预演"、"模拟" → flood_simulation
3. 涉及"预案"、"调度方案" → emergency_plan
4. 涉及"损失"、"灾损"、"转移" → damage_assessment
5. 涉及对比、判断、统计、汇总等后续处理，或需要获取特征参数（如防洪高水位、设计水位、汛限水位等）与实时数据对比 → other
6. 查询对象为群体/不明确 → other
7. 针对单个明确对象直接查询水情数据，无需对比判断 → data_query
8. 无法明确归类 → other
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
   示例："去年6月中旬那场洪水预报"、"历史预报记录"、"2025年9月4日那场降雨的洪水预报"

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

1. **时间判断（flood_forecast子意图必须遵守）**
   - entities.time为具体历史日期（如"2024年7月"、"去年"、"上次"） → 选择历史查询工作流
   - entities.time为"当前"、"最新"、"未来"或null → 选择最新查询工作流

2. **data_query子意图必须严格匹配数据来源**
   - 数据来源由entities中的object_type字段确定
   - 工作流的数据来源必须与object_type完全对应

3. **工作流必须完全覆盖用户需求**，部分满足返回null

4. **无可用工作流时返回null**

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

## 业务流程参考
{rag_context}

## 用户意图
意图: {intent}
实体: {entities}
目标知识库: {target_kbs}

## 用户消息
{user_message}

## 输出JSON格式
{{
    "steps": [
        {{
            "step_id": 1,
            "description": "步骤描述",
            "tool_name": "工具名称或null",
            "tool_args": {{"参数": "值"}},
            "dependencies": [依赖步骤id],
            "is_async": false,
            "result_display": "skip/summary/full",
            "result_fields": ["字段1", "字段2"]
        }}
    ],
    "estimated_time_seconds": 30,
    "output_type": "text或web_page"
}}


**重要：tool_args中的布尔类型参数必须使用JSON布尔值true/false，不要使用字符串"true"/"false"**

**dependencies字段格式（重要）：**
- dependencies是整数数组，表示当前步骤依赖哪些步骤的执行结果
- 正确示例：[1] 或 [1, 2]（纯数字）
- 错误示例：["step_1"] 或 ["1"]（不要使用字符串）

**步骤间参数传递（重要）：**
- 当后续步骤需要使用前面步骤的结果时，在tool_args中使用占位符格式：$$step_N.字段名$$
- 例如：步骤1返回 {{"data": {{"stcd": "31005650"}}}}，步骤2要使用stcd，应写：$$step_1.stcd$$
- **数组返回值处理**：如果步骤返回的是数组（如列表查询），需要使用索引访问：$$step_N[0].字段名$$
  - 例如：步骤1返回 {{"data": [{{"code": "xxx", "name": "yyy"}}]}}，步骤2要使用code，应写：$$step_1[0].code$$
- 常用字段：stcd（站点编码）、stnm（站点名称）、code（设备编码）、data（数据对象）
- 错误示例：$$STEP_1.result_code$$（result_code不存在）
- 正确示例：$$step_1.stcd$$（直接使用返回数据中的字段名）
- 正确示例：$$step_1[0].code$$（数组返回值需要索引访问）

**result_display字段（结果展示模式）：**
根据用户问题判断每个步骤的结果对最终回答用户问题的重要程度：
- "skip": 不提交 - 此步骤结果对回答用户问题无直接帮助
- "summary": 摘要提交 - 此步骤结果有参考价值，但只需展示摘要
- "full": 完整提交 - 此步骤结果是回答用户问题的核心数据
注意：最后一个步骤必须是 "full"

**result_fields字段（结果字段筛选）：**
- 从工具"返回字段"中选择后续步骤实际需要的字段名列表
- 对返回列表数据的工具（如查询所有水库、所有河道），务必只选所需字段，避免传递过多无关数据
- 如果不需要筛选（如工具返回字段较少），可省略此字段或设为空数组
- 示例：用户问"各水库的总库容"，调用get_reservoir_flood_list时只需 ["stcd", "stnm", "ttcp"]

规划原则:
1. 步骤应该清晰、可执行
2. 正确设置步骤间的依赖关系
3. 耗时操作（如模型调用）应标记为异步
4. 对于数据对比、分析推理、结论生成等不需要调用外部接口的步骤，将 tool_name 设为 null，系统会自动使用LLM完成处理
5. 参考"业务流程参考"中的信息
6. 只使用可用工具列表中存在的工具名称，不要使用不存在的工具如"generate_response"

**站点编码查询规则（重要）：**
- **如果 entities 中已经包含 stcd 字段，直接使用该 stcd，不需要调用 lookup_station_code 工具**
- 使用 lookup_station_code 工具时，exact_match 参数必须设为 false（模糊匹配）
- 如果需要查询特定类型的站点（如视频监测），必须传递 station_type 参数进行过滤
- 因为用户输入的站点名称（如"新村水文站"）可能与数据库中的名称（如"新村"）不完全一致

**视频监控查询规则（重要）：**
- 查询视频监控需要两步：
  1. 先调用 get_camera_list(stcd=站点编码) 获取该站点下的摄像头列表
  2. 再调用 query_camera_preview(code=摄像头编码) 获取视频流地址
- **摄像头编码(code)和站点编码(stcd)是不同的！**
  - 站点编码(stcd)格式如：41000020003-A4
  - 摄像头编码(code)格式如：41062240201327003002（从get_camera_list返回结果的code字段获取）
- query_camera_preview 的 code 参数必须引用 get_camera_list 返回结果中的 code 字段，如：$step_1[0].code$

**数组结果访问规则（重要）：**
- 如果某个步骤返回的是数组（如摄像头列表、站点列表），后续步骤引用时必须使用索引
- 正确：$step_1[0].code$ （获取数组第一个元素的code字段）
- 错误：$step_1.code$ （数组没有code属性，会返回None）

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

## 判断规则（按顺序执行）
1. 首先检查"待识别对象"是否包含"水库/站/闸/蓄滞洪区/流域"等关键词，若不包含，则忽略该对象，直接从"用户消息"中提取包含这些关键词的有效对象
2. 优先使用数据库查询结果中的station_type字段
3. 如果数据库无结果，根据知识库检索内容推断
4. 如果名称中包含"水库"且无其他信息，推断为"水库水文站"
5. 若用户消息中也无有效对象，默认object为"全流域"，object_type为"流域"

## 输出要求
返回JSON格式：
{{
    "object": "对象名称（从用户消息中提取的有效对象或全流域）",
    "object_type": "对象类型",
    "stcd": "站点编码（如果有）",
    "confidence": 0.9,
    "source": "类型来源：db/rag/infer/user_message",
    "reason": "判断依据"
}}

## 对象类型选项
- 站点类：水库水文站、河道水文站、雨量站、闸站监测、AI监测站点、工程安全监测、取水监测、墒情站
- 工程类：水库、河道、蓄滞洪区、闸站
- 业务类：洪水预报、洪水预演、预案生成、灾损评估
- 区域类：流域、行政区
- 其他：unknown（如果无法确定）
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

## 选择原则（严格按顺序执行）
1. **【强制规则】流域基本信息工具(basin_info)选用原则**：
   - 当提取的实体包含水库、水闸、蓄滞洪区、测站、河道等流域对象时，必须从流域基本信息(basin_info)中选择对应工具
   - 水库相关 → get_reservoir_info(水库基础信息), get_reservoir_flood_detail(水库防洪详情), get_reservoir_flood_list(水库防洪列表)
   - 水闸相关 → get_sluice_info(水闸信息)
   - 蓄滞洪区相关 → get_flood_storage_area(蓄滞洪区信息), get_flood_dam_info(分洪闸堰信息)
   - 河道相关 → get_river_flood_list(河道防洪列表)
   - 测站相关 → get_station_list(测站列表), get_camera_list(摄像头列表)
   - 地图数据 → get_map_data(地图数据源), get_list_data(列表数据源)
2. **【强制规则】水雨情等监测工具(hydro_monitor)选用原则**：
   - 当用户问题意图为获取监测数据时，必须根据监测数据类型从水雨情监测数据(hydro_monitor)中选择工具
   - 当用户消息包含当前、实时、最新、现在、目前等时间关键词时，也必须根据监测数据类型从水雨情监测数据(hydro_monitor)中选择工具
   - 水库水情 → query_reservoir_last(最新水情), query_reservoir_process(历史过程)
   - 河道水情 → query_river_last(最新水情), query_river_process(历史过程)
   - 雨量数据 → query_rain_process(历史过程), query_rain_statistics(统计), query_rain_sum(累计雨量)
   - AI监测 → query_ai_water_last(AI水情), query_ai_rain_last(AI雨情)
3. **工具组合原则**：
   - 需要基础信息+实时数据时，同时选择 basin_info 和 hydro_monitor 工具
   - 需要站点编码时包含 lookup_station_code
   - 需要知识库检索时包含 search_knowledge
4. 如果不确定需要哪个工具，可以多选几个相关的
"""

