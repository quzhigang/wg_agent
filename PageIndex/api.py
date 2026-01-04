"""
PageIndex 多知识库检索 API

支持多知识库的文档检索和问答功能。
"""

import os
import re
import json
import asyncio
from typing import List, Optional
from fastapi import FastAPI, Query
from pydantic import BaseModel
from pageindex.utils import ConfigLoader, ChatGPT_API, ChatGPT_API_async, get_text_of_pages, remove_fields
from pageindex.vector_index import get_vector_index, search_documents, get_multi_kb_vector_index
from pageindex.kb_manager import get_kb_manager, KnowledgeBaseInfo
import uvicorn

app = FastAPI(title="PageIndex Multi-KB Retrieval API")


# ============================================================================
# 请求模型
# ============================================================================

class QueryRequest(BaseModel):
    """查询请求"""
    q: str                                    # 查询文本
    top_k: int = 10                           # 向量检索返回的最大结果数
    kb_ids: Optional[List[str]] = None        # 指定知识库ID列表，为空则搜索所有知识库


class KBCreateRequest(BaseModel):
    """创建知识库请求"""
    id: str                                   # 知识库ID（英文/拼音）
    name: str                                 # 知识库名称（中文）
    description: str = ""                     # 知识库描述（可选）


# ============================================================================
# 配置
# ============================================================================

config_loader = ConfigLoader()
default_config = config_loader.load()
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME") or os.getenv("CHATGPT_MODEL", "gpt-4o")

# 图片引用正则表达式
IMAGE_PATTERN = re.compile(r'\s*\n!\[\]\(images/([a-zA-Z0-9]+)\.jpg\)\s*\n')
IMAGE_CAPTION_PATTERN = re.compile(r'^图\s*[\d\.\-\s]+\s*(.+)$')
IMAGE_WITH_CAPTION_PATTERN = re.compile(r'\s*\n!\[\]\(images/([a-zA-Z0-9]+)\.jpg\)\s*\n(图\s*[\d\.\-\s]+[^\n]*)\s*\n?')
STANDALONE_CAPTION_PATTERN = re.compile(r'\n(图\s*[\d\.\-\s]+[^\n]*)\s*\n')


# ============================================================================
# 辅助函数
# ============================================================================

def extract_image_info(text: str) -> list:
    """从文本中提取所有图片信息"""
    if not text:
        return []
    
    results = []
    for match in IMAGE_WITH_CAPTION_PATTERN.finditer(text):
        code = match.group(1)
        caption_line = match.group(2).strip()
        caption_match = IMAGE_CAPTION_PATTERN.match(caption_line)
        caption = caption_match.group(1).strip() if caption_match else caption_line
        results.append({"code": code, "caption": caption})
    
    all_codes = set(IMAGE_PATTERN.findall(text))
    found_codes = set(item["code"] for item in results)
    for code in all_codes - found_codes:
        results.append({"code": code, "caption": ""})
    
    return results


def extract_image_codes(text: str) -> list:
    """从文本中提取所有图片编码"""
    if not text:
        return []
    return IMAGE_PATTERN.findall(text)


def remove_image_references(text: str) -> str:
    """删除文本中的所有图片引用和图名"""
    if not text:
        return text
    text = IMAGE_WITH_CAPTION_PATTERN.sub('\n', text)
    text = IMAGE_PATTERN.sub('\n', text)
    text = STANDALONE_CAPTION_PATTERN.sub('\n', text)
    return text


def get_image_info_list(image_info: list, upload_dir: str) -> list:
    """根据图片信息列表获取完整的图片路径和图名列表"""
    results = []
    for item in image_info:
        image_path = os.path.join(upload_dir, "images", f"{item['code']}.jpg")
        if os.path.exists(image_path):
            results.append({"path": image_path, "caption": item.get("caption", "")})
    return results


def get_image_paths(image_codes: list, upload_dir: str) -> list:
    """根据图片编码获取完整的图片路径列表"""
    paths = []
    for code in image_codes:
        image_path = os.path.join(upload_dir, "images", f"{code}.jpg")
        if os.path.exists(image_path):
            paths.append(image_path)
    return paths


def get_node_mapping(structure, mapping=None):
    """从树结构中构建 node_id 到节点的映射"""
    if mapping is None: 
        mapping = {}
    if isinstance(structure, list):
        for item in structure:
            get_node_mapping(item, mapping)
    elif isinstance(structure, dict):
        if 'node_id' in structure:
            mapping[structure['node_id']] = structure
        if 'nodes' in structure:
            get_node_mapping(structure['nodes'], mapping)
    return mapping


def load_document_structure(doc_name: str, results_dir: str):
    """加载文档的结构 JSON 文件"""
    possible_names = [
        f"{doc_name}_structure.json",
        f"{doc_name.replace('.pdf', '')}_structure.json",
        f"{doc_name.replace('.md', '')}_structure.json",
    ]
    
    for name in possible_names:
        path = os.path.join(results_dir, name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    return None


def get_document_file_path(doc_name: str, upload_dir: str):
    """获取文档的原始文件路径"""
    for ext in ["", ".pdf", ".md", ".markdown"]:
        path = os.path.join(upload_dir, doc_name + ext)
        if os.path.exists(path):
            return path
    
    base_name = doc_name.replace("_structure.json", "")
    for ext in ["", ".pdf", ".md", ".markdown"]:
        path = os.path.join(upload_dir, base_name + ext)
        if os.path.exists(path):
            return path
    
    return None


# ============================================================================
# 知识库管理接口
# ============================================================================

@app.get("/kb/list")
async def list_knowledge_bases():
    """列出所有知识库"""
    try:
        kb_manager = get_kb_manager()
        kb_list = kb_manager.list_all()
        
        # 更新每个知识库的统计信息
        multi_kb_index = get_multi_kb_vector_index()
        result = []
        for kb in kb_list:
            try:
                stats = multi_kb_index.get_stats(kb.id, kb_manager.get_chroma_dir(kb.id))
                kb.doc_count = stats.get("total_documents", 0)
                kb.node_count = stats.get("total_nodes", 0)
            except:
                pass
            result.append(kb.to_dict())
        
        return {
            "status": "ok",
            "total": len(result),
            "knowledge_bases": result
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/kb/create")
async def create_knowledge_base(request: KBCreateRequest):
    """创建新知识库"""
    try:
        kb_manager = get_kb_manager()
        
        # 检查ID是否已存在
        if kb_manager.exists(request.id):
            return {
                "status": "error",
                "message": f"知识库ID '{request.id}' 已存在，请使用其他ID"
            }
        
        kb_info = kb_manager.create(request.id, request.name, request.description)
        
        return {
            "status": "ok",
            "message": f"知识库 '{request.name}' 创建成功",
            "knowledge_base": kb_info.to_dict()
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.delete("/kb/{kb_id}")
async def delete_knowledge_base(kb_id: str):
    """删除知识库"""
    try:
        kb_manager = get_kb_manager()
        
        if not kb_manager.exists(kb_id):
            return {
                "status": "error",
                "message": f"知识库 '{kb_id}' 不存在"
            }
        
        success = kb_manager.delete(kb_id)
        
        if success:
            # 清除向量索引缓存
            multi_kb_index = get_multi_kb_vector_index()
            multi_kb_index.clear_cache(kb_id)
            
            return {
                "status": "ok",
                "message": f"知识库 '{kb_id}' 已删除"
            }
        else:
            return {
                "status": "error",
                "message": "删除失败"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/kb/{kb_id}")
async def get_knowledge_base(kb_id: str):
    """获取知识库详情"""
    try:
        kb_manager = get_kb_manager()
        kb_info = kb_manager.get(kb_id)
        
        if not kb_info:
            return {
                "status": "error",
                "message": f"知识库 '{kb_id}' 不存在"
            }
        
        # 获取统计信息
        multi_kb_index = get_multi_kb_vector_index()
        try:
            stats = multi_kb_index.get_stats(kb_id, kb_manager.get_chroma_dir(kb_id))
            kb_info.doc_count = stats.get("total_documents", 0)
            kb_info.node_count = stats.get("total_nodes", 0)
        except:
            pass
        
        return {
            "status": "ok",
            "knowledge_base": kb_info.to_dict()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# 多知识库检索接口
# ============================================================================

@app.post("/query")
async def query_documents(request: QueryRequest):
    """
    多知识库向量检索问答
    
    参数:
        q: 查询文本
        top_k: 返回结果数量
        kb_ids: 指定知识库ID列表，为空则搜索所有知识库
    """
    q = request.q
    top_k = request.top_k
    kb_ids = request.kb_ids
    
    kb_manager = get_kb_manager()
    multi_kb_index = get_multi_kb_vector_index()
    
    # 确定要搜索的知识库
    if kb_ids:
        # 验证知识库是否存在
        valid_kb_ids = [kb_id for kb_id in kb_ids if kb_manager.exists(kb_id)]
        if not valid_kb_ids:
            return {
                "answer": "指定的知识库不存在。",
                "sources": [],
                "thinking": f"请求的知识库: {kb_ids}"
            }
    else:
        # 搜索所有知识库
        valid_kb_ids = kb_manager.list_ids()
    
    if not valid_kb_ids:
        return {
            "answer": "没有可用的知识库，请先创建知识库并上传文档。",
            "sources": [],
            "thinking": "系统中没有任何知识库。"
        }
    
    # 构建知识库配置
    kb_configs = [
        {"kb_id": kb_id, "chroma_dir": kb_manager.get_chroma_dir(kb_id)}
        for kb_id in valid_kb_ids
    ]
    
    # 执行跨知识库检索
    try:
        search_results = multi_kb_index.search_multi_kb(kb_configs, q, top_k)
    except Exception as e:
        return {
            "answer": f"向量检索失败: {str(e)}",
            "sources": [],
            "thinking": "请检查 Embedding 模型服务是否正常运行。"
        }
    
    if not search_results:
        return {
            "answer": "未找到与问题相关的文档内容。",
            "sources": [],
            "thinking": f"在 {len(valid_kb_ids)} 个知识库中未找到相关内容。"
        }
    
    # 内容提取
    all_relevant_text = ""
    all_reference_nodes = []
    thinking_parts = [f"在 {len(valid_kb_ids)} 个知识库中检索，返回 {len(search_results)} 个相关节点"]
    
    # 按知识库和文档分组处理结果
    kb_doc_results = {}
    for result in search_results:
        kb_id = result.get("kb_id", "")
        doc_name = result.get("doc_name", "")
        key = (kb_id, doc_name)
        if key not in kb_doc_results:
            kb_doc_results[key] = []
        kb_doc_results[key].append(result)
    
    for (kb_id, doc_name), results in kb_doc_results.items():
        kb_info = kb_manager.get(kb_id)
        kb_name = kb_info.name if kb_info else kb_id
        results_dir = kb_manager.get_results_dir(kb_id)
        upload_dir = kb_manager.get_uploads_dir(kb_id)
        
        doc_data = load_document_structure(doc_name, results_dir)
        if not doc_data:
            thinking_parts.append(f"[{kb_name}/{doc_name}] 未找到结构文件")
            continue
        
        node_map = get_node_mapping(doc_data.get("structure", []))
        doc_file_path = get_document_file_path(doc_name, upload_dir)
        
        for result in results:
            node_id = result.get("node_id", "")
            title = result.get("title", "")
            score = result.get("score", 0)
            
            all_reference_nodes.append(f"[{kb_name}] {doc_name} - {title} (相似度: {score:.3f})")
            
            node = node_map.get(node_id)
            if node:
                if node.get("text"):
                    clean_text = remove_image_references(node['text'])
                    all_relevant_text += f"\n--- 知识库: {kb_name}, 文档: {doc_name}, 章节: {title} ---\n{clean_text}\n"
                elif doc_file_path and doc_file_path.lower().endswith(".pdf"):
                    try:
                        start_page = node.get("start_index")
                        end_page = node.get("end_index")
                        if start_page and end_page:
                            page_text = get_text_of_pages(doc_file_path, start_page, end_page, tag=False)
                            clean_text = remove_image_references(page_text)
                            all_relevant_text += f"\n--- 知识库: {kb_name}, 文档: {doc_name}, 章节: {title} ---\n{clean_text}\n"
                    except Exception as e:
                        thinking_parts.append(f"[{kb_name}/{doc_name}] 提取页面内容失败: {e}")
                elif result.get("summary"):
                    clean_summary = remove_image_references(result['summary'])
                    all_relevant_text += f"\n--- 知识库: {kb_name}, 文档: {doc_name}, 章节: {title} (摘要) ---\n{clean_summary}\n"
    
    # 答案生成
    if not all_relevant_text.strip():
        return {
            "answer": "检索到相关节点，但未能提取到有效内容。请确保文档已正确处理。",
            "sources": all_reference_nodes,
            "thinking": "\n".join(thinking_parts)
        }
    
    answer_prompt = f"""你是一个专业的研究助手。你有来自多个知识库和文档的内容片段。
根据提供的上下文回答用户的问题。
如果来源有冲突的信息，请提及。
在回答中始终引用知识库和文档名称。

问题: {q}

上下文:
{all_relevant_text[:15000]}

助手:"""
    
    try:
        full_answer = ChatGPT_API(model=MODEL_NAME, prompt=answer_prompt)
    except Exception as e:
        full_answer = f"答案生成失败: {str(e)}"
    
    return {
        "answer": full_answer,
        "sources": all_reference_nodes,
        "thinking": "\n".join(thinking_parts),
        "searched_kb": valid_kb_ids
    }


@app.post("/query/raw")
async def query_documents_raw(request: QueryRequest):
    """
    多知识库向量检索，只返回原始检索结果（不调用大模型）
    
    参数:
        q: 查询文本
        top_k: 返回结果数量
        kb_ids: 指定知识库ID列表，为空则搜索所有知识库
    """
    q = request.q
    top_k = request.top_k
    kb_ids = request.kb_ids
    
    kb_manager = get_kb_manager()
    multi_kb_index = get_multi_kb_vector_index()
    
    # 确定要搜索的知识库
    if kb_ids:
        valid_kb_ids = [kb_id for kb_id in kb_ids if kb_manager.exists(kb_id)]
        if not valid_kb_ids:
            return {
                "status": "error",
                "message": "指定的知识库不存在",
                "results": []
            }
    else:
        valid_kb_ids = kb_manager.list_ids()
    
    if not valid_kb_ids:
        return {
            "status": "error",
            "message": "没有可用的知识库",
            "results": []
        }
    
    # 构建知识库配置
    kb_configs = [
        {"kb_id": kb_id, "chroma_dir": kb_manager.get_chroma_dir(kb_id)}
        for kb_id in valid_kb_ids
    ]
    
    # 执行跨知识库检索
    try:
        search_results = multi_kb_index.search_multi_kb(kb_configs, q, top_k)
    except Exception as e:
        return {
            "status": "error",
            "message": f"向量检索失败: {str(e)}",
            "results": []
        }
    
    if not search_results:
        return {
            "status": "ok",
            "message": "未找到与问题相关的文档内容",
            "query": q,
            "searched_kb": valid_kb_ids,
            "total_results": 0,
            "results": []
        }
    
    # 内容提取
    enriched_results = []
    
    for result in search_results:
        kb_id = result.get("kb_id", "")
        doc_name = result.get("doc_name", "")
        node_id = result.get("node_id", "")
        title = result.get("title", "")
        score = result.get("score", 0)
        summary = result.get("summary", "")
        
        kb_info = kb_manager.get(kb_id)
        kb_name = kb_info.name if kb_info else kb_id
        results_dir = kb_manager.get_results_dir(kb_id)
        upload_dir = kb_manager.get_uploads_dir(kb_id)
        
        text = None
        doc_data = load_document_structure(doc_name, results_dir)
        
        if doc_data:
            node_map = get_node_mapping(doc_data.get("structure", []))
            node = node_map.get(node_id)
            
            if node:
                if node.get("text"):
                    text = node["text"]
                else:
                    doc_file_path = get_document_file_path(doc_name, upload_dir)
                    if doc_file_path and doc_file_path.lower().endswith(".pdf"):
                        try:
                            start_page = node.get("start_index")
                            end_page = node.get("end_index")
                            if start_page and end_page:
                                text = get_text_of_pages(doc_file_path, start_page, end_page, tag=False)
                        except:
                            pass
        
        # 提取图片信息
        summary_image_info = extract_image_info(summary)
        text_image_info = extract_image_info(text) if text else []
        
        seen_codes = set()
        all_image_info = []
        for info in summary_image_info + text_image_info:
            if info["code"] not in seen_codes:
                seen_codes.add(info["code"])
                all_image_info.append(info)
        
        clean_summary = remove_image_references(summary)
        clean_text = remove_image_references(text) if text else None
        
        enriched_result = {
            "kb_id": kb_id,
            "kb_name": kb_name,
            "doc_name": doc_name,
            "node_id": node_id,
            "title": title,
            "score": score,
            "summary": clean_summary,
            "text": clean_text,
            "images": get_image_info_list(all_image_info, upload_dir)
        }
        
        enriched_results.append(enriched_result)
    
    return {
        "status": "ok",
        "query": q,
        "searched_kb": valid_kb_ids,
        "total_results": len(enriched_results),
        "results": enriched_results
    }


# ============================================================================
# 索引管理接口
# ============================================================================

@app.get("/kb/{kb_id}/index/stats")
async def get_kb_index_stats(kb_id: str):
    """获取指定知识库的向量索引统计信息"""
    try:
        kb_manager = get_kb_manager()
        
        if not kb_manager.exists(kb_id):
            return {
                "status": "error",
                "message": f"知识库 '{kb_id}' 不存在"
            }
        
        multi_kb_index = get_multi_kb_vector_index()
        stats = multi_kb_index.get_stats(kb_id, kb_manager.get_chroma_dir(kb_id))
        
        return {
            "status": "ok",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/kb/{kb_id}/index/rebuild")
async def rebuild_kb_index(kb_id: str):
    """重建指定知识库的向量索引"""
    try:
        kb_manager = get_kb_manager()
        
        if not kb_manager.exists(kb_id):
            return {
                "status": "error",
                "message": f"知识库 '{kb_id}' 不存在"
            }
        
        results_dir = kb_manager.get_results_dir(kb_id)
        chroma_dir = kb_manager.get_chroma_dir(kb_id)
        
        if not os.path.exists(results_dir):
            return {"status": "error", "message": "results 目录不存在"}
        
        structure_files = [f for f in os.listdir(results_dir) if f.endswith("_structure.json")]
        
        if not structure_files:
            return {"status": "error", "message": "没有找到任何结构文件"}
        
        multi_kb_index = get_multi_kb_vector_index()
        rebuilt_count = 0
        errors = []
        
        for filename in structure_files:
            try:
                filepath = os.path.join(results_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                doc_name = data.get("doc_name", filename.replace("_structure.json", ""))
                doc_description = data.get("doc_description", "")
                structure = data.get("structure", [])
                
                node_count = multi_kb_index.add_document(kb_id, chroma_dir, doc_name, structure, doc_description)
                rebuilt_count += 1
                print(f"已重建 [{kb_id}] {doc_name} 的索引，共 {node_count} 个节点")
                
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
        
        return {
            "status": "ok",
            "kb_id": kb_id,
            "rebuilt_documents": rebuilt_count,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.delete("/kb/{kb_id}/index/{doc_name}")
async def delete_kb_document_index(kb_id: str, doc_name: str):
    """删除指定知识库中文档的向量索引"""
    try:
        kb_manager = get_kb_manager()
        
        if not kb_manager.exists(kb_id):
            return {
                "status": "error",
                "message": f"知识库 '{kb_id}' 不存在"
            }
        
        multi_kb_index = get_multi_kb_vector_index()
        deleted_count = multi_kb_index.delete_document(kb_id, kb_manager.get_chroma_dir(kb_id), doc_name)
        
        return {
            "status": "ok",
            "kb_id": kb_id,
            "doc_name": doc_name,
            "deleted_nodes": deleted_count
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


# ============================================================================
# 兼容旧版接口（使用默认单知识库）
# ============================================================================

# 旧版目录配置
RESULTS_DIR = os.getenv("PAGEINDEX_RESULTS_DIR", "./PageIndex/results")
UPLOAD_DIR = os.getenv("PAGEINDEX_UPLOAD_DIR", "./PageIndex/uploads")


@app.get("/index/stats")
async def get_index_stats():
    """获取向量索引统计信息（兼容旧版）"""
    try:
        vector_index = get_vector_index()
        stats = vector_index.get_stats()
        return {
            "status": "ok",
            "stats": stats
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.post("/index/rebuild")
async def rebuild_index():
    """重建所有文档的向量索引（兼容旧版）"""
    try:
        vector_index = get_vector_index()
        
        if not os.path.exists(RESULTS_DIR):
            return {"status": "error", "message": "results 目录不存在"}
        
        structure_files = [f for f in os.listdir(RESULTS_DIR) if f.endswith("_structure.json")]
        
        if not structure_files:
            return {"status": "error", "message": "没有找到任何结构文件"}
        
        rebuilt_count = 0
        errors = []
        
        for filename in structure_files:
            try:
                filepath = os.path.join(RESULTS_DIR, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                doc_name = data.get("doc_name", filename.replace("_structure.json", ""))
                doc_description = data.get("doc_description", "")
                structure = data.get("structure", [])
                
                node_count = vector_index.add_document(doc_name, structure, doc_description)
                rebuilt_count += 1
                print(f"已重建 {doc_name} 的索引，共 {node_count} 个节点")
                
            except Exception as e:
                errors.append(f"{filename}: {str(e)}")
        
        return {
            "status": "ok",
            "rebuilt_documents": rebuilt_count,
            "errors": errors if errors else None
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@app.delete("/index/{doc_name}")
async def delete_document_index(doc_name: str):
    """删除指定文档的向量索引（兼容旧版）"""
    try:
        vector_index = get_vector_index()
        deleted_count = vector_index.delete_document(doc_name)
        return {
            "status": "ok",
            "deleted_nodes": deleted_count
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8502)
