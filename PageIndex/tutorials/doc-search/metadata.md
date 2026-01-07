
## 按元数据搜索文档

在多知识库系统中，利用知识库的元数据（ID、名称、描述）进行文档分类和精准检索是最高效的方式之一。

### 适用场景

此方法适用于以下文档类型：
- 按业务领域分类的文档（如：流域概况、水利工程、监测站点）
- 按文档类型分类的文档（如：规划报告、设计方案、预案文档）
- 按时间或版本分类的文档
- 需要精确控制检索范围的场景

### 工作流程

#### 1. 了解知识库分类

首先获取系统中所有知识库及其描述：

```python
import requests

response = requests.get("http://localhost:8502/kb/list")
kb_list = response.json()["knowledge_bases"]

for kb in kb_list:
    print(f"ID: {kb['id']}")
    print(f"名称: {kb['name']}")
    print(f"描述: {kb['description']}")
    print("---")
```

#### 2. 根据问题选择知识库

使用 LLM 根据用户问题自动选择最相关的知识库：

```python
def select_knowledge_bases(query: str, kb_list: list) -> list:
    """使用 LLM 选择最相关的知识库"""
    kb_info = "\n".join([
        f"- ID: {kb['id']}, 名称: {kb['name']}, 描述: {kb['description']}"
        for kb in kb_list
    ])

    prompt = f"""
    你将获得一个用户问题和一个知识库列表。请选择最可能包含答案的知识库。

    用户问题: {query}

    知识库列表:
    {kb_info}

    响应格式:
    {{
        "thinking": "<你选择知识库的推理过程>",
        "selected_kb_ids": ["kb_id1", "kb_id2"]
    }}

    仅返回 JSON 结构，不要有额外输出。
    """

    # 调用 LLM API 获取响应
    response = call_llm(prompt)
    return response["selected_kb_ids"]
```

#### 3. 在指定知识库中检索

```python
import requests

# 假设选择了 "water_project" 和 "flood_preplan" 知识库
selected_kb_ids = ["water_project", "flood_preplan"]

response = requests.post(
    "http://localhost:8502/query",
    json={
        "q": "水库的防洪库容是多少？",
        "top_k": 10,
        "kb_ids": selected_kb_ids
    }
)

result = response.json()
print(f"答案: {result['answer']}")
print(f"来源: {result['sources']}")
print(f"搜索的知识库: {result['searched_kb']}")
```

### 示例：两阶段检索

结合知识库元数据和向量检索的两阶段检索策略：

```python
import requests

def two_stage_retrieval(query: str, top_k: int = 10):
    """两阶段检索：先选择知识库，再进行向量检索"""

    # 阶段1：获取知识库列表并选择
    kb_response = requests.get("http://localhost:8502/kb/list")
    kb_list = kb_response.json()["knowledge_bases"]

    # 使用 LLM 选择知识库
    selected_kb_ids = select_knowledge_bases(query, kb_list)

    # 阶段2：在选定的知识库中进行向量检索
    query_response = requests.post(
        "http://localhost:8502/query",
        json={
            "q": query,
            "top_k": top_k,
            "kb_ids": selected_kb_ids
        }
    )

    return query_response.json()

# 使用示例
result = two_stage_retrieval("共产主义渠的设计流量是多少？")
print(result["answer"])
```

### 创建新知识库

当需要添加新的文档分类时，可以创建新的知识库：

```python
import requests

response = requests.post(
    "http://localhost:8502/kb/create",
    json={
        "id": "emergency_plan",
        "name": "应急预案",
        "description": "本知识库用于存储各类防洪应急预案、抢险方案等"
    }
)

print(response.json())
```

### 优势

- **精准定位**：通过知识库分类快速缩小检索范围
- **减少噪音**：避免在不相关的文档中检索
- **提高效率**：减少向量检索的计算量
- **可解释性**：用户可以明确知道答案来自哪个知识库

