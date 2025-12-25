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

### 停止服务
taskkill /F /IM python.exe

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

## 工具系统（共7类模块，175个工具）

### 工具注册机制

所有工具都实现了自动注册机制：

1. **工具定义**：每个工具继承 `BaseTool` 基类，实现 `name`、`description`、`category` 和 `execute()` 方法
2. **工具注册**：使用 `register_tool()` 函数将工具实例注册到全局 `ToolRegistry`
3. **自动初始化**：在 `src/tools/registry.py` 的 `init_default_tools()` 函数中导入所有工具模块，触发自动注册
4. **工具调用**：通过 `ToolRegistry` 的 `execute()` 方法执行工具

### 工具分类（按功能）

1. **流域基本信息工具** (14个接口)
   - 地图数据源查询（地理要素的空间坐标）
   - 水库基础信息及防洪特征值
   - 水闸堰基础信息
   - 蓄滞洪区信息
   - 河道防洪特征值
   - 测站列表
   - 视频监控及无人机
   - 遥感任务管理

2. **水雨情监测工具** (15个接口)
   - 雨量监测（过程、统计、累计）
   - 水库水情（最新、历史过程）
   - 河道水情（最新、历史过程）
   - AI智能监测（水情、雨量）
   - 视频监控预览
   - 传感器数据
   - 无人机设备状态
   - 告警短信发送

3. **模型及方案管理业务工具** (20个)
   - 模拟方案管理(12个)
   - 基础模型管理(3个)
   - 模型实例管理（2个）
   - 业务模型管理（3个）

4. **降雨获取设置相关工具** (33个)
   - 格网降雨预报（流域平均、各子流域、矩形区域）(5个)
   - 降雨等值面（当日、任意时段、方案、图片）(7个)
   - 降雨监测更新(2个)
   - 设计/典型暴雨雨型管理(7个)
   - 方案降雨查询（各流域、统计、等值面）(7个)
   - 方案降雨设置（手动、中心区域、导入）(5个)

5. **其他洪水业务工具** (29个)
   - 子流域产流洪水结果查询
   - 洪水淹没分析（新增、计算、查询GIS结果）
   - 防汛预案管理（列表、新增、删除、查看）
   - 水雨情态势研判（实时水情、形势统计、纳蓄能力）
   - 闸站工情
   - MIKE模型辅助工具（产流、水库、控制建筑物、库容曲线、计算Pa值等）

6. **水利专业模型工具** (4个模块61个接口)
   - 模型参数设置和方案新建(16个)
   - 模型相关基础信息获取(13个)
   - 模型参数及边界条件获取(8个)
   - 模型方案及结果数据获取(24个)

7. **灾损评估避险转移工具**(3个接口)
   - 洪涝灾害损失计算
   - 避险安置点列表查询
   - 转移路线列表查询

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
│   ├── tools/                  # 工具模块（10个工具模块，100+个工具）
│   │   ├── base.py            # 工具基类和工具类别定义
│   │   ├── registry.py        # 工具注册表（单例模式）
│   │   ├── basin_info.py      # 流域基本信息工具（14个）
│   │   ├── hydro_monitor.py   # 水雨情监测工具（15个）
│   │   ├── rain_control.py    # 降雨相关业务工具（32个）
│   │   ├── modelplan_control.py     # 模型及方案管理工具
│   │   ├── flood_otherbusiness.py   # 防洪业务其他工具（29个）
│   │   ├── damage_assess.py   # 灾损评估工具
│   │   ├── hydromodel_set.py  # 水利模型参数设置工具
│   │   ├── hydromodel_baseinfo.py   # 水利模型基础信息工具
│   │   ├── hydromodel_parget.py     # 水利模型参数获取工具
│   │   └── hydromodel_resultget.py  # 水利模型结果获取工具
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
