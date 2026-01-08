"""
批量构建向量索引脚本（多知识库版本）

遍历所有知识库的 results 文件夹中的 JSON 结构文件，为每个文档构建向量索引。
"""

import os
import json
import time
from pageindex.kb_manager import get_kb_manager
from pageindex.vector_index import MultiKBVectorIndex


def build_kb_index(kb_id: str, multi_kb_index: MultiKBVectorIndex, doc_delay: float = 1.0):
    """为指定知识库构建向量索引"""
    kb_manager = get_kb_manager()
    kb_info = kb_manager.get(kb_id)

    if not kb_info:
        print(f"错误: 知识库 '{kb_id}' 不存在")
        return 0, 0

    results_dir = kb_manager.get_results_dir(kb_id)
    chroma_dir = kb_manager.get_chroma_dir(kb_id)

    if not os.path.exists(results_dir):
        print(f"错误: {results_dir} 目录不存在")
        return 0, 0

    # 获取所有 JSON 结构文件
    structure_files = [f for f in os.listdir(results_dir) if f.endswith("_structure.json")]

    if not structure_files:
        print(f"在 {results_dir} 目录中没有找到任何结构文件")
        return 0, 0

    print(f"\n[{kb_info.name}] 找到 {len(structure_files)} 个结构文件")

    success_count = 0
    error_count = 0

    for i, filename in enumerate(structure_files, 1):
        filepath = os.path.join(results_dir, filename)
        print(f"  [{i}/{len(structure_files)}] 正在处理: {filename}")

        try:
            # 读取结构文件
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 提取文档信息
            doc_name = data.get("doc_name", filename.replace("_structure.json", ""))
            doc_description = data.get("doc_description", "")
            structure = data.get("structure", [])

            if not structure:
                print(f"    跳过: 结构为空")
                continue

            # 构建向量索引
            node_count = multi_kb_index.add_document(kb_id, chroma_dir, doc_name, structure, doc_description)
            print(f"    成功: 添加了 {node_count} 个节点")
            success_count += 1

            # 文档之间添加延迟，避免连接池问题
            if i < len(structure_files):
                time.sleep(doc_delay)

        except Exception as e:
            print(f"    失败: {str(e)}")
            error_count += 1

    return success_count, error_count


def build_all_indexes(kb_ids: list = None, doc_delay: float = 1.0):
    """
    为所有知识库（或指定知识库）构建向量索引

    参数:
        kb_ids: 要构建的知识库ID列表，为None时构建所有知识库
        doc_delay: 文档之间的延迟时间（秒）
    """
    kb_manager = get_kb_manager()
    multi_kb_index = MultiKBVectorIndex()

    # 获取要构建的知识库列表
    if kb_ids is None:
        kb_ids = kb_manager.list_ids()

    if not kb_ids:
        print("没有找到任何知识库")
        return

    print(f"准备为 {len(kb_ids)} 个知识库构建向量索引...")
    print("=" * 50)

    total_success = 0
    total_error = 0

    for kb_id in kb_ids:
        success, error = build_kb_index(kb_id, multi_kb_index, doc_delay)
        total_success += success
        total_error += error

    # 打印统计信息
    print("\n" + "=" * 50)
    print("构建完成!")
    print(f"总成功: {total_success} 个文档")
    print(f"总失败: {total_error} 个文档")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="构建知识库向量索引")
    parser.add_argument("--kb", type=str, help="指定知识库ID（不指定则构建所有知识库）")
    parser.add_argument("--delay", type=float, default=1.0, help="文档之间的延迟时间（秒）")

    args = parser.parse_args()

    if args.kb:
        build_all_indexes(kb_ids=[args.kb], doc_delay=args.delay)
    else:
        build_all_indexes(doc_delay=args.delay)
