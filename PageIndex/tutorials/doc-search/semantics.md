## 按语义搜索文档

PageIndex 使用 ChromaDB 向量数据库和 Embedding 模型（默认 bge-m3）实现跨知识库的语义搜索。系统会为每个文档节点生成多个向量，包括主向量和关键点向量，以提高检索精度。

### 向量索引机制

当前系统为每个节点生成以下类型的向量：

1. **主向量（main）**：`title + summary` 的组合
2. **关键点向量（key_point）**：每个 `key_point` 单独生成向量，格式为 `title: key_point`
3. **标题向量（title_only）**：仅当节点没有摘要和关键点时使用

检索时，系统会自动按 `node_id` 去重，保留每个节点的最高分结果。

### 工作流程

#### 1. 直接向量检索

最简单的方式是直接调用 `/query/raw` 接口获取原始检索结果：

```python
import requests

response = requests.post(
    "http://localhost:8502/query/raw",
    json={
        "q": "蓄滞洪区的启用条件是什么？",
        "top_k": 10
    }
)

results = response.json()["results"]

for result in results:
    print(f"知识库: {result['kb_name']}")
    print(f"文档: {result['doc_name']}")
    print(f"章节: {result['title']}")
    print(f"相似度: {result['score']:.3f}")
    print(f"摘要: {result['summary'][:200]}...")
    print("---")
```

#### 2. 带 LLM 问答的检索

调用 `/query` 接口，系统会自动提取相关内容并使用 LLM 生成答案：

```python
import requests

response = requests.post(
    "http://localhost:8502/query",
    json={
        "q": "21.7 洪水造成了哪些损失？",
        "top_k": 10,
        "kb_ids": ["history_flood"]  # 可选：限定搜索范围
    }
)

result = response.json()
print(f"答案: {result['answer']}")
print(f"\n参考来源:")
for source in result['sources']:
    print(f"  - {source}")
```

### 跨知识库检索评分

当检索多个知识库时，系统会合并所有结果并按相似度排序。相似度分数计算方式：

```
score = 1 - distance
```

其中 `distance` 是 ChromaDB 计算的向量距离。分数越高，表示语义相似度越高。

### 文档得分聚合

如果需要按文档而非节点聚合结果，可以使用以下策略：

```python
import math
from collections import defaultdict

def aggregate_by_document(results: list) -> list:
    """按文档聚合检索结果，计算文档级别的相关性得分"""

    doc_scores = defaultdict(lambda: {"chunks": [], "total_score": 0})

    for result in results:
        doc_key = f"{result['kb_id']}:{result['doc_name']}"
        doc_scores[doc_key]["chunks"].append(result)
        doc_scores[doc_key]["total_score"] += result["score"]
        doc_scores[doc_key]["kb_name"] = result["kb_name"]
        doc_scores[doc_key]["doc_name"] = result["doc_name"]

    # 计算归一化文档得分
    doc_results = []
    for doc_key, data in doc_scores.items():
        n = len(data["chunks"])
        # 使用平方根归一化，平衡命中数量和单个命中质量
        normalized_score = data["total_score"] / math.sqrt(n + 1)

        doc_results.append({
            "kb_name": data["kb_name"],
            "doc_name": data["doc_name"],
            "score": normalized_score,
            "chunk_count": n,
            "top_chunks": sorted(data["chunks"], key=lambda x: x["score"], reverse=True)[:3]
        })

    # 按得分排序
    doc_results.sort(key=lambda x: x["score"], reverse=True)
    return doc_results

# 使用示例
import requests

response = requests.post(
    "http://localhost:8502/query/raw",
    json={"q": "河道治理方案", "top_k": 20}
)

doc_results = aggregate_by_document(response.json()["results"])
for doc in doc_results[:5]:
    print(f"{doc['kb_name']} / {doc['doc_name']}: {doc['score']:.3f} ({doc['chunk_count']} hits)")
```

### 重建向量索引

当文档更新后，可以重建指定知识库的向量索引：

```python
import requests

# 重建单个知识库的索引
response = requests.post("http://localhost:8502/kb/water_project/index/rebuild")
print(response.json())

# 查看索引统计
response = requests.get("http://localhost:8502/kb/water_project/index/stats")
stats = response.json()["stats"]
print(f"文档数: {stats['total_documents']}")
print(f"节点数: {stats['total_nodes']}")
```

### 命令行构建索引

也可以使用命令行工具批量构建索引：

```bash
# 构建所有知识库的索引
python build_vector_index.py

# 构建指定知识库的索引
python build_vector_index.py --kb water_project

# 设置文档处理延迟（避免连接池问题）
python build_vector_index.py --kb water_project --delay 2.0
```

### 配置说明

向量索引相关配置通过环境变量设置：

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| `EMBEDDING_MODEL_NAME` | `bge-m3:latest` | Embedding 模型名称 |
| `EMBEDDING_MODEL_API_URL` | `http://10.20.2.135:11434` | Ollama API 地址 |
| `EMBEDDING_MODEL_TYPE` | `ollama` | Embedding 模型类型 |

