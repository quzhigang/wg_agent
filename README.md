# 卫共流域数字孪生智能体

基于Python 3.11和LangGraph框架开发的Plan-and-Execute智能体系统，用于卫共流域数字孪生系统。

## 功能特性

- **一般对话**：日常对话和流域相关知识问答
- **固有知识查询**：查询流域固有知识（9个知识库）
- **流域业务**：水雨情查询、洪水预报、洪水模拟、应急预案、灾损评估等

## 技术架构

### Plan-and-Execute架构

- **Planner（规划调度器）**：分析用户意图（三大类分类），匹配工作流，制定执行计划
- **Executor（任务执行器）**：执行工具调用，处理异步任务
- **Controller（结果合成器）**：整合结果，生成最终响应，决定输出类型

### 三大类意图分类

1. **chat（一般对话）**：问候、感谢、告别、闲聊、询问助手信息
2. **knowledge（固有知识查询）**：9个知识库的查询
   - catchment_basin（流域概况）、water_project（水利工程）、monitor_site（监测站点）
   - history_flood（历史洪水）、flood_preplan（防洪预案）、system_function（系统功能）
   - hydro_model（水文模型）、catchment_planning（流域规划）、project_designplan（工程设计）
3. **business（业务相关）**：data_query、flood_forecast、flood_simulation、emergency_plan、damage_assessment、other

### 核心模块

```
src/
├── agents/          # 智能体核心（state, planner, executor, controller, graph）
├── api/             # RESTful API接口（chat, pages, knowledge, saved_workflows, health）
├── config/          # 配置管理（settings, logging_config, llm_prompt_logger）
├── models/          # 数据模型（database, schemas）
├── tools/           # 工具模块（12个工具模块，175+个工具）
├── workflows/       # 工作流模块（预定义工作流、向量化索引）
├── rag/             # RAG知识库（knowledge_base, retriever）
└── output/          # Web页面生成（templates, page_generator, async_page_agent）
```

### 其他目录

```
wg_agent/
├── web/             # Web前端资源（web_templates, main, generated_pages）
├── PageIndex/       # 知识库系统（独立模块，可选启动）
├── workflow_vectors/# 工作流向量化存储
├── logs/            # 日志目录（wg_agent.log, llm_prompt.md）
├── scripts/         # 脚本工具
└── 开发资料/         # 开发文档资料
```

## 安装

### 1. 环境要求

- Python 3.11+
- MySQL 5.7+（可选，默认使用SQLite）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制`.env.example`为`.env`并修改配置：

```bash
cp .env.example .env
```

主要配置项：

```env
# LLM配置
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_API_KEY=your_api_key

# 数据库配置
DATABASE_URL=sqlite:///./wg_agent.db

# API配置
API_HOST=0.0.0.0
API_PORT=8000
```

## 运行

### 启动服务

```bash
# 启动主程序
python -m src.main

# 可选：启动PageIndex知识库服务（独立运行，非必需）
python PageIndex/api.py
```

> 注意：PageIndex是独立的知识库模块，主程序可以独立运行。

### 停止服务

```bash
taskkill /F /IM python.exe
```

### 访问地址

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 智能体主页面: http://localhost:8000/ui/index.html
- 动态流程管理页面: http://localhost:8000/ui/saved_workflows.html

## API接口

### 对话接口

```http
POST /chat
Content-Type: application/json

{
    "message": "查询卫共流域的基本信息",
    "user_id": "user123",
    "conversation_id": null
}
```

### 流式对话

```http
POST /chat/stream
Content-Type: application/json

{
    "message": "进行洪水预报",
    "user_id": "user123"
}
```

### 知识库管理

```http
# 搜索知识库
POST /knowledge/search
{
    "query": "防洪预警等级",
    "top_k": 5
}

# 添加知识
POST /knowledge/documents
{
    "content": "知识内容...",
    "category": "流域概况"
}
```

### 页面管理

```http
# 获取生成的页面列表
GET /pages

# 获取具体页面
GET /pages/{filename}
```

### 动态流程管理

```http
# 获取流程清单（分页）
GET /saved-workflows?page=1&size=20&sub_intent=data_query

# 获取流程详情
GET /saved-workflows/{id}

# 编辑流程
PUT /saved-workflows/{id}
{
    "name": "新名称",
    "description": "新描述",
    "is_active": true
}

# 删除流程
DELETE /saved-workflows/{id}

# 启用/禁用流程
PATCH /saved-workflows/{id}/toggle
```

管理页面：`/ui/saved_workflows.html`

## 工具系统（共12个模块，175+个工具）

### 工具注册机制

所有工具都实现了自动注册机制：

1. **工具定义**：每个工具继承 `BaseTool` 基类，实现 `name`、`description`、`category` 和 `execute()` 方法
2. **工具注册**：使用 `register_tool()` 函数将工具实例注册到全局 `ToolRegistry`
3. **自动初始化**：在 `src/tools/registry.py` 的 `init_default_tools()` 函数中导入所有工具模块，触发自动注册
4. **工具调用**：通过 `ToolRegistry` 的 `execute()` 方法执行工具

### 工具分类（按功能）

1. **流域基本信息工具** (`basin_info.py`, 14个)
   - 地图数据源查询、水库基础信息、水闸堰信息、蓄滞洪区、河道防洪特征值、测站列表、视频监控、遥感任务

2. **水雨情监测工具** (`hydro_monitor.py`, 15个)
   - 雨量监测、水库水情、河道水情、AI智能监测、视频预览、传感器数据、无人机状态、告警短信

3. **模型及方案管理工具** (`modelplan_control.py`, 20个)
   - 模拟方案管理、基础模型管理、模型实例管理、业务模型管理

4. **降雨获取设置工具** (`rain_control.py`, 33个)
   - 格网降雨预报、降雨等值面、降雨监测更新、设计暴雨、方案降雨查询、方案降雨设置

5. **其他洪水业务工具** (`flood_otherbusiness.py`, 29个)
   - 产流洪水结果、淹没分析、防汛预案、水雨情态势、闸站工情、MIKE模型辅助

6. **水利专业模型工具** (4个模块，61个)
   - `hydromodel_set.py` - 模型参数设置和方案新建（16个）
   - `hydromodel_baseinfo.py` - 模型基础信息获取（13个）
   - `hydromodel_parget.py` - 模型参数及边界条件获取（8个）
   - `hydromodel_resultget.py` - 模型方案及结果数据获取（24个）

7. **灾损评估避险转移工具** (`damage_assess.py`, 3个)
   - 洪涝灾害损失计算、避险安置点、转移路线

8. **其他工具**
   - `auth.py` - 认证工具
   - `station_lookup.py` - 测站查询工具
   - `mcp_websearch.py` - 网络搜索工具

## 工作流系统

### 预定义工作流

位于 `src/workflows/` 目录：

- `flood_autoforecast_getresult.py` - 自动预报结果获取
- `flood_manualforecast_getresult.py` - 手动预报结果获取
- `get_autoforecast_result.py` - 获取自动预报结果
- `get_history_autoforecast_result.py` - 获取历史预报结果
- `get_manualforecast_result.py` - 获取手动预报结果

### 工作流向量化索引

`workflow_vector_index.py` 实现工作流的向量化存储和检索，支持：
- 工作流向量化保存
- 向量检索匹配（置信度阈值≥0.75）
- 动态工作流自动保存

### 动态流程自动保存机制

触发条件：
- 动态规划成功生成计划
- 计划步骤数 >= 2
- 意图类别为 business

保存内容：
- 流程名称、触发模式、意图类别、子意图
- 实体提取模式、完整执行步骤、输出类型

## 项目结构

```
wg_agent/
├── src/
│   ├── __init__.py
│   ├── main.py                       # FastAPI主入口
│   ├── agents/                       # 智能体核心
│   │   ├── state.py                 # 状态定义（AgentState, IntentCategory, PlanStep等）
│   │   ├── planner.py               # 规划调度器（意图分析、工作流匹配、计划生成）
│   │   ├── executor.py              # 任务执行器（工具调用、异步处理）
│   │   ├── controller.py            # 结果合成器（响应生成、页面输出）
│   │   └── graph.py                 # LangGraph状态图（工作流编排）
│   ├── api/                          # API接口
│   │   ├── health.py                # 健康检查
│   │   ├── chat.py                  # 对话接口（/chat, /chat/stream）
│   │   ├── pages.py                 # 页面服务
│   │   ├── knowledge.py             # 知识库管理
│   │   └── saved_workflows.py       # 动态流程管理
│   ├── config/                       # 配置
│   │   ├── settings.py              # 配置管理
│   │   ├── logging_config.py        # 日志配置
│   │   └── llm_prompt_logger.py     # LLM调用日志记录
│   ├── models/                       # 数据模型
│   │   ├── database.py              # SQLAlchemy数据库模型
│   │   └── schemas.py               # Pydantic验证模型
│   ├── tools/                        # 工具模块（12个模块，175+个工具）
│   │   ├── base.py                  # 工具基类和类别定义
│   │   ├── registry.py              # 工具注册表（单例模式）
│   │   ├── basin_info.py            # 流域基本信息工具
│   │   ├── hydro_monitor.py         # 水雨情监测工具
│   │   ├── rain_control.py          # 降雨相关业务工具
│   │   ├── modelplan_control.py     # 模型及方案管理工具
│   │   ├── flood_otherbusiness.py   # 防洪业务其他工具
│   │   ├── damage_assess.py         # 灾损评估工具
│   │   ├── hydromodel_set.py        # 水利模型参数设置
│   │   ├── hydromodel_baseinfo.py   # 水利模型基础信息
│   │   ├── hydromodel_parget.py     # 水利模型参数获取
│   │   ├── hydromodel_resultget.py  # 水利模型结果获取
│   │   ├── station_lookup.py        # 测站查询工具
│   │   ├── auth.py                  # 认证工具
│   │   └── mcp_websearch.py         # 网络搜索工具
│   ├── workflows/                    # 工作流
│   │   ├── base.py                  # 工作流基类
│   │   ├── registry.py              # 工作流注册表
│   │   ├── workflow_vector_index.py # 工作流向量化索引
│   │   └── *.py                     # 预定义工作流
│   ├── output/                       # 输出模块
│   │   ├── templates.py             # 页面模板
│   │   ├── page_generator.py        # 页面生成器
│   │   └── async_page_agent.py      # 异步页面生成代理
│   └── rag/                          # RAG模块
│       ├── knowledge_base.py        # 知识库管理
│       └── retriever.py             # 检索器
├── web/                              # Web前端
│   ├── web_templates/               # 页面模板和资源
│   ├── main/                        # 主界面
│   └── generated_pages/             # 生成的页面
├── PageIndex/                        # 知识库系统（独立模块）
│   ├── knowledge_bases/             # 知识库数据
│   ├── chroma_db/                   # 向量数据库
│   └── pageindex/                   # PageIndex核心模块
├── workflow_vectors/                 # 工作流向量化存储
├── logs/                             # 日志目录
├── scripts/                          # 脚本工具
├── requirements.txt                  # Python依赖
├── .env.example                      # 环境变量示例
├── work_flow.md                      # 工作流说明文档
└── README.md                         # 项目说明
```

## 开发说明

### 添加新工具

1. 在`src/tools/`下创建新的工具文件或在现有文件中添加
2. 继承`BaseTool`类实现工具逻辑
3. 在模块末尾注册工具

```python
from .base import BaseTool, ToolCategory
from .registry import register_tool

class MyNewTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_new_tool"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO

    async def _execute(self, **kwargs) -> Dict[str, Any]:
        # 实现工具逻辑
        return {"result": "data"}

# 注册工具
register_tool(MyNewTool())
```

### 添加新工作流

1. 在`src/workflows/`下创建新的工作流文件
2. 继承`BaseWorkflow`类定义工作流
3. 在模块末尾注册工作流

```python
from .base import BaseWorkflow, WorkflowStep
from .registry import register_workflow

class MyWorkflow(BaseWorkflow):
    @property
    def name(self) -> str:
        return "my_workflow"

    @property
    def steps(self) -> List[WorkflowStep]:
        return [
            WorkflowStep(step_id=1, name="Step 1", tool_name="tool1"),
            # ...
        ]

    async def execute(self, state):
        # 执行逻辑
        pass

register_workflow(MyWorkflow())
```

## 许可证

MIT License
