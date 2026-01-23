# 工具按需加载优化方案

## 一、背景与目标

### 当前问题
1. **一次性全量加载**：`generate_plan()` 方法通过 `_get_available_tools_description()` 获取所有工具的完整描述传给LLM
2. **Token浪费**：每次计划生成都传递全部工具描述（约30+个工具），即使大部分工具与当前任务无关
3. **干扰决策**：过多无关工具描述可能干扰LLM的计划生成质量

### 优化目标
采用类似 Claude Skills 的**两阶段加载机制**：
1. **第一阶段（工具筛选）**：LLM根据工具摘要判断需要哪些工具
2. **第二阶段（详细加载）**：只加载被选中工具的完整定义

## 二、修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `src/tools/base.py` | 新增 `ToolSummary` 数据类和 `get_summary()` 方法 |
| `src/tools/registry.py` | 新增 `get_tools_summary()` 和 `get_tools_description_by_names()` 方法 |
| `src/agents/planner.py` | 新增工具筛选提示词、筛选链、`_select_relevant_tools()` 方法，修改 `generate_plan()` |

## 三、详细实现方案

### 3.1 修改 `src/tools/base.py`

**新增 ToolSummary 数据类**（在 `ToolResult` 类之后）：

```python
class ToolSummary(BaseModel):
    """工具摘要（用于第一阶段筛选）"""
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述（完整保留，不截断）")
    category: ToolCategory = Field(..., description="工具类别")
```

**在 BaseTool 类中新增方法**（在 `get_definition()` 方法之后）：

```python
def get_summary(self) -> 'ToolSummary':
    """
    获取工具摘要（用于第一阶段筛选）

    Returns:
        工具摘要对象
    """
    return ToolSummary(
        name=self.name,
        description=self.description,
        category=self.category
    )
```

### 3.2 修改 `src/tools/registry.py`

**新增两个方法**（在 `get_tools_description()` 方法之后）：

```python
def get_tools_summary(self, category: Optional[ToolCategory] = None) -> str:
    """
    获取工具摘要列表（用于第一阶段筛选）

    摘要格式保留完整描述，便于LLM准确判断工具相关性

    Args:
        category: 可选的类别过滤

    Returns:
        格式化的工具摘要文本
    """
    tools = list(self._tools.values())
    if category:
        tools = [t for t in tools if t.category == category]

    summaries = []
    for tool in tools:
        summary = tool.get_summary()
        summaries.append(
            f"- {summary.name} [{summary.category.value}]: {summary.description}"
        )

    # 添加函数工具（如 search_knowledge）
    for name in self._tool_functions:
        if name not in self._tools:
            # 函数工具没有完整的摘要信息，使用简单格式
            summaries.append(f"- {name} [function]: 函数工具")

    return "\n".join(summaries) if summaries else "无可用工具"

def get_tools_description_by_names(self, tool_names: List[str]) -> str:
    """
    根据工具名称列表获取详细描述（用于第二阶段）

    Args:
        tool_names: 需要加载的工具名称列表

    Returns:
        格式化的工具详细描述
    """
    descriptions = []
    for i, name in enumerate(tool_names, 1):
        tool = self._tools.get(name)
        if tool:
            descriptions.append(f"{i}. {tool.get_prompt_description()}")
        elif name in self._tool_functions:
            # 函数工具使用简化描述
            descriptions.append(f"{i}. 工具名称: {name}\n描述: 函数工具\n类别: function\n参数:\n  无详细参数信息")

    return "\n".join(descriptions) if descriptions else "无可用工具"
```

### 3.3 修改 `src/agents/planner.py`

#### 3.3.1 新增工具筛选提示词（在 `OBJECT_TYPE_SYNTHESIS_PROMPT` 之后）

```python
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
```

#### 3.3.2 修改 `Planner.__init__` 方法

在 `self.sub_intent_chain` 初始化之后，新增工具筛选链：

```python
# 工具筛选LLM（使用workflow配置，与工作流匹配节点一致）
self.tool_select_prompt = ChatPromptTemplate.from_template(TOOL_SELECTION_PROMPT)
self.tool_select_chain = self.tool_select_prompt | workflow_llm | self.json_parser
```

#### 3.3.3 新增 `_select_relevant_tools` 方法（在 `_resolve_object_type` 方法之后）

```python
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
```

#### 3.3.4 修改 `generate_plan` 方法

修改 `generate_plan` 方法中获取工具描述的部分（约第1122-1123行）：

**原代码：**
```python
# 2. 获取可用工具描述
available_tools = self._get_available_tools_description()
```

**修改为：**
```python
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
```

## 四、数据流示意

```
用户消息 + 业务子意图 + 实体
        ↓
┌─────────────────────────────────┐
│  第一阶段：工具筛选              │
│  输入：工具摘要（名称+描述）      │
│  输出：selected_tools 列表       │
│  LLM配置：workflow_config        │
└─────────────────────────────────┘
        ↓
┌─────────────────────────────────┐
│  第二阶段：详细加载              │
│  输入：selected_tools            │
│  输出：完整工具描述（含参数）     │
└─────────────────────────────────┘
        ↓
┌─────────────────────────────────┐
│  计划生成                        │
│  输入：精简的工具描述            │
│  输出：执行计划                  │
└─────────────────────────────────┘
```

## 五、预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 工具描述Token数 | ~3000-5000（全部工具） | ~500-800（摘要）+ ~500-1500（选中工具） |
| LLM调用次数 | 1次（计划生成） | 2次（筛选 + 计划生成） |
| 总Token消耗 | 高 | 降低约30-50% |
| 计划生成准确性 | 一般（工具太多干扰） | 提升（聚焦相关工具） |

## 六、验证方案

1. **启动服务**：`python -m src.main`
2. **测试用例**：
   - 数据查询："盘石头水库当前水位" → 应筛选出 lookup_station_code, query_reservoir_last
   - 洪水预报："启动自动预报" → 应筛选出预报相关工具
   - 复合查询："修武站水位和雨量" → 应筛选出河道水情和雨量查询工具
3. **检查日志**：确认工具筛选步骤正常执行，查看筛选结果和理由
4. **对比Token消耗**：通过LLM日志对比优化前后的Token使用量
