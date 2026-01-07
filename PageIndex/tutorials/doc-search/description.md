
## 按描述搜索文档

对于没有细粒度元数据的文档，可以使用 LLM 生成的文档描述来帮助文档选择。这是一种轻量级方法，最适合少量文档或需要快速定位相关文档的场景。

### 系统支持

PageIndex 在处理文档时可以自动生成文档描述（`doc_description`）。描述会存储在结构文件中，并在向量索引的元数据中保留。

### 工作流程

#### 1. 获取文档描述

从检索结果中获取文档描述：

```python
import requests

# 获取原始检索结果，包含文档描述
response = requests.post(
    "http://localhost:8502/query/raw",
    json={
        "q": "防洪",  # 宽泛的查询词
        "top_k": 50   # 获取较多结果以覆盖更多文档
    }
)

# 提取唯一的文档及其描述
results = response.json()["results"]
documents = {}

for result in results:
    doc_key = f"{result['kb_id']}:{result['doc_name']}"
    if doc_key not in documents:
        documents[doc_key] = {
            "kb_id": result["kb_id"],
            "kb_name": result["kb_name"],
            "doc_name": result["doc_name"],
            "doc_description": result.get("doc_description", "")
        }

for doc_key, doc in documents.items():
    print(f"[{doc['kb_name']}] {doc['doc_name']}")
    print(f"  描述: {doc['doc_description']}")
    print()
```

#### 2. 使用 LLM 选择相关文档

基于文档描述使用 LLM 选择最相关的文档：

```python
import json

def select_documents_by_description(query: str, documents: dict) -> list:
    """使用 LLM 根据文档描述选择相关文档"""

    doc_list = [
        {
            "key": key,
            "kb_name": doc["kb_name"],
            "doc_name": doc["doc_name"],
            "description": doc["doc_description"]
        }
        for key, doc in documents.items()
        if doc["doc_description"]  # 只包含有描述的文档
    ]

    prompt = f"""
    你将获得一个包含文档名称和描述的文档列表。你的任务是选择可能包含与回答用户查询相关信息的文档。

    查询: {query}

    文档列表:
    {json.dumps(doc_list, indent=2, ensure_ascii=False)}

    响应格式:
    {{
        "thinking": "<你选择文档的推理过程>",
        "selected_keys": ["kb_id:doc_name", ...]
    }}

    如果没有相关文档则返回空列表。仅返回 JSON 结构，不要有额外输出。
    """

    # 调用 LLM API
    response = call_llm(prompt)
    return response.get("selected_keys", [])

# 使用示例
selected = select_documents_by_description(
    "水库泄洪时下游河道的防洪能力",
    documents
)
print(f"选中的文档: {selected}")
```

#### 3. 在选定文档中进行精确检索

```python
import requests

def search_in_selected_documents(query: str, selected_docs: list, top_k: int = 10):
    """在选定的文档中进行检索"""

    # 从 selected_docs 提取知识库和文档名
    kb_docs = {}
    for doc_key in selected_docs:
        kb_id, doc_name = doc_key.split(":", 1)
        if kb_id not in kb_docs:
            kb_docs[kb_id] = []
        kb_docs[kb_id].append(doc_name)

    # 在相关知识库中检索
    response = requests.post(
        "http://localhost:8502/query",
        json={
            "q": query,
            "top_k": top_k,
            "kb_ids": list(kb_docs.keys())
        }
    )

    return response.json()

# 使用示例
result = search_in_selected_documents(
    "水库泄洪时下游河道的防洪能力",
    selected
)
print(result["answer"])
```

### 基于树结构生成描述

如果需要手动为文档生成描述，可以基于 PageIndex 树结构：

```python
def generate_doc_description_from_structure(structure: list, model: str = "gpt-4o") -> str:
    """根据文档的 PageIndex 树结构生成描述"""

    # 提取树结构的标题层级
    def extract_titles(nodes, depth=0) -> list:
        titles = []
        for node in nodes:
            prefix = "  " * depth
            titles.append(f"{prefix}- {node.get('title', '')}")
            if node.get("nodes"):
                titles.extend(extract_titles(node["nodes"], depth + 1))
        return titles

    tree_text = "\n".join(extract_titles(structure))

    prompt = f"""
    你将获得一个文档的目录结构。
    你的任务是为该文档生成一句话描述，使其易于与其他文档区分。

    文档树结构:
    {tree_text}

    直接返回描述，不要包含任何其他文本。
    """

    # 调用 LLM API 生成描述
    description = call_llm(prompt)
    return description
```

### 完整示例：描述驱动的文档检索

```python
import requests
import json

class DescriptionBasedRetriever:
    """基于描述的文档检索器"""

    def __init__(self, api_base: str = "http://localhost:8502"):
        self.api_base = api_base
        self.documents_cache = {}

    def build_document_index(self):
        """构建文档描述索引"""
        # 获取所有知识库
        kb_response = requests.get(f"{self.api_base}/kb/list")
        kb_list = kb_response.json()["knowledge_bases"]

        for kb in kb_list:
            # 获取知识库的索引统计
            stats_response = requests.get(f"{self.api_base}/kb/{kb['id']}/index/stats")
            stats = stats_response.json().get("stats", {})

            for doc_name in stats.get("documents", []):
                doc_key = f"{kb['id']}:{doc_name}"
                self.documents_cache[doc_key] = {
                    "kb_id": kb["id"],
                    "kb_name": kb["name"],
                    "doc_name": doc_name,
                    "kb_description": kb["description"]
                }

        return len(self.documents_cache)

    def retrieve(self, query: str, top_k: int = 10) -> dict:
        """执行检索"""
        # 1. 使用知识库描述选择相关知识库
        kb_response = requests.get(f"{self.api_base}/kb/list")
        kb_list = kb_response.json()["knowledge_bases"]

        selected_kb_ids = self._select_kb_by_description(query, kb_list)

        # 2. 在选定知识库中检索
        query_response = requests.post(
            f"{self.api_base}/query",
            json={
                "q": query,
                "top_k": top_k,
                "kb_ids": selected_kb_ids
            }
        )

        return query_response.json()

    def _select_kb_by_description(self, query: str, kb_list: list) -> list:
        """基于描述选择知识库"""
        # 简单实现：选择描述中包含查询关键词的知识库
        # 实际应用中应使用 LLM 进行智能选择
        selected = []
        query_lower = query.lower()

        for kb in kb_list:
            desc = kb.get("description", "").lower()
            name = kb.get("name", "").lower()
            if any(keyword in desc or keyword in name
                   for keyword in query_lower.split()):
                selected.append(kb["id"])

        # 如果没有匹配，返回所有知识库
        return selected if selected else [kb["id"] for kb in kb_list]

# 使用示例
retriever = DescriptionBasedRetriever()
retriever.build_document_index()

result = retriever.retrieve("蓄滞洪区分洪运用条件")
print(f"答案: {result['answer']}")
print(f"搜索的知识库: {result.get('searched_kb', [])}")
```

### 适用场景

- 文档数量较少（< 100 个）
- 需要快速原型验证
- 文档主题差异明显
- 不需要精确的元数据分类

### 局限性

- 描述可能无法覆盖文档的所有细节
- 对于大量文档，LLM 选择可能变慢
- 描述质量依赖于文档结构的完整性

