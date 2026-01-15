
*****会话ID: 0a82501b-5882-4307-b4e2-ccf3bcc0c119 | 问题: 修武站当前水位流量？*****

## 意图分析 [1.82s] (Planner.analyze_intent)
**时间**: 2026-01-15 09:03:13
**提示词模板**: INTENT_ANALYSIS_PROMPT

**上下文变量**:
- context_summary: 无
- chat_history: 无
- user_message: 修武站当前水位流量？

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

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
对话历史摘要: 无

最近对话:
无

## 用户当前消息
修武站当前水位流量？

## 输出要求
请分析用户意图，返回JSON格式:

**如果是 chat（一般对话/闲聊），直接生成回复：**
{
    "intent_category": "chat",
    "confidence": 0.95,
    "direct_response": "你的友好回复内容（控制在100字以内）",
    "is_greeting": true/false
}
注意：is_greeting仅在用户打招呼（你好、您好、hi、hello等）或询问"你是谁"、"介绍一下你自己"等自我介绍场景时为true。
- 当is_greeting=true时，回复需包含自我介绍："您好！我是卫共流域数字孪生系统的智能助手小卫，..."
- 当is_greeting=false时（如感谢、告别、闲聊等），直接回复，不要加自我介绍

**如果是 knowledge（固有知识查询）：**
{
    "intent_category": "knowledge",
    "confidence": 0.95,
    "target_kbs": ["知识库id1", "知识库id2"],
    "entities": {"关键词": "值"},
    "needs_kb_search": true,
    "needs_web_search": false,
    "rewritten_query": "结合对话历史补全后的完整查询语句"
}
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
{
    "intent_category": "business",
    "confidence": 0.95,
    "entities": {
        "object": "对象名称",
        "object_type": "对象类型或null",
        "action": "要执行的操作",
        "time": "时间范围或null"
    },
    "target_kbs": ["需要参考的知识库id列表"]
}

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
- "修武站当前水位流量" → {"object": "修武站", "object_type": null, "action": "查询水位流量", "time": "当前"}
- "盘石头水库实时水情" → {"object": "盘石头水库", "object_type": "水库水文站", "action": "查询实时水情", "time": "当前"}
- "启动洪水预报" → {"object": "洪水预报", "object_type": "洪水预报", "action": "启动", "time": null}
- "查询最新自动预报结果" → {"object": "自动预报", "object_type": "洪水预报", "action": "查询结果", "time": "最新"}

注意：
- business类只需识别类别和提取实体，具体业务子意图和工作流将在下一阶段确定
- 如果无法确定object_type，一定要填null，不要猜测！后续阶段会通过数据库和知识库查询补全
- target_kbs用于辅助计划生成阶段的知识库检索，从以下知识库id中选择相关的：catchment_basin, water_project, monitor_site, history_flood, flood_preplan, system_function, business_workflow, hydro_model, catchment_planning, project_designplan
- 根据问题涉及的内容选择相关知识库，如涉及历史洪水则包含history_flood，涉及水库信息则包含water_project

```

**LLM响应**:
```
{'intent_category': 'business', 'confidence': 0.95, 'entities': {'object': '修武站', 'object_type': '河道水文站', 'action': '查询水位流量', 'time': '当前'}, 'target_kbs': ['monitor_site']}
```

## 工作流选择 [2.50s] (Planner.check_workflow_match)
**时间**: 2026-01-15 09:03:15
**提示词模板**: WORKFLOW_SELECT_PROMPT

**上下文变量**:
- user_message: 修武站当前水位流量？
- entities: {"object": "修武站", "object_type": "河道水文站", "action": "查询水位流量", "time": "当前"}
- saved_workflows: - ID: 1a1cafb9-04e4-447e-b16d-afa641e8d7e9
  名称: query_reservoir_realtime_water_level
  描述: 查询指定水库的实时水情数据，包括当前水位、蓄水量等。仅适用于水库水文站类型的站点。
  触发模式: 查询水库当前水位、水库实时水情、水库蓄水量（仅适用于水库水文站）
  子意图: data_query
  使用次数: 5

**完整提示词**:
```
你是卫共流域数字孪生系统的业务流程选择器。

## 用户消息
修武站当前水位流量？

## 提取的实体（含对象类型信息）
{"object": "修武站", "object_type": "河道水文站", "action": "查询水位流量", "time": "当前"}

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
- ID: 1a1cafb9-04e4-447e-b16d-afa641e8d7e9
  名称: query_reservoir_realtime_water_level
  描述: 查询指定水库的实时水情数据，包括当前水位、蓄水量等。仅适用于水库水文站类型的站点。
  触发模式: 查询水库当前水位、水库实时水情、水库蓄水量（仅适用于水库水文站）
  子意图: data_query
  使用次数: 5

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
{
    "object_type_check": "对象类型检查结果，说明匹配或排除了哪些工作流",
    "sub_requirements": ["子需求1描述", "子需求2描述", ...],
    "coverage_analysis": "分析每个子需求的覆盖情况",
    "is_fully_covered": true/false,
    "business_sub_intent": "子意图类别",
    "matched_workflow": null或"工作流名称",
    "saved_workflow_id": null或"工作流ID",
    "output_type": "text 或 web_page",
    "reason": "最终决策理由"
}

**关键规则：**
- 对象类型不匹配时，必须在object_type_check中说明，并将该工作流排除
- is_fully_covered=false时，matched_workflow和saved_workflow_id必须都为null
- 部分匹配=不匹配，宁可动态规划也不能返回只能满足部分需求的工作流

## 示例

**示例1（对象类型不匹配→排除）：**
用户问："修武站当前水位流量？"
实体：{"object": "修武站", "object_type": "河道水文站", "action": "查询水位流量", "time": "当前"}

正确输出：
{
    "object_type_check": "修武站是河道水文站，query_reservoir_realtime_water_level是水库工作流，类型不匹配，排除",
    "sub_requirements": ["查询修武站当前水位流量[API调用]"],
    "coverage_analysis": "没有匹配河道水文站的已保存工作流",
    "is_fully_covered": false,
    "business_sub_intent": "data_query",
    "matched_workflow": null,
    "saved_workflow_id": null,
    "output_type": "web_page",
    "reason": "对象类型为河道水文站，无匹配的河道查询工作流，需动态规划"
}

**示例2（对象类型匹配+完全覆盖→匹配）：**
用户问："盘石头水库当前水位是多少？"
实体：{"object": "盘石头水库", "object_type": "水库水文站", "action": "查询水位", "time": "当前"}

正确输出：
{
    "object_type_check": "盘石头水库是水库水文站，与query_reservoir_realtime_water_level工作流类型匹配",
    "sub_requirements": ["查询当前实时水位[API调用]"],
    "coverage_analysis": "query_reservoir_realtime_water_level工作流完全满足这唯一的子需求，覆盖率100%",
    "is_fully_covered": true,
    "business_sub_intent": "data_query",
    "matched_workflow": null,
    "saved_workflow_id": "xxx-xxx-xxx",
    "output_type": "web_page",
    "reason": "对象类型匹配，工作流完全覆盖，可以匹配"
}

```

**LLM响应**:
```
{'object_type_check': '修武站是河道水文站，query_reservoir_realtime_water_level是水库工作流，类型不匹配，排除', 'sub_requirements': ['查询修武站当前水位流量[API调用]'], 'coverage_analysis': '没有匹配河道水文站的已保存工作流', 'is_fully_covered': False, 'business_sub_intent': 'data_query', 'matched_workflow': None, 'saved_workflow_id': None, 'output_type': 'web_page', 'reason': '对象类型为河道水文站，无匹配的河道查询工作流，需动态规划'}
```

## 任务执行(LLM) [0.69s] (Executor._execute_with_llm)
**时间**: 2026-01-15 09:03:42
**提示词模板**: EXECUTOR_LLM_PROMPT

**上下文变量**:
- task_description: 直接回答用户问题
- user_message: 修武站当前水位流量？
- execution_results: 无
- retrieved_documents: 无

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手。

## 任务
直接回答用户问题

## 用户原始消息
修武站当前水位流量？

## 已有执行结果
无

## 检索到的知识
无

请根据以上信息完成任务，给出清晰、准确的回答。

```

**LLM响应**:
```
目前没有获取到修武站当前水位流量的具体数据。建议您稍后再次查询或联系相关水利管理部门获取最新信息。
```

---

