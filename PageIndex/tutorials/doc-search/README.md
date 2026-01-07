
## 多知识库文档搜索指南

PageIndex 支持多知识库管理和跨知识库文档检索。本指南介绍如何在多知识库环境中进行高效的文档搜索。

### 系统架构

当前系统采用多知识库架构，每个知识库拥有独立的：
- `uploads/` - 文档上传目录
- `results/` - 结构文件目录（存储 PageIndex 解析后的树结构）
- `chroma_db/` - 向量索引目录（基于 ChromaDB）

### 多知识库检索方式

对于需要跨多个文档和知识库搜索的用户，我们提供以下最佳实践工作流：

* [**按元数据搜索**](metadata.md): 适用于可以通过元数据区分的文档，利用知识库分类进行精准检索。
* [**按语义搜索**](semantics.md): 适用于具有不同语义内容或涵盖不同主题的文档，使用向量相似度检索。
* [**按描述搜索**](description.md): 适用于少量文档的轻量级策略，利用 LLM 生成的文档描述进行匹配。

### 快速开始

#### 1. 列出所有知识库

```python
import requests

response = requests.get("http://localhost:8502/kb/list")
print(response.json())
```

#### 2. 跨知识库查询

```python
import requests

# 在所有知识库中搜索
response = requests.post(
    "http://localhost:8502/query",
    json={
        "q": "你的查询问题",
        "top_k": 10
    }
)
print(response.json())

# 在指定知识库中搜索
response = requests.post(
    "http://localhost:8502/query",
    json={
        "q": "你的查询问题",
        "top_k": 10,
        "kb_ids": ["catchment_basin", "water_project"]
    }
)
print(response.json())
```

#### 3. 获取原始检索结果（不调用 LLM）

```python
import requests

response = requests.post(
    "http://localhost:8502/query/raw",
    json={
        "q": "你的查询问题",
        "top_k": 10
    }
)
# 返回检索到的节点信息，包含文本、摘要和图片路径
print(response.json())
```

### API 接口一览

| 接口 | 方法 | 说明 |
|------|------|------|
| `/kb/list` | GET | 列出所有知识库 |
| `/kb/create` | POST | 创建新知识库 |
| `/kb/{kb_id}` | GET | 获取知识库详情 |
| `/kb/{kb_id}` | DELETE | 删除知识库 |
| `/query` | POST | 多知识库检索问答 |
| `/query/raw` | POST | 多知识库检索（仅返回原始结果） |
| `/kb/{kb_id}/index/stats` | GET | 获取知识库索引统计 |
| `/kb/{kb_id}/index/rebuild` | POST | 重建知识库索引 |

### 向量索引说明

系统使用 ChromaDB 作为向量数据库，支持：
- 基于 Ollama 部署的 Embedding 模型（默认 `bge-m3:latest`）
- 多知识库隔离，每个知识库使用独立的 collection
- 自动去重，同一节点的多个向量会按最高分保留
- 细分向量：除主向量（title + summary）外，还为每个 key_point 单独生成向量

