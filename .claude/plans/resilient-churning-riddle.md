# 动态Web页面生成系统重构方案

## 一、需求概述

用户需要重构动态Web页面生成系统，满足以下5个需求：
1. **集中参数配置** - 在某个地方集中进行参数配置，方便作为模板供后续使用
2. **API优先** - 尽量采用接口调用的方式获取数据
3. **数据文件分离** - 无法通过接口获取的数据或需要二次处理的数据，单独写成.js文件
4. **智能布局** - 根据展示需求动态生成页面布局和选择合适的图表、地图等
5. **上下文收集** - 搜集本次对话的上下文数据，包括工具调用、参数、结果等

## 二、整体架构

**设计原则**：将布局选择和页面生成合并为一个LLM调用，减少延迟和复杂度。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           对话处理流程                                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  意图识别 → Planner → Executor → Controller                                  │
│       │          │          │          │                                    │
│       └──────────┴──────────┴──────────┘                                    │
│                         │                                                    │
│                         ▼                                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              ConversationContextCollector (新增)                     │   │
│  │  - 收集意图识别结果、执行计划、工具调用记录                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DynamicPageGenerator (新增)                          │
│                    【单次LLM调用完成布局选择+配置生成】                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  LLM: 分析数据特征 → 选择布局和组件 → 生成PAGE_CONFIG                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌──────────────────┐    ┌──────────────────┐                              │
│  │ DataFileGenerator│───▶│  页面目录生成     │                              │
│  │  (config.js等)   │    │                  │                              │
│  └──────────────────┘    └──────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           生成的页面目录结构                                  │
│  pages/dynamic_20260123_abc123/                                             │
│  ├── index.html          (从 dynamic_shell 复制)                            │
│  ├── config.js           (PAGE_CONFIG + API配置)                            │
│  ├── data.js             (静态数据/二次处理数据)                              │
│  └── js/                 (布局引擎和组件库)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 三、新建文件

### 3.1 ConversationContextCollector
**文件**: `src/utils/conversation_context_collector.py`

**职责**: 收集整个对话过程中的工具调用、参数、结果

**核心类**:
- `ToolCallRecord`: 工具调用记录数据类
- `ConversationContext`: 对话上下文数据结构
- `ConversationContextCollector`: 收集器主类

**关键方法**:
- `set_intent_result()`: 记录意图识别结果
- `set_plan()`: 记录执行计划
- `record_tool_call()`: 记录工具调用
- `to_frontend_format()`: 导出为前端可用格式（过滤敏感信息）

### 3.2 DynamicPageGenerator（合并布局选择和页面生成）
**文件**: `src/output/dynamic_page_generator.py`

**职责**: 使用单次LLM调用完成布局选择和PAGE_CONFIG生成，然后生成完整页面

**核心功能**:
1. **单次LLM调用**：分析数据特征 + 选择组件 + 生成PAGE_CONFIG
2. **生成数据文件**：config.js 和 data.js
3. **组装页面目录**：复制模板框架，写入配置文件

**LLM提示词设计要点**:
- 输入：用户问题、意图、实体、工具调用结果
- 输出：完整的PAGE_CONFIG JSON配置
- 组件选择规则：时序数据→Echarts、键值对→InfoCard、列表→SimpleTable

### 3.3 DataFileGenerator
**文件**: `src/output/data_file_generator.py`

**职责**: 生成config.js和data.js文件

**生成的文件**:
1. **config.js**: 包含PAGE_CONFIG配置
   - meta: 页面元信息
   - layout: 布局配置
   - components: 组件配置
   - api_config: API配置（URL、参数、认证）

2. **data.js**: 包含静态数据
   - 无法通过API获取的数据
   - 需要二次处理的数据
   - 使用 `window.PAGE_DATA = {...}` 格式

## 四、修改文件

### 4.1 src/agents/state.py
**修改内容**: 添加conversation_context字段
```python
class AgentState(TypedDict):
    # ... 现有字段 ...
    conversation_context: Optional[Dict[str, Any]]  # 新增
```

### 4.2 src/agents/executor.py
**修改内容**: 在工具执行后记录到ConversationContextCollector
```python
# 在 _execute_step 方法中，工具执行完成后添加：
if context_collector:
    context_collector.record_tool_call(
        tool_name=step.get("tool_name"),
        input_params=params,
        output_result=result,
        success=success,
        execution_time_ms=elapsed_ms,
        step_id=step.get("step_id"),
        step_description=step.get("description")
    )
```

### 4.3 src/agents/controller.py
**修改内容**:
1. 在synthesize_response中创建ConversationContextCollector
2. 调用DynamicPageGenerator生成页面
```python
async def synthesize_response(self, state: AgentState) -> Dict[str, Any]:
    # 创建上下文收集器
    collector = ConversationContextCollector(
        conversation_id=state.get('conversation_id', ''),
        user_message=state.get('user_message', '')
    )

    # 收集意图、计划、执行结果
    collector.set_intent_result(...)
    collector.set_plan(state.get('plan', []))
    # ... 从execution_results中提取工具调用记录 ...

    # 判断是否需要生成Web页面
    if await self._should_generate_web_page(state):
        # 使用新的DynamicPageGenerator
        generator = get_dynamic_page_generator()
        page_url = await generator.generate(
            conversation_context=collector.to_frontend_format()
        )
```

### 4.4 web/web_templates/dynamic_shell/js/components.js
**修改内容**: 增强组件的数据源处理能力
- 支持API参数模板替换 `{context.path}`
- 支持认证头注入
- 增加数据转换器机制

## 五、PAGE_CONFIG 配置格式

```json
{
  "meta": {
    "title": "盘石头水库洪水预报结果",
    "description": "基于最新降雨数据的洪水预报分析",
    "generated_at": "2026-01-23T10:30:00"
  },
  "layout": {
    "type": "grid",
    "rows": [
      { "height": "120px", "cols": ["summary_card", "status_card"] },
      { "height": "calc(100vh - 200px)", "cols": ["main_chart"] }
    ]
  },
  "components": {
    "summary_card": {
      "type": "InfoCard",
      "title": "预报摘要",
      "data_source": {
        "type": "context",
        "mapping": {
          "入库洪峰": "execution.tool_calls.0.output_result.Max_InQ",
          "最高水位": "execution.tool_calls.0.output_result.Max_Level"
        }
      }
    },
    "main_chart": {
      "type": "Echarts",
      "title": "入库出库过程",
      "chart_type": "line",
      "data_source": {
        "type": "api",
        "api_name": "flood_result"
      }
    }
  },
  "api_config": {
    "flood_result": {
      "url": "http://172.16.16.253/wg_modelserver/...",
      "method": "GET",
      "params": {
        "request_type": "get_tjdata_result",
        "request_pars": "{context.execution.tool_calls.forecast.output_result.planCode}"
      }
    }
  },
  "static_data": {
    "processed_rain": [...]
  },
  "context_data": { ... }
}
```

## 六、实施步骤

### 步骤1: 创建ConversationContextCollector
- 新建 `src/utils/conversation_context_collector.py`
- 实现ToolCallRecord、ConversationContext、ConversationContextCollector类
- 添加敏感信息过滤逻辑

### 步骤2: 创建DataFileGenerator
- 新建 `src/output/data_file_generator.py`
- 实现config.js生成逻辑
- 实现data.js生成逻辑
- 支持API配置模板替换

### 步骤3: 创建DynamicPageGenerator（含布局选择）
- 新建 `src/output/dynamic_page_generator.py`
- 实现单次LLM调用完成布局选择+PAGE_CONFIG生成
- 整合DataFileGenerator
- 实现页面目录生成逻辑
- 使用 `settings.get_page_gen_config()` 获取LLM配置

### 步骤4: 修改现有文件
- 修改 `src/agents/state.py` 添加字段
- 修改 `src/agents/executor.py` 记录工具调用
- 修改 `src/agents/controller.py` 集成新组件

### 步骤5: 增强前端组件
- 修改 `web/web_templates/dynamic_shell/js/components.js`
- 增强API数据源处理
- 添加数据转换器支持

## 七、验证方案

### 测试场景1: 水库洪水预报
1. 发送请求："盘石头水库洪水预报"
2. 验证：
   - ConversationContextCollector正确收集了login、query_stcd、forecast等工具调用
   - LayoutSelector生成了包含InfoCard和Echarts的布局
   - 生成的config.js包含正确的API配置
   - 页面能正确渲染并通过API获取数据

### 测试场景2: 多对象查询
1. 发送请求："查询盘石头水库和小南海水库的预报结果"
2. 验证：
   - 上下文收集器记录了多个对象的查询结果
   - 布局选择器生成了适合多对象展示的布局
   - 数据文件正确分离了各对象的数据

### 测试场景3: 知识库查询
1. 发送请求："什么是洪水预报？"
2. 验证：
   - 上下文收集器记录了检索结果
   - 布局选择器选择了适合文本展示的组件
   - 页面正确展示了知识库内容

## 八、关键文件路径

### 新建文件
- `src/utils/conversation_context_collector.py`
- `src/output/data_file_generator.py`
- `src/output/dynamic_page_generator.py`

### 修改文件
- `src/agents/state.py` - 添加 `conversation_context` 字段（注意：已有 `workflow_context` 字段可复用）
- `src/agents/executor.py` - 在工具执行后记录到收集器
- `src/agents/controller.py` - 集成新的页面生成流程
- `web/web_templates/dynamic_shell/js/components.js` - 增强数据源处理

### 参考文件
- `src/utils/workflow_context.py` - 现有上下文管理
- `src/utils/template_configurator.py` - 现有模板配置器
- `src/output/page_generator.py` - 现有页面生成器
- `src/config/settings.py` - 使用 `get_page_gen_config()` 获取LLM配置
- `web/web_templates/res_module/js/main.js` - API调用参考

## 九、与现有代码的集成点

### 9.1 复用现有字段
- `AgentState.workflow_context` - 已存在，可用于存储工作流执行上下文
- `AgentState.execution_results` - 已存在，包含所有步骤的执行结果
- `ExecutionResult` - 已包含 step_id, success, output, error, execution_time_ms

### 9.2 数据收集时机
1. **意图识别后** - 在 `intent_analyzer.py` 的 `analyze_intent()` 返回后收集
2. **计划生成后** - 在 `planner.py` 的 `create_plan()` 返回后收集
3. **每步执行后** - 在 `executor.py` 的 `execute_step()` 返回后收集
4. **响应合成前** - 在 `controller.py` 的 `synthesize_response()` 中汇总

### 9.3 ConversationContextCollector 与 WorkflowContext 的关系
- **WorkflowContext**: 工作流执行期间的数据传递，用于步骤间参数引用（如 `steps.login.token`）
- **ConversationContextCollector**: 对话级别的完整记录，用于页面生成和调试
- 两者可以合并：在 `synthesize_response` 中，将 `workflow_context` 的数据合并到 `ConversationContextCollector`

## 十、LLM配置

**说明**：布局选择已合并到页面生成节点，直接复用现有的 `get_page_gen_config()` 配置，无需新增LLM配置。

### 10.1 复用现有配置
DynamicPageGenerator 使用 `settings.get_page_gen_config()` 获取LLM配置：
- `page_gen_api_key` / `page_gen_api_base` / `page_gen_model_name`
- 未配置时自动回退到默认配置

### 10.2 PAGE_CONFIG生成提示词设计要点
- 输入：用户问题、意图、实体、工具调用结果（截断）
- 输出：PAGE_CONFIG JSON
- 组件选择规则：
  - 时序数据（InQ_Dic, Level_Dic等）→ Echarts折线图
  - 键值对（Max_InQ, Max_Level等）→ InfoCard
  - 列表数据 → SimpleTable
  - 地理坐标 → GISMap
  - 富文本/Markdown → HtmlContent

## 十一、错误处理和回退

### 11.1 LayoutSelector 失败回退
如果LLM调用失败或返回无效JSON，使用默认布局：
```python
def _get_default_layout(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """返回默认布局配置"""
    return {
        "meta": {"title": "查询结果", "generated_at": datetime.now().isoformat()},
        "layout": {"type": "grid", "rows": [{"cols": ["main_content"]}]},
        "components": {
            "main_content": {
                "type": "HtmlContent",
                "title": "结果",
                "data_source": {"type": "static_value", "value": "<p>数据加载中...</p>"}
            }
        },
        "context_data": context
    }
```

### 11.2 API调用失败处理
前端组件应处理API调用失败的情况，显示友好的错误提示。
