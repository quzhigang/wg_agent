"""
LLM 层进式目录结构检索模块

参考开源 PageIndex (VectifyAI) 的 Reasoning-based RAG 理念：
让 LLM 阅读文档的树结构索引，通过推理定位相关节点，而非向量相似度匹配。
"""

import os
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional

import openai

logger = logging.getLogger(__name__)

# LLM 检索专用配置（从 PageIndex/.env 读取）
LLM_RETRIEVAL_API_KEY = os.getenv("LLM_RETRIEVAL_API_KEY", "")
LLM_RETRIEVAL_API_BASE = os.getenv("LLM_RETRIEVAL_API_BASE", "")
LLM_RETRIEVAL_MODEL_NAME = os.getenv("LLM_RETRIEVAL_MODEL_NAME", "qwen3-32b")


def update_retrieval_config(api_key: str = None, api_base: str = None, model_name: str = None):
    """更新 LLM 检索配置（供前端侧边栏调用）"""
    global LLM_RETRIEVAL_API_KEY, LLM_RETRIEVAL_API_BASE, LLM_RETRIEVAL_MODEL_NAME
    if api_key is not None:
        LLM_RETRIEVAL_API_KEY = api_key
    if api_base is not None:
        LLM_RETRIEVAL_API_BASE = api_base
    if model_name is not None:
        LLM_RETRIEVAL_MODEL_NAME = model_name


def _strip_text_fields(structure):
    """递归去掉树结构中的 text 字段，减少 token 消耗"""
    if isinstance(structure, dict):
        result = {}
        for k, v in structure.items():
            if k == "text":
                continue
            if k == "nodes":
                result[k] = _strip_text_fields(v)
            else:
                result[k] = v
        return result
    elif isinstance(structure, list):
        return [_strip_text_fields(item) for item in structure]
    return structure


def _build_node_mapping(structure, mapping=None):
    """从树结构中构建 node_id → 节点的映射"""
    if mapping is None:
        mapping = {}
    if isinstance(structure, list):
        for item in structure:
            _build_node_mapping(item, mapping)
    elif isinstance(structure, dict):
        if "node_id" in structure:
            mapping[structure["node_id"]] = structure
        if "nodes" in structure:
            _build_node_mapping(structure["nodes"], mapping)
    return mapping


def _extract_json(content: str):
    """从 LLM 响应中提取 JSON"""
    try:
        start_idx = content.find("```json")
        if start_idx != -1:
            start_idx += 7
            end_idx = content.rfind("```")
            json_content = content[start_idx:end_idx].strip()
        else:
            json_content = content.strip()

        json_content = json_content.replace("None", "null")
        json_content = json_content.replace("\n", " ").replace("\r", " ")
        json_content = " ".join(json_content.split())
        return json.loads(json_content)
    except json.JSONDecodeError:
        try:
            json_content = json_content.replace(",]", "]").replace(",}", "}")
            return json.loads(json_content)
        except Exception:
            return {}
    except Exception:
        return {}


async def _call_llm(prompt: str, api_key: str = None, api_base: str = None, model: str = None) -> str:
    """调用 LLM（OpenAI 兼容接口）"""
    _api_key = api_key or LLM_RETRIEVAL_API_KEY
    _api_base = api_base or LLM_RETRIEVAL_API_BASE
    _model = model or LLM_RETRIEVAL_MODEL_NAME

    if not _api_key:
        raise ValueError("LLM_RETRIEVAL_API_KEY 未配置，请在 PageIndex/.env 中设置")

    max_retries = 3
    for i in range(max_retries):
        try:
            client = openai.AsyncOpenAI(api_key=_api_key, base_url=_api_base)
            response = await client.chat.completions.create(
                model=_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                extra_body={"enable_thinking": False},
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"LLM 调用失败 (第{i+1}次): {e}")
            if i < max_retries - 1:
                await asyncio.sleep(1)
            else:
                raise


async def _search_single_document(
    query: str,
    kb_id: str,
    doc_name: str,
    structure: list,
    doc_description: str = "",
    top_k: int = 5,
) -> Dict[str, Any]:
    """
    对单个文档执行 LLM 层进式检索

    返回: {"node_ids": [...], "thinking": "...", "doc_name": ..., "kb_id": ...}
    """
    tree_without_text = _strip_text_fields(structure)

    prompt = f"""你是一个专业的文档检索助手。给定一个问题和一个文档的树形目录结构，
每个节点包含 node_id（节点ID）、title（标题）和 summary（摘要）。
你的任务是找出所有可能包含问题答案的节点。

文档名称: {doc_name}
{f'文档描述: {doc_description}' if doc_description else ''}

问题: {query}

文档树形结构:
{json.dumps(tree_without_text, indent=2, ensure_ascii=False)}

请按以下 JSON 格式回复（最多返回 {top_k} 个最相关的节点）:
{{
    "thinking": "<你的推理过程：分析哪些节点与问题相关，为什么>",
    "node_list": ["node_id_1", "node_id_2", ...]
}}
直接返回 JSON，不要输出其他内容。"""

    try:
        response = await _call_llm(prompt)
        result = _extract_json(response)
        node_ids = result.get("node_list", [])[:top_k]
        if not node_ids:
            logger.warning(f"LLM 未返回有效节点 [{kb_id}/{doc_name}]，原始响应: {response[:300]}")
        return {
            "kb_id": kb_id,
            "doc_name": doc_name,
            "node_ids": node_ids,
            "thinking": result.get("thinking", ""),
        }
    except Exception as e:
        logger.error(f"LLM 检索文档 [{kb_id}/{doc_name}] 失败: {e}")
        return {
            "kb_id": kb_id,
            "doc_name": doc_name,
            "node_ids": [],
            "thinking": f"检索失败: {e}",
        }


class LLMRetriever:
    """基于 LLM 推理的层进式目录结构检索"""

    async def search(
        self,
        query: str,
        kb_configs: List[Dict[str, str]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        LLM 检索主流程

        Args:
            query: 查询文本
            kb_configs: 知识库配置列表 [{"kb_id": ..., "results_dir": ..., "uploads_dir": ...}]
            top_k: 每个文档最多返回的节点数

        Returns:
            检索结果列表，格式与向量检索一致
        """
        # 1. 收集所有文档的树结构
        doc_tasks = []
        doc_structures = []  # (kb_id, doc_name, structure, doc_description)

        for config in kb_configs:
            kb_id = config["kb_id"]
            results_dir = config["results_dir"]

            if not os.path.exists(results_dir):
                continue

            structure_files = [f for f in os.listdir(results_dir) if f.endswith("_structure.json")]
            for filename in structure_files:
                filepath = os.path.join(results_dir, filename)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    doc_name = data.get("doc_name", filename.replace("_structure.json", ""))
                    doc_description = data.get("doc_description", "")
                    structure = data.get("structure", [])
                    if structure:
                        doc_structures.append((kb_id, doc_name, structure, doc_description))
                except Exception as e:
                    logger.warning(f"加载文档结构失败 {filepath}: {e}")

        if not doc_structures:
            return []

        # 2. 并发对每个文档执行 LLM 检索
        tasks = [
            _search_single_document(query, kb_id, doc_name, structure, doc_description, top_k)
            for kb_id, doc_name, structure, doc_description in doc_structures
        ]
        doc_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 汇总结果，提取节点内容
        all_results = []
        all_thinking = []

        for i, doc_result in enumerate(doc_results):
            if isinstance(doc_result, Exception):
                logger.error(f"文档检索异常: {doc_result}")
                continue

            kb_id = doc_result["kb_id"]
            doc_name = doc_result["doc_name"]
            node_ids = doc_result["node_ids"]
            thinking = doc_result["thinking"]

            if thinking:
                all_thinking.append(f"[{kb_id}/{doc_name}] {thinking}")

            if not node_ids:
                continue

            # 加载完整结构以获取节点内容
            _, _, structure, _ = doc_structures[i]
            node_map = _build_node_mapping(structure)

            for rank, node_id in enumerate(node_ids):
                node = node_map.get(node_id)
                if not node:
                    continue

                # 按排名赋分：第1个=1.0，第2个=0.9，递减，最低0.1
                score = max(1.0 - rank * 0.1, 0.1)

                all_results.append({
                    "kb_id": kb_id,
                    "doc_name": doc_name,
                    "node_id": node_id,
                    "title": node.get("title", ""),
                    "score": score,
                    "summary": node.get("summary", ""),
                    "text": node.get("text", ""),
                    "start_index": node.get("start_index"),
                    "end_index": node.get("end_index"),
                })

        # 4. 按 score 降序排序
        all_results.sort(key=lambda x: x["score"], reverse=True)

        return all_results, "\n".join(all_thinking)


# 单例
_llm_retriever: Optional[LLMRetriever] = None


def get_llm_retriever() -> LLMRetriever:
    global _llm_retriever
    if _llm_retriever is None:
        _llm_retriever = LLMRetriever()
    return _llm_retriever
