# PageIndex

PageIndex 是一个专门用于从 PDF和md文档中提取高精度、层级化目录结构（Table of Contents, TOC）的 Python 库。它为检索增强生成（RAG）场景提供了"无需向量（Vectorless）"的全新思路，通过对文档结构的深度理解，实现更符合人类阅读习惯的精准检索与推理。

## 核心特性

- **高精度目录提取**：利用 LLM 智能解析PDF和MD文档，不仅能提取原有的目录，还能为没有目录的文档自动生成层级结构。
- **物理页面映射**：将层级标题精确映射到 PDF和MD文档 的物理页码，确保检索定位的准确性。
- **多知识库管理**：支持创建多个独立知识库，每个知识库有独立的文档存储和向量索引。
- **结构化摘要**：为每个节点生成中文摘要（summary）和关键描述点（key_points），提升向量匹配精度。
- **混合检索**：结合向量检索的速度优势和目录树结构的上下文优势，实现毫秒级精准检索。
- **灵活的配置**：支持添加节点 ID、摘要、全文内容以及文档整体描述。

## 快速开始

### 安装

```bash
cd PageIndex
pip install -r requirements.txt
```

### 环境配置

复制 `.env.example` 为 `.env` 并配置以下环境变量：

```bash
# 大模型 API 配置
CHATGPT_API_KEY=sk-9JMYkWWXziidMbCTiePVvgfxsCobO0wldI5hLYSNBxTwlt4o
CHATGPT_API_BASE=https://newapi.xiaochuang.cc/v1
CHATGPT_MODEL=gemini-3-flash-preview  # 大模型名称

# Embedding 模型配置 (用于向量检索)
EMBEDDING_MODEL_NAME=bge-m3:latest
EMBEDDING_MODEL_API_URL=http://localhost:11434
EMBEDDING_MODEL_TYPE=ollama

# ChromaDB 向量数据库存储路径
CHROMA_PERSIST_DIR=./chroma_db
```

## 网页界面 (UI) 与 API

PageIndex 提供了直观的 Streamlit 网页界面以及 REST API，方便进行文档处理和自动化集成。

### 启动方式

```bash
cd PageIndex

# 网页界面启动
streamlit run app.py

# REST API 服务启动
python api.py
```

### 访问地址

- 前端页面：http://localhost:8501/
- API 文档：http://localhost:8502/docs （Swagger UI）

### 主要功能

- **文档处理**：支持 PDF/Markdown 文件批量上传、自动解析目录、生成摘要及物理页码映射。
- **多知识库管理**：创建、管理多个独立知识库，支持跨知识库检索。
- **智能对话 (RAG)**：
    - **跨知识库检索**：自动在多个知识库中检索相关内容。
    - **精准定位**：基于 PageIndex 的层级结构，直接定位到具体章节或页面。
    - **推理原生回答**：整合多处上下文，给出引经据典的详细回答。

---

## REST API 使用说明

启动 `api.py` 后，API 服务运行在 **8502** 端口。

### 一、知识库管理接口

#### 1. 列出所有知识库
- **Endpoint**: `GET /kb/list`
- **返回**: 所有知识库列表及统计信息

```bash
curl -X GET "http://localhost:8502/kb/list"
```

**响应示例**:
```json
{
  "status": "ok",
  "total": 2,
  "knowledge_bases": [
    {
      "id": "default",
      "name": "默认知识库",
      "description": "系统默认知识库",
      "doc_count": 5,
      "node_count": 120
    }
  ]
}
```

#### 2. 创建知识库
- **Endpoint**: `POST /kb/create`
- **Body**:
```json
{
  "id": "my_kb",
  "name": "我的知识库",
  "description": "知识库描述（可选）"
}
```

```bash
curl -X POST "http://localhost:8502/kb/create" \
  -H "Content-Type: application/json" \
  -d '{"id": "my_kb", "name": "我的知识库", "description": "测试知识库"}'
```

#### 3. 获取知识库详情
- **Endpoint**: `GET /kb/{kb_id}`

```bash
curl -X GET "http://localhost:8502/kb/default"
```

#### 4. 删除知识库
- **Endpoint**: `DELETE /kb/{kb_id}`

```bash
curl -X DELETE "http://localhost:8502/kb/my_kb"
```

---

### 二、多知识库检索接口

#### 1. 智能问答接口（带大模型生成答案）
- **Endpoint**: `POST /query`
- **Body**:
```json
{
  "q": "用户的问题",
  "top_k": 10,
  "kb_ids": ["kb1", "kb2"]  // 可选，为空或不传则搜索所有知识库
}
```

```bash
# 搜索所有知识库
curl -X POST "http://localhost:8502/query" \
  -H "Content-Type: application/json" \
  -d '{"q": "什么是PageIndex？", "top_k": 10}'

# 搜索指定知识库
curl -X POST "http://localhost:8502/query" \
  -H "Content-Type: application/json" \
  -d '{"q": "什么是PageIndex？", "top_k": 10, "kb_ids": ["your_kb_id"]}'
```

**响应示例**:
```json
{
  "answer": "PageIndex 是一个用于从 PDF 文档中提取层级化目录结构的工具...",
  "sources": [
    "[默认知识库] 文档名 - 章节标题 (相似度: 0.892)"
  ],
  "thinking": "在 2 个知识库中检索，返回 5 个相关节点",
  "searched_kb": ["default", "my_kb"]
}
```

#### 2. 原始检索结果接口（不调用大模型）
- **Endpoint**: `POST /query/raw`
- **Body**: 同上

```bash
# 搜索所有知识库（不指定 kb_ids）
curl -X POST "http://localhost:8502/query/raw" \
  -H "Content-Type: application/json" \
  -d '{"q": "什么是PageIndex？", "top_k": 10}'

# 搜索指定知识库（kb_ids 为知识库ID列表，需先通过 /kb/list 获取）
curl -X POST "http://localhost:8502/query/raw" \
  -H "Content-Type: application/json" \
  -d '{"q": "什么是PageIndex？", "top_k": 10, "kb_ids": ["your_kb_id"]}'
```

**响应示例**:
```json
{
  "status": "ok",
  "query": "什么是PageIndex？",
  "searched_kb": ["default"],
  "total_results": 5,
  "results": [
    {
      "kb_id": "default",
      "kb_name": "默认知识库",
      "doc_name": "PageIndex文档",
      "node_id": "0001",
      "title": "1. 简介",
      "score": 0.892,
      "summary": "PageIndex 简介与核心功能",
      "text": "完整的章节内容...",
      "images": []
    }
  ]
}
```

---

### 三、索引管理接口

#### 1. 获取知识库索引统计
- **Endpoint**: `GET /kb/{kb_id}/index/stats`

```bash
curl -X GET "http://localhost:8502/kb/default/index/stats"
```

**响应示例**:
```json
{
  "status": "ok",
  "stats": {
    "total_nodes": 120,
    "total_documents": 5,
    "documents": ["文档1", "文档2"]
  }
}
```

#### 2. 重建知识库索引
- **Endpoint**: `POST /kb/{kb_id}/index/rebuild`

```bash
curl -X POST "http://localhost:8502/kb/default/index/rebuild"
```

**响应示例**:
```json
{
  "status": "ok",
  "kb_id": "default",
  "rebuilt_documents": 5,
  "errors": null
}
```

#### 3. 删除文档索引
- **Endpoint**: `DELETE /kb/{kb_id}/index/{doc_name}`

```bash
curl -X DELETE "http://localhost:8502/kb/default/index/我的文档"
```

---

### 四、兼容旧版接口（单知识库）

以下接口用于兼容旧版单知识库模式，操作默认的 `./PageIndex/results` 目录：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/index/stats` | GET | 获取向量索引统计信息 |
| `/index/rebuild` | POST | 重建所有文档的向量索引 |
| `/index/{doc_name}` | DELETE | 删除指定文档的向量索引 |

---

## 项目结构

```
PageIndex/
├── pageindex/              # 核心代码库
│   ├── page_index.py       # PDF 文档处理
│   ├── page_index_md.py    # Markdown 文档处理
│   ├── vector_index.py     # 向量索引（支持多知识库）
│   ├── kb_manager.py       # 知识库管理器
│   └── utils.py            # 工具函数（含摘要生成）
├── knowledge_bases/        # 多知识库配置存储
├── chroma_db/              # ChromaDB 向量数据库
├── app.py                  # Streamlit 网页界面
├── api.py                  # FastAPI REST 接口
└── requirements.txt        # 依赖包
```

---

## 技术细节

### 文档处理流程

1. **TOC 检测**：识别文档是否自带目录
2. **结构转换**：将原始文本目录转换为结构化的 JSON 数据
3. **偏移修正**：自动计算物理页码与逻辑页码之间的偏移
4. **层级递归补全**：对于缺失目录的部分，通过 LLM 递归生成细分层级
5. **摘要生成**：为每个节点生成结构化摘要（summary + key_points）

### 节点数据结构

```json
{
  "node_id": "0016",
  "title": "1. 地图数据源查询接口",
  "summary": "地图数据源查询接口技术规范",
  "key_points": [
    "支持GeoJSON格式",
    "REST API接口调用",
    "返回河流、湖泊等水文要素数据"
  ],
  "start_index": 84,
  "end_index": 127,
  "text": "完整章节内容..."
}
```

### 向量化策略

每个节点生成多条向量，提升检索精度：
- **主向量**: `{title}: {summary}`
- **细分向量**: `{title}: {key_point}` （每个 key_point 单独向量化）

检索时自动按 node_id 去重，保留最高分结果。

---

## 检索原理对比

### 三种检索方式对比

| 特性 | 传统向量检索 | PageIndex 原版（Vectorless） | 当前方案（混合检索） |
|------|-------------|---------------------------|-------------------|
| 索引方式 | 文档切片 → 向量化 | 文档 → 目录树结构 | 目录树 + 节点向量 |
| 检索方式 | 向量相似度匹配 | LLM 推理定位 | 向量召回 + 结构定位 |
| Token 消耗 | 0（检索阶段） | 高（每次查询需多次 LLM 调用） | 0（检索阶段） |
| 检索速度 | 毫秒级 | 秒级（依赖 LLM 响应） | 毫秒级 |
| 上下文保留 | 差（切片破坏上下文） | 优（保留文档层级结构） | 优（保留结构信息） |
| 语义理解 | 浅层（向量相似度） | 深层（LLM 推理） | 中等（向量 + 摘要） |

### 当前混合检索流程

```
用户查询
    ↓
1. 查询文本向量化
    ↓
2. 向量检索 Top-K 相关节点
   （基于 title + summary + key_points 的向量）
    ↓
3. 按 node_id 去重，保留最高分
    ↓
4. 根据节点的 start_index/end_index 提取原文
    ↓
5. LLM 生成最终答案
```

### 关键优势

- **检索速度快**：毫秒级响应
- **检索阶段不消耗 Token**
- **保留文档层级结构信息**
- **每个节点有完整上下文**（不是随机切片）
- **key_points 细分向量提升匹配精度**
