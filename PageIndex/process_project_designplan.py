"""
处理工程治理知识库文档
将开发资料中的MD文件复制到知识库uploads目录，处理成结构化JSON并构建向量索引
"""

import asyncio
import os
import json
import sys
import shutil
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加pageindex模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pageindex.page_index_md import md_to_tree
from pageindex.kb_manager import get_kb_manager
from pageindex.vector_index import get_multi_kb_vector_index

# 知识库ID
KB_ID = "project_designplan"

# 模型名称
MODEL_NAME = os.getenv("OPENAI_MODEL_NAME") or os.getenv("CHATGPT_MODEL", "gpt-4o")

# 源文档目录
SOURCE_DIR = r"c:\Users\15257\Desktop\wg_agent\开发资料\知识库文档\10、工程治理"


def collect_md_files(source_dir):
    """递归收集所有MD文件及其images目录"""
    md_files = []

    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.md'):
                md_path = os.path.join(root, file)
                # 检查同级是否有images目录
                images_dir = os.path.join(root, 'images')
                has_images = os.path.isdir(images_dir)
                md_files.append({
                    'md_path': md_path,
                    'md_name': file,
                    'images_dir': images_dir if has_images else None
                })

    return md_files


def copy_files_to_kb(md_files, uploads_dir):
    """复制MD文件和images目录到知识库uploads目录"""
    copied_files = []

    for item in md_files:
        md_src = item['md_path']
        md_name = item['md_name']
        md_dst = os.path.join(uploads_dir, md_name)

        # 复制MD文件
        shutil.copy2(md_src, md_dst)
        copied_files.append(md_dst)
        print(f"  复制: {md_name}")

        # 复制images目录（如果存在）
        if item['images_dir']:
            images_dst = os.path.join(uploads_dir, 'images')
            if not os.path.exists(images_dst):
                os.makedirs(images_dst)

            # 复制images目录中的所有文件
            for img_file in os.listdir(item['images_dir']):
                img_src = os.path.join(item['images_dir'], img_file)
                img_dst = os.path.join(images_dst, img_file)
                if os.path.isfile(img_src) and not os.path.exists(img_dst):
                    shutil.copy2(img_src, img_dst)

    return copied_files


async def process_single_document(md_path, results_dir):
    """处理单个MD文档"""
    filename = os.path.basename(md_path)

    try:
        result = await md_to_tree(
            md_path=md_path,
            if_thinning=False,
            if_add_node_summary=True,
            model=MODEL_NAME,
            if_add_doc_description=True,
            if_add_node_text=True,
            if_add_node_id=True,
            if_build_vector_index=False
        )

        # 保存结构文件
        doc_name = result.get('doc_name', filename.replace('.md', ''))
        output_path = os.path.join(results_dir, f"{doc_name}_structure.json")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return {'success': True, 'doc_name': doc_name, 'result': result, 'output_path': output_path}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e), 'filename': filename}


async def main():
    """主函数"""
    kb_manager = get_kb_manager()
    kb_info = kb_manager.get(KB_ID)

    if not kb_info:
        print(f"错误: 知识库 '{KB_ID}' 不存在")
        return

    uploads_dir = kb_manager.get_uploads_dir(KB_ID)
    results_dir = kb_manager.get_results_dir(KB_ID)
    chroma_dir = kb_manager.get_chroma_dir(KB_ID)

    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"工程治理知识库文档处理")
    print(f"{'='*60}")

    # 1. 收集所有MD文件
    print(f"\n[步骤1] 扫描源目录: {SOURCE_DIR}")
    md_files = collect_md_files(SOURCE_DIR)
    print(f"找到 {len(md_files)} 个MD文件")

    # 2. 复制文件到知识库
    print(f"\n[步骤2] 复制文件到知识库uploads目录")
    copied_files = copy_files_to_kb(md_files, uploads_dir)
    print(f"已复制 {len(copied_files)} 个文件")

    # 3. 处理MD文件生成结构化JSON
    print(f"\n[步骤3] 处理MD文件生成结构化JSON")
    success_count = 0
    failed_files = []
    processed_results = []

    for i, md_path in enumerate(copied_files, 1):
        filename = os.path.basename(md_path)
        print(f"\n[{i}/{len(copied_files)}] 正在处理: {filename}")

        result = await process_single_document(md_path, results_dir)

        if result['success']:
            print(f"  成功: 已保存到 {result['output_path']}")
            success_count += 1
            processed_results.append(result)
        else:
            print(f"  失败: {result['error']}")
            failed_files.append(result['filename'])

    # 4. 构建向量索引
    print(f"\n[步骤4] 构建向量索引")
    multi_kb_index = get_multi_kb_vector_index()
    index_count = 0

    for result in processed_results:
        try:
            doc_name = result['doc_name']
            doc_description = result['result'].get('doc_description', '')
            structure = result['result'].get('structure', [])

            node_count = multi_kb_index.add_document(
                KB_ID, chroma_dir, doc_name, structure, doc_description
            )
            index_count += 1
            print(f"  已索引: {doc_name} ({node_count} 个节点)")
        except Exception as e:
            print(f"  索引失败: {result['doc_name']} - {e}")

    # 5. 更新知识库统计
    kb_manager.update_stats(KB_ID, doc_count=success_count)

    # 6. 输出总结
    print(f"\n{'='*60}")
    print(f"处理完成!")
    print(f"{'='*60}")
    print(f"总文件数: {len(md_files)}")
    print(f"成功处理: {success_count}")
    print(f"成功索引: {index_count}")

    if failed_files:
        print(f"\n失败文件 ({len(failed_files)}):")
        for f in failed_files:
            print(f"  - {f}")


if __name__ == "__main__":
    asyncio.run(main())
