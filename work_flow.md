# 卫共流域数字孪生智能体 - 工作流说明

## 整体架构流程图

```
                                用户提问
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────┐
│                    PLAN 节点 (planner_node)                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. 意图分析 (analyze_intent) - 三大类分类                 │  │
│  │    ├── 第1类: chat (一般对话/闲聊)                        │  │
│  │    ├── 第2类: knowledge (固有知识查询)                    │  │
│  │    └── 第3类: business (业务相关)                         │  │
│  │         └── 子意图: data_query/flood_forecast/            │  │
│  │                    flood_simulation/emergency_plan/       │  │
│  │                    damage_assessment/other                │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ 2. 工作流匹配 (check_workflow_match) ← 仅business类执行    │  │
│  │    ├── 2.1 向量检索匹配预定义工作流模板（置信度≥0.75）      │  │
│  │    ├── 2.2 静态映射匹配（备选）                             │  │
│  │    └── 2.3 匹配自动保存的流程 (_match_saved_workflow)       │  │
│  ├────────────────────────────────────────────────────────────┤  │
│  │ 3. 计划生成 (generate_plan) ← 仅当无匹配工作流时执行         │  │
│  │    ├── 3.1 RAG检索，获取相关知识和业务流程                   │  │
│  │    ├── 3.2 获取可用工具描述                                 │  │
│  │    ├── 3.3 获取可用工作流描述                               │  │
│  │    ├── 3.4 LLM生成执行计划                                  │  │
│  │    └── 3.5 自动保存动态流程 (_save_dynamic_plan)            │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
                          plan_router 路由函数
               ┌───────────┬───────────┬───────────┐
               │           │           │           │
               ▼           ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
        │quick_chat│ │knowledge │ │ workflow │ │ execute  │
        │   节点   │ │_rag 节点  │ │   节点   │ │   节点   │
        └──────────┘ └──────────┘ └──────────┘ └──────────┘
               │           │           │           │
               ▼           │           │           │
              END          │           │           │
                           ▼           ▼           ▼
                    ┌─────────────────────────────────┐
                    │         EXECUTE 节点            │
                    │       (executor_node)           │
                    │     执行计划中的各步骤          │
                    │     调用工具（API接口）         │
                    └─────────────────────────────────┘
                                   │
                                   ▼
                          should_continue 路由
             ┌────────┬────────┬────────┬────────┐
             │        │        │        │        │
             ▼        ▼        ▼        ▼        ▼
         execute  wait_async respond    plan     END
         (继续)   (等待异步)  (响应)    (重规划)
             │        │        │
             │        ▼        │
             │  ┌──────────┐   │
             │  │wait_async│   │
             │  │   节点   │   │
             │  └──────────┘   │
             │        │        │
             │        ▼        │
             │  ┌─────────────────────────────────┐
             └► │        RESPOND 节点             │
                │      (controller_node)          │
                │      合成最终响应文本           │
                │      可能生成Web页面            │
                └─────────────────────────────────┘
                                │
                                ▼
                               END
```

## 三大类意图分类说明

### 第1类: chat (一般对话)

**触发条件**：
- 问候、感谢、告别、闲聊
- 询问助手信息

**处理流程**：
```
plan → quick_chat → END
```

### 第2类: knowledge (固有知识查询)

**10个知识库**：
| 知识库ID | 名称 | 说明 |
|---------|------|------|
| catchment_basin | 流域概况 | 流域基本信息 |
| water_project | 水利工程 | 水库、水闸等工程信息 |
| monitor_site | 监测站点 | 雨量站、水文站等 |
| history_flood | 历史洪水 | 历史洪水事件记录 |
| flood_preplan | 防洪预案 | 防洪应急预案 |
| system_function | 系统功能 | 系统操作说明 |
| hydro_model | 水文模型 | 水文模型相关知识 |
| catchment_planning | 流域规划 | 流域发展规划 |
| project_designplan | 工程设计 | 工程设计方案 |
| business_workflow  | 业务流程 | 工程设计方案 |

**处理流程**：
```
plan → knowledge_rag → 网络搜索(特定问题或RAG无结果时) → respond → END
```

### 第3类: business (业务相关)

**子意图分类**：
| 子意图 | 说明 |
|-------|------|
| data_query | 数据查询 |
| flood_forecast | 洪水预报 |
| flood_simulation | 洪水模拟 |
| emergency_plan | 应急预案 |
| damage_assessment | 灾损评估 |
| other | 其他业务 |

**匹配优先级**：
1. 预定义工作流模板（向量检索，置信度≥0.75）
2. 静态映射（子意图→工作流）
3. 自动保存的流程（按使用次数排序）
4. 动态规划（LLM生成）→ 自动保存

**处理流程**：
```
plan → [workflow/execute] → respond → END
```

## 核心节点说明

### 1. PLAN 节点 (planner_node)

**位置**：`src/agents/planner.py`

**功能**：
- 意图分析：识别用户意图类别和子意图
- 实体提取：提取时间、地点、站点等关键实体
- 工作流匹配：匹配预定义或已保存的工作流
- 计划生成：动态生成执行计划

**输出**：
- `intent_category`: 意图类别 (chat/knowledge/business)
- `business_sub_intent`: 业务子意图
- `extracted_entities`: 提取的实体
- `matched_workflow`: 匹配的工作流
- `plan_steps`: 执行计划步骤

### 2. EXECUTE 节点 (executor_node)

**位置**：`src/agents/executor.py`

**功能**：
- 执行计划中的各个步骤
- 调用工具（API接口）
- 处理异步任务
- 参数变量解析和替换
- 错误处理和重试

**输出**：
- `execution_results`: 各步骤执行结果
- `current_step_index`: 当前步骤索引
- `has_async_tasks`: 是否有异步任务

### 3. RESPOND 节点 (controller_node)

**位置**：`src/agents/controller.py`

**功能**：
- 整合执行结果
- 生成最终响应文本
- 决定是否生成Web页面
- 敏感信息过滤
- 格式化输出

**输出**：
- `final_response`: 最终响应文本
- `output_type`: 输出类型 (text/web_page)
- `generated_page_url`: 生成的页面URL（如有）

## 自动保存流程机制

### 触发条件

- 动态规划成功生成计划
- 计划步骤数 >= 2
- 意图类别为 business

### 保存内容

| 字段 | 说明 |
|-----|------|
| name | 流程名称（auto_{sub_intent}_{随机ID}） |
| trigger_pattern | 触发模式（用户消息特征） |
| intent_category | 意图类别 |
| sub_intent | 子意图 |
| entity_extraction_pattern | 实体提取模式 |
| steps | 完整执行步骤（JSON） |
| output_type | 输出类型 |

### 匹配逻辑

1. 按子意图筛选已保存流程
2. 按使用次数降序排序
3. 匹配成功后自动增加使用次数
4. 支持启用/禁用控制

### 管理接口

| 方法 | 路径 | 说明 |
|-----|------|------|
| GET | /saved-workflows | 获取清单（分页） |
| GET | /saved-workflows/{id} | 获取详情 |
| PUT | /saved-workflows/{id} | 编辑流程 |
| DELETE | /saved-workflows/{id} | 删除流程 |
| PATCH | /saved-workflows/{id}/toggle | 启用/禁用 |

**管理页面**：`/ui/saved_workflows.html`

## 工作流向量化索引

### 功能说明

**位置**：`src/workflows/workflow_vector_index.py`

工作流向量化索引实现了工作流的语义匹配，支持：
- 将工作流描述向量化存储
- 基于用户输入进行向量检索
- 返回最匹配的工作流（置信度阈值≥0.75）

### 存储位置

向量化数据存储在 `workflow_vectors/` 目录。

## 预定义工作流

### 工作流列表

| 文件 | 名称 | 说明 |
|-----|------|------|
| flood_autoforecast_getresult.py | 自动预报结果获取 | 获取自动洪水预报结果 |
| flood_manualforecast_getresult.py | 手动预报结果获取 | 获取手动洪水预报结果 |
| get_autoforecast_result.py | 获取自动预报结果 | 自动预报结果查询 |
| get_history_autoforecast_result.py | 获取历史预报结果 | 历史预报数据查询 |
| get_manualforecast_result.py | 获取手动预报结果 | 手动预报结果查询 |

### 工作流结构

每个工作流包含：
- `name`: 工作流名称
- `description`: 工作流描述
- `trigger_keywords`: 触发关键词
- `steps`: 执行步骤列表
- `output_type`: 输出类型

## 工具系统

### 工具分类

| 模块 | 工具数量 | 说明 |
|-----|---------|------|
| basin_info.py | 14 | 流域基本信息 |
| hydro_monitor.py | 15 | 水雨情监测 |
| modelplan_control.py | 20 | 模型及方案管理 |
| rain_control.py | 33 | 降雨获取设置 |
| flood_otherbusiness.py | 29 | 其他洪水业务 |
| hydromodel_set.py | 16 | 水利模型参数设置 |
| hydromodel_baseinfo.py | 13 | 水利模型基础信息 |
| hydromodel_parget.py | 8 | 水利模型参数获取 |
| hydromodel_resultget.py | 24 | 水利模型结果获取 |
| damage_assess.py | 3 | 灾损评估避险转移 |
| station_lookup.py | - | 测站查询 |
| mcp_websearch.py | - | 网络搜索 |
| auth.py | - | 认证工具 |

**总计**：175+ 个工具

### 工具调用流程

```
Executor
    │
    ▼
ToolRegistry.execute(tool_name, params)
    │
    ▼
BaseTool._execute(**kwargs)
    │
    ▼
API调用 / 数据处理
    │
    ▼
ToolResult
```

## 状态定义

### AgentState 结构

**位置**：`src/agents/state.py`

```python
class AgentState(TypedDict):
    # 会话信息
    conversation_id: str
    user_id: str
    messages: List[Dict]

    # 意图分析结果
    intent_category: IntentCategory  # chat/knowledge/business
    business_sub_intent: BusinessSubIntent
    extracted_entities: Dict

    # 工作流匹配
    matched_workflow: Optional[str]
    workflow_confidence: float

    # 执行计划
    plan_steps: List[PlanStep]
    current_step_index: int

    # 执行结果
    execution_results: List[ExecutionResult]
    has_async_tasks: bool

    # RAG检索
    rag_context: str
    knowledge_base_used: str

    # 最终输出
    final_response: str
    output_type: OutputType  # text/web_page
    generated_page_url: Optional[str]
```

## 路由函数

### plan_router

根据意图类别决定下一步：
- `chat` → `quick_chat` 节点
- `knowledge` → `knowledge_rag` 节点
- `business` + 匹配工作流 → `workflow` 节点
- `business` + 无匹配 → `execute` 节点

### should_continue

根据执行状态决定下一步：
- 还有步骤未执行 → `execute`
- 有异步任务等待 → `wait_async`
- 需要重新规划 → `plan`
- 执行完成 → `respond`

## LLM调用日志

### 功能说明

**位置**：`src/config/llm_prompt_logger.py`

记录每次LLM调用的完整信息：
- 调用时间
- 调用步骤（意图分析、计划生成、响应合成等）
- 完整提示词
- LLM响应
- Token使用量

### 日志位置

`logs/llm_prompt.md`
