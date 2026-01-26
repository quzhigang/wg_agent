# CLAUDE.md - 卫共流域数字孪生智能体项目

## 项目概述

这是一个基于 LangGraph 框架的 Plan-and-Execute 智能体系统，用于河南省卫共流域数字孪生系统的防洪业务支撑，使其具备一般对话、流域特有知识问答、流域基础数据和实时监测数据查询、通过接口调用实现洪水预报预演及预案生成等业务功能，通过判断会话内容，输出符合用户需求的结果。

## 技术栈

- **语言**: Python 3.11+
- **智能体框架**: LangGraph (>=0.2.0) + LangChain (>=0.3.0)
- **Web框架**: FastAPI (>=0.115.0) + Uvicorn
- **数据库**: MySQL 5.7+ (主要) / SQLite (备选)
- **ORM**: SQLAlchemy (>=2.0.0)
- **向量数据库**: ChromaDB (>=0.5.0)
- **向量模型**: sentence-transformers (bge-m3)
- **日志**: loguru (>=0.7.0)
- **数据验证**: Pydantic (>=2.9.0)

## 项目结构

```
wg_agent/
├── src/                    # 核心应用代码
│   ├── main.py            # FastAPI 主入口
│   ├── agents/            # 智能体核心 (planner/executor/controller/graph)
│   ├── api/               # RESTful API 接口
│   ├── config/            # 配置管理
│   ├── models/            # 数据模型 (SQLAlchemy + Pydantic)
│   ├── tools/             # 工具模块 (175+ 个工具)
│   ├── workflows/         # 工作流模块
│   ├── output/            # 页面输出模块
│   └── rag/               # RAG 知识库模块
├── web/                   # Web 前端资源
├── PageIndex/             # 知识库系统 (独立模块)
├── workflow_vectors/      # 工作流向量化存储
├── logs/                  # 日志目录
└── scripts/               # 脚本工具
```

## 核心模块说明

### 智能体架构 (src/agents/)

采用 Plan-and-Execute 模式，四大节点：
- **Planner** (`planner.py`): 意图分析、工作流匹配、计划生成
- **Executor** (`executor.py`): 工具调用执行
- **Controller** (`controller.py`): 响应合成、页面生成
- **Graph** (`graph.py`): LangGraph 状态图编排

### 意图分类

三大类意图：
1. `chat` - 一般对话 → quick_chat 节点
2. `knowledge` - 知识查询 → RAG 检索节点
3. `business` - 业务相关 → 工作流匹配/动态规划

业务子意图：`data_query` / `flood_forecast` / `flood_simulation` / `emergency_plan` / `damage_assessment` / `other`

### 工具系统 (src/tools/)

- 工具继承 `BaseTool` 基类
- 实现 `name`、`description`、`category`、`execute()` 方法
- 使用 `register_tool()` 注册到 `ToolRegistry`

### 工作流系统 (src/workflows/)

- 工作流继承 `BaseWorkflow` 基类
- 支持向量化检索匹配 (置信度阈值 ≥0.75)
- 支持动态流程自动保存

## 常用命令

```bash
# 启动主服务
python -m src.main

# 启动知识库 API (可选)
python PageIndex/api.py

# 启动知识库 Streamlit UI (可选)
streamlit run PageIndex/app.py
```

## 访问地址

- API 文档: http://localhost:8000/docs
- 主界面: http://localhost:8000/ui/index.html
- 流程管理: http://localhost:8000/ui/saved_workflows.html

## 配置文件

- `.env` - 环境变量配置 (API密钥、数据库连接等)
- `src/config/settings.py` - 全局配置类

主要配置项：
- LLM 配置 (支持各节点独立配置)
- MySQL 数据库连接
- ChromaDB 向量库路径
- 外部 API 服务地址

## 代码规范

- 使用中文注释
- 函数命名: `snake_case`
- 类命名: `PascalCase`
- 异步函数使用 `async/await`
- 使用 `loguru` 进行日志记录
- 使用 Pydantic 进行数据验证

## 数据库表

- `conversations` - 会话表
- `messages` - 消息历史表
- `async_tasks` - 异步任务表
- `generated_pages` - 生成页面缓存表
- `saved_workflows` - 自动保存的动态流程表
- `tool_call_logs` - 工具调用日志表

## 知识库 (PageIndex/)

9 个知识库：
- `catchment_basin` - 流域概况
- `water_project` - 水利工程
- `monitor_site` - 监测站点
- `history_flood` - 历史洪水
- `flood_preplan` - 防洪预案
- `system_function` - 系统功能
- `hydro_model` - 水文模型
- `catchment_planning` - 流域规划
- `project_designplan` - 工程设计

## 注意事项

- 不要直接修改 `PageIndex/knowledge_bases/` 下的 ChromaDB 数据库文件
- 不要修改 `workflow_vectors/` 下的向量索引文件
- 添加新工具时需在对应模块中调用 `register_tool()` 注册
- 添加新工作流时需在 `workflows/registry.py` 中注册
- API 响应统一使用 Pydantic 模型包装
- 工具的 `execute()` 方法应返回字典格式结果
- 日志文件位于 `logs/` 目录
- 给出的修改计划要注意全局性，不要就事论事，把特定功能的流程、提示词当成通用的，要考虑全局适应性。

## 外部系统集成

- `.NET 模型服务` - 水文模型计算 (`wg_model_server_url`)
- `基础数据服务` - 工程基础数据 (`wg_data_server_url`)
- `防洪业务服务` - Java Spring Boot 接口 (`wg_flood_server_url`)

## 参考文档

在处理特定领域时请阅读这些文档：

| 文档 | 何时阅读 |
|----------|--------------|
| `.claude/PRD.md` | 了解需求、功能、API 规范 |
