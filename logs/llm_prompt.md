
*****会话ID: de88151a-1f76-4b9d-9623-89a1574d7bbb | 问题: 图文并茂的介绍盐土庄闸？*****

## 一、意图分析 [2.89s] (Planner.analyze_intent)
**时间**: 2026-02-11 12:03:09
**提示词模板**: INTENT_ANALYSIS_PROMPT

**上下文变量**:
- context_summary: 无
- chat_history: 无
- user_message: 图文并茂的介绍盐土庄闸？

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
图文并茂的介绍盐土庄闸？

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
{'intent_category': 'knowledge', 'confidence': 0.95, 'target_kbs': ['water_project'], 'entities': {'关键词': '盐土庄闸'}, 'needs_kb_search': True, 'needs_web_search': False, 'rewritten_query': '图文并茂的介绍盐土庄闸'}
```

## 二、模板LLM精选 [3.27s] (TemplateMatchService._llm_select_template)
**时间**: 2026-02-11 12:03:15
**提示词模板**: TEMPLATE_SELECT_PROMPT

**上下文变量**:
- user_message: 图文并茂的介绍盐土庄闸？
- sub_intent: None
- object_type: 未知
- entity_params: 无
- workflow_params: 无
- candidates: - ID: 6cde78a6-2662-4f0e-a09f-874cba21dea7
  名称: 单一河道断面洪水预报、预演结果展示
  描述: 用于展示单一河道断面的洪水预报结果。包含地图定位、水位流量过程曲线（双轴）、河道断面地形及实时水位图。单一河道断面包括任一断面、河道水文站点断面、闸站断面等
  触发模式: 单一河道断面 洪水预报 断面水位流量  河道断面 水文站点 河道预报 断面预报 洪峰流量 断面水情 最高水文 闸站预报 水闸洪水
  支持子意图: flood_forecast
  所需参数: 
  必须匹配的对象类型: 无限制
  优先级: 10
  向量分数: 0.383
- ID: 9db9c3b2-1dd1-4e09-bc0d-c2cae1e57587
  名称: 单一水库的洪水预报、预演结果展示
  描述: 用于展示单一水库的洪水预报、预演结果，包含地图定位、该水库入库/出库流量曲线、水位变化图表、关键指标卡片。支持动态数据注入，可展示任意水库的预报预演结果。
  触发模式: 单一水库预报预演结果 洪水预报 洪水预演 入库流量 出库流量 水位变化 预报方案结果 水库水情 水库洪水 盘石头水库 水库调度
  支持子意图: flood_forecast
  所需参数: 
  必须匹配的对象类型: 无限制
  优先级: 10
  向量分数: 0.346
- ID: 449f95d8-e959-4346-b079-09f0c5f397dd
  名称: 闸站详情展示
  描述: 展示某闸的基本信息、功能特点及现场图片等详细内容
  触发模式: 查询 闸 水闸 介绍 详情 参数 图文并茂
  支持子意图: knowledge
  所需参数: 闸站名称(需要展示的闸站具体名称)
  必须匹配的对象类型: 拦河闸,节制闸,分洪闸,退水闸
  优先级: 5
  向量分数: 0.513
- ID: 9c5080cb-3723-43b4-8d03-91ffbd1d92c4
  名称: 查询河道水情
  描述: 展示某河道水文站的基本信息及当前水情数据，用于实时水文监测与分析。
  触发模式: 查询 水文站 河道水文站 水情 当前水位 实时水情 信息 详情 参数
  支持子意图: data_query
  所需参数: stcd(站点编码),stnm(站点名称)
  必须匹配的对象类型: 河道水文站,雨量站,墒情站,闸站监测
  优先级: 5
  向量分数: 0.388
- ID: 8a11bb4d-5e81-42b7-adca-8c59640927c1
  名称: 视频监控展示
  描述: 展示某水库的实时视频监控信息，包括设备状态和访问地址等。
  触发模式: 查看 视频监控 实况 当前 水库 监测站 视频 视频监测
  支持子意图: data_query
  所需参数: stcd(站点编码),code(设备编码)
  必须匹配的对象类型: 视频监测,视频监测站
  优先级: 5
  向量分数: 0.355

**完整提示词**:
```
你是一个Web模板选择专家。根据用户问题和可提供的参数，从候选模板中选择最合适的模板。

## 用户问题
图文并茂的介绍盐土庄闸？

## 业务子意图
None

## 当前对象类型
未知

## 对象识别可提供的参数
（来自实体解析阶段：数据库查询+知识库查询+LLM匹配）
无

## 工作流可提供的参数
（来自工作流执行结果）
无

## 候选模板列表
- ID: 6cde78a6-2662-4f0e-a09f-874cba21dea7
  名称: 单一河道断面洪水预报、预演结果展示
  描述: 用于展示单一河道断面的洪水预报结果。包含地图定位、水位流量过程曲线（双轴）、河道断面地形及实时水位图。单一河道断面包括任一断面、河道水文站点断面、闸站断面等
  触发模式: 单一河道断面 洪水预报 断面水位流量  河道断面 水文站点 河道预报 断面预报 洪峰流量 断面水情 最高水文 闸站预报 水闸洪水
  支持子意图: flood_forecast
  所需参数: 
  必须匹配的对象类型: 无限制
  优先级: 10
  向量分数: 0.383
- ID: 9db9c3b2-1dd1-4e09-bc0d-c2cae1e57587
  名称: 单一水库的洪水预报、预演结果展示
  描述: 用于展示单一水库的洪水预报、预演结果，包含地图定位、该水库入库/出库流量曲线、水位变化图表、关键指标卡片。支持动态数据注入，可展示任意水库的预报预演结果。
  触发模式: 单一水库预报预演结果 洪水预报 洪水预演 入库流量 出库流量 水位变化 预报方案结果 水库水情 水库洪水 盘石头水库 水库调度
  支持子意图: flood_forecast
  所需参数: 
  必须匹配的对象类型: 无限制
  优先级: 10
  向量分数: 0.346
- ID: 449f95d8-e959-4346-b079-09f0c5f397dd
  名称: 闸站详情展示
  描述: 展示某闸的基本信息、功能特点及现场图片等详细内容
  触发模式: 查询 闸 水闸 介绍 详情 参数 图文并茂
  支持子意图: knowledge
  所需参数: 闸站名称(需要展示的闸站具体名称)
  必须匹配的对象类型: 拦河闸,节制闸,分洪闸,退水闸
  优先级: 5
  向量分数: 0.513
- ID: 9c5080cb-3723-43b4-8d03-91ffbd1d92c4
  名称: 查询河道水情
  描述: 展示某河道水文站的基本信息及当前水情数据，用于实时水文监测与分析。
  触发模式: 查询 水文站 河道水文站 水情 当前水位 实时水情 信息 详情 参数
  支持子意图: data_query
  所需参数: stcd(站点编码),stnm(站点名称)
  必须匹配的对象类型: 河道水文站,雨量站,墒情站,闸站监测
  优先级: 5
  向量分数: 0.388
- ID: 8a11bb4d-5e81-42b7-adca-8c59640927c1
  名称: 视频监控展示
  描述: 展示某水库的实时视频监控信息，包括设备状态和访问地址等。
  触发模式: 查看 视频监控 实况 当前 水库 监测站 视频 视频监测
  支持子意图: data_query
  所需参数: stcd(站点编码),code(设备编码)
  必须匹配的对象类型: 视频监测,视频监测站
  优先级: 5
  向量分数: 0.355

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
```json
{
    "selected_template_id": "449f95d8-e959-4346-b079-09f0c5f397dd",
    "confidence": 0.88,
    "reason": "用户问题要求图文并茂地介绍盐土庄闸，与模板'闸站详情展示'的描述和触发模式高度匹配。该模板支持展示闸的基本信息、功能特点及现场图片等详细内容，符合'图文并茂'的需求。虽然缺少闸站名称参数，但假设后续流程可以提供该参数，因此认为基本满足条件。"
}
```
```

## 三、文字响应生成 [17.83s] (Controller.generate_text_only)
**时间**: 2026-02-11 12:03:29
**提示词模板**: RESPONSE_GENERATION_PROMPT

**上下文变量**:
- chat_history: 无
- user_message: 图文并茂的介绍盐土庄闸？
- intent: knowledge_qa
- plan_summary: 无执行计划
- execution_results: 无执行结果
- retrieved_documents: [1] 来源: 知识库: water_project, 文档: 主要建筑物泄流曲线
来源引用格式: [主要建筑物泄流曲线](http://localhost:8000/knowledge/kb-doc/water_project/主要建筑物泄流曲线)
内容: ## 盐土庄闸
- **序号**: 2.0
- **建筑物编码**: GQ_YTZJZZ
- **闸门类型**: 平板闸
- **河道ID**: GQ
- **河道名称**: 共渠
- **所在桩号**: 80857.0
- **建筑物上游水位和流量的关系**: [[0,53],[20,54.07],[50,54.78],[80,55.28],[100,55.57],[120,55.86],[150,56.25],[200,56.70],[250,57.15],[300,57.60],[400,58.20],[500,58.85],[600,59.30],[700,59.85],[800,60.25],[900,60.60],[1000,60.92],[1100,61.30],[
1200,61.60],[1300,61.80],[1400,62.0],[1500,62.20],[1600,62.46],[2000,63.4],[2500,64.3]]

[2] 来源: 知识库: water_project, 文档: 卫共流域各建筑物信息表
来源引用格式: [卫共流域各建筑物信息表](http://localhost:8000/knowledge/kb-doc/water_project/卫共流域各建筑物信息表)
内容: ## 盐土庄节制闸
- **id**: 13
- **建筑物id**: GQ_YTZJZZ
- **闸门类型**: 平板闸
- **建筑类型**: 拦河闸
- **所在河道id**: GQ
- **所在河道**: 共渠
- **桩号**: 93001
- **设计流量**: 1600.0
- **闸底高程**: 53.0
- **闸孔数**: 7
- **单孔净宽**: 11.0
- **闸门高度**: 10.0
- **闸顶高程**: 62.8
- **now_state**: 全开
- **update_time**: 2024-07-29 08:00:00
- **open_n**: 20
- **open_h**: 5.0
- **调度规则**: 视汤河、安阳河来水情况，按五陵站不超过2000m³/s、元村集站不超过2500m³/s控制下泄，最大流量不大于1600m³/s。
- **模型实例**: wg_mike11

[3] 来源: 知识库: water_project, 文档: 卫共流域典型建筑物照片
来源引用格式: [卫共流域典型建筑物照片](http://localhost:8000/knowledge/kb-doc/water_project/卫共流域典型建筑物照片)
内容: # 1.2.6共渠盐土庄闸  

共渠盐土庄闸现场照片。  

![](images/06f8ac5a8730c32760b35aac28739c3617c8eb1bbae8b9169c45067ab72ca629.jpg)

[4] 来源: 知识库: water_project, 文档: 闸站监测
来源引用格式: [闸站监测](http://localhost:8000/knowledge/kb-doc/water_project/闸站监测)
内容: ### 记录 12

- **code:** SZ27
- **name:** 盐土庄节制闸
- **type:** 拦河闸
- **n:** 7
- **width:** 11.00
- **height:** 62.80
- **discharge:** 1600.00
- **latitude:** 35.740422
- **longitude:** 114.478433
- **datum:** 53.00
- **location:** 鹤壁市浚县屯子镇
- **atriver:** 共渠
- **state:** 已建

---

[5] 来源: 知识库: water_project, 文档: 大沙河和卫共河道治理水力要素
来源引用格式: [大沙河和卫共河道治理水力要素](http://localhost:8000/knowledge/kb-doc/water_project/大沙河和卫共河道治理水力要素)
内容: # 5.3.1.2共产主义渠治理方案  

共产主义渠是1958年为引黄修建的,1962年停止引黄后用于行洪。近年来由于共产主义渠来水较少,共产主义渠刘庄闸以下现状渠道河槽有所淤积。现状情...(已截断)

**完整提示词**:
```
你是卫共流域数字孪生系统的智能助手，负责生成最终响应。

## 最近对话历史
无

## 用户原始问题
图文并茂的介绍盐土庄闸？

## 用户意图
knowledge_qa

## 执行计划
无执行计划

## 执行结果
无执行结果

## 检索到的相关知识
[1] 来源: 知识库: water_project, 文档: 主要建筑物泄流曲线
来源引用格式: [主要建筑物泄流曲线](http://localhost:8000/knowledge/kb-doc/water_project/主要建筑物泄流曲线)
内容: ## 盐土庄闸
- **序号**: 2.0
- **建筑物编码**: GQ_YTZJZZ
- **闸门类型**: 平板闸
- **河道ID**: GQ
- **河道名称**: 共渠
- **所在桩号**: 80857.0
- **建筑物上游水位和流量的关系**: [[0,53],[20,54.07],[50,54.78],[80,55.28],[100,55.57],[120,55.86],[150,56.25],[200,56.70],[250,57.15],[300,57.60],[400,58.20],[500,58.85],[600,59.30],[700,59.85],[800,60.25],[900,60.60],[1000,60.92],[1100,61.30],[
1200,61.60],[1300,61.80],[1400,62.0],[1500,62.20],[1600,62.46],[2000,63.4],[2500,64.3]]

[2] 来源: 知识库: water_project, 文档: 卫共流域各建筑物信息表
来源引用格式: [卫共流域各建筑物信息表](http://localhost:8000/knowledge/kb-doc/water_project/卫共流域各建筑物信息表)
内容: ## 盐土庄节制闸
- **id**: 13
- **建筑物id**: GQ_YTZJZZ
- **闸门类型**: 平板闸
- **建筑类型**: 拦河闸
- **所在河道id**: GQ
- **所在河道**: 共渠
- **桩号**: 93001
- **设计流量**: 1600.0
- **闸底高程**: 53.0
- **闸孔数**: 7
- **单孔净宽**: 11.0
- **闸门高度**: 10.0
- **闸顶高程**: 62.8
- **now_state**: 全开
- **update_time**: 2024-07-29 08:00:00
- **open_n**: 20
- **open_h**: 5.0
- **调度规则**: 视汤河、安阳河来水情况，按五陵站不超过2000m³/s、元村集站不超过2500m³/s控制下泄，最大流量不大于1600m³/s。
- **模型实例**: wg_mike11

[3] 来源: 知识库: water_project, 文档: 卫共流域典型建筑物照片
来源引用格式: [卫共流域典型建筑物照片](http://localhost:8000/knowledge/kb-doc/water_project/卫共流域典型建筑物照片)
内容: # 1.2.6共渠盐土庄闸  

共渠盐土庄闸现场照片。  

![](images/06f8ac5a8730c32760b35aac28739c3617c8eb1bbae8b9169c45067ab72ca629.jpg)

[4] 来源: 知识库: water_project, 文档: 闸站监测
来源引用格式: [闸站监测](http://localhost:8000/knowledge/kb-doc/water_project/闸站监测)
内容: ### 记录 12

- **code:** SZ27
- **name:** 盐土庄节制闸
- **type:** 拦河闸
- **n:** 7
- **width:** 11.00
- **height:** 62.80
- **discharge:** 1600.00
- **latitude:** 35.740422
- **longitude:** 114.478433
- **datum:** 53.00
- **location:** 鹤壁市浚县屯子镇
- **atriver:** 共渠
- **state:** 已建

---

[5] 来源: 知识库: water_project, 文档: 大沙河和卫共河道治理水力要素
来源引用格式: [大沙河和卫共河道治理水力要素](http://localhost:8000/knowledge/kb-doc/water_project/大沙河和卫共河道治理水力要素)
内容: # 5.3.1.2共产主义渠治理方案  

共产主义渠是1958年为引黄修建的,1962年停止引黄后用于行洪。近年来由于共产主义渠来水较少,共产主义渠刘庄闸以下现状渠道河槽有所淤积。现状情况下渠道过流 $250\mathrm{m}^{3})$ s时,白寺附近局部水位已平左侧堤,过流400m²/s时在同山至盐土庄之间洪水已漫过左侧堤进入共西行洪区,现状渠道过流能力不足400m3/s。  

可行性研究阶段对共产主义渠进行清淤和加培堤防相结合的方案与单纯加培堤防两个方案进行比较,经分析,共产主义渠加堤方案从工程投资角度分析比清淤方案优,可以减免因河道清淤对沿河建筑物的不利影响,对卫河坡洼的淹没影响不同程度有所增加,但增加的幅度较小(滞洪水位高 $2{\sim}9\mathrm{cm}$ ):同时在小麦生长期会加重对共西的浸没影响,但影响是暂时的。 因此,本次对共产主义渠的治理采取单纯堤防加培方案,不对河道进行清淤。  

依据防洪规划总体安排,发生50年一遇洪水时,共产主义渠及共渠以西行洪区共同行洪,在共产主义渠河道桩号32+280处新建盐土庄闸,控制下泄流量不超过 $1600\mathrm{m^{3}/s}$ 在盐土庄闸以下共卫合流。因此,本次对共产主义渠盐土庄闸以上左堤不进行加培,仅对右堤进行加培设计:盐土庄闸以下右堤不进行加培仅对左堤进行加培设计。  

<html><body><table><tr><td rowspan="2">序号</td><td rowspan="2">河道里程</td><td rowspan="2">地点</td><td colspan="4">行洪</td><td colspan="2">排涝</td></tr><tr><td>设计流量</td><td>水位</td><td>左堤设计堤顶高程</td><td>右堤设计堤顶高程</td><td>流量</td><td></td><td>水位</td></tr><tr><td>1</td><td>0+000</td><td>淇共汇合口</td><td rowspan="17"></td><td>66.53</td><td></td><td>67.83</td><td></td><td>63.19</td></tr><tr><td>2</td><td>0+490</td><td></td><td>66.29</td><td>67.59</td><td></td><td>63.08</td></tr><tr><td>3</td><td>0+970</td><td></td><td>66.10</td><td>67.40</td><td></td><td>62.96</td></tr><tr><td>4</td><td>1+450</td><td></td><td>65.97</td><td>67.27</td><td></td><td>62.85</td></tr><tr><td>5</td><td>1+950</td><td></td><td>65.83</td><td>67.13</td><td></td><td>62.74</td></tr><tr><td>6</td><td>2+450</td><td></td><td>65.74</td><td>67.04</td><td></td><td>62.62</td></tr><tr><td>7</td><td>2+950</td><td></td><td>65.60</td><td>66.90</td><td></td><td>62.50</td></tr><tr><td>8</td><td>3+450</td><td></td><td>65.47</td><td>66.77</td><td></td><td>62.40</td></tr><tr><td>9</td><td>3+950</td><td></td><td>65.36</td><td>66.66</td><td></td><td>62.29</td></tr><tr><td>10</td><td>4+450</td><td></td><td>65.27</td><td>66.57</td><td></td><td>62.19</td></tr><tr><td>11</td><td>4+950</td><td></td><td>65.16</td><td>66.46</td><td>250</td><td>62.09</td></tr><tr><td>12</td><td>5+450</td><td></td><td>与共产主义 65.07</td><td></td><td>66.37</td><td>61.98</td></tr><tr><td>13</td><td>5+950</td><td></td><td>渠以西行洪 取共同承泄 64.95</td><td></td><td>66.25</td><td>61.88</td></tr><tr><td>14</td><td>6+450</td><td></td><td>上游共产主 64.84</td><td></td><td>66.14</td><td>61.78</td></tr><tr><td>15</td><td>6+950</td><td></td><td>义渠和淇河 64.76</td><td></td><td></td><td>61.67</td></tr><tr><td>16</td><td>7+450</td><td>牛四马湖</td><td>洪水，洪峰 64.70 64.58</td><td></td><td>66.06 66.00</td><td>61.56</td></tr><tr><td>17</td><td>7+950</td><td></td><td>流量3100</td><td></td><td>65.88</td><td>61.46</td></tr><tr><td>18</td><td>8+450</td><td></td><td>64.48</td><td></td><td>65.78</td><td>61.35</td></tr><tr><td>19</td><td>8+950</td><td></td><td>64.39</td><td></td><td>65.69</td><td>61.24</td></tr><tr><td>20</td><td>9+450</td><td></td><td>64.28</td><td></td><td>65.58</td><td>61.13</td></tr><tr><td>21</td><td>9+950</td><td></td><td>64.18</td><td></td><td>65.48</td><td>60.95</td></tr><tr><td>22</td><td>10+450</td><td></td><td>64.09</td><td></td><td>65.39</td><td>60.75</td></tr><tr><td>23</td><td>10+950</td><td></td><td>63.88</td><td></td><td>65.18</td><td>60.54</td></tr><tr><td>24</td><td>11+450</td><td></td><td>63.79</td><td></td><td>65.09</td><td>60.34</td></tr><tr><td>25</td><td>11+950</td><td></td><td>63.68</td><td></td><td>64.98</td><td></td></tr><tr><td>26</td><td>12+450</td><td></td><td>63.46</td><td></td><td>64.76</td><td>60.18 60.01</td></tr></table></body></html>  

#表5.3-1共产主义渠河道设计指标表 单位:流量m²/s,其余为m  
<html><body><table><tr><td rowspan="2">序号</td><td rowspan="2">河道里程</td><td rowspan="2">地点</td><td colspan="4">行洪</td><td colspan="2">排涝</td></tr><tr><td>设计流量</td><td>水位</td><td>左堤设计堤顶高程</td><td>右堤设计堤顶高程</td><td>流量</td><td>水位</td></tr><tr><td>27</td><td>12+950</td><td></td><td></td><td>62.82</td><td></td><td>64.12</td><td></td><td>59.85</td></tr><tr><td>28</td><td>13+450</td><td></td><td></td><td>60.29</td><td>61.59</td><td></td><td>59.74</td></tr><tr><td>29</td><td>13+950</td><td></td><td>62.95</td><td></td><td>64.25</td><td></td><td>59.59</td></tr><tr><td>30</td><td>14+450</td><td></td><td>62.70</td><td></td><td>64.00</td><td></td><td>59.42</td></tr><tr><td>31</td><td>14+950</td><td></td><td></td><td>62.60</td><td>63.90</td><td></td><td>59.35</td></tr><tr><td>32</td><td>15+450</td><td></td><td>62.47</td><td></td><td>63.77</td><td></td><td>59.29</td></tr><tr><td>33</td><td>15+950</td><td></td><td>62.37</td><td></td><td>63.67</td><td></td><td>59.24</td></tr><tr><td>34</td><td>16+450</td><td></td><td>62.18</td><td></td><td>63.48</td><td></td><td>59.19</td></tr><tr><td>35</td><td>16+950</td><td></td><td>61.96</td><td></td><td>63.26</td><td></td><td>59.14</td></tr><tr><td>36</td><td>17+450</td><td></td><td>61.82</td><td></td><td>63.12</td><td></td><td>59.07</td></tr><tr><td>37</td><td>17+950</td><td></td><td>61.73</td><td></td><td>63.03</td><td></td><td>58.99</td></tr><tr><td>38</td><td>18+450</td><td></td><td>61.69</td><td></td><td>62.99</td><td></td><td>58.92</td></tr><tr><td>39</td><td>18+950</td><td></td><td>61.68</td><td></td><td>62.98</td><td></td><td>58.87</td></tr><tr><td>40</td><td>19+450</td><td></td><td>61.65</td><td></td><td>62.95</td><td></td><td>58.82</td></tr><tr><td>41</td><td>19+950</td><td></td><td>61.65</td><td></td><td>62.95</td><td></td><td>58.78</td></tr><tr><td>42</td><td>20+450</td><td></td><td>61.63</td><td></td><td>62.93</td><td></td><td>58.70</td></tr><tr><td>43</td><td>20+950</td><td></td><td>61.61</td><td></td><td>62.91</td><td></td><td>58.62</td></tr><tr><td>44</td><td>21+450</td><td></td><td>61.60</td><td></td><td>62.90</td><td></td><td>58.55</td></tr><tr><td>45</td><td>21+950</td><td></td><td>61.59</td><td></td><td>62.89</td><td></td><td>58.47</td></tr><tr><td>46</td><td>22+450</td><td></td><td>61.58</td><td></td><td>62.88</td><td></td><td>58.40</td></tr><tr><td>47</td><td>22+950</td><td></td><td>61.56</td><td></td><td>62.86</td><td></td><td>58.30</td></tr><tr><td>48</td><td>23+450</td><td></td><td>61.54</td><td></td><td>62.84</td><td></td><td>58.21</td></tr><tr><td>49</td><td>23+950</td><td></td><td>61.53</td><td></td><td>62.83</td><td></td><td>58.13</td></tr><tr><td>50</td><td>24+450</td><td></td><td>61.52</td><td></td><td>62.82</td><td></td><td>58.07</td></tr><tr><td>51</td><td>24+950</td><td></td><td>61.51</td><td></td><td>62.81</td><td></td><td>58.04</td></tr><tr><td>52</td><td>25+450</td><td></td><td>61.48</td><td></td><td>62.78</td><td></td><td>57.96</td></tr></table></body></html>  

<html><body><table><tr><td rowspan="2">序号</td><td rowspan="2">河道里程</td><td rowspan="2">地点</td><td colspan="4">行洪</td><td colspan="2">排涝</td></tr><tr><td>设计流量</td><td>水位</td><td>左堤设计堤顶高程</td><td>右堤设计堤顶高程</td><td>流量</td><td>水位 57.88</td></tr><tr><td>53</td><td>25+950</td><td></td><td rowspan="19"></td><td>61.48</td><td></td></tr><tr><td>54</td><td>26+450</td><td>61.46</td><td></td><td>62.78 62.76</td><td>57.80</td></tr><tr><td>55</td><td>26+950</td><td></td><td>61.43</td><td>62.73</td><td>57.69</td></tr><tr><td>56</td><td>27+450</td><td></td><td>61.44</td><td>62.74</td><td>57.50</td></tr><tr><td>57</td><td>27+950</td><td></td><td>61.37/61.4</td><td>62.70</td><td>57.52</td></tr><tr><td>58</td><td>28+450</td><td></td><td>61.34/61.4</td><td>62.70</td><td>57.43</td></tr><tr><td>59</td><td>28+940</td><td></td><td>61.31/61.4</td><td>62.70</td><td>57.34</td></tr><tr><td>60</td><td>29+430</td><td></td><td>61.31/61.4</td><td>62.70</td><td>57.30</td></tr><tr><td>61</td><td>29+960</td><td></td><td>61.27/61.4</td><td>62.70</td><td>57.22</td></tr><tr><td>62</td><td>30+430</td><td></td><td>61.24/61.4</td><td>62.70</td><td>57.16</td></tr><tr><td>63</td><td>30+930</td><td></td><td>61.22/61.4</td><td>62.70</td><td>57.10</td></tr><tr><td>64</td><td>31+430</td><td></td><td>61.18/61.4</td><td>62.70</td><td>57.04</td></tr><tr><td>65</td><td>31+930</td><td></td><td>61.14/61.4</td><td>62.70</td><td>56.97</td></tr><tr><td rowspan="2">66</td><td rowspan="2">32+280 盐土庄节制闸</td><td rowspan="2"></td><td rowspan="2">61.14/61.4</td><td rowspan="2">62.70</td><td rowspan="2"></td><td>56.96</td></tr><tr><td></td></tr><tr><td></td><td>33+030</td><td></td><td>59.94 59.9</td><td>61.94 61.9</td><td></td><td></td></tr><tr><td>67</td><td>33+540</td><td></td><td>59.87</td><td>61.87</td><td></td><td>56.82</td></tr><tr><td>68</td><td></td><td></td><td></td><td>61.84</td><td></td><td>56.77</td></tr><tr><td>69</td><td>34+040</td><td></td><td>59.84</td><td>61.77</td><td></td><td>56.73</td></tr><tr><td>70</td><td>34+490</td><td></td><td>59.77</td><td>61.76</td><td></td><td>56.67</td></tr><tr><td>71</td><td>34+690 35+030</td><td></td><td>59.76</td><td>61.72</td><td></td><td>56.61</td></tr><tr><td>72</td><td>35+550</td><td></td><td>59.72 59.67</td><td>61.67</td><td></td><td>56.55</td></tr><tr><td>73</td><td>36+020</td><td></td><td>59.57</td><td>61.57</td><td></td><td>56.41</td></tr><tr><td>74 75</td><td>36+510</td><td></td><td>59.48</td><td>61.48</td><td></td><td>56.33</td></tr><tr><td>76</td><td>36+970</td><td></td><td>59.41</td><td>61.41</td><td></td><td>56.25 56.14</td></tr><tr><td>77</td><td>37+570</td><td></td><td>59.34</td><td>61.34</td><td>维持现状堤顶高程</td><td>55.99</td></tr></table></body></html>  

#表5.3-1共产主义渠河道设计指标表 单位:流量m2/s,其余为m  
<html><body><table><tr><td rowspan="2">序号</td><td rowspan="2">河道里程</td><td rowspan="2">地点</td><td colspan="4">行洪</td><td colspan="2">排涝</td></tr><tr><td>设计流量</td><td>水位</td><td>左堤设计堤顶高程</td><td>右堤设计堤顶高程</td><td>流量</td><td></td><td>水位 55.9</td></tr><tr><td>78</td><td>38+010</td><td></td><td rowspan="17">2000（共卫 合流）</td><td>59.27</td><td>61.27</td><td></td><td rowspan="10"></td><td rowspan="10"></td><td></td></tr><tr><td>79</td><td>38+220</td><td></td><td>59.25</td><td>61.25</td><td>55.83</td></tr><tr><td>80</td><td>38+420</td><td></td><td>59.21</td><td>61.21</td><td>55.81</td></tr><tr><td>81</td><td>38+980</td><td></td><td>59.09</td><td>61.09</td><td>55.67</td></tr><tr><td>82</td><td>39+510</td><td></td><td>59.02</td><td>61.02</td><td>55.61</td></tr><tr><td>83</td><td>40+000</td><td></td><td>58.89</td><td>60.89</td><td>55.53</td></tr><tr><td>84</td><td>40+490</td><td></td><td>58.79</td><td>60.79</td><td>55.45</td></tr><tr><td>85</td><td>41+000</td><td></td><td>58.7</td><td>60.7</td><td>55.33</td></tr><tr><td>86</td><td>41+510</td><td></td><td>58.6</td><td>60.6</td><td>55.06</td></tr><tr><td>87</td><td>42+000</td><td></td><td>58.54</td><td>60.54</td><td>55.03</td></tr><tr><td>88</td><td>42+500</td><td></td><td>58.5</td><td>60.5</td><td>54.94</td></tr><tr><td>89</td><td>43+040</td><td></td><td>58.42</td><td>60.42</td><td>54.88</td></tr><tr><td>90</td><td>43+280</td><td></td><td>58.41</td><td>60.41</td><td>54.86</td></tr><tr><td>91</td><td>43+510</td><td></td><td>58.36</td><td>60.36</td><td>54.85</td></tr><tr><td>92</td><td>43+930</td><td></td><td>58.31</td><td>60.31</td><td>54.84</td></tr><tr><td>93</td><td>44+200</td><td>入卫河口</td><td>58.15</td><td>60.12</td><td></td><td>54.84</td></tr></table></body></html>

注:1、共产主义渠河道断面桩号与河槽里程桩号、堤防桩号均一致。2、盐土庄闸以上右堤堤顶高程为河道设计水位加 $1.3\mathrm{m}$ 堤防超高与白寺坡设计滞蓄水位加 $1.3\mathrm{m}$ 堤防超高的外包线,表中“上下数据分别为共渠河道设计水位与白寺坡设计滞蓄水位。3、盐土庄闸以下左堤堤顶高程为河道设计水位加2.0m的堤防超高。  

<html><body><table><tr><td colspan="4"></td><td rowspan="3">卫河</td><td colspan="6">清淤设计指标对比表</td></tr><tr><td rowspan="3">序号</td><td rowspan="3">河道桩号</td><td rowspan="3">主槽桩号</td><td rowspan="3">地点</td><td colspan="3">可研方案 设计断面</td><td colspan="3">本次设计方案</td></tr><tr><td colspan="3">河底高程</td><td colspan="3">设计断面</td></tr><tr><td>（m）</td><td>底宽 (m）</td><td>河道比降</td><td>河底高程 (m)</td><td>底宽 (m)</td><td>河道比降</td></tr><tr><td>1</td><td>0+000</td><td>0+140</td><td colspan="2">淇共汇合口</td><td>58.48</td><td rowspan="6">70</td><td></td><td>58.48</td><td rowspan="6">60</td><td></td></tr><tr><td>2</td><td>0+300</td><td>0+490</td><td colspan="2">小河口节制闸</td><td>58</td><td></td><td>58</td><td></td></tr><tr><td>3</td><td>0+500</td><td>0+730</td><td colspan="2"></td><td>57.95</td><td></td><td>57.95</td><td rowspan="6"></td></tr><tr><td>4</td><td>1+190</td><td>2+040</td><td>淇门</td><td></td><td>57.73</td><td>57.73</td><td></td></tr><tr><td></td><td>6+020</td><td>6+970</td><td></td><td>耿湾村</td><td>57.14</td><td>57.14</td><td>17</td></tr><tr><td>6</td><td>7+850</td><td>8+890</td><td></td><td>东郭村</td><td>56.91</td><td>56.91</td><td></td><td rowspan="6">1/8230</td></tr><tr><td>7</td><td>14+200</td><td>15+580</td><td></td><td>纸坊村</td><td>56.13</td><td>56.13</td><td rowspan="6"></td></tr><tr><td>8</td><td>16+400</td><td>17+190</td><td></td><td>雷村</td><td>55.82</td><td></td></tr><tr><td>9</td><td></td><td></td><td></td><td></td><td></td><td></td></tr><tr><td></td><td></td><td>26+920</td><td></td><td>宗湾上</td><td>54.82</td><td>54.82</td></tr><tr><td>10</td><td>23+900</td><td></td><td></td><td>宗湾下</td><td>54.49</td><td>1/7427</td></tr><tr><td>11</td><td>26+360</td><td>29+290</td><td></td><td></td><td></td><td rowspan="4">1/7665 1/7893</td><td rowspan="4">54.25</td><td rowspan="4">22</td><td rowspan="4"></td></tr><tr><td>12</td><td>27+680</td><td></td><td>31+150 长虹渠入卫河口54.25/53.85</td><td></td><td>22</td></tr><tr><td>13</td><td>33+920</td><td></td><td>38+240</td><td>柴湾村</td><td>53.06</td></tr><tr><td>14</td><td>37+700</td><td>42+020</td><td></td><td>苑刘庄</td><td>52.44</td><td>52.44</td></tr></table></body></html>  

<html><body><table><tr><td rowspan="3"></td><td rowspan="3">序号河道桩号主槽桩号</td><td rowspan="3"></td><td rowspan="3">地点</td><td colspan="3">可研方案</td><td colspan="3">本次设计方案</td></tr><tr><td colspan="3">设计断面</td><td colspan="3">设计断面</td></tr><tr><td rowspan="2">河底高程 （m）</td><td rowspan="2">底宽 (m）</td><td rowspan="2">河道比降</td><td rowspan="2"></td><td rowspan="2">河底高程 底宽 (m） (m)</td><td rowspan="2">河道比降</td></tr><tr><td></td></tr><tr><td>15</td><td>42+850</td><td>47+250</td><td>浚县上</td><td>51.84/51.37</td><td rowspan="4">10</td><td rowspan="2">1/7336</td><td>51.55</td><td></td><td rowspan="2"></td></tr><tr><td>16</td><td>44+380</td><td>48+760</td><td>浚县下</td><td>51.16</td><td>51.3</td><td></td></tr><tr><td rowspan="2">17</td><td rowspan="2">46+660</td><td rowspan="2">51+260</td><td rowspan="2">十里铺上</td><td rowspan="2">50.82</td><td rowspan="2"></td><td rowspan="2">1/8128</td><td>50.89</td><td rowspan="2"></td></tr><tr><td></td></tr><tr><td>18</td><td>48+120</td><td>52+730</td><td>十里铺下</td><td>50.64</td><td>维持 现状</td><td>维持现状</td><td>50.64 46.98</td><td>维持 现状</td><td>维持现状</td></tr><tr><td>19</td><td>64+590</td><td>69+870</td><td>老观嘴</td><td>47.96</td><td rowspan="2">60</td><td rowspan="2">1/9815</td><td rowspan="2">45.21</td><td rowspan="2">20</td><td rowspan="2">1/5266</td></tr><tr><td>20</td><td>73+520</td><td>79+190</td><td>浚内沟口</td><td>47.03</td></tr></table></body></html>  

<html><body><table><tr><td>治理范围</td><td>提防核子</td><td>设计水位 (m)</td><td>(m)</td><td>设计提项高程视状顶高程 (m)</td><td>久高 (m)</td><td>治理指施</td></tr><tr><td rowspan="3">Z37+500- Z38+550</td><td>Z37+544</td><td>60.97/61.4</td><td>62.6</td><td>62.31</td><td>60</td><td rowspan="3">结合提顶遥机 路建设加高</td></tr><tr><td>Z37+955</td><td>60.94/61.4</td><td>62.6</td><td>62.19</td><td>1+0</td></tr><tr><td>238+540</td><td>60.62/61.4</td><td>62.6</td><td>62.33</td><td>0.27</td></tr><tr><td>Z43+200-</td><td>Z43+233</td><td>60.55</td><td>61.75</td><td>1119</td><td>0.64</td><td></td></tr></table></body></html>  

#表5.4-12卫河干流左堤提防加培治理措统计表  


<html><body><table><tr><td>治理范围</td><td>提防桩号</td><td>设计水位 (m）</td><td>设计提项高程规状提项高程</td><td></td><td>欠高 (m）</td><td>治理指施</td></tr><tr><td rowspan="2">Z43+850</td><td>Z43+635</td><td>60.51</td><td>（m） 61.71</td><td>61.15</td><td>0.56</td><td rowspan="8"></td></tr><tr><td>Z43+830</td><td>60.48</td><td>61.68</td><td>61.09</td><td>0.59</td></tr><tr><td rowspan="2">Z44+800 245+150</td><td>Z44+835</td><td>60.35</td><td>61.55</td><td>61.22</td><td>0.33 迎水侧加防油</td></tr><tr><td>Z45+120</td><td>60.33</td><td>61.53</td><td>61.19</td><td>0.34 （位于</td></tr><tr><td rowspan="4">Z46+100- Z47+700</td><td>Z46+117</td><td>60.20</td><td>019</td><td>+L09</td><td>0.66 城，提项为</td></tr><tr><td>Z46+609</td><td>60.15</td><td></td><td></td><td>土路）</td></tr><tr><td></td><td></td><td>61.35</td><td>60.76</td><td>0.59</td></tr><tr><td>Z47+240</td><td>60.11</td><td>61.31</td><td>60.76</td><td>0.55</td></tr><tr><td rowspan="11">Z49+600- Z54+290</td><td>Z47+672 Z49+663</td><td>60.11 60.01</td><td>61.31 1219</td><td>60.78 60.85</td><td>0.53 0.36</td><td rowspan="11">土提加培</td></tr><tr><td>Z50+291</td><td>60.00</td><td>61.20</td><td>60.32</td><td>0.88</td></tr><tr><td></td><td>59.99</td><td></td><td></td><td></td></tr><tr><td>Z50+909</td><td>5665</td><td></td><td>60.49 60.21</td><td>0.70</td></tr><tr><td>Z51+505</td><td>59.98</td><td>61.19 61.18</td><td>60.16</td><td>0.98 1.02</td></tr><tr><td>Z52+005</td><td>9665</td><td></td><td>60.4</td><td>0.76</td></tr><tr><td>252+505 Z53+005</td><td>59.95</td><td>61.16 61.15</td><td>60.1</td><td>1.05</td></tr><tr><td></td><td>59.93</td><td></td><td></td><td></td></tr><tr><td>Z53+407</td><td>59.92</td><td>61.13 61.12</td><td>60.22 60.21</td><td>0.91</td></tr><tr><td>Z53+932</td><td>1665</td><td></td><td>60.77</td><td>160</td></tr><tr><td>Z54+206</td><td></td><td>61.11</td><td></td><td>0.34 0.51</td></tr><tr><td rowspan="4">Z93+870 056+46Z</td><td>Z93+921 Z94+317</td><td>55.10 55.05</td><td>0695</td><td>56.39 56.28</td><td>0.57</td><td rowspan="4">土提加培</td></tr><tr><td>Z94+620</td><td></td><td>56.85</td><td></td><td>0.66</td></tr><tr><td></td><td>55.02</td><td>56.82</td><td>56.16</td><td></td></tr><tr><td>Z94+920 Z95+423</td><td>55.00</td><td>56.80</td><td>56.2</td><td>0.60</td></tr><tr><td rowspan="2">Z95+400 295+650 295+970</td><td>Z95+626</td><td>54.93</td><td>56.73</td><td>56.25</td><td>0.48 水侧加防流</td><td rowspan="2">境（提项为 2018年铺设 凝土路）</td></tr><tr><td>520-962</td><td></td><td>56.68</td><td>56.27</td><td>0.41</td></tr><tr><td rowspan="11">OLI-96Z</td><td>Z96+108</td><td>54.85 54.84</td><td>56.65 56.64</td><td>56.1 56.23</td><td>0.55 0.41</td><td rowspan="11">（提填为</td></tr><tr><td>606+101Z</td><td>54.18</td><td>55.98</td><td>55.4</td><td>0.58</td></tr><tr><td>2102-411</td><td>54.12</td><td>55.92</td><td>55.44</td><td>0.48</td></tr><tr><td>Z102-911</td><td>54.07</td><td>55.87</td><td>55.1</td><td>0.77</td></tr><tr><td>Z103-514</td><td>53.98</td><td>55.78</td><td>55.07</td><td>0.71</td></tr><tr><td>Z104+014</td><td>53.87</td><td>55.67</td><td>54.99</td><td>0.68 面水侧加防箱</td></tr><tr><td>Z101+850- Z106+450 Z104+514</td><td>53.77</td><td>55.57</td><td>54.8</td><td>0.77</td><td rowspan="4">凝土路）</td></tr><tr><td>Z105+011</td><td>53.73</td><td>55.53</td><td>54.8</td><td>0.73</td></tr><tr><td>Z105+413</td><td>53.66</td><td>55.46</td><td>54.7</td><td>0.76</td></tr><tr><td>2105-914</td><td>53.53</td><td>55.33</td><td>54.4</td><td>0.93</td></tr><tr><td></td><td>Z106-414</td><td>53.45</td><td>55.25</td><td>54.48</td><td>0.77</td></tr><tr><td>Z107+700-</td><td>Z107+729</td><td>53.25</td><td>55.05</td><td>54.42</td><td>0.63</td><td></td></tr></table></body></html>  

<html><body><table><tr><td>治理范围</td><td>堤防桩号</td><td>设计水位 (m)</td><td>设计提顶高程现状堤项高程 （m）</td><td></td><td>欠高 （m）</td><td>治理措施</td></tr><tr><td rowspan="7">Z110+730</td><td>Z108+230</td><td>53.14</td><td>54.94</td><td>54.12</td><td>0.82</td><td rowspan="7">迎水侧加防浪 凝土路面）</td></tr><tr><td>Z108+730</td><td>53.06</td><td>54.86</td><td>54.25</td><td>0.61</td></tr><tr><td>Z109+230</td><td>53.00</td><td>54.80</td><td>54.24</td><td>0.56</td></tr><tr><td>Z109+730</td><td>52.94</td><td>54.74</td><td>53.96</td><td>0.78 墙（堤顶为混</td></tr><tr><td>Z110+229</td><td>52.87</td><td>54.67</td><td>53.75</td><td>0.92</td></tr><tr><td>Z110+327</td><td>52.85</td><td>54.65</td><td>53.89</td><td>0.76</td></tr><tr><td>Z110+428</td><td>52.83</td><td>54.63</td><td>53.87</td><td>0.76</td></tr><tr><td rowspan="5">Z110+730~ Z113+100</td><td>Z111+228</td><td>52.69</td><td>54.49</td><td>54.13</td><td>0.36</td><td rowspan="8"></td></tr><tr><td>Z111+768</td><td>52.56</td><td>54.36</td><td>53.85</td><td>0.51</td></tr><tr><td>Z112+270</td><td>52.45</td><td>54.25</td><td>53.86</td><td>0.39</td></tr><tr><td>Z112+769</td><td>52.41</td><td>54.21</td><td>53.88</td><td>0.33 结合堤顶巡视</td></tr><tr><td>Z113+063</td><td>52.39</td><td>54.19</td><td>53.9</td><td>0.29 道路建设加高</td><td rowspan="5">至设计项高程</td></tr><tr><td>Z115+859</td><td></td><td>51.76</td><td>53.56 53.17</td><td>0.39</td></tr><tr><td rowspan="2">Z115+780~ Z116+100</td><td>Z116+060</td><td>51.67</td><td>53.47</td><td>53 0.47</td></tr><tr><td>Z140+302</td><td>48.27</td><td>50.27</td><td>49.88 0.39</td></tr><tr><td rowspan="2">Z140+250~ Z140+550</td><td>Z140+507</td><td>48.26</td><td>50.26</td><td>49.82</td><td>0.44</td></tr><tr><td>Z141+903</td><td>48.12</td><td>50.12</td><td>49.67</td><td>0.45</td></tr><tr><td rowspan="4">Z141+850~ Z142+650</td><td>Z142+204</td><td>48.11</td><td>50.11</td><td>49.64</td><td>0.47</td><td rowspan="4">迎水侧加防浪 墙（堤顶为混 凝土路面）</td></tr><tr><td>Z142+402</td><td>48.11</td><td>50.11</td><td>49.7</td><td>0.41</td></tr><tr><td>Z142+602</td><td>48.10</td><td>50.10</td><td></td><td></td></tr><tr><td></td><td></td><td></td><td>49.71</td><td>0.39</td></tr><tr><td rowspan="6">Z143+550~ Z146+050</td><td>Z143+607 Z144+104</td><td>48.02 47.94</td><td>50.02 49.94</td><td>49.48 49.31</td><td>0.54 0.63</td><td rowspan="6">土堤加培 (Z144+350- 在背水侧堤脚</td></tr><tr><td>Z144+605</td><td>47.91</td><td>49.91</td><td>49.13</td><td>0.78</td></tr><tr><td></td><td>47.81</td><td>49.81</td><td>49.12</td><td>Z145+050段 0.69</td></tr><tr><td>Z145+103</td><td></td><td>49.78</td><td>49.14</td><td>0.64</td></tr><tr><td>Z145+603</td><td>47.78</td><td></td><td></td><td>修筑挡土墙）</td></tr><tr><td>Z146+003</td><td>47.72</td><td>49.72</td><td>49.25</td><td>0.47</td></tr><tr><td rowspan="5">Z147+150- Z148+850</td><td>Z147+203</td><td>47.56</td><td>49.56 49.55</td><td>48.95</td><td>0.61 0.62</td><td rowspan="5">土堤加培</td></tr><tr><td>Z147+403 Z147+803</td><td>47.55 47.50</td><td>49.50</td><td>48.93</td><td>0.51</td></tr><tr><td>Z148+303</td><td></td><td>49.48</td><td>48.99</td><td>0.46</td></tr><tr><td>Z148+802</td><td>47.48</td><td></td><td>49.02</td><td></td></tr><tr><td></td><td>47.42</td><td>49.42</td><td>49.03</td><td>0.39</td></tr><tr><td rowspan="5">Z149+150~ Z151+450</td><td>Z149+204</td><td>47.30</td><td>49.30</td><td>48.83</td><td>0.47 0.34</td><td rowspan="5">土堤加培</td></tr><tr><td>Z149+704</td><td>47.28</td><td>49.28</td><td>48.94</td><td>0.46</td></tr><tr><td>Z150+202 Z150+703</td><td>47.28</td><td>49.28</td><td>48.82</td><td>0.55</td></tr><tr><td></td><td>47.23</td><td>49.23</td><td>48.68</td><td></td></tr><tr><td>Z151+203 Z151+403</td><td>47.14 47.11</td><td>49.14 49.11</td><td>48.6 48.56</td><td>0.54 0.55</td></tr></table></body></html>  

<html><body><table><tr><td>治理范围</td><td>堤防桩号</td><td>设计水位 （m）</td><td>设计堤顶高程现状堤顶高程 （m）</td><td>（m）</td><td>欠高 (m）</td><td>治理措施</td></tr><tr><td rowspan="5">Z151+850~ Z153+550</td><td>Z151+903</td><td>47.06</td><td>49.06</td><td>48.58</td><td>0.48</td><td rowspan="5">土堤加培</td></tr><tr><td>Z152+403</td><td>47.00</td><td>49.00</td><td>48.54</td><td>0.46</td></tr><tr><td>Z152+903</td><td>46.95</td><td>48.95</td><td>48.41</td><td>0.54</td></tr><tr><td>Z153+403</td><td>46.92</td><td>48.92</td><td>48.39</td><td>0.53</td></tr><tr><td>Z153+504</td><td>46.91</td><td>48.91</td><td>48.46</td><td>0.45</td></tr><tr><td rowspan="3">Z153+850~ Z154+150</td><td>Z153+903</td><td>46.86</td><td>48.86</td><td>48.38</td><td>0.48</td><td rowspan="3">土堤加培</td></tr><tr><td>Z154+003</td><td>46.84</td><td>48.84</td><td>48.31</td><td>0.53</td></tr><tr><td>Z154+102</td><td>46.82</td><td>48.82</td><td>48.36</td><td>0.46</td></tr><tr><td rowspan="2">Z158+800~ Z159+150</td><td>Z158+829</td><td>46.26</td><td>48.26</td><td>47.66</td><td>0.60</td><td rowspan="2">土堤加培</td></tr><tr><td>Z159+127</td><td>46.20</td><td>48.20</td><td>47.58</td><td>0.62</td></tr><tr><td rowspan="3">Z160+800~ Z161+050</td><td>Z160+830</td><td>45.92</td><td>47.92</td><td>47.41</td><td>0.51</td><td rowspan="3">迎水侧加防浪 墙（堤顶为混 凝土路面）</td></tr><tr><td>Z160+933</td><td>45.90</td><td>47.90</td><td>47.47</td><td>0.43</td></tr><tr><td>Z161+035</td><td>45.88</td><td>47.88</td><td>47.33</td><td>0.55</td></tr><tr><td rowspan="3">Z169+500~ Z170+250</td><td>Z169+539</td><td>45.03</td><td>47.03</td><td>46.59</td><td>0.44</td><td rowspan="3">土堤加培</td></tr><tr><td>Z169+735</td><td>45.01</td><td>47.01</td><td>46.48</td><td>0.53</td></tr><tr><td>Z169+935</td><td>44.99</td><td>46.99</td><td>46.48</td><td>0.51</td></tr><tr><td rowspan="4">Z172+300~ Z173+750</td><td>Z172+338</td><td>44.68</td><td>46.68</td><td>46.25</td><td>0.43</td><td rowspan="4">土堤加培</td></tr><tr><td>Z172+837</td><td>44.65</td><td>46.65</td><td>46</td><td>0.65</td></tr><tr><td>Z173+337</td><td>44.62</td><td>46.62</td><td>46.11</td><td>0.51</td></tr><tr><td>Z173+737</td><td>44.59</td><td>46.59</td><td>46</td><td>0.59</td></tr><tr><td rowspan="6">Z174+300~ Z176+030</td><td>Z174+336</td><td>44.54</td><td>46.54</td><td>46.07</td><td>0.47</td><td rowspan="6">土堤加培</td></tr><tr><td>Z174+435</td><td>44.53</td><td>46.53</td><td>45.98</td><td>0.55</td></tr><tr><td>Z174+836</td><td>44.51</td><td>46.51</td><td>46.23</td><td>0.28</td></tr><tr><td>Z175+334</td><td>44.48</td><td>46.48</td><td>45.82</td><td>0.66</td></tr><tr><td>Z175+834</td><td>44.43</td><td>46.43</td><td>45.82</td><td>0.61</td></tr><tr><td>Z175+935</td><td>44.42</td><td>46.42</td><td>45.89</td><td>0.53</td></tr><tr><td rowspan="3">Z177+700~ Z177+950</td><td>Z177+734</td><td>44.26</td><td>46.26</td><td>45.81</td><td>0.45</td><td rowspan="3">土堤加培</td></tr><tr><td>Z177+834</td><td>44.26</td><td>46.26</td><td>45.7</td><td>0.56</td></tr><tr><td>Z177+934</td><td>44.26</td><td>46.26</td><td>45.83</td><td>0.43</td></tr><tr><td rowspan="2">Z180+000~ Z180+150</td><td>Z180+030</td><td>44.06</td><td>46.06</td><td>45.54</td><td>0.52</td><td rowspan="2">土堤加培</td></tr><tr><td>Z180+130</td><td>44.06</td><td>46.06</td><td>45.54</td><td>0.52</td></tr><tr><td rowspan="4">Z181+600~ Z182+150</td><td>Z181+631</td><td>43.97</td><td>45.97</td><td>45.3</td><td>0.67</td><td rowspan="3">土堤加培</td></tr><tr><td>Z181+931</td><td>43.92</td><td>45.92</td><td>45.42</td><td>0.50</td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td>Z182+132</td><td>43.89</td><td>45.89</td><td>45.2</td><td>0.69</td><td></td></tr></table></body></html>

注:表中"”上下数据为卫河河道设计洪水位与白寺坡设计滞蓄水位。  

#表5.4-13 卫河干流右堤堤防加培治理措施统计表  


<html><body><table><tr><td>治理范围</td><td>典型断面</td><td>设计水位 （m）</td><td>设计堤顶高程 (m)</td><td>现状堤顶高程 （m）</td><td>欠高 （m）</td></tr><tr><td rowspan="4">Y28+400~ Y29+250</td><td>Y28+413</td><td>61.78/62.49</td><td>63.69</td><td>63.07</td><td>0.62</td></tr><tr><td>Y28+639</td><td>61.77/62.49</td><td>63.69</td><td>62.78</td><td>0.91</td></tr><tr><td>Y28+913</td><td>61.74/62.49</td><td>63.69</td><td>62.9</td><td>0.79</td></tr><tr><td>Y29+231</td><td>61.72/62.49</td><td>63.69</td><td>63.4</td><td>0.29</td></tr><tr><td rowspan="20">Y53+250~ Y65+950</td><td>Y53+297</td><td>59.99</td><td>61.19</td><td>60.82</td><td>0.37</td></tr><tr><td>Y53+887</td><td>59.99</td><td>61.19</td><td>60.6</td><td>0.59</td></tr><tr><td>Y54+365</td><td>59.98</td><td>61.18</td><td>60.79</td><td>0.39</td></tr><tr><td>Y54+405</td><td>59.98</td><td>61.18</td><td>60.6</td><td>0.58</td></tr><tr><td>Y54+889</td><td>59.95</td><td>61.15</td><td>60.95</td><td>0.20</td></tr><tr><td>Y55+378</td><td>59.94</td><td>61.14</td><td>60.67</td><td>0.47</td></tr><tr><td>Y55+897</td><td>59.92</td><td>61.12</td><td>60.75</td><td>0.37</td></tr><tr><td>Y56+417</td><td>59.91</td><td>61.71</td><td>60.56</td><td>1.15</td></tr><tr><td>Y56+878</td><td>59.90</td><td>61.90</td><td>60.65</td><td>1.25</td></tr><tr><td>Y57+372</td><td>59.90</td><td>61.90</td><td>60.7</td><td>1.20</td></tr><tr><td>Y57+872</td><td>59.89</td><td>61.89</td><td>60.7</td><td>1.19</td></tr><tr><td>Y58+358</td><td>59.85</td><td>61.85</td><td>60.6</td><td>1.25</td></tr><tr><td>Y58+870</td><td>59.72</td><td>61.72</td><td>60.7</td><td>1.02</td></tr><tr><td>Y59+371</td><td>59.64</td><td>61.64</td><td>60.47</td><td>1.17</td></tr><tr><td>Y59+878</td><td>59.52</td><td>61.52</td><td>60.5</td><td>1.02</td></tr><tr><td>Y60+383</td><td>59.45</td><td>61.45</td><td>60.2</td><td>1.25</td></tr><tr><td></td><td></td><td></td><td></td><td></td></tr><tr><td>Y60+833</td><td>59.39</td><td>61.39</td><td>60.35</td><td>1.04</td></tr></table></body></html>  

<html><body><table><tr><td>治理范围</td><td colspan="2">典型断面</td><td>设计水位 (m）</td><td>设计堤顶高程 (m)</td><td>现状堤顶高程 (m)</td><td>欠高 (m)</td><td>治理指施</td></tr><tr><td rowspan="11"></td><td colspan="2">Y61+311</td><td>59.36</td><td>61.36</td><td>60.25</td><td>1.11</td><td rowspan="11">土堤加培 0.49 0.42</td></tr><tr><td>Y61+785</td><td></td><td>59.32</td><td>61.32</td><td>60.33</td><td>660</td></tr><tr><td>Y62+288</td><td></td><td>59.26</td><td>61.26</td><td>60.18</td><td>1.08</td></tr><tr><td>Y62+784</td><td></td><td>59.15</td><td>61.15</td><td>60.56</td><td>0.59</td></tr><tr><td>Y63+288</td><td></td><td>59.07</td><td>61.07</td><td>60.61</td><td>0.46</td></tr><tr><td>Y63+769</td><td></td><td>59.02</td><td>61.02</td><td>60.06</td><td>0.96</td></tr><tr><td>Y64+293</td><td></td><td>58.93</td><td>60.93</td><td>60.12</td><td>0.81</td></tr><tr><td>Y64+764</td><td></td><td>58.82</td><td>60.82</td><td>59.94</td><td>0.88</td></tr><tr><td colspan="2">Y65+295</td><td>58.67</td><td>60.67</td><td>60.08</td><td>0.59</td></tr><tr><td colspan="2">Y65+704</td><td>58.60</td><td>60.60</td><td>59.99</td><td>0.61</td></tr><tr><td colspan="2" rowspan="3">Y67+600~ Y68+300</td><td colspan="2">Y67+600 58.40</td><td>60.40 60.38</td><td>59.7</td><td rowspan="3">0.70</td></tr><tr><td colspan="2">Y67+800</td><td>58.38</td><td>59.51</td><td>0.87 0.94</td></tr><tr><td colspan="2">Y68+002</td><td>58.36</td><td>60.36</td><td>59.42</td></tr><tr><td colspan="2">Y68+300</td><td>58.33</td><td>60.33</td><td>59.63</td><td>0.70</td></tr><tr><td colspan="2">Y78+590</td><td>56.95</td><td>58.75</td><td>57.95</td><td>0.80</td><td></td></tr><tr><td colspan="2">Y79+084 5984+500</td><td>56.92</td><td>58.72</td><td>58.16</td><td>0.56</td><td></td><td></td></tr><tr><td colspan="2">Y88+100~</td><td colspan="2">Y84+440</td><td>56.19</td><td>57.99 57.44</td><td colspan="2">57.5</td></tr><tr><td colspan="2">Y88+250</td><td colspan="2">Y88+137</td><td>55.64</td><td></td><td colspan="2">57.02</td></tr><tr><td rowspan="6">Y92+400~ Y94+850</td><td colspan="2">Y88+237</td><td>55.64</td><td>57.44</td><td colspan="2">56.88</td><td>0.56</td></tr><tr><td colspan="2">Y92+440</td><td>55.23</td><td>57.03</td><td colspan="2">56.49</td><td>0.54</td></tr><tr><td colspan="2">Y92+939</td><td>55.20</td><td>57.00</td><td colspan="2">56.29</td><td>0.71</td></tr><tr><td colspan="2">Y93+440</td><td>55.18</td><td>56.98</td><td colspan="2">56.3</td><td>0.68</td></tr><tr><td colspan="2">Y93+940</td><td>55.14</td><td>56.94</td><td colspan="2">56.38</td><td>0.56</td></tr><tr><td colspan="2">Y94+439</td><td>55.06</td><td>56.86</td><td colspan="2">56.34</td><td>0.52</td></tr><tr><td rowspan="4">Y101+950- Y103+200</td><td colspan="2">Y101+957</td><td>54.26</td><td>56.06</td><td colspan="2">55.42</td><td>90</td></tr><tr><td colspan="2">Y102+457</td><td>54.21</td><td>56.01</td><td colspan="2">55.51</td><td>0.50</td></tr><tr><td colspan="2">Y102+957</td><td>54.16</td><td>55.96</td><td colspan="2">55.25</td><td>0.71</td></tr><tr><td colspan="2">Y103+158</td><td>54.13</td><td>55.93</td><td colspan="2">55.39</td><td>0.54</td></tr><tr><td rowspan="5">Y105+750~Y 107+800</td><td colspan="2">Y105+752</td><td>53.77</td><td>55.57</td><td colspan="2">54.8</td><td>0.77</td></tr><tr><td colspan="2">Y106+251</td><td>53.70</td><td>55.50</td><td colspan="2">54.47</td><td>1.03</td></tr><tr><td colspan="2">Y106+753</td><td>53.60</td><td>55.40</td><td colspan="2">54.48</td><td>0.92</td></tr><tr><td colspan="2">Y107+252</td><td>53.51</td><td>55.31</td><td colspan="2">54.63</td><td>0.68</td></tr><tr><td colspan="2">Y107+756</td><td>53.45</td><td>55.25</td><td colspan="2">54.5</td><td>0.75</td></tr></table></body></html>  

<html><body><table><tr><td>治理范围</td><td>典型断面</td><td>设计水位 (m）</td><td>设计堤顶高程现状堤顶高程 (m）</td><td>(m)</td><td>欠高 (m）</td><td>治理措施</td></tr><tr><td rowspan="5">Y112+450- Y114+000</td><td>Y112+476</td><td>52.63</td><td>54.43</td><td>54.07</td><td>0.36</td><td rowspan="5">土堤加培</td></tr><tr><td>Y112+574</td><td>52.61</td><td>54.41</td><td>53.97</td><td>0.44</td></tr><tr><td>Y113+076</td><td>52.53</td><td>54.33</td><td>53.79</td><td></td></tr><tr><td>Y113+575</td><td>52.45</td><td>54.25</td><td>53.73</td><td>0.52</td></tr><tr><td>Y113+875</td><td>52.42</td><td>54.22</td><td>53.71</td><td>0.51</td></tr><tr><td>Y140+050~</td><td>Y140+065</td><td>48.64</td><td>50.64</td><td>50.04</td><td>0.60</td><td rowspan="2">土堤加培</td></tr><tr><td rowspan="8">Y140+300</td><td>Y140+265</td><td>48.56</td><td>50.56</td><td>49.96</td><td>0.60</td></tr><tr><td>Y143+965 Y144+465</td><td>48.12 48.10</td><td>50.12 50.10</td><td>49.45</td><td>0.67</td><td rowspan="8">土堤加培</td></tr><tr><td></td><td>48.07</td><td>50.07</td><td>49.28</td><td>0.82</td></tr><tr><td>Y144+966</td><td></td><td></td><td>49.33</td><td>0.74</td></tr><tr><td>Y145+465</td><td>48.01</td><td>50.01</td><td>49.18</td><td>0.83</td></tr><tr><td>Y145+965</td><td>47.93</td><td>49.93</td><td>49</td><td>0.93</td></tr><tr><td>Y146+466</td><td>47.84</td><td>49.84</td><td>49.1</td><td>0.74</td></tr><tr><td>Y146+966</td><td>47.77</td><td>49.77</td><td>49.06</td><td>0.71</td></tr><tr><td>Y147+467</td><td>47.60</td><td>49.60</td><td>49.33</td><td>0.27</td></tr><tr><td rowspan="4"></td><td>Y147+967</td><td>47.56</td><td>49.56</td><td>48.94</td><td>0.62</td></tr><tr><td>Y148+466</td><td>47.56</td><td>49.56</td><td>48.99</td><td>0.57</td></tr><tr><td>Y148+966</td><td>47.50</td><td>49.50</td><td>49.05</td><td>0.45</td></tr><tr><td>Y149+166</td><td>47.49</td><td>49.49</td><td>48.92</td><td>0.57</td></tr><tr><td rowspan="4">Y150+850~ Y151+800</td><td>Y150+866</td><td>47.29</td><td>49.29</td><td>47.76</td><td>1.53</td><td rowspan="4">迎水侧加防浪墙 （堤顶为2019年 铺设沥青路面）</td></tr><tr><td>Y151+166</td><td>47.28</td><td>49.28</td><td>48.62</td><td>0.66</td></tr><tr><td>Y151+667</td><td>47.24</td><td>49.24</td><td>48.76</td><td>0.48</td></tr><tr><td>Y151+767</td><td>47.22</td><td>49.22</td><td>48.64</td><td>0.58</td></tr><tr><td rowspan="3">Y160+500~ Y160+750</td><td>Y160+515</td><td>46.21</td><td>48.21</td><td>47.5</td><td>0.71</td><td rowspan="3">土堤加培</td></tr><tr><td>Y160+615</td><td>46.20</td><td>48.20</td><td>47.18</td><td>1.02</td></tr><tr><td>Y160+716</td><td>46.18</td><td>48.18</td><td>47.49</td><td>0.69</td></tr><tr><td rowspan="4">Y175+650- Y176+600</td><td>Y175+670</td><td>44.67</td><td>46.47</td><td>46.21</td><td>0.26</td><td rowspan="4">迎水侧加防浪墙 （提顶为2016年 铺设沥青路面）</td></tr><tr><td>Y175+870</td><td>44.65</td><td>46.45</td><td>46.17</td><td>0.28</td></tr><tr><td>Y176+170</td><td>44.64</td><td>46.44</td><td>46.12</td><td>0.32</td></tr><tr><td>Y176+570</td><td>44.62</td><td>46.42</td><td>46.13</td><td>0.29</td></tr><tr><td rowspan="2">Y176+950~ Y177+100</td><td>Y176+970</td><td>44.59</td><td>46.39</td><td>45.98</td><td>0.41</td><td rowspan="2">迎水侧加防浪墙 （堤顶为2016年 铺设沥青路面）</td></tr><tr><td>Y177+070</td><td>44.59</td><td>46.39</td><td>46.05</td><td>0.34</td></tr><tr><td rowspan="2">Y178+550~ Y178+700</td><td>Y178+573</td><td>44.43</td><td>46.23</td><td>45.72</td><td>0.51</td><td rowspan="2">土堤加培</td></tr><tr><td>Y178+674</td><td>44.42</td><td>46.22</td><td>45.83</td><td>0.39</td></tr><tr><td rowspan="3">Y179+350~ Y180+200</td><td>Y179+374</td><td>44.33</td><td>46.13</td><td>45.7</td><td>0.43</td><td rowspan="2">结合堤顶巡视道 路建设加高至设</td></tr><tr><td>Y179+574</td><td>44.32</td><td>46.12</td><td>45.82</td><td>0.30</td></tr><tr><td>Y179+876</td><td>44.31</td><td>46.11</td><td>45.79</td><td>0.32</td><td>计顶高程</td></tr></table></body></html>

## 输出要求
1. 结合对话历史理解用户问题的完整含义（如用户说"小南海呢？"，需结合历史知道是在问流域面积）
2. 根据执行结果，生成清晰、准确、专业的回答
3. 回答应该简洁明了，直接切中主题，突出关键数据和结论
4. 如果执行过程中有错误，请适当说明并给出建议
5. 【重要】如果使用了检索到的知识，必须在回答末尾添加"参考来源"部分。直接复制上面每条知识的"来源引用格式"字段内容作为来源链接，不要修改或简化！

## 格式禁止
- 【禁止】不要使用Markdown表格格式（如 | 列1 | 列2 | 这种格式）
- 【禁止】不要罗列大量数据项，表格和详细数据应在左侧报告页面中展示
- 【建议】使用简洁的文字描述或短列表（如"- 项目: 值"）来呈现关键信息
- 【建议】如果数据较多，只提取最关键的2-3个指标进行说明，并提示用户查看左侧报告页面获取完整信息

请生成最终回答:

```

**LLM响应**:
```
盐土庄闸是位于中国卫共流域的重要水利工程，以下是其关键信息的概述：

- **地理位置**: 盐土庄闸位于河南省鹤壁市浚县屯子镇，处于共产主义渠（简称“共渠”）上。
- **功能与设计**:
  - 盐土庄节制闸为拦河闸，主要用于控制洪水和调节流量。
  - 设计最大泄洪能力为1600立方米/秒，闸门类型为平板闸，共有7孔，单孔净宽11米。
  - 闸底高程为53.0米，闸顶高程为62.8米。
- **调度规则**:
  - 根据汤河、安阳河来水情况，按五陵站不超过2000m³/s、元村集站不超过2500m³/s控制下泄，最大流量不大于1600m³/s。
- **现状**:
  - 当前状态为全开，闸门开启高度为5.0米，开启数量为20个。
- **历史背景**:
  - 共产主义渠在1958年修建，1962年后主要用于行洪。由于河道淤积问题，近年来进行了治理，盐土庄闸作为重要节点被新建以控制下泄流量。

此外，盐土庄闸的照片及详细数据可参考相关资料进行进一步了解。

参考来源:  
[主要建筑物泄流曲线](http://localhost:8000/knowledge/kb-doc/water_project/主要建筑物泄流曲线)  
[卫共流域各建筑物信息表](http://localhost:8000/knowledge/kb-doc/water_project/卫共流域各建筑物信息表)  
[卫共流域典型建筑物照片](http://localhost:8000/knowledge/kb-doc/water_project/卫共流域典型建筑物照片)  
[闸站监测](http://localhost:8000/knowledge/kb-doc/water_project/闸站监测)
```

---

