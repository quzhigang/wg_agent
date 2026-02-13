
*****会话ID: 0c7d1cc0-2512-4298-9d26-c65df3edee14 | 问题: 给我统计一下当前监测的各个大中型水库的库容总和？*****

## 一、意图分析 [3.68s] (Planner.analyze_intent)
**时间**: 2026-02-13 09:49:55
**提示词模板**: INTENT_ANALYSIS_PROMPT

**上下文变量**:
- context_summary: 无
- chat_history: 无
- user_message: 给我统计一下当前监测的各个大中型水库的库容总和？

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
给我统计一下当前监测的各个大中型水库的库容总和？

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
{'intent_category': 'business', 'confidence': 0.95, 'entities': {'object': '各个大中型水库', 'object_type': '水库', 'action': '统计当前库容总和', 'time': '当前'}, 'target_kbs': ['monitor_site', 'water_project']}
```

## 二、业务子意图分类 [3.53s] (Planner.classify_business_sub_intent)
**时间**: 2026-02-13 09:49:59
**提示词模板**: BUSINESS_SUB_INTENT_PROMPT

**上下文变量**:
- user_message: 给我统计一下当前监测的各个大中型水库的库容总和？
- entities: {"object": "各个大中型水库", "object_type": "水库", "action": "统计当前库容总和", "time": "当前"}

**完整提示词**:
```
你是河南省卫共流域数字孪生系统的业务意图分类器，负责对业务类意图进行细分。

## 用户消息
给我统计一下当前监测的各个大中型水库的库容总和？

## 提取的实体
{"object": "各个大中型水库", "object_type": "水库", "action": "统计当前库容总和", "time": "当前"}

## 业务子意图分类体系

### data_query（监测数据查询）
- 针对单个明确站点/对象的监测数据查询（当前/实时/历史某时刻）
- 不涉及对比、分析、判断、统计、汇总等后续处理

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
- 查询对象为群体/不明确，或需要多步处理（对比、统计、汇总、排序等）

## 输出要求
返回JSON格式：
{
    "business_sub_intent": "子意图类别（data_query/flood_forecast/flood_simulation/emergency_plan/damage_assessment/other）",
    "confidence": 0.95,
    "reason": "分类理由"
}

## 分类规则
1. 针对单个明确对象的监测数据查询，无后续处理 → data_query
2. 涉及"预报"、"预测"、"未来洪水" → flood_forecast
3. 涉及"预演"、"模拟" → flood_simulation
4. 涉及"预案"、"调度方案" → emergency_plan
5. 涉及"损失"、"灾损"、"转移" → damage_assessment
6. 查询对象为群体/不明确，或需要多步处理（对比、统计、汇总等） → other
7. 无法明确归类 → other

```

**LLM响应**:
```
{'business_sub_intent': 'other', 'confidence': 0.95, 'reason': "用户请求对'各个大中型水库'的库容进行统计总和，查询对象为群体且涉及统计处理，符合'other'类别规则。"}
```

## 三、对象类型合成 [3.48s] (Planner._resolve_object_type)
**时间**: 2026-02-13 09:50:05
**提示词模板**: OBJECT_TYPE_SYNTHESIS_PROMPT

**上下文变量**:
- user_message: 给我统计一下当前监测的各个大中型水库的库容总和？
- object_name: 各个大中型水库
- db_result: 数据库中未找到名为'各个大中型水库'的站点
- rag_context: 以下是相关的知识库内容：

[1] 文档: 卫共流域系统接入监测站点情况, 章节: (3)水情监测
# (3)水情监测  

卫共流域水情监测包括:  

1、大型、中型和小型水库水情监测站点 89 个,监测数据包含库水位、需水量、下泄流量过程;  

2、河道水情监测站点 20 个,其中常年具备完整监测数据的国家级水文站点 11 个,监测数据包含水位和流量过程;  

(4)闸站监测  

接入卫共流域除水库闸站以外的各类主干河道闸站共计 44 个,包括拦河闸、退水闸、分洪闸(堰),主要为大沙河、卫河、共渠、汤永河、安阳河上的拦河闸及各蓄滞洪区分洪闸、分洪堰、退水闸。

[2] 文档: 卫共流域大中型水库主要水力特性, 章节: 群英水库
## 群英水库
水库编码: 4.10821000003e11
类型: 中型
所在河流: 大沙河
流域面积: 165.0
坝顶高程: 490.5
防浪墙高程: 491.6
溢洪道高程: 477.0
溢洪道宽度: 56.0
溢洪道闸门孔数: 7.0
溢洪道闸门尺寸:
溢洪道设计泄量/最大泄量: 1330/2710
泄洪洞底高程: 412（445）
泄洪洞宽*高*长: 1*1（0.8*0.8）
泄洪洞设计流量/最大泄量: 10.52/10.74（8.16/8.51）
输水洞高程: 412（445）
输水洞尺寸宽*高*长:
输水洞设计流量/最大流量:
电站装机功率/kw:
电站引水流量:
库底高程: 390.0
死水位: 425.0
汛限水位: 477.0
防洪高水位:
兴利水位: 477.0
设计洪水位: 481.75
校核洪水位: 485.2
总库容: 1660.0
调洪库容: 828.0
防洪库容: 700.0
兴利库容: 1300.0
死库容: 53.0
最大泄洪量: 2480.0
备注:

[3] 文档: 水库水文站, 章节: 英雄水库 (4)
### 英雄水库 (4)

- **county:** 林州市
- **dead_cap:** 0.23
- **res_name:** 英雄水库
- **che_flo_sta:** 100
- **che_flo_lev:** 412.92
- **main_dam_wav_wal_elev:** 
- **main_dam_top_len:** 200
- **wat_shed_a
...(更多内容已省略)

**完整提示词**:
```
你是卫共流域数字孪生系统的实体识别助手，负责根据检索到的信息确定对象的类型。

## 用户消息
给我统计一下当前监测的各个大中型水库的库容总和？

## 待识别对象
对象名称：各个大中型水库

## 数据库查询结果
数据库中未找到名为'各个大中型水库'的站点

## 知识库检索结果
以下是相关的知识库内容：

[1] 文档: 卫共流域系统接入监测站点情况, 章节: (3)水情监测
# (3)水情监测  

卫共流域水情监测包括:  

1、大型、中型和小型水库水情监测站点 89 个,监测数据包含库水位、需水量、下泄流量过程;  

2、河道水情监测站点 20 个,其中常年具备完整监测数据的国家级水文站点 11 个,监测数据包含水位和流量过程;  

(4)闸站监测  

接入卫共流域除水库闸站以外的各类主干河道闸站共计 44 个,包括拦河闸、退水闸、分洪闸(堰),主要为大沙河、卫河、共渠、汤永河、安阳河上的拦河闸及各蓄滞洪区分洪闸、分洪堰、退水闸。

[2] 文档: 卫共流域大中型水库主要水力特性, 章节: 群英水库
## 群英水库
水库编码: 4.10821000003e11
类型: 中型
所在河流: 大沙河
流域面积: 165.0
坝顶高程: 490.5
防浪墙高程: 491.6
溢洪道高程: 477.0
溢洪道宽度: 56.0
溢洪道闸门孔数: 7.0
溢洪道闸门尺寸:
溢洪道设计泄量/最大泄量: 1330/2710
泄洪洞底高程: 412（445）
泄洪洞宽*高*长: 1*1（0.8*0.8）
泄洪洞设计流量/最大泄量: 10.52/10.74（8.16/8.51）
输水洞高程: 412（445）
输水洞尺寸宽*高*长:
输水洞设计流量/最大流量:
电站装机功率/kw:
电站引水流量:
库底高程: 390.0
死水位: 425.0
汛限水位: 477.0
防洪高水位:
兴利水位: 477.0
设计洪水位: 481.75
校核洪水位: 485.2
总库容: 1660.0
调洪库容: 828.0
防洪库容: 700.0
兴利库容: 1300.0
死库容: 53.0
最大泄洪量: 2480.0
备注:

[3] 文档: 水库水文站, 章节: 英雄水库 (4)
### 英雄水库 (4)

- **county:** 林州市
- **dead_cap:** 0.23
- **res_name:** 英雄水库
- **che_flo_sta:** 100
- **che_flo_lev:** 412.92
- **main_dam_wav_wal_elev:** 
- **main_dam_top_len:** 200
- **wat_shed_a
...(更多内容已省略)

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
{
    "object": "对象名称（从用户消息中提取的有效对象或全流域）",
    "object_type": "对象类型",
    "stcd": "站点编码（如果有）",
    "confidence": 0.9,
    "source": "类型来源：db/rag/infer/user_message",
    "reason": "判断依据"
}

## 对象类型选项
- 站点类：水库水文站、河道水文站、雨量站、闸站监测、AI监测站点、工程安全监测、取水监测、墒情站
- 工程类：水库、河道、蓄滞洪区、闸站
- 业务类：洪水预报、洪水预演、预案生成、灾损评估
- 区域类：流域、行政区
- 其他：unknown（如果无法确定）

```

**LLM响应**:
```
{'object': '大中型水库', 'object_type': '水库', 'stcd': '', 'confidence': 0.85, 'source': 'infer', 'reason': "用户消息中提到'各个大中型水库'，名称中包含'水库'关键词，且知识库中提及了多个中型和大型水库的详细信息。虽然数据库未找到该名称的站点，但根据上下文可推断其为工程类中的'水库'类型。"}
```

## 四、工作流选择 [1.35s] (Planner.check_workflow_match)
**时间**: 2026-02-13 09:50:06
**提示词模板**: WORKFLOW_SELECT_PROMPT

**上下文变量**:
- user_message: 给我统计一下当前监测的各个大中型水库的库容总和？
- entities: {"object": "大中型水库", "object_type": "水库", "action": "统计当前库容总和", "time": "当前"}
- business_sub_intent: other
- predefined_workflows: 
暂无预定义工作流模板，请检查已保存的动态工作流或进行动态规划。

- saved_workflows: - ID: 19c0e794-39fb-48dc-beb4-bc537e538a65
  名称: compare_reservoir_realtime_vs_historical_flood
  中文名: 水库实时与历史洪水水位对比
  描述: 获取特定水库的当前实时水位，并检索历史特定洪水事件期间的最高水位进行对比分析。
  触发模式: 用户询问水库当前水位是否超过了历史上某次特定洪水（如21.7洪水）的最高水位或特征水位。
  相似度: 0.529
- ID: ef95bb00-d9cf-48c5-8326-e787e7542405
  名称: query_reservoir_water_level_limit
  中文名: 水库水情查询对比
  描述: 用于查询指定水库的实时水情数据，并与该水库的汛限水位、设计水位、防洪高水位等进行对比，判断是否超过或低于。
  触发模式: 用于查询指定水库的实时水情数据，并与该水库的汛限水位、设计水位、防洪高水位等进行对比，判断是否超过或低于。只适合水库
  相似度: 0.502
- ID: c9ea37ec-3985-49fe-8d07-6f84a0e0f39a
  名称: flood_event_comparison
  中文名: 洪水事件对比分析
  描述: 针对特定水文站点，查询历史洪水期间的最大洪峰、总过洪量，并与当前实时流量进行对比分析。
  触发模式: 询问{{对象}}在某次洪水期间的最大洪峰、总过洪量，并要求与当前流量进行对比（适用于河道水文站及历史洪水数据来源）
  相似度: 0.488
- ID: 95d5eace-d98a-4613-90f0-72d603c722a2
  名称: query_river_water_level_status
  中文名: 河道水情查询对比
  描述: 用于查询指定河道测站当前水位是否超过警戒水位、保证水位等的通用工作流
  触发模式: 用户询问某河道测站当前水位是否超过警戒水位、保证水位等特征值，仅适用于河道水文站数据来源，只适合河道
  相似度: 0.466

**完整提示词**:
```
你是河南省卫共流域数字孪生系统的业务流程选择器，负责从可用工作流中选择最匹配的一个。

## 输入信息
- 用户消息：给我统计一下当前监测的各个大中型水库的库容总和？
- 实体：{"object": "大中型水库", "object_type": "水库", "action": "统计当前库容总和", "time": "当前"}
- 子意图：other

## 可用的预定义工作流

暂无预定义工作流模板，请检查已保存的动态工作流或进行动态规划。


## 可用的已保存工作流
- ID: 19c0e794-39fb-48dc-beb4-bc537e538a65
  名称: compare_reservoir_realtime_vs_historical_flood
  中文名: 水库实时与历史洪水水位对比
  描述: 获取特定水库的当前实时水位，并检索历史特定洪水事件期间的最高水位进行对比分析。
  触发模式: 用户询问水库当前水位是否超过了历史上某次特定洪水（如21.7洪水）的最高水位或特征水位。
  相似度: 0.529
- ID: ef95bb00-d9cf-48c5-8326-e787e7542405
  名称: query_reservoir_water_level_limit
  中文名: 水库水情查询对比
  描述: 用于查询指定水库的实时水情数据，并与该水库的汛限水位、设计水位、防洪高水位等进行对比，判断是否超过或低于。
  触发模式: 用于查询指定水库的实时水情数据，并与该水库的汛限水位、设计水位、防洪高水位等进行对比，判断是否超过或低于。只适合水库
  相似度: 0.502
- ID: c9ea37ec-3985-49fe-8d07-6f84a0e0f39a
  名称: flood_event_comparison
  中文名: 洪水事件对比分析
  描述: 针对特定水文站点，查询历史洪水期间的最大洪峰、总过洪量，并与当前实时流量进行对比分析。
  触发模式: 询问{{对象}}在某次洪水期间的最大洪峰、总过洪量，并要求与当前流量进行对比（适用于河道水文站及历史洪水数据来源）
  相似度: 0.488
- ID: 95d5eace-d98a-4613-90f0-72d603c722a2
  名称: query_river_water_level_status
  中文名: 河道水情查询对比
  描述: 用于查询指定河道测站当前水位是否超过警戒水位、保证水位等的通用工作流
  触发模式: 用户询问某河道测站当前水位是否超过警戒水位、保证水位等特征值，仅适用于河道水文站数据来源，只适合河道
  相似度: 0.466

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

## 五、工具筛选 [3.80s] (Planner._select_relevant_tools)
**时间**: 2026-02-13 09:50:10
**提示词模板**: TOOL_SELECTION_PROMPT

**上下文变量**:
- user_message: 给我统计一下当前监测的各个大中型水库的库容总和？
- business_sub_intent: other
- entities: {"object": "大中型水库", "object_type": "水库", "action": "统计当前库容总和", "time": "当前"}
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
给我统计一下当前监测的各个大中型水库的库容总和？

## 业务子意图
other

## 提取的实体
{"object": "大中型水库", "object_type": "水库", "action": "统计当前库容总和", "time": "当前"}

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
  - monitor_rsvr_now: 获取水库河道实时水情（无需登录），返回水位、库容、入库流量、出库流量等实时数据
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

## 选择原则（严格按顺序执行）
1. **【强制规则】水雨情等监测工具选用原则**：
   - 当用于问题意图为获取监测数据时，必须从 hydro_monitor.py 中选择工具
   - 当用户消息包含当前、实时、最新、现在、目前等时间关键词时，也必须从 hydro_monitor.py 中选择工具
2. **辅助工具**：需要站点编码时包含lookup_station_code，需要知识库检索时包含search_knowledge
3. 如果不确定需要哪个工具，可以多选几个相关的
4. 根据数据类型选择对应的查询工具：
   - 水库水情 → query_reservoir_last, query_reservoir_process
   - 河道水情 → query_river_last, query_river_process
   - 雨量数据 → query_rain_process, query_rain_statistics, query_rain_sum
   - AI监测 → query_ai_water_last, query_ai_rain_last 等

```

**LLM响应**:
```
{'selected_tools': ['query_reservoir_last'], 'reason': '用户需要统计当前监测的各个大中型水库的库容总和，因此需要获取每个水库的实时水情数据，其中包含蓄水量（库容）信息。query_reservoir_last 是 hydro_monitor.py 中用于获取水库最新实时水情数据的工具，符合需求。'}
```

