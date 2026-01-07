## 树搜索教程

PageIndex 将文档解析为层级树结构，每个节点包含标题、摘要、关键点等信息。本教程介绍如何利用树结构进行高效的文档检索。

### 树结构说明

PageIndex 生成的树结构包含以下字段：

```json
{
  "node_id": "1",
  "title": "章节标题",
  "start_index": 1,
  "end_index": 10,
  "summary": "章节摘要",
  "key_points": ["关键点1", "关键点2"],
  "text": "章节原文内容",
  "nodes": [
    // 子节点
  ]
}
```

### 基本 LLM 树搜索

使用 LLM 代理遍历树结构，找到与查询最相关的节点：

```python
import json

def tree_search(query: str, tree_structure: list, model: str = "gpt-4o") -> list:
    """使用 LLM 在树结构中搜索相关节点"""

    # 准备树结构的简化表示
    def simplify_tree(nodes, depth=0) -> list:
        simplified = []
        for node in nodes:
            simplified.append({
                "node_id": node.get("node_id"),
                "title": node.get("title"),
                "summary": node.get("summary", "")[:200],  # 截断摘要
                "depth": depth
            })
            if node.get("nodes"):
                simplified.extend(simplify_tree(node["nodes"], depth + 1))
        return simplified

    simplified_tree = simplify_tree(tree_structure)

    prompt = f"""
    你将获得一个查询和一个文档的树结构。
    你需要找到所有可能包含答案的节点。

    查询: {query}

    文档树结构:
    {json.dumps(simplified_tree, indent=2, ensure_ascii=False)}

    以以下 JSON 格式回复:
    {{
        "thinking": "<你关于哪些节点相关的推理>",
        "node_list": ["node_id1", "node_id2", ...]
    }}

    仅返回 JSON 结构，不要有额外输出。
    """

    # 调用 LLM API
    response = call_llm(prompt)
    return response.get("node_list", [])
```

### 结合向量检索的混合搜索

PageIndex 系统已经内置了向量检索功能。可以结合树结构和向量检索实现混合搜索：

```python
import requests

def hybrid_search(query: str, kb_id: str, top_k: int = 10):
    """混合搜索：向量检索 + 树结构导航"""

    # 1. 向量检索获取初步结果
    response = requests.post(
        "http://localhost:8502/query/raw",
        json={
            "q": query,
            "top_k": top_k,
            "kb_ids": [kb_id]
        }
    )

    results = response.json()["results"]

    # 2. 根据检索结果的节点路径，找到相关的上下文
    enriched_results = []
    for result in results:
        enriched_results.append({
            "node_id": result["node_id"],
            "title": result["title"],
            "path": result.get("path", ""),  # 节点路径
            "score": result["score"],
            "summary": result["summary"],
            "text": result.get("text", "")
        })

    return enriched_results
```

### 集成用户偏好或专家知识

与基于向量的 RAG 不同，PageIndex 可以通过修改树搜索提示来轻松整合用户偏好或专家知识：

```python
def tree_search_with_preferences(
    query: str,
    tree_structure: list,
    preferences: str,
    model: str = "gpt-4o"
) -> list:
    """带专家偏好的树搜索"""

    simplified_tree = simplify_tree(tree_structure)

    prompt = f"""
    你将获得一个问题和一个文档的树结构。
    你需要找到所有可能包含答案的节点。

    查询: {query}

    文档树结构:
    {json.dumps(simplified_tree, indent=2, ensure_ascii=False)}

    相关章节的专家知识:
    {preferences}

    以以下 JSON 格式回复:
    {{
        "thinking": "<关于哪些节点相关的推理>",
        "node_list": ["node_id1", "node_id2", ...]
    }}

    仅返回 JSON 结构，不要有额外输出。
    """

    response = call_llm(prompt)
    return response.get("node_list", [])

# 使用示例
preferences = """
- 如果查询涉及水库调度，优先考虑"汛期调度运用计划"相关章节
- 如果查询涉及历史洪水，优先考虑"洪水过程"和"受灾情况"章节
- 如果查询涉及工程参数，优先考虑"工程特性"和"设计参数"章节
"""

relevant_nodes = tree_search_with_preferences(
    query="峪门水库的汛限水位是多少？",
    tree_structure=structure,
    preferences=preferences
)
```

### 获取节点详细内容

找到相关节点后，可以获取其完整内容：

```python
def get_node_content(structure: list, node_ids: list) -> list:
    """从树结构中获取指定节点的完整内容"""

    node_map = {}

    def build_map(nodes):
        for node in nodes:
            node_map[node.get("node_id")] = node
            if node.get("nodes"):
                build_map(node["nodes"])

    build_map(structure)

    contents = []
    for node_id in node_ids:
        if node_id in node_map:
            node = node_map[node_id]
            contents.append({
                "node_id": node_id,
                "title": node.get("title"),
                "text": node.get("text", ""),
                "summary": node.get("summary", ""),
                "key_points": node.get("key_points", [])
            })

    return contents
```

### 完整示例：多知识库树搜索

```python
import requests
import json
import os

class TreeSearchRetriever:
    """基于树结构的文档检索器"""

    def __init__(self, kb_base_dir: str = "knowledge_bases"):
        self.kb_base_dir = kb_base_dir
        self.structures = {}

    def load_structure(self, kb_id: str, doc_name: str) -> dict:
        """加载文档的树结构"""
        cache_key = f"{kb_id}:{doc_name}"
        if cache_key in self.structures:
            return self.structures[cache_key]

        results_dir = os.path.join(self.kb_base_dir, kb_id, "results")
        structure_file = os.path.join(results_dir, f"{doc_name}_structure.json")

        if os.path.exists(structure_file):
            with open(structure_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.structures[cache_key] = data
                return data

        return None

    def search(self, query: str, kb_id: str, doc_name: str, top_k: int = 5) -> list:
        """在指定文档中进行树搜索"""

        # 1. 加载树结构
        doc_data = self.load_structure(kb_id, doc_name)
        if not doc_data:
            return []

        structure = doc_data.get("structure", [])

        # 2. 使用 LLM 进行树搜索
        relevant_node_ids = tree_search(query, structure)

        # 3. 获取节点内容
        contents = get_node_content(structure, relevant_node_ids[:top_k])

        return contents

    def search_with_vector_hints(
        self,
        query: str,
        kb_ids: list = None,
        top_k: int = 10
    ) -> list:
        """结合向量检索的树搜索"""

        # 1. 先用向量检索获取候选节点
        response = requests.post(
            "http://localhost:8502/query/raw",
            json={
                "q": query,
                "top_k": top_k * 2,
                "kb_ids": kb_ids
            }
        )

        vector_results = response.json()["results"]

        # 2. 按文档分组
        doc_nodes = {}
        for result in vector_results:
            doc_key = f"{result['kb_id']}:{result['doc_name']}"
            if doc_key not in doc_nodes:
                doc_nodes[doc_key] = []
            doc_nodes[doc_key].append(result)

        # 3. 对每个文档进行树搜索验证
        final_results = []
        for doc_key, nodes in doc_nodes.items():
            kb_id, doc_name = doc_key.split(":", 1)

            # 加载完整树结构
            doc_data = self.load_structure(kb_id, doc_name)
            if doc_data:
                # 获取向量检索找到的节点的完整信息
                structure = doc_data.get("structure", [])
                node_ids = [n["node_id"] for n in nodes]
                contents = get_node_content(structure, node_ids)

                for content, vector_result in zip(contents, nodes):
                    content["score"] = vector_result["score"]
                    content["kb_id"] = kb_id
                    content["doc_name"] = doc_name
                    final_results.append(content)

        # 按分数排序
        final_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return final_results[:top_k]

# 使用示例
retriever = TreeSearchRetriever("PageIndex/knowledge_bases")

# 基本树搜索
results = retriever.search(
    query="共产主义渠的设计流量",
    kb_id="water_project",
    doc_name="共产主义渠工程概况"
)

# 结合向量检索的混合搜索
results = retriever.search_with_vector_hints(
    query="21.7洪水期间的水库调度",
    kb_ids=["history_flood", "flood_preplan"]
)

for r in results:
    print(f"[{r.get('kb_id', '')}] {r['title']}")
    print(f"  摘要: {r.get('summary', '')[:100]}...")
    print()
```

### 优势

- **结构化导航**：利用文档的层级结构快速定位相关章节
- **上下文感知**：可以获取节点的父子关系和路径信息
- **可解释性**：LLM 的推理过程清晰展示为什么选择某些节点
- **灵活定制**：可以轻松整合领域知识和用户偏好

### 与向量检索的配合

建议的最佳实践是：
1. 使用向量检索获取初步候选
2. 利用树结构获取上下文信息
3. 使用 LLM 进行最终的相关性判断和答案生成

