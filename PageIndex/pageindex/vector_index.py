"""
PageIndex 向量索引模块

本模块提供基于 ChromaDB 的向量索引功能，用于加速文档检索。
支持 Ollama 部署的 Embedding 模型。
支持多知识库隔离，每个知识库使用独立的 collection。
"""

import os
import json
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Embedding 模型配置
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "bge-m3:latest")
EMBEDDING_MODEL_API_URL = os.getenv("EMBEDDING_MODEL_API_URL", "http://10.20.2.135:11434")
EMBEDDING_MODEL_TYPE = os.getenv("EMBEDDING_MODEL_TYPE", "ollama")

# Reranker 模型配置
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-base")
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "true").lower() == "true"
RERANKER_TOP_K = int(os.getenv("RERANKER_TOP_K", "5"))

# ChromaDB 存储路径（使用绝对路径确保一致性）
# 默认使用当前模块所在目录的上级目录下的 chroma_db
_module_dir = os.path.dirname(os.path.abspath(__file__))
_default_chroma_dir = os.path.join(os.path.dirname(_module_dir), "chroma_db")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", _default_chroma_dir)


class OllamaEmbedding:
    """
    Ollama Embedding 模型封装类

    调用 Ollama API 生成文本的向量表示
    """

    def __init__(self, model_name: str = None, api_url: str = None):
        self.model_name = model_name or EMBEDDING_MODEL_NAME
        self.api_url = api_url or EMBEDDING_MODEL_API_URL
        self.embed_endpoint = f"{self.api_url.rstrip('/')}/api/embeddings"

        # 创建带有重试机制的 session
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=1, pool_maxsize=1)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def embed(self, text: str, max_retries: int = 3) -> List[float]:
        """
        为单个文本生成 embedding
        
        参数:
            text: 输入文本
            max_retries: 最大重试次数
        
        返回:
            embedding 向量
        """
        for attempt in range(max_retries):
            try:
                response = self.session.post(
                    self.embed_endpoint,
                    json={
                        "model": self.model_name,
                        "prompt": text
                    },
                    timeout=60
                )
                response.raise_for_status()
                result = response.json()
                return result.get("embedding", [])
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2  # 递增等待时间
                    print(f"Embedding 生成失败 (尝试 {attempt + 1}/{max_retries}): {e}, {wait_time}秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"Embedding 生成失败: {e}")
                    raise
    
    def embed_batch(self, texts: List[str], batch_delay: float = 0.1) -> List[List[float]]:
        """
        批量生成 embedding
        
        参数:
            texts: 文本列表
            batch_delay: 每个请求之间的延迟（秒），避免连接池耗尽
        
        返回:
            embedding 向量列表
        """
        embeddings = []
        for i, text in enumerate(texts):
            embedding = self.embed(text)
            embeddings.append(embedding)
            # 添加小延迟，避免连接池问题
            if i < len(texts) - 1 and batch_delay > 0:
                time.sleep(batch_delay)
        return embeddings


# 模块级别的模型缓存（避免 Streamlit 重复加载）
_RERANKER_MODEL_CACHE = {}

class Reranker:
    """
    基于 sentence-transformers 的重排序模型

    使用交叉编码器对候选结果进行精确重排序
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        """延迟加载模型，使用模块级缓存"""
        if RERANKER_MODEL_NAME not in _RERANKER_MODEL_CACHE:
            try:
                from sentence_transformers import CrossEncoder
                print(f"正在加载 Reranker 模型: {RERANKER_MODEL_NAME}...")
                _RERANKER_MODEL_CACHE[RERANKER_MODEL_NAME] = CrossEncoder(RERANKER_MODEL_NAME, max_length=512)
                print("Reranker 模型加载完成")
            except ImportError:
                print("警告: sentence-transformers 未安装，rerank 功能不可用")
                print("请运行: pip install sentence-transformers")
            except Exception as e:
                print(f"Reranker 模型加载失败: {e}")

    def rerank(self, query: str, documents: List[Dict[str, Any]],
               top_k: int = None) -> List[Dict[str, Any]]:
        """
        对检索结果进行重排序

        参数:
            query: 查询文本
            documents: 检索结果列表，每个元素需包含 title 和 summary
            top_k: 返回的结果数量，默认使用配置值

        返回:
            重排序后的结果列表
        """
        if not documents:
            return documents[:top_k] if top_k else documents

        self._load_model()
        model = _RERANKER_MODEL_CACHE.get(RERANKER_MODEL_NAME)
        if model is None:
            return documents[:top_k] if top_k else documents

        top_k = top_k or RERANKER_TOP_K

        # 构建 query-document 对
        pairs = []
        for doc in documents:
            doc_text = f"{doc.get('title', '')}: {doc.get('summary', '')}"
            pairs.append([query, doc_text])

        # 计算相关性分数
        scores = model.predict(pairs)

        # 将分数添加到文档并排序
        for i, doc in enumerate(documents):
            doc['rerank_score'] = float(scores[i])

        # 按 rerank_score 降序排序
        reranked = sorted(documents, key=lambda x: x.get('rerank_score', 0), reverse=True)

        return reranked[:top_k]


# 全局 Reranker 实例
_reranker_instance = None

def get_reranker() -> Reranker:
    """获取全局 Reranker 实例"""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker()
    return _reranker_instance


class MultiKBVectorIndex:
    """
    多知识库向量索引管理类
    
    基于 ChromaDB 实现多知识库的向量索引和检索。
    每个知识库使用独立的 collection，命名格式：kb_{kb_id}_nodes
    """
    
    def __init__(self):
        """初始化多知识库向量索引"""
        # 初始化 Embedding 模型（全局共享）
        self.embedding_model = OllamaEmbedding()
        
        # 缓存各知识库的 ChromaDB 客户端
        self._clients: Dict[str, chromadb.PersistentClient] = {}
        self._collections: Dict[str, Any] = {}
    
    def _get_collection_name(self, kb_id: str) -> str:
        """获取知识库对应的 collection 名称"""
        return f"kb_{kb_id}_nodes"
    
    def _get_client(self, kb_id: str, chroma_dir: str) -> chromadb.PersistentClient:
        """
        获取知识库的 ChromaDB 客户端
        
        参数:
            kb_id: 知识库ID
            chroma_dir: ChromaDB 存储目录
        
        返回:
            ChromaDB 客户端
        """
        if kb_id not in self._clients:
            os.makedirs(chroma_dir, exist_ok=True)
            self._clients[kb_id] = chromadb.PersistentClient(path=chroma_dir)
        return self._clients[kb_id]
    
    def _get_collection(self, kb_id: str, chroma_dir: str):
        """
        获取知识库的 collection
        
        参数:
            kb_id: 知识库ID
            chroma_dir: ChromaDB 存储目录
        
        返回:
            ChromaDB collection
        """
        if kb_id not in self._collections:
            client = self._get_client(kb_id, chroma_dir)
            collection_name = self._get_collection_name(kb_id)
            self._collections[kb_id] = client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"知识库 {kb_id} 的文档节点向量索引"}
            )
        return self._collections[kb_id]

    def _get_node_text(self, node: Dict[str, Any]) -> str:
        """获取节点的主文本表示（用于生成主 embedding）"""
        title = node.get("title", "")
        summary = node.get("summary", "") or node.get("prefix_summary", "")
        if summary:
            return f"{title}: {summary}"
        return title

    def _prepare_node_vectors(self, node: Dict[str, Any], doc_name: str,
                               doc_description: str, kb_id: str) -> List[Dict[str, Any]]:
        """
        为单个节点准备向量化数据（包含主向量和细分向量）

        返回:
            向量数据列表，每个元素包含 id, text, metadata
        """
        vectors = []
        title = node.get("title", "")
        summary = node.get("summary", "") or node.get("prefix_summary", "")
        key_points = node.get("key_points", []) or node.get("prefix_key_points", [])
        node_id = node.get("node_id", "")

        base_metadata = {
            "kb_id": kb_id,
            "doc_name": doc_name,
            "doc_description": doc_description,
            "node_id": node_id,
            "title": title,
            "path": node.get("path", ""),
            "start_index": str(node.get("start_index", "")),
            "end_index": str(node.get("end_index", "")),
            "line_num": str(node.get("line_num", "")),
            "has_children": str(node.get("has_children", False)),
            "summary": summary[:500] if summary else ""
        }

        # 1. 主向量：title + summary
        if summary:
            vectors.append({
                "id": f"{doc_name}_{node_id}_main",
                "text": f"{title}: {summary}",
                "metadata": {**base_metadata, "vector_type": "main"}
            })

        # 2. 细分向量：每个 key_point 单独向量化
        for i, kp in enumerate(key_points):
            if kp:  # 确保 key_point 非空
                vectors.append({
                    "id": f"{doc_name}_{node_id}_kp_{i}",
                    "text": f"{title}: {kp}",
                    "metadata": {**base_metadata, "vector_type": "key_point", "key_point": kp[:200]}
                })

        # 3. 如果没有摘要和关键点，仅用标题
        if not vectors and title:
            vectors.append({
                "id": f"{doc_name}_{node_id}_title",
                "text": title,
                "metadata": {**base_metadata, "vector_type": "title_only"}
            })

        return vectors

    def _flatten_structure(self, structure: Any, doc_name: str) -> List[Dict[str, Any]]:
        """将树结构扁平化为节点列表"""
        nodes = []

        def traverse(node, parent_path=""):
            if isinstance(node, dict):
                node_id = node.get("node_id", "")
                title = node.get("title", "")
                current_path = f"{parent_path}/{title}" if parent_path else title

                nodes.append({
                    "doc_name": doc_name,
                    "node_id": node_id,
                    "title": title,
                    "path": current_path,
                    "summary": node.get("summary", "") or node.get("prefix_summary", ""),
                    "key_points": node.get("key_points", []) or node.get("prefix_key_points", []),
                    "start_index": node.get("start_index"),
                    "end_index": node.get("end_index"),
                    "line_num": node.get("line_num"),
                    "has_children": bool(node.get("nodes")),
                    "text": node.get("text", "")
                })

                if node.get("nodes"):
                    for child in node["nodes"]:
                        traverse(child, current_path)

            elif isinstance(node, list):
                for item in node:
                    traverse(item, parent_path)

        traverse(structure)
        return nodes

    def add_document(self, kb_id: str, chroma_dir: str, doc_name: str,
                     structure: Any, doc_description: str = "") -> int:
        """
        将文档添加到指定知识库的向量索引

        参数:
            kb_id: 知识库ID
            chroma_dir: ChromaDB 存储目录
            doc_name: 文档名称
            structure: 文档的树结构
            doc_description: 文档描述

        返回:
            添加的向量数量
        """
        collection = self._get_collection(kb_id, chroma_dir)

        # 先删除该文档的旧索引
        self.delete_document(kb_id, chroma_dir, doc_name)

        # 扁平化结构
        nodes = self._flatten_structure(structure, doc_name)

        if not nodes:
            return 0

        # 准备向量化数据（每个节点可能生成多条向量）
        all_vectors = []
        for node in nodes:
            vectors = self._prepare_node_vectors(node, doc_name, doc_description, kb_id)
            all_vectors.extend(vectors)

        if not all_vectors:
            return 0

        # 提取数据
        ids = [v["id"] for v in all_vectors]
        texts = [v["text"] for v in all_vectors]
        metadatas = [v["metadata"] for v in all_vectors]

        # 生成 embeddings
        print(f"正在为 [{kb_id}] {doc_name} 生成 {len(texts)} 个向量的 embedding...")
        embeddings = self.embedding_model.embed_batch(texts)

        # 添加到 ChromaDB
        collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )

        print(f"已将 {len(nodes)} 个节点（{len(all_vectors)} 个向量）添加到知识库 [{kb_id}] 的向量索引")
        return len(all_vectors)

    def _deduplicate_by_node(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        按 node_id 去重，保留每个节点最高分的结果

        由于同一节点可能有多个向量（主向量 + key_points 向量），
        检索时可能返回同一节点的多个结果，需要去重。

        参数:
            results: 检索结果列表

        返回:
            去重后的结果列表
        """
        seen_nodes = {}
        for result in results:
            # 使用 doc_name + node_id 作为唯一标识
            node_key = f"{result.get('doc_name', '')}_{result.get('node_id', '')}"
            if node_key not in seen_nodes or result.get('score', 0) > seen_nodes[node_key].get('score', 0):
                seen_nodes[node_key] = result
        return list(seen_nodes.values())
    
    def search(self, kb_id: str, chroma_dir: str, query: str,
               top_k: int = 10, doc_filter: List[str] = None) -> List[Dict[str, Any]]:
        """
        在指定知识库中进行向量相似度检索

        参数:
            kb_id: 知识库ID
            chroma_dir: ChromaDB 存储目录
            query: 查询文本
            top_k: 返回的最大结果数（去重后）
            doc_filter: 限定搜索的文档名称列表（可选）

        返回:
            检索结果列表（按 node_id 去重，保留最高分）
        """
        collection = self._get_collection(kb_id, chroma_dir)

        # 生成查询 embedding
        query_embedding = self.embedding_model.embed(query)

        # 构建过滤条件
        where_filter = None
        if doc_filter:
            if len(doc_filter) == 1:
                where_filter = {"doc_name": doc_filter[0]}
            else:
                where_filter = {"doc_name": {"$in": doc_filter}}

        # 执行检索（多检索一些结果以应对去重后数量减少）
        search_top_k = top_k * 3
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=search_top_k,
            where=where_filter,
            include=["metadatas", "distances", "documents"]
        )

        # 格式化结果
        formatted_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                document = results["documents"][0][i] if results["documents"] else ""

                formatted_results.append({
                    "id": id,
                    "kb_id": kb_id,
                    "doc_name": metadata.get("doc_name", ""),
                    "doc_description": metadata.get("doc_description", ""),
                    "node_id": metadata.get("node_id", ""),
                    "title": metadata.get("title", ""),
                    "path": metadata.get("path", ""),
                    "start_index": metadata.get("start_index", ""),
                    "end_index": metadata.get("end_index", ""),
                    "line_num": metadata.get("line_num", ""),
                    "summary": metadata.get("summary", ""),
                    "has_children": metadata.get("has_children", "False") == "True",
                    "score": 1 - distance,
                    "document": document,
                    "vector_type": metadata.get("vector_type", ""),
                    "key_point": metadata.get("key_point", "")
                })

        # 按 node_id 去重，保留最高分
        deduplicated_results = self._deduplicate_by_node(formatted_results)

        # 按分数排序并返回 top_k
        deduplicated_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return deduplicated_results[:top_k]
    
    def search_multi_kb(self, kb_configs: List[Dict[str, str]], query: str,
                        top_k: int = 10, use_rerank: bool = True) -> List[Dict[str, Any]]:
        """
        跨多个知识库进行向量相似度检索

        参数:
            kb_configs: 知识库配置列表，每个元素包含 {"kb_id": ..., "chroma_dir": ...}
            query: 查询文本
            top_k: 返回的最大结果数（去重后）
            use_rerank: 是否使用 rerank 重排序

        返回:
            合并后的检索结果列表（按相似度排序，按 node_id 去重）
        """
        all_results = []

        # 如果启用 rerank，多召回一些候选
        recall_k = top_k * 2 if use_rerank else top_k

        for config in kb_configs:
            kb_id = config.get("kb_id")
            chroma_dir = config.get("chroma_dir")

            if not kb_id or not chroma_dir:
                continue

            try:
                results = self.search(kb_id, chroma_dir, query, recall_k)
                all_results.extend(results)
            except Exception as e:
                print(f"搜索知识库 [{kb_id}] 失败: {e}")

        # 跨知识库按 node_id 去重
        deduplicated_results = self._deduplicate_by_node(all_results)

        # 按相似度分数排序
        deduplicated_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        # 使用 rerank 重排序
        if use_rerank and len(deduplicated_results) > top_k:
            reranker = get_reranker()
            return reranker.rerank(query, deduplicated_results, top_k)

        return deduplicated_results[:top_k]
    
    def delete_document(self, kb_id: str, chroma_dir: str, doc_name: str) -> int:
        """
        删除指定知识库中文档的向量索引
        
        参数:
            kb_id: 知识库ID
            chroma_dir: ChromaDB 存储目录
            doc_name: 文档名称
        
        返回:
            删除的节点数量
        """
        try:
            collection = self._get_collection(kb_id, chroma_dir)
            
            results = collection.get(
                where={"doc_name": doc_name},
                include=["metadatas"]
            )
            
            if results and results["ids"]:
                collection.delete(ids=results["ids"])
                print(f"已删除 [{kb_id}] {doc_name} 的 {len(results['ids'])} 个节点索引")
                return len(results["ids"])
            
            return 0
        except Exception as e:
            print(f"删除文档索引失败: {e}")
            return 0
    
    def get_all_documents(self, kb_id: str, chroma_dir: str) -> List[str]:
        """获取指定知识库中所有已索引的文档名称"""
        try:
            collection = self._get_collection(kb_id, chroma_dir)
            results = collection.get(include=["metadatas"])
            if results and results["metadatas"]:
                doc_names = set()
                for metadata in results["metadatas"]:
                    if metadata.get("doc_name"):
                        doc_names.add(metadata["doc_name"])
                return list(doc_names)
            return []
        except Exception as e:
            print(f"获取文档列表失败: {e}")
            return []
    
    def get_document_node_count(self, kb_id: str, chroma_dir: str, doc_name: str) -> int:
        """获取指定知识库中文档的节点数量"""
        try:
            collection = self._get_collection(kb_id, chroma_dir)
            results = collection.get(
                where={"doc_name": doc_name},
                include=["metadatas"]
            )
            return len(results["ids"]) if results and results["ids"] else 0
        except Exception as e:
            print(f"获取节点数量失败: {e}")
            return 0
    
    def get_stats(self, kb_id: str, chroma_dir: str) -> Dict[str, Any]:
        """获取指定知识库的向量索引统计信息"""
        try:
            collection = self._get_collection(kb_id, chroma_dir)
            total_count = collection.count()
            documents = self.get_all_documents(kb_id, chroma_dir)
            
            return {
                "kb_id": kb_id,
                "total_nodes": total_count,
                "total_documents": len(documents),
                "documents": documents
            }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {"kb_id": kb_id, "total_nodes": 0, "total_documents": 0, "documents": []}
    
    def clear_cache(self, kb_id: str = None):
        """
        清除缓存的客户端和 collection
        
        参数:
            kb_id: 知识库ID，如果为 None 则清除所有缓存
        """
        if kb_id:
            self._clients.pop(kb_id, None)
            self._collections.pop(kb_id, None)
        else:
            self._clients.clear()
            self._collections.clear()


# ============================================================================
# 兼容旧版单知识库接口（向后兼容）
# ============================================================================

class VectorIndex:
    """
    向量索引管理类（兼容旧版接口）
    
    基于 ChromaDB 实现文档节点的向量索引和检索
    """
    
    def __init__(self, persist_dir: str = None):
        """
        初始化向量索引
        
        参数:
            persist_dir: ChromaDB 持久化目录
        """
        self.persist_dir = persist_dir or CHROMA_PERSIST_DIR
        
        # 初始化 ChromaDB 客户端（持久化模式）
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="pageindex_nodes",
            metadata={"description": "PageIndex 文档节点向量索引"}
        )
        
        # 初始化 Embedding 模型
        self.embedding_model = OllamaEmbedding()
    
    def _get_node_text(self, node: Dict[str, Any]) -> str:
        """获取节点的主文本表示（用于生成主 embedding）"""
        title = node.get("title", "")
        summary = node.get("summary", "") or node.get("prefix_summary", "")
        if summary:
            return f"{title}: {summary}"
        return title

    def _prepare_node_vectors(self, node: Dict[str, Any], doc_name: str,
                               doc_description: str) -> List[Dict[str, Any]]:
        """
        为单个节点准备向量化数据（包含主向量和细分向量）

        返回:
            向量数据列表，每个元素包含 id, text, metadata
        """
        vectors = []
        title = node.get("title", "")
        summary = node.get("summary", "") or node.get("prefix_summary", "")
        key_points = node.get("key_points", []) or node.get("prefix_key_points", [])
        node_id = node.get("node_id", "")

        base_metadata = {
            "doc_name": doc_name,
            "doc_description": doc_description,
            "node_id": node_id,
            "title": title,
            "path": node.get("path", ""),
            "start_index": str(node.get("start_index", "")),
            "end_index": str(node.get("end_index", "")),
            "line_num": str(node.get("line_num", "")),
            "has_children": str(node.get("has_children", False)),
            "summary": summary[:500] if summary else ""
        }

        # 1. 主向量：title + summary
        if summary:
            vectors.append({
                "id": f"{doc_name}_{node_id}_main",
                "text": f"{title}: {summary}",
                "metadata": {**base_metadata, "vector_type": "main"}
            })

        # 2. 细分向量：每个 key_point 单独向量化
        for i, kp in enumerate(key_points):
            if kp:  # 确保 key_point 非空
                vectors.append({
                    "id": f"{doc_name}_{node_id}_kp_{i}",
                    "text": f"{title}: {kp}",
                    "metadata": {**base_metadata, "vector_type": "key_point", "key_point": kp[:200]}
                })

        # 3. 如果没有摘要和关键点，仅用标题
        if not vectors and title:
            vectors.append({
                "id": f"{doc_name}_{node_id}_title",
                "text": title,
                "metadata": {**base_metadata, "vector_type": "title_only"}
            })

        return vectors

    def _deduplicate_by_node(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按 node_id 去重，保留每个节点最高分的结果"""
        seen_nodes = {}
        for result in results:
            node_key = f"{result.get('doc_name', '')}_{result.get('node_id', '')}"
            if node_key not in seen_nodes or result.get('score', 0) > seen_nodes[node_key].get('score', 0):
                seen_nodes[node_key] = result
        return list(seen_nodes.values())

    def _flatten_structure(self, structure: Any, doc_name: str) -> List[Dict[str, Any]]:
        """将树结构扁平化为节点列表"""
        nodes = []

        def traverse(node, parent_path=""):
            if isinstance(node, dict):
                node_id = node.get("node_id", "")
                title = node.get("title", "")
                current_path = f"{parent_path}/{title}" if parent_path else title

                nodes.append({
                    "doc_name": doc_name,
                    "node_id": node_id,
                    "title": title,
                    "path": current_path,
                    "summary": node.get("summary", "") or node.get("prefix_summary", ""),
                    "key_points": node.get("key_points", []) or node.get("prefix_key_points", []),
                    "start_index": node.get("start_index"),
                    "end_index": node.get("end_index"),
                    "line_num": node.get("line_num"),
                    "has_children": bool(node.get("nodes")),
                    "text": node.get("text", "")
                })

                if node.get("nodes"):
                    for child in node["nodes"]:
                        traverse(child, current_path)

            elif isinstance(node, list):
                for item in node:
                    traverse(item, parent_path)

        traverse(structure)
        return nodes

    def add_document(self, doc_name: str, structure: Any, doc_description: str = "") -> int:
        """将文档添加到向量索引"""
        self.delete_document(doc_name)

        nodes = self._flatten_structure(structure, doc_name)

        if not nodes:
            return 0

        # 准备向量化数据（每个节点可能生成多条向量）
        all_vectors = []
        for node in nodes:
            vectors = self._prepare_node_vectors(node, doc_name, doc_description)
            all_vectors.extend(vectors)

        if not all_vectors:
            return 0

        # 提取数据
        ids = [v["id"] for v in all_vectors]
        texts = [v["text"] for v in all_vectors]
        metadatas = [v["metadata"] for v in all_vectors]

        print(f"正在为 {doc_name} 生成 {len(texts)} 个向量的 embedding...")
        embeddings = self.embedding_model.embed_batch(texts)

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=texts
        )

        print(f"已将 {len(nodes)} 个节点（{len(all_vectors)} 个向量）添加到向量索引")
        return len(all_vectors)

    def search(self, query: str, top_k: int = 10, doc_filter: List[str] = None) -> List[Dict[str, Any]]:
        """向量相似度检索（按 node_id 去重）"""
        query_embedding = self.embedding_model.embed(query)

        where_filter = None
        if doc_filter:
            if len(doc_filter) == 1:
                where_filter = {"doc_name": doc_filter[0]}
            else:
                where_filter = {"doc_name": {"$in": doc_filter}}

        # 多检索一些结果以应对去重后数量减少
        search_top_k = top_k * 3
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=search_top_k,
            where=where_filter,
            include=["metadatas", "distances", "documents"]
        )

        formatted_results = []
        if results and results["ids"] and results["ids"][0]:
            for i, id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                document = results["documents"][0][i] if results["documents"] else ""

                formatted_results.append({
                    "id": id,
                    "doc_name": metadata.get("doc_name", ""),
                    "doc_description": metadata.get("doc_description", ""),
                    "node_id": metadata.get("node_id", ""),
                    "title": metadata.get("title", ""),
                    "path": metadata.get("path", ""),
                    "start_index": metadata.get("start_index", ""),
                    "end_index": metadata.get("end_index", ""),
                    "line_num": metadata.get("line_num", ""),
                    "summary": metadata.get("summary", ""),
                    "has_children": metadata.get("has_children", "False") == "True",
                    "score": 1 - distance,
                    "document": document,
                    "vector_type": metadata.get("vector_type", ""),
                    "key_point": metadata.get("key_point", "")
                })

        # 按 node_id 去重，保留最高分
        deduplicated_results = self._deduplicate_by_node(formatted_results)

        # 按分数排序并返回 top_k
        deduplicated_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return deduplicated_results[:top_k]
    
    def delete_document(self, doc_name: str) -> int:
        """删除文档的向量索引"""
        try:
            results = self.collection.get(
                where={"doc_name": doc_name},
                include=["metadatas"]
            )
            
            if results and results["ids"]:
                self.collection.delete(ids=results["ids"])
                print(f"已删除 {doc_name} 的 {len(results['ids'])} 个节点索引")
                return len(results["ids"])
            
            return 0
        except Exception as e:
            print(f"删除文档索引失败: {e}")
            return 0
    
    def get_all_documents(self) -> List[str]:
        """获取所有已索引的文档名称"""
        try:
            results = self.collection.get(include=["metadatas"])
            if results and results["metadatas"]:
                doc_names = set()
                for metadata in results["metadatas"]:
                    if metadata.get("doc_name"):
                        doc_names.add(metadata["doc_name"])
                return list(doc_names)
            return []
        except Exception as e:
            print(f"获取文档列表失败: {e}")
            return []
    
    def get_document_node_count(self, doc_name: str) -> int:
        """获取文档的节点数量"""
        try:
            results = self.collection.get(
                where={"doc_name": doc_name},
                include=["metadatas"]
            )
            return len(results["ids"]) if results and results["ids"] else 0
        except Exception as e:
            print(f"获取节点数量失败: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取向量索引统计信息"""
        try:
            total_count = self.collection.count()
            documents = self.get_all_documents()
            
            return {
                "total_nodes": total_count,
                "total_documents": len(documents),
                "documents": documents
            }
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {"total_nodes": 0, "total_documents": 0, "documents": []}


# ============================================================================
# 全局实例和便捷函数
# ============================================================================

# 全局向量索引实例（兼容旧版）
_vector_index_instance = None

# 全局多知识库向量索引实例
_multi_kb_vector_index_instance = None


def get_vector_index() -> VectorIndex:
    """获取全局向量索引实例（单例模式，兼容旧版）"""
    global _vector_index_instance
    if _vector_index_instance is None:
        _vector_index_instance = VectorIndex()
    return _vector_index_instance


def get_multi_kb_vector_index() -> MultiKBVectorIndex:
    """获取全局多知识库向量索引实例（单例模式）"""
    global _multi_kb_vector_index_instance
    if _multi_kb_vector_index_instance is None:
        _multi_kb_vector_index_instance = MultiKBVectorIndex()
    return _multi_kb_vector_index_instance


def build_index_for_document(doc_name: str, structure: Any, doc_description: str = "") -> int:
    """为文档构建向量索引的便捷函数（兼容旧版）"""
    index = get_vector_index()
    return index.add_document(doc_name, structure, doc_description)


def search_documents(query: str, top_k: int = 10, doc_filter: List[str] = None) -> List[Dict[str, Any]]:
    """搜索文档的便捷函数（兼容旧版）"""
    index = get_vector_index()
    return index.search(query, top_k, doc_filter)


if __name__ == "__main__":
    # 测试代码
    print("测试向量索引模块...")
    
    # 测试 Embedding
    embedding_model = OllamaEmbedding()
    test_text = "这是一个测试文本"
    try:
        embedding = embedding_model.embed(test_text)
        print(f"Embedding 维度: {len(embedding)}")
        print("Embedding 模型连接成功！")
    except Exception as e:
        print(f"Embedding 模型连接失败: {e}")
    
    # 测试向量索引
    index = VectorIndex()
    stats = index.get_stats()
    print(f"向量索引统计: {stats}")
