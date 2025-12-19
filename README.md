# 卫共流域数字孪生智能体

基于Python 3.11和LangGraph框架开发的Plan-and-Execute智能体系统，用于卫共流域数字孪生系统。

## 功能特性

- **一般对话**：日常对话和流域相关知识问答
- **流域数据查询**：基础数据和实时监测数据查询
- **洪水预报预演**：洪水预报模型调用和结果分析
- **预案生成**：应急响应预案自动生成

## 技术架构

### Plan-and-Execute架构

- **Planner（规划调度器）**：分析用户意图，制定执行计划
- **Executor（任务执行器）**：执行工具调用，处理异步任务
- **Controller（结果合成器）**：整合结果，生成最终响应

### 核心模块

- `agents/` - 智能体核心（Planner, Executor, Controller, Graph）
- `tools/` - 工具模块（5类API工具）
- `workflows/` - 固定工作流
- `rag/` - RAG知识库
- `output/` - Web页面生成
- `api/` - RESTful API接口
- `models/` - 数据模型
- `config/` - 配置管理

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
python -m src.main
```

或使用uvicorn：

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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

## 工具分类

1. **流域基本信息** (basin_info)
   - 获取流域信息
   - 获取河流信息
   - 获取水利工程信息

2. **水雨情监测** (hydro_monitor)
   - 查询水位数据
   - 查询雨量数据
   - 查询流量数据

3. **防洪业务** (flood_control)
   - 运行洪水预报
   - 获取预报结果
   - 生成应急预案

4. **水利模型** (hydro_model)
   - 运行水文模型
   - 运行水动力模型

5. **灾损评估** (damage_assess)
   - 评估洪水灾损
   - 获取脆弱性数据

## 预定义工作流

- **洪水预报工作流** (flood_forecast)：完整的洪水预报流程
- **应急预案工作流** (emergency_plan)：应急响应预案生成

## 项目结构

```
wg_agent/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI主入口
│   ├── agents/                 # 智能体核心
│   │   ├── state.py           # 状态定义
│   │   ├── planner.py         # 规划器
│   │   ├── executor.py        # 执行器
│   │   ├── controller.py      # 控制器
│   │   └── graph.py           # LangGraph图
│   ├── api/                    # API接口
│   │   ├── health.py          # 健康检查
│   │   ├── chat.py            # 对话接口
│   │   ├── pages.py           # 页面服务
│   │   └── knowledge.py       # 知识库管理
│   ├── config/                 # 配置
│   │   ├── settings.py        # 配置管理
│   │   └── logging_config.py  # 日志配置
│   ├── models/                 # 数据模型
│   │   ├── database.py        # 数据库模型
│   │   └── schemas.py         # Pydantic模型
│   ├── tools/                  # 工具模块
│   │   ├── base.py            # 工具基类
│   │   ├── registry.py        # 工具注册表
│   │   ├── basin_info.py      # 流域信息工具
│   │   ├── hydro_monitor.py   # 水雨情工具
│   │   ├── flood_control.py   # 防洪业务工具
│   │   ├── hydro_model.py     # 水利模型工具
│   │   └── damage_assess.py   # 灾损评估工具
│   ├── workflows/              # 工作流
│   │   ├── base.py            # 工作流基类
│   │   ├── registry.py        # 工作流注册表
│   │   └── flood_forecast.py  # 洪水预报工作流
│   ├── output/                 # 输出模块
│   │   ├── templates.py       # 页面模板
│   │   └── page_generator.py  # 页面生成器
│   └── rag/                    # RAG模块
│       ├── knowledge_base.py  # 知识库
│       └── retriever.py       # 检索器
├── requirements.txt            # Python依赖
├── .env.example               # 环境变量示例
└── README.md                  # 项目说明
```

## 开发说明

### 添加新工具

1. 在`src/tools/`下创建新的工具文件
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
