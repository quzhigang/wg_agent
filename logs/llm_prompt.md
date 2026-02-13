
*****会话ID: c3c102c0-1a83-470a-96e7-4c4ab93d227f | 问题: 当前新村站水位超过警戒水位了吗？*****

## 一、意图分析 [1.84s] (Planner.analyze_intent)
**时间**: 2026-02-13 20:39:40
**提示词模板**: INTENT_ANALYSIS_PROMPT

**上下文变量**:
- context_summary: 无
- chat_history: 无
- user_message: 当前新村站水位超过警戒水位了吗？

**完整提示词**:
```
你是河南省卫共流域数字孪生系统的智能助手"小卫"，负责分析用户意图。

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
对话历史摘要: 无

最近对话:
无

## 用户当前消息
当前新村站水位超过警戒水位了吗？

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
  - 具体站点/水库/河道/工程名称（如"修武站"、"盘石头水库"、"卫河"、"盐土庄闸"）
  - 业务事件名称（如"洪水预报"、"预演方案"、"23.7洪水"）
  - 区域名称（如"卫共流域"、"新乡市"）
- object_type: 对象的类型，如果能明确判断则填写，否则填null
- action: 用户想要执行的具体操作（如"查询当前水位"、"启动预报"、"对比分析"）
- time: 时间范围（如"当前"、"最近24小时"、"2023年7月"），无时间要求则填null

**示例：**
- "盘石头水库实时水情" → {"object": "盘石头水库", "object_type": "水库", "action": "查询实时水情", "time": "当前"}

注意：
- business类只需识别类别和提取实体，具体业务子意图和工作流将在下一阶段确定
- 如果无法确定object_type，一定要填null，不要猜测！后续阶段会通过数据库和知识库查询补全
- target_kbs用于辅助计划生成阶段的知识库检索，从以下知识库id中选择相关的：catchment_basin, water_project, monitor_site, history_flood, flood_preplan, system_function, business_workflow, hydro_model, catchment_planning, project_designplan
- 根据问题涉及的内容选择相关知识库，如涉及历史洪水则包含history_flood，涉及水库信息则包含water_project

```

**LLM响应**:
```
{'intent_category': 'business', 'confidence': 0.95, 'entities': {'object': '新村站', 'object_type': None, 'action': '查询是否超过警戒水位', 'time': '当前'}, 'target_kbs': ['monitor_site']}
```

## 二、业务子意图分类 [1.79s] (Planner.classify_business_sub_intent)
**时间**: 2026-02-13 20:39:42
**提示词模板**: BUSINESS_SUB_INTENT_PROMPT

**上下文变量**:
- user_message: 当前新村站水位超过警戒水位了吗？
- entities: {"object": "新村站", "object_type": null, "action": "查询是否超过警戒水位", "time": "当前"}

**完整提示词**:
```
你是河南省卫共流域数字孪生系统的业务意图分类器，负责对业务类意图进行细分。

## 用户消息
当前新村站水位超过警戒水位了吗？

## 提取的实体
{"object": "新村站", "object_type": null, "action": "查询是否超过警戒水位", "time": "当前"}

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
{
    "business_sub_intent": "子意图类别（data_query/flood_forecast/flood_simulation/emergency_plan/damage_assessment/other）",
    "confidence": 0.95,
    "reason": "分类理由"
}

## 分类规则
1. 涉及"预报"、"预测"、"未来洪水" → flood_forecast
2. 涉及"预演"、"模拟" → flood_simulation
3. 涉及"预案"、"调度方案" → emergency_plan
4. 涉及"损失"、"灾损"、"转移" → damage_assessment
5. 涉及对比、判断、统计、汇总等后续处理，或需要获取特征参数（如防洪高水位、设计水位、汛限水位等）与实时数据对比 → other
6. 查询对象为群体/不明确 → other
7. 针对单个明确对象直接查询水情数据，无需对比判断 → data_query
8. 无法明确归类 → other

```

**LLM响应**:
```
{'business_sub_intent': 'other', 'confidence': 0.95, 'reason': "用户询问新村站水位是否超过警戒水位，需要获取特征参数（如警戒水位）并与实时数据进行对比判断，因此属于'other'类别。"}
```

## 三、多类型站点选择 [0.41s] (Planner._llm_select_station_type)
**时间**: 2026-02-13 20:39:43
**提示词模板**: STATION_TYPE_SELECT_PROMPT

**上下文变量**:
- object_name: 新村站
- user_message: 当前新村站水位超过警戒水位了吗？
- candidate_types: ['河道水文站', '墒情站', '雨量站', '视频监测']

**完整提示词**:
```
根据用户的对话意图，判断"新村站"最可能是哪种类型的监测站点。

## 用户消息
当前新村站水位超过警戒水位了吗？

## 候选类型（数据库查询到的）
河道水文站, 墒情站, 雨量站, 视频监测

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

请直接返回最可能的类型名称（必须是候选类型之一），不要解释：
```

**LLM响应**:
```
河道水文站
```

## 四、工作流选择 [0.84s] (Planner.check_workflow_match)
**时间**: 2026-02-13 20:39:46
**提示词模板**: WORKFLOW_SELECT_PROMPT

**上下文变量**:
- user_message: 当前新村站水位超过警戒水位了吗？
- entities: {"object": "新村站", "object_type": "河道水文站", "action": "查询是否超过警戒水位", "time": "当前", "stcd": "31005700"}
- business_sub_intent: other
- predefined_workflows: 
暂无预定义工作流模板，请检查已保存的动态工作流或进行动态规划。

- saved_workflows: - ID: 19c0e794-39fb-48dc-beb4-bc537e538a65
  名称: compare_reservoir_realtime_vs_historical_flood
  中文名: 水库实时与历史洪水水位对比
  描述: 获取特定水库的当前实时水位，并检索历史特定洪水事件期间的最高水位进行对比分析。
  触发模式: 用户询问水库当前水位是否超过了历史上某次特定洪水（如21.7洪水）的最高水位或特征水位。
  相似度: 0.459
- ID: c9ea37ec-3985-49fe-8d07-6f84a0e0f39a
  名称: flood_event_comparison
  中文名: 洪水事件对比分析
  描述: 针对特定水文站点，查询历史洪水期间的最大洪峰、总过洪量，并与当前实时流量进行对比分析。
  触发模式: 询问{{对象}}在某次洪水期间的最大洪峰、总过洪量，并要求与当前流量进行对比（适用于河道水文站及历史洪水数据来源）
  相似度: 0.412

**完整提示词**:
```
你是河南省卫共流域数字孪生系统的业务流程选择器，负责从可用工作流中选择最匹配的一个。

## 输入信息
- 用户消息：当前新村站水位超过警戒水位了吗？
- 实体：{"object": "新村站", "object_type": "河道水文站", "action": "查询是否超过警戒水位", "time": "当前", "stcd": "31005700"}
- 子意图：other

## 可用的预定义工作流

暂无预定义工作流模板，请检查已保存的动态工作流或进行动态规划。


## 可用的已保存工作流
- ID: 19c0e794-39fb-48dc-beb4-bc537e538a65
  名称: compare_reservoir_realtime_vs_historical_flood
  中文名: 水库实时与历史洪水水位对比
  描述: 获取特定水库的当前实时水位，并检索历史特定洪水事件期间的最高水位进行对比分析。
  触发模式: 用户询问水库当前水位是否超过了历史上某次特定洪水（如21.7洪水）的最高水位或特征水位。
  相似度: 0.459
- ID: c9ea37ec-3985-49fe-8d07-6f84a0e0f39a
  名称: flood_event_comparison
  中文名: 洪水事件对比分析
  描述: 针对特定水文站点，查询历史洪水期间的最大洪峰、总过洪量，并与当前实时流量进行对比分析。
  触发模式: 询问{{对象}}在某次洪水期间的最大洪峰、总过洪量，并要求与当前流量进行对比（适用于河道水文站及历史洪水数据来源）
  相似度: 0.412

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
{
    "matched_workflow": null或"预定义工作流名称",
    "saved_workflow_id": null或"已保存工作流的UUID",
    "output_type": "text或web_page"
}

注意：matched_workflow填预定义工作流名称，saved_workflow_id填已保存工作流的UUID，两者不要混淆。

```

**LLM响应**:
```
{'matched_workflow': None, 'saved_workflow_id': None, 'output_type': None}
```

## 五、工具筛选 [2.25s] (Planner._select_relevant_tools)
**时间**: 2026-02-13 20:39:48
**提示词模板**: TOOL_SELECTION_PROMPT

**上下文变量**:
- user_message: 当前新村站水位超过警戒水位了吗？
- business_sub_intent: other
- entities: {"object": "新村站", "object_type": "河道水文站", "action": "查询是否超过警戒水位", "time": "当前", "stcd": "31005700"}
- tools_summary: 
## 流域基本信息 (basin_info)
  - login_basin_system: 登录卫共流域数字孪生系统，获取访问令牌(Token)。通常在需要鉴权的接口调用前执行。
  - get_map_data: 查询各类地理要素的地图数据（包含空间坐标），支持测站、水库、蓄滞洪区、分洪闸堰等类型
  - get_list_data: 查询各类要素的列表数据（不含空间坐标），如水库防洪责任人扩展信息
  - get_reservoir_info: 查询水库的基础属性信息，包括位置、工程等级、流域面积、库容、校核洪水位等
  - get_reservoir_flood_detail: 查询单个水库的防洪特征值详情，包括校核洪水位、设计洪水位、正常蓄水位、死水位、库容等
  - get_reservoir_flood_list: 获取所有水库的防洪特征值信息列表，包含各水库的校核洪水位、设计洪水位、正常蓄水位、库容等
  - get_sluice_info: 查询水闸的基础属性信息，包括位置、河流名称、工程规模、设计流量等
  - get_flood_dam_info: 查询分洪闸堰的基础信息，包括位置、设计分洪流量等
  - get_flood_storage_area: 查询蓄滞洪区的基础信息，包括面积、进洪设施、设计蓄洪库容、设计蓄洪水位等
  - get_river_flood_list: 获取所有河道测站的防洪特征值信息列表，包括警戒水位、保证水位、左右堤高程、实测最高水位等
  - get_station_list: 按测站类型查询测站的基础信息列表，包括测站编码、名称、位置、河流名称等
  - get_camera_list: 获取视频监控摄像头列表，包括摄像头编码、名称、关联测站、视频流地址等
  - get_drone_project_list: 查询无人机项目列表，获取项目ID和项目名称
  - get_drone_device_list: 查询无人机设备列表，获取设备序列号、名称、类型、状态等信息
  - get_remote_sensing_task_list: 查询遥感监测任务列表，支持洪涝水淹、洪涝监测、水利工程变形、小流域监测等任务类型
  - lookup_station_code: 根据站点名称查询站点编码(stcd)，支持精确匹配和模糊匹配，可用于水雨情实时数据查询前获取站点编码

## 水雨情监测数据 (hydro_monitor)
  - query_rain_process: 根据测站编码和时间范围查询雨量历史过程数据，返回时段降水量、日降水量、累计降水量等信息
  - query_rain_statistics: 根据测站编码查询雨量统计数据，返回1小时、3小时、6小时、12小时、24小时等多时段的雨量统计信息
  - query_rain_sum: 根据时间范围查询所有测站的雨量累计数据，返回测站编码、名称、累计降水量、测站位置等信息
  - query_reservoir_last: 获取水库的最新实时水情数据，可以指定水库测站编码，包括库水位、蓄水量、入库流量、出库流量等信息
  - query_reservoir_process: 根据测站编码和时间范围查询水库的历史水情过程数据，返回库水位、蓄水量、入库流量、出库流量等时序数据
  - query_river_last: 获取河道测站的当前、最新、实时水情数据，可以指定河道测站编码，包括水位、流量、水势、告警级别等信息
  - query_river_process: 根据测站编码和时间范围查询河道水情历史过程数据，返回水位、流量、水势等时序数据，当前河道水情查询请用query_river_last工具
  - query_ai_water_last: 获取AI智能监测设备的最新水情数据，返回测站编码、名称、水位、数据时间等信息
  - query_ai_water_process: 根据测站编码和时间范围查询AI智能监测设备的水情历史过程数据
  - query_ai_rain_last: 获取AI智能监测设备的最新雨量数据，返回测站编码、名称、时段降水量、数据时间等信息
  - query_ai_rain_process: 根据测站编码和时间范围查询AI智能监测设备的雨量历史过程数据
  - query_camera_preview: 根据摄像头编码(code)获取实时视频预览流地址。注意：code是摄像头编码(如41062240201327003002)，不是站点编码(stcd)！需要先调用get_camera_list获取摄像头列表，从返回的code字段获取摄像头编码
  - query_sensor_data_p...(已截断)

**完整提示词**:
```
你是河南省卫共流域数字孪生系统的工具选择助手，负责根据用户需求筛选需要的工具。

## 用户消息
当前新村站水位超过警戒水位了吗？

## 业务子意图
other

## 提取的实体
{"object": "新村站", "object_type": "河道水文站", "action": "查询是否超过警戒水位", "time": "当前", "stcd": "31005700"}

## 可用工具摘要

## 流域基本信息 (basin_info)
  - login_basin_system: 登录卫共流域数字孪生系统，获取访问令牌(Token)。通常在需要鉴权的接口调用前执行。
  - get_map_data: 查询各类地理要素的地图数据（包含空间坐标），支持测站、水库、蓄滞洪区、分洪闸堰等类型
  - get_list_data: 查询各类要素的列表数据（不含空间坐标），如水库防洪责任人扩展信息
  - get_reservoir_info: 查询水库的基础属性信息，包括位置、工程等级、流域面积、库容、校核洪水位等
  - get_reservoir_flood_detail: 查询单个水库的防洪特征值详情，包括校核洪水位、设计洪水位、正常蓄水位、死水位、库容等
  - get_reservoir_flood_list: 获取所有水库的防洪特征值信息列表，包含各水库的校核洪水位、设计洪水位、正常蓄水位、库容等
  - get_sluice_info: 查询水闸的基础属性信息，包括位置、河流名称、工程规模、设计流量等
  - get_flood_dam_info: 查询分洪闸堰的基础信息，包括位置、设计分洪流量等
  - get_flood_storage_area: 查询蓄滞洪区的基础信息，包括面积、进洪设施、设计蓄洪库容、设计蓄洪水位等
  - get_river_flood_list: 获取所有河道测站的防洪特征值信息列表，包括警戒水位、保证水位、左右堤高程、实测最高水位等
  - get_station_list: 按测站类型查询测站的基础信息列表，包括测站编码、名称、位置、河流名称等
  - get_camera_list: 获取视频监控摄像头列表，包括摄像头编码、名称、关联测站、视频流地址等
  - get_drone_project_list: 查询无人机项目列表，获取项目ID和项目名称
  - get_drone_device_list: 查询无人机设备列表，获取设备序列号、名称、类型、状态等信息
  - get_remote_sensing_task_list: 查询遥感监测任务列表，支持洪涝水淹、洪涝监测、水利工程变形、小流域监测等任务类型
  - lookup_station_code: 根据站点名称查询站点编码(stcd)，支持精确匹配和模糊匹配，可用于水雨情实时数据查询前获取站点编码

## 水雨情监测数据 (hydro_monitor)
  - query_rain_process: 根据测站编码和时间范围查询雨量历史过程数据，返回时段降水量、日降水量、累计降水量等信息
  - query_rain_statistics: 根据测站编码查询雨量统计数据，返回1小时、3小时、6小时、12小时、24小时等多时段的雨量统计信息
  - query_rain_sum: 根据时间范围查询所有测站的雨量累计数据，返回测站编码、名称、累计降水量、测站位置等信息
  - query_reservoir_last: 获取水库的最新实时水情数据，可以指定水库测站编码，包括库水位、蓄水量、入库流量、出库流量等信息
  - query_reservoir_process: 根据测站编码和时间范围查询水库的历史水情过程数据，返回库水位、蓄水量、入库流量、出库流量等时序数据
  - query_river_last: 获取河道测站的当前、最新、实时水情数据，可以指定河道测站编码，包括水位、流量、水势、告警级别等信息
  - query_river_process: 根据测站编码和时间范围查询河道水情历史过程数据，返回水位、流量、水势等时序数据，当前河道水情查询请用query_river_last工具
  - query_ai_water_last: 获取AI智能监测设备的最新水情数据，返回测站编码、名称、水位、数据时间等信息
  - query_ai_water_process: 根据测站编码和时间范围查询AI智能监测设备的水情历史过程数据
  - query_ai_rain_last: 获取AI智能监测设备的最新雨量数据，返回测站编码、名称、时段降水量、数据时间等信息
  - query_ai_rain_process: 根据测站编码和时间范围查询AI智能监测设备的雨量历史过程数据
  - query_camera_preview: 根据摄像头编码(code)获取实时视频预览流地址。注意：code是摄像头编码(如41062240201327003002)，不是站点编码(stcd)！需要先调用get_camera_list获取摄像头列表，从返回的code字段获取摄像头编码
  - query_sensor_data_process: 根据传感器ID和时间范围查询传感器的历史监测数据
  - query_drone_status: 查询大疆无人机设备的实时状态，包括设备序列号、状态、电量、位置等信息
  - send_sms: 发送告警短信通知，需要提供接收手机号码和短信内容

## 防洪业务 (flood_control)
  - model_plan_add: 新增洪水预报模拟方案，设置方案名称、时间范围、业务模型等参数
  - model_plan_edit: 编辑已存在的洪水预报模拟方案
  - model_plan_delete: 删除指定的洪水预报模拟方案
  - model_plan_detail: 根据方案编码查看模拟方案的详细信息
  - model_plan_state: 查看模拟方案的当前计算状态
  - model_plan_list_all: 查询全部洪水预报模拟方案列表(不分页)，支持按方案名称、编码、状态等条件筛选
  - model_plan_calc: 启动指定方案的洪水预报模型计算
  - model_plan_stop: 终止正在进行的模拟方案计算
  - model_plan_progress: 获取模拟方案的计算进度信息
  - model_plan_count_state: 获取不同计算状态的方案数量统计
  - model_plan_count_plan: 获取各业务模型的模拟方案数量统计
  - model_plan_auto_forecast: 手动触发一次自动洪水预报计算（无需登录）
  - model_basic_list_all: 查询全部基础模型列表(不分页)，支持按模型名称、编码、类型等条件筛选
  - model_basic_detail: 根据模型ID查看基础模型的详细信息，包括模型介绍、原理、参数等
  - model_basic_count: 获取基础模型、模型实例、业务模型、模拟方案的数量统计
  - model_instance_list_all: 查询全部模型实例列表(不分页)，支持按实例名称、编码、基础模型、流域等条件筛选
  - model_instance_detail: 根据实例ID查看模型实例的详细信息
  - model_business_list_all: 查询全部业务模型列表(不分页)，支持按业务模型名称、编码、类型等条件筛选
  - model_business_add: 新增业务模型，设置业务模型名称、编码、类型等参数
  - model_business_detail: 根据业务模型编码查看业务模型的详细信息
  - forecast_rain_ecmwf_avg: 获取流域平均的格网预报降雨过程(无需登录)，返回时序降雨数据
  - forecast_rain_ecmwf_each: 获取各子流域的格网预报降雨过程，返回按子流域编码分组的降雨时序数据
  - forecast_rain_ecmwf_rect: 获取矩形区域内的格网预报降雨过程，通过经纬度范围指定区域
  - forecast_rain_ecmwf_stc: 获取指定时段的ECMWF降雨分区统计信息，包括各子流域累计、平均、最大降雨量
  - forecast_rain_ecmwf_acc: 获取所有格网点指定时段的ECMWF累计降雨，返回经纬度和累计降雨值
  - contour_rain_today: 获取8点以后降雨等值面，返回GeoJSON格式的等值面数据
  - contour_rain_any: 生成/获取任意时段累计降雨等值面
  - contour_rain_plan: 生成/获取方案累计降雨等值面
  - contour_rain_proc: 获取逐小时降雨等值面过程
  - contour_rain_acc: 获取不同时段累计降雨等值面，interval负数表示历史，正数表示未来
  - contour_rain_future_img: 获取未来24/48/72小时降雨等值面图片(Base64格式)
  - contour_rain_update: 更新等值面(无需登录)
  - monitor_rain_area_proc_whole: 获取指定时段的流域整体面雨量过程
  - monitor_rain_manual: 手动更新降水监测数据(无需登录)
  - model_rain_pattern_list: 查询设计雨型列表
  - model_rain_pattern_add: 新增设计雨型
  - model_rain_pattern_detail: 查看设计雨型详情
  - model_typical_rain_list: 分页查询典型暴雨列表
  - model_typical_rain_add: 新增典型暴雨
  - model_typical_rain_detail: 查看典型暴雨详情
  - model_typical_rain_add_from_history: 从历史数据新增典型暴雨
  - model_rain_area_get_by_plan: 获取指定方案的各子流域降雨过程(无需登录)，返回按子流域编码分组的降雨时序数据
  - model_rain_area_get_basin_area_rain_stc: 获取指定方案的全流域平均面雨量过程及统计值(无需登录)，包括累计、最大降雨量和平均值
  - model_rain_area_get_basin_area_rain_acc: 获取指定方案的全流域平均面雨量过程及实时累计降雨
  - model_rain_area_get_basin_list: 获取指定方案有降雨预报的流域清单
  - model_rain_area_detail: 获取指定方案、指定流域的降雨过程及统计，包括累计、最大降雨量和时间
  - model_rain_area_get_by_rsvr: 获取指定方案、指定水文站的上游流域降雨过程
  - model_rain_area_forecast_rain_stc: 获取自动预报方案的降雨态势，包括平均、最大降雨量和降雨等级
  - model_rain_area_add_ecmwf: 根据格网预报(ECMWF)设置方案降雨过程
  - model_rain_area_add_ecmwf_translate: 根据格网预报设置方案降雨过程(可放大平移)，支持设置放大倍数和经纬度偏移量
  - model_rain_area_add_manual: 手动设置方案降雨过程，通过JSON格式指定降水量时序数据
  - model_rain_area_add_manual_center: 手动设置方案降雨过程(可设降雨中心)，支持设置多个降雨中心区域
  - model_rain_area_add_bnd: 从数据库导入方案降雨过程
  - model_result_outflow_delete: 删除产流结果，根据方案编码和可选的流域编码删除子流域洪水计算结果
  - model_result_outflow_get_basin_list: 获取指定方案的子流域基础信息清单，返回子流域编码和名称列表
  - model_result_outflow_detail: 获取指定方案、指定子流域的降雨及洪水过程结果及统计结果，包括降雨过程、洪水过程、峰值时间、累计降雨、洪峰流量等
  - model_result_outflow_source: 获取洪水来源类型：0=降雨计算、1=直接导入、2=无洪水
  - loss_plan_list: 分页查询淹没分析方案列表，支持按编码、名称、状态、蓄滞洪区编码、类型等条件过滤
  - loss_plan_add: 新增淹没分析方案，用于创建新的洪水淹没分析计算方案
  - loss_plan_delete: 删除指定的淹没分析方案
  - loss_plan_calc: 执行淹没分析方案计算，返回预计计算所需时间（秒）
  - loss_plan_detail: 获取淹没分析方案详情及计算结果数据
  - loss_plan_gis: 获取淹没分布GIS数据，返回GeoJSON格式的淹没范围和深度信息
  - loss_plan_auto: 自动计算淹没分析（无需登录）
  - flood_plan_list_all: 查询全部防汛预案列表（不分页），支持按预案名称、文号、年度、分类等条件过滤
  - flood_plan_add: 新增防汛预案（支持文件上传），用于创建新的防汛预案记录
  - flood_plan_delete: 删除指定的防汛预案
  - flood_plan_detail: 查看防汛预案详情，包括预案名称、文号、年度、分类、文件信息等
  - flood_plan_catalog: 获取防汛预案类型目录，返回一级分类及其下属二级分类的树形结构
  - monitor_rsvr_now: 获取水库河道实时水情（无需登录）。注意：此工具只返回测站编码(stcd)、名称(stnm)、数据时间(tm)、水位(z)、流量(q)，不包含库容、蓄水量、入库/出库流量等数据。如需水库的库容、蓄水量等详细信息，请使用 query_reservoir_last 工具或 monitor_rsvr_storage 工具
  - monitor_rsvr_stc: 获取水库当前形势统计，返回总数、正常数、预警数、危险数等统计信息
  - monitor_rsvr_track: 水雨情态势过程回溯，获取指定时段内水库水情变化过程
  - monitor_rsvr_storage: 水库纳蓄能力分析，返回总库容、当前蓄量、可用库容、蓄水率等信息
  - mike_gate_all: 获取闸门工情（无需登录），返回闸门状态（全开/半开/全关）、开度、开启孔数等信息
  - mike_runoff: 获取子流域NAM模型产流结果（无需登录），返回各子流域的产流时间序列
  - mike_rsvr_info: 获取水库基本信息（无需登录），包括水库编码、名称、汛限水位、正常水位、死水位、总库容等
  - mike_control: 获取水库的可控建筑物，返回泄洪洞、溢洪道等可控设施信息及最大过流能力
  - mike_hvrela: 获取蓄滞洪区的库容曲线，返回水位-库容关系数据
  - mike_spec_time: 获取指定时刻的水情，返回各水库测站的水位、入库流量、出库流量等数据
  - mike_cal_pa: 计算指定时间各子流域的前期影响雨量(Pa值)，用于洪水预报模型参数计算
  - mike_fsda_struct: 获取指定业务模型对应蓄滞洪区的建筑物信息，如分洪堰等
  - mike_fsda_set_boundary: 设置蓄滞洪区进洪预演模型的边界条件，用于配置模型计算参数

## 灾损评估 (damage_assess)
  - flood_damage_loss_calc: 根据模型编码和业务类型计算洪涝灾害造成的损失，包括受灾面积、受灾人口、受灾GDP、受灾企业数等，并返回受灾村庄和区县的GeoJSON数据
  - hedge_placement_list: 根据预案编码查询避险安置点列表，包括安置点名称、位置、联系人、容纳人数等信息
  - hedge_transfer_route_list: 根据预案编码查询转移路线列表，包括转移村庄、目标安置点、转移时间、联系人等信息

## 水利专业模型 (hydro_model)
  - auto_forcast: 创建洪水自动预报模型方案并进行计算
  - create_model: 手工创建模型方案，仅创建方案不设置边界条件，也不计算
  - change_model_baseinfo: 修改模型方案名称、描述和保存时间步长
  - del_model: 删除模型方案，返回剩下的模型方案基础信息集合
  - run_model: 计算模型，返回所需的计算时间(秒)
  - run_model_quick: 一维快速计算模型(不进行GIS结果后处理)，返回所需的计算时间(秒)
  - stop_model: 停止模型计算，返回成功信息
  - modify_initial: 修改方案的水库河道初始水位条件
  - change_rfmodel: 修改方案的各个子流域产汇流模型类型
  - change_boundry: 修改方案的洪水入流边界条件，可指定为利用降雨计算洪水、直接指定子流域洪水过程、指定河道洪水过程或无洪水入流
  - modify_gatestate: 修改方案闸站调度设置
  - change_reach_break: 修改方案河堤溃口设置
  - set_dispatch_target: 设置方案的优化调度目标参数
  - iter_cal: 开始方案的优化迭代计算
  - backcal_resdd: 反向推演水库的调度方案和该调度方案下的调蓄结果。需要设置水库允许达到的最高水位，并且只针对已经完成的预报预演方案
  - set_fault_gate: 设置方案的故障闸门
  - get_sampleline: 获取GIS样板线，为geojson格式的河道分段线要素，用于在地图区分色动态渲染过程结果，如流量、流速等
  - get_reachinfo: 获取河道基本信息，包括河道名称、编码、起止桩号及长度等信息
  - get_gatestate: 获取全流域里各闸站建筑最新状态监测信息，包括闸门状态、开孔数、开度、更新时间
  - get_sectiondata: 根据断面STCD和桩号，获取河道断面原始测量数据。当断面为水文站点或闸站时，第1个参数为该站点STCD，第2个为空字符串；否则第1个参数为河道编码，第2个为桩号
  - get_sectiondata_frompoint: 根据坐标点，获取河道断面原始测量数据
  - get_reachsection_location: 根据河道断面桩号，获取该河道断面中心点的经纬度坐标位置信息
  - get_station_info: 获取河道上各大中型水库、河道水文站点、河道控制闸站的基本信息和监测水情信息，包括站点stcd、所在河道和桩号、控制流域面积、水位流量等监测水情信息等
  - get_strddrule_info: 获取水库、河道闸站等所有洪水控制建筑的规则调度信息
  - get_control_strs: 根据业务编码和站点STCD获取关联的洪水控制建筑物，如水库的各个溢流堰和泄洪洞，蓄滞洪区的各个进洪分洪闸堰
  - get_now_waterinfo: 获取所有水库、河道闸站、水文站点当前最新水情信息。如果业务编码字符串为空字符串，则获取所有水库闸站和水文站点的当前水情，否则是业务模型相关的
  - get_design_flood: 获取和业务模型相关的各河道不同量级设计洪水过程，如50年一遇设计洪水过程
  - get_nsbd_sectioninfo: 获取流域范围内，各河道与南水北调交叉断面的基本信息，包括交叉断面位置、设计水位、设计流量、校核流量、堤顶高程等
  - get_business_view: 获取业务模型的默认初始三维场景相机姿态信息，包括相机位置坐标、朝向和俯仰角
  - get_rfmodel: 获取方案的产汇流模型类型，返回各子流域采用的产汇流模型编码（共3种：nam、swmm5、xaj）
  - get_reach_break: 获取方案河堤溃口设置信息，包括溃口编码、名称、位置、溃口宽度、溃堤时长、溃决水位、溃口底高程、开始溃口时间等
  - get_faultgate_baseinfo: 获取故障水闸的闸门基本信息，根据业务编码获取，一个业务编码对应一个故障水闸。返回建筑物编码、名称及各闸门的编码、名称、闸底高程、闸门高度、经纬度坐标等信息
  - get_fault_gate: 获取方案的故障闸门信息，包括故障水闸名称、故障描述、各闸门最大开度和当前开度、故障闸门名称及经纬度
  - get_ddinfo: 获取模型方案所有可控建筑物的调度信息，包括建筑物编码、序号、名称、类型、所在河道及闸门调度过程
  - get_initial_waterlevel: 获取模型方案的初始水情信息，包括各水库和河道站点的序号、名称、初始水位、水位来源、stcd编码等
  - get_bndinfo: 获取模型方案的边界条件信息，包括边界条件类型描述（如'降雨计算洪水'）和边界条件值（各子流域的流量过程）
  - get_dispatch_target: 获取方案的优化调度目标设置信息，包括方案ID、调度目标（站点名称、stcd、最大流量）、各水库约束水位及其他约束条件
  - get_models: 获取已有所有模型方案信息，包括方案名称、描述、业务模型编码、起止时间、状态、进度等12个属性
  - get_dispatch_plan: 获取方案主要控制闸站的简短调度指令，包含水库、河道闸站、蓄滞洪区3种类型的各控制闸站的调度信息
  - get_tjdata_result: 获取方案的结果数据，包含水库、河道断面、蓄滞洪区的洪水计算结果以及结果概述、河道风险，此外还可能包含调度方案结果
  - get_gisgc_polygon_result: 获取方案某时刻河道水面GIS面要素结果，为geojson格式的带Z值的三维水面要素，用于在三维场景中绘制三维水面
  - get_sampleline_data_result: 获取方案的GIS过程线的全过程属性结果，用于在地图区分色动态渲染过程结果，如流量、流速等
  - get_gistj_result: 获取方案的GIS统计线结果，为geojson格式的河道分段线要素，用于在地图区分色渲染全过程最大流量、流速等分布结果
  - get_gistj_polygon_result: 获取方案的GIS统计面结果(淹没面)，为geojson格式的二维面要素，用于在地图中分水渲染淹没区水深分布
  - get_point_result: 查询方案河道上某点的水位流量等结果，用于在地图中点击查询某位置结果信息。如果时间为空字符串，则返回时间序列
  - get_zp_result: 获取方案某类结果的顺河道纵剖面数据，用于前端页面纵剖图绘制
  - get_reachsections: 获取方案有水位结果的河道断面桩号清单，包括各河道基本信息和各河道有水位结果的断面桩号
  - get_sectionres: 获取方案单一河道断面的水位流量过程
  - get_sectionlist_res: 获取方案多个河道断面的水位流量过程
  - get_catchment_discharges: 获取方案多个子流域的产汇流模型流量过程
  - get_gateres: 获取方案某闸门的水力要素结果，包括过闸流量、上下游水位过程、流速过程、水头差等
  - get_atreach: 根据方案ID获取该方案的特殊河道断面信息，包括河道ID和桩号
  - get_risk_warning: 获取方案的风险预警信息，包含水库风险预警、河道风险预警、蓄滞洪区进洪风险预警、降雨预警、南水北调交叉断面风险预警、山洪风险预警
  - get_history_autoforcast_list: 获取历史洪水自动预报方案信息清单，包含方案ID、预报起止时间和本场次降雨总降雨量
  - del_history_autoforcast: 删除某场历史自动预报方案
  - get_rain_flood_list: 获取预演场次洪水信息列表，所有预演方案均关联有一场场次洪水，一场场次洪水可能对应多个预演方案，但只有一个推荐方案
  - get_rainflood_plan_list: 获取某场次洪水的预演方案清单，包含方案名称、描述、业务模型、起止时间、状态等信息
  - change_rainflood_recomplan: 修改某场次洪水的推荐预演方案
  - important_inspect: 获取预演方案的工程重点巡查区域信息，即通过方案预演后得到的工程风险区域作为重点巡查区域，包含水库、河道、蓄滞洪区的巡查信息
  - get_history_autoforcast_res: 获取历史洪水自动预报结果，结果与get_tjdata_result接口返回结果相同
  - get_mountain_forecast_flood: 获取山区预报信息，包括山洪区域名称、村庄名称、经纬度、被淹时间、风险等级等

## 函数工具 (function)
  - search_knowledge: 函数工具
  - generate_report_page: 函数工具

## 任务
从上述工具中选择完成任务所需的工具。

## 输出要求
返回JSON格式：
{
    "selected_tools": ["工具名称1", "工具名称2", ...],
    "reason": "选择理由（简短说明为什么选择这些工具）"
}

## 选择原则
1. **【强制规则】basin_info**：提取的实体包含水库、水闸、蓄滞洪区、测站、河道等流域对象时，必须从 basin_info 选择对应工具
   - 河道水文站 → get_river_flood_list(警戒水位等特征值)
   - 水库 → get_reservoir_flood_detail(防洪特征值)
   - 水闸 → get_sluice_info
   - 蓄滞洪区 → get_flood_storage_area, get_flood_dam_info

2. **【强制规则】hydro_monitor**：问题意图为获取监测数据，或包含当前/实时/最新等时间关键词时，必须从 hydro_monitor 选择
   - 河道水情 → query_river_last
   - 水库水情 → query_reservoir_last
   - 雨量 → query_rain_statistics, query_rain_sum
   - AI监测 → query_ai_water_last, query_ai_rain_last

3. **【强制规则】组合使用**：两条强制规则彼此独立，需同时判断。问题需要与警戒水位、保证水位、设计水位、汛限水位等特征水位进行数值对比时，必须同时选择 basin_info 的特征值工具和 hydro_monitor 的实时数据工具

4. 其他：需要站点编码时包含 lookup_station_code，需要知识库检索时包含 search_knowledge

```

**LLM响应**:
```
{'selected_tools': ['query_river_last', 'get_river_flood_list'], 'reason': '问题需要判断新村站当前水位是否超过警戒水位，需获取实时水位数据(query_river_last)和警戒水位特征值(get_river_flood_list)，符合组合使用规则'}
```

## 六、计划生成 [8.49s] (Planner.generate_plan)
**时间**: 2026-02-13 20:39:56
**提示词模板**: PLAN_GENERATION_PROMPT

**上下文变量**:
- available_tools: 1. 工具名称: lookup_station_code
描述: 根据站点名称查询站点编码(stcd)，支持精确匹配和模糊匹配，可用于水雨情实时数据查询前获取站点编码
类别: basin_info
参数:
  - station_name [string] (必需): 站点名称，支持模糊匹配（如输入'淇门'可匹配'淇门'、'淇门东街断面'等）
  - station_type [string] (可选): 站点类型过滤（可选）：河道水文站、水库水文站、工程安全监测、墒情站、闸站监测、AI监测站点、雨量站
  - exact_match [boolean] (可选): 是否精确匹配，默认False（模糊匹配）

2. 工具名称: query_river_last
描述: 获取河道测站的当前、最新、实时水情数据，可以指定河道测站编码，包括水位、流量、水势、告警级别等信息
类别: hydro_monitor
参数:
  - stcd [string] (可选): 测站编码（可选，不传则查询所有河道）
返回字段:
  - stcd: 测站编码
  - stnm: 测站名称
  - lgtd: 经度
  - lttd: 纬度
  - z: 水位(m)
  - q: 流量(m³/s)
  - tm: 数据时间
  - sttp: 测站类型
  - rvnm: 河流名称
  - hnnm: 水系名称
  - bsnm: 流域名称
  - stlc: 测站位置
  - wptn: 水势
  - warn: 告警级别

3. 工具名称: get_river_flood_list
描述: 获取所有河道测站的防洪特征值信息列表，包括警戒水位、保证水位、左右堤高程、实测最高水位等
类别: basin_info
参数:
  无参数
返回字段:
  - stcd: 测站编码
  - grz: 保证水位(m)
  - wrz: 警戒水位(m)
  - ldkel: 左堤高程(m)
  - rdkel: 右堤高程(m)
  - wrq: 警戒流量(m³/s)
  - grq: 保证流量(m³/s)
  - obhtz: 实测最高水位(m)
  - obhtztm: 实测最高水位时间
  - obmxq: 实测最大流量(m³/s)
  - obmxqtm: 实测最大流量时间

- rag_context: 无相关业务流程参考
- intent: business
- entities: {'object': '新村站', 'object_type': '河道水文站', 'action': '查询是否超过警戒水位', 'time': '当前', 'stcd': '31005700'}
- target_kbs: ['monitor_site']
- user_message: 当前新村站水位超过警戒水位了吗？

**完整提示词**:
```
你是河南省卫共流域数字孪生系统的任务规划器，负责制定执行计划。

## 可用工具
1. 工具名称: lookup_station_code
描述: 根据站点名称查询站点编码(stcd)，支持精确匹配和模糊匹配，可用于水雨情实时数据查询前获取站点编码
类别: basin_info
参数:
  - station_name [string] (必需): 站点名称，支持模糊匹配（如输入'淇门'可匹配'淇门'、'淇门东街断面'等）
  - station_type [string] (可选): 站点类型过滤（可选）：河道水文站、水库水文站、工程安全监测、墒情站、闸站监测、AI监测站点、雨量站
  - exact_match [boolean] (可选): 是否精确匹配，默认False（模糊匹配）

2. 工具名称: query_river_last
描述: 获取河道测站的当前、最新、实时水情数据，可以指定河道测站编码，包括水位、流量、水势、告警级别等信息
类别: hydro_monitor
参数:
  - stcd [string] (可选): 测站编码（可选，不传则查询所有河道）
返回字段:
  - stcd: 测站编码
  - stnm: 测站名称
  - lgtd: 经度
  - lttd: 纬度
  - z: 水位(m)
  - q: 流量(m³/s)
  - tm: 数据时间
  - sttp: 测站类型
  - rvnm: 河流名称
  - hnnm: 水系名称
  - bsnm: 流域名称
  - stlc: 测站位置
  - wptn: 水势
  - warn: 告警级别

3. 工具名称: get_river_flood_list
描述: 获取所有河道测站的防洪特征值信息列表，包括警戒水位、保证水位、左右堤高程、实测最高水位等
类别: basin_info
参数:
  无参数
返回字段:
  - stcd: 测站编码
  - grz: 保证水位(m)
  - wrz: 警戒水位(m)
  - ldkel: 左堤高程(m)
  - rdkel: 右堤高程(m)
  - wrq: 警戒流量(m³/s)
  - grq: 保证流量(m³/s)
  - obhtz: 实测最高水位(m)
  - obhtztm: 实测最高水位时间
  - obmxq: 实测最大流量(m³/s)
  - obmxqtm: 实测最大流量时间


## 业务流程参考
无相关业务流程参考

## 用户意图
意图: business
实体: {'object': '新村站', 'object_type': '河道水文站', 'action': '查询是否超过警戒水位', 'time': '当前', 'stcd': '31005700'}
目标知识库: ['monitor_site']

## 用户消息
当前新村站水位超过警戒水位了吗？

## 输出JSON格式
{
    "steps": [
        {
            "step_id": 1,
            "description": "步骤描述",
            "tool_name": "工具名称或null",
            "tool_args": {"参数": "值"},
            "dependencies": [依赖步骤id],
            "is_async": false,
            "result_display": "skip/summary/full",
            "result_fields": ["字段1", "字段2"]
        }
    ],
    "estimated_time_seconds": 30,
    "output_type": "text或web_page"
}


**重要：tool_args中的布尔类型参数必须使用JSON布尔值true/false，不要使用字符串"true"/"false"**

**dependencies字段格式（重要）：**
- dependencies是整数数组，表示当前步骤依赖哪些步骤的执行结果
- 正确示例：[1] 或 [1, 2]（纯数字）
- 错误示例：["step_1"] 或 ["1"]（不要使用字符串）

**步骤间参数传递（重要）：**
- 当后续步骤需要使用前面步骤的结果时，在tool_args中使用占位符格式：$$step_N.字段名$$
- 例如：步骤1返回 {"data": {"stcd": "31005650"}}，步骤2要使用stcd，应写：$$step_1.stcd$$
- **数组返回值处理**：如果步骤返回的是数组（如列表查询），需要使用索引访问：$$step_N[0].字段名$$
  - 例如：步骤1返回 {"data": [{"code": "xxx", "name": "yyy"}]}，步骤2要使用code，应写：$$step_1[0].code$$
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
- search_knowledge工具参数：{"query": "检索关键词", "target_kbs": ["知识库id列表"]}
- 目标知识库应根据问题内容选择，参考上面的"目标知识库"字段
- 知识库检索步骤应安排在需要该信息的步骤之前
- 例如：查询历史洪水水位需要先search_knowledge检索history_flood，再进行数据处理

```

**LLM响应**:
```
{'steps': [{'step_id': 1, 'description': '查询新村站当前实时水情数据', 'tool_name': 'query_river_last', 'tool_args': {'stcd': '31005700'}, 'dependencies': [], 'is_async': False, 'result_display': 'skip', 'result_fields': ['stcd', 'stnm', 'z', 'q', 'tm', 'wptn', 'warn']}, {'step_id': 2, 'description': '获取新村站防洪特征值（警戒水位、保证水位等）', 'tool_name': 'get_river_flood_list', 'tool_args': {}, 'dependencies': [], 'is_async': False, 'result_display': 'skip', 'result_fields': ['stcd', 'stnm', 'wrz', 'grz', 'wrq', 'grq']}, {'step_id': 3, 'description': '对比当前水位与警戒水位，判断是否超警', 'tool_name': None, 'tool_args': {}, 'dependencies': [1, 2], 'is_async': False, 'result_display': 'full', 'result_fields': []}], 'estimated_time_seconds': 10, 'output_type': 'text'}
```

## 七、任务执行(LLM) [3.00s] (Executor._execute_with_llm)
**时间**: 2026-02-13 20:40:00
**提示词模板**: EXECUTOR_LLM_PROMPT

**上下文变量**:
- task_description: 对比当前水位与警戒水位，判断是否超警
- user_message: 当前新村站水位超过警戒水位了吗？
- execution_results: 

步骤1 (成功): {'success': True, 'data': [{'stnm': '新村', 'warn': None, 'q': 1.42, 'stcd': '31005700', 'z': 97.67, 'tm': '2026-02-13 08:00:00', 'wptn': '4'}], 'error': None, 'execution_time_ms': 826, 'metadata': {'query_type': 'river_last', 'record_count': 1}}

步骤2 (成功): {'success': True, 'data': [{'stcd': '31003600', 'grz': '71.200', 'wrz': '69.200', 'wrq': None, 'grq': '160.000'}, {'stcd': '31003700', 'grz': '66.100', 'wrz': '64.100', 'wrq': None, 'grq': '400.000'}, {'stcd': '31003800', 'grz': '62.590', 'wrz': '60.590', 'wrq': None, 'grq': '350.000'}, {'stcd': '31003910', 'grz': '57.890', 'wrz': '56.000', 'wrq': None, 'grq': '2000.000'}, {'stcd': '31004000', 'grz': '55.500', 'wrz': '53.500', 'wrq': None, 'grq': '2000.000'}, {'stcd': '31004300', 'grz': '49.680', 'wrz': '47.680', 'wrq': None, 'grq': '2500.000'}, {'stcd': '31004900', 'grz': '83.500', 'wrz': '82.000', 'wrq': None, 'grq': '230.000'}, {'stcd': '31005700', 'grz': None, 'wrz': None, 'wrq': None, 'grq': '800.000'}, {'stcd': '31006200', 'grz': '75.800', 'wrz': '74.000', 'wrq': None, 'grq': '1000.000'}, {'stcd': '31006302', 'grz': '71.500', 'wrz': '70.000', 'wrq': None, 'grq': '900.000'}, {'stcd': '31006410', 'grz': '66.200', 'wrz': '64.440', 'wrq': None, 'grq': '400.000'}, {'stcd': '31006600', 'grz': None, 'wrz': None, 'wrq': None, 'grq': None}, {'stcd': '31006900', 'grz': '75.180', 'wrz': '73.180', 'wrq': None, 'grq': '1180.000'}], 'error': None, 'execution_time_ms': 29, 'metadata': {'code': '00000', 'message': '请求成功'}}
- retrieved_documents: 无

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手。

## 任务
对比当前水位与警戒水位，判断是否超警

## 用户原始消息
当前新村站水位超过警戒水位了吗？

## 已有执行结果
步骤1 (成功): {'success': True, 'data': [{'stnm': '新村', 'warn': None, 'q': 1.42, 'stcd': '31005700', 'z': 97.67, 'tm': '2026-02-13 08:00:00', 'wptn': '4'}], 'error': None, 'execution_time_ms': 826, 'metadata': {'query_type': 'river_last', 'record_count': 1}}步骤2 (成功): {'success': True, 'data': [{'stcd': '31003600', 'grz': '71.200', 'wrz': '69.200', 'wrq': None, 'grq': '160.000'}, {'stcd': '31003700', 'grz': '66.100', 'wrz': '64.100', 'wrq': None, 'grq': '400.000'}, {'stcd': '31003800', 'grz': '62.590', 'wrz': '60.590', 'wrq': None, 'grq': '350.000'}, {'stcd': '31003910', 'grz': '57.890', 'wrz': '56.000', 'wrq': None, 'grq': '2000.000'}, {'stcd': '31004000', 'grz': '55.500', 'wrz': '53.500', 'wrq': None, 'grq': '2000.000'}, {'stcd': '31004300', 'grz': '49.680', 'wrz': '47.680', 'wrq': None, 'grq': '2500.000'}, {'stcd': '31004900', 'grz': '83.500', 'wrz': '82.000', 'wrq': None, 'grq': '230.000'}, {'stcd': '31005700', 'grz': None, 'wrz': None, 'wrq': None, 'grq': '800.000'}, {'stcd': '31006200', 'grz': '75.800', 'wrz': '74.000', 'wrq': None, 'grq': '1000.000'}, {'stcd': '31006302', 'grz': '71.500', 'wrz': '70.000', 'wrq': None, 'grq': '900.000'}, {'stcd': '31006410', 'grz': '66.200', 'wrz': '64.440', 'wrq': None, 'grq': '400.000'}, {'stcd': '31006600', 'grz': None, 'wrz': None, 'wrq': None, 'grq': None}, {'stcd': '31006900', 'grz': '75.180', 'wrz': '73.180', 'wrq': None, 'grq': '1180.000'}], 'error': None, 'execution_time_ms': 29, 'metadata': {'code': '00000', 'message': '请求成功'}}

## 检索到的知识
无

请根据以上信息完成任务，给出清晰、准确的回答。

```

**LLM响应**:
```
根据提供的信息：

- 新村站的当前水位（z）为 **97.67**。
- 新村站的警戒水位（wrz）为 **None**，即未提供明确的警戒水位值。

由于没有明确的警戒水位值可供对比，无法判断新村站当前水位是否超过警戒水位。建议核实或补充该站点的警戒水位数据以进行进一步分析。
```

## 八、模板LLM精选 [1.61s] (TemplateMatchService._llm_select_template)
**时间**: 2026-02-13 20:40:02
**提示词模板**: TEMPLATE_SELECT_PROMPT

**上下文变量**:
- user_message: 当前新村站水位超过警戒水位了吗？
- sub_intent: other
- object_type: 河道水文站
- entity_params: - stcd: 31005700 (站点代码)
- object_type: 河道水文站 (对象类型)
- workflow_params: 无
- candidates: - ID: 5f0afebd-b480-47c3-b00d-9d26e74b4ba5
  名称: 水位警戒查询
  描述: 展示某河道水文站的实时水位数据及是否超过警戒水位的判断结果，用于防汛预警和应急响应。
  触发模式: 查询 水文站 水位 超过 警戒 是否 判断 当前 实时
  支持子意图: other
  所需参数: stcd(水文站编码),z(当前实时水位值),wptn(警戒水位阈值)
  必须匹配的对象类型: 水文站,河道水文站
  优先级: 5
  向量分数: 0.610

**完整提示词**:
```
你是一个Web模板选择专家。根据用户问题和可提供的参数，从候选模板中选择最合适的模板。

## 用户问题
当前新村站水位超过警戒水位了吗？

## 业务子意图
other

## 当前对象类型
河道水文站

## 对象识别可提供的参数
（来自实体解析阶段：数据库查询+知识库查询+LLM匹配）
- stcd: 31005700 (站点代码)
- object_type: 河道水文站 (对象类型)

## 工作流可提供的参数
（来自工作流执行结果）
无

## 候选模板列表
- ID: 5f0afebd-b480-47c3-b00d-9d26e74b4ba5
  名称: 水位警戒查询
  描述: 展示某河道水文站的实时水位数据及是否超过警戒水位的判断结果，用于防汛预警和应急响应。
  触发模式: 查询 水文站 水位 超过 警戒 是否 判断 当前 实时
  支持子意图: other
  所需参数: stcd(水文站编码),z(当前实时水位值),wptn(警戒水位阈值)
  必须匹配的对象类型: 水文站,河道水文站
  优先级: 5
  向量分数: 0.610

## 选择标准（按优先级排序）

### 必要条件（不满足则必须返回null）
1. **参数完全满足**：上述两类参数（对象识别参数+工作流参数）必须完全覆盖模板的"所需参数"。逐一检查模板所需的每个参数（如token、planCode、stcd、object_name等），确认都能提供。如果有任何一个所需参数无法满足，该模板不可选择。
2. **子意图匹配**：模板必须支持当前的业务子意图。
3. **对象类型匹配**：如果模板指定了"必须匹配的对象类型"（非空列表），则当前对象类型必须在该列表中。如果当前对象类型不在列表中，该模板不可选择。如果模板的"必须匹配的对象类型"为空或未指定，则跳过此校验。

### 优选条件（在满足必要条件后考虑）
4. 模板的触发模式与用户问题相关性高
5. 优先选择优先级高的模板

## 输出格式
请返回JSON格式，包含以下字段：
{
    "selected_template_id": "模板ID或null",
    "confidence": 0.0-1.0的置信度（注意：这是你对选择结果的信心程度，不是向量分数！如果模板完全匹配用户需求，应给0.85-0.95；如果基本匹配但有小瑕疵，给0.7-0.85；如果勉强匹配，给0.5-0.7）,
    "reason": "选择理由（如果返回null，说明哪些条件不满足：参数不满足/子意图不匹配/对象类型不匹配）"
}

请直接返回JSON，不要包含其他内容。

```

**LLM响应**:
```
{
    "selected_template_id": null,
    "confidence": 0.0,
    "reason": "参数不满足：模板所需参数包括 stcd、z（当前实时水位值）、wptn（警戒水位阈值），但 z 和 wptn 参数未提供，无法满足模板的参数需求。"
}
```

