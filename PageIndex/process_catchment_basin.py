"""
处理流域概况知识库文档
将uploads目录中的MD文件处理成结构化JSON并构建向量索引
"""

import asyncio
import os
import json
import sys

# 添加pageindex模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pageindex.page_index_md import md_to_tree
from pageindex.kb_manager import get_kb_manager


async def process_kb_documents(kb_id: str):
    """处理指定知识库的所有MD文档"""
    kb_manager = get_kb_manager()
    kb_info = kb_manager.get(kb_id)
    
    if not kb_info:
        print(f"错误: 知识库 '{kb_id}' 不存在")
        return
    
    uploads_dir = kb_manager.get_uploads_dir(kb_id)
    results_dir = kb_manager.get_results_dir(kb_id)
    
    # 确保results目录存在
    os.makedirs(results_dir, exist_ok=True)
    
    # 获取所有MD文件
    md_files = [f for f in os.listdir(uploads_dir) if f.endswith('.md')]
    
    if not md_files:
        print(f"在 {uploads_dir} 目录中没有找到任何MD文件")
        return
    
    print(f"\n[{kb_info.name}] 找到 {len(md_files)} 个MD文件")
    print("=" * 50)
    
    success_count = 0
    
    for i, filename in enumerate(md_files, 1):
        md_path = os.path.join(uploads_dir, filename)
        print(f"\n[{i}/{len(md_files)}] 正在处理: {filename}")
        
        try:
            # 处理MD文件生成结构化数据
            result = await md_to_tree(
                md_path=md_path,
                if_thinning=False,
                if_add_node_summary=True,
                if_add_doc_description=True,
                if_add_node_text=True,
                if_add_node_id=True,
                if_build_vector_index=False  # 先不构建向量索引，后面统一构建
            )
            
            # 保存结构文件
            doc_name = result.get('doc_name', filename.replace('.md', ''))
            output_path = os.path.join(results_dir, f"{doc_name}_structure.json")
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"  成功: 已保存到 {output_path}")
            success_count += 1
            
        except Exception as e:
            print(f"  失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"处理完成! 成功: {success_count}/{len(md_files)}")
    
    # 更新知识库统计
    kb_manager.update_stats(kb_id, doc_count=success_count)


if __name__ == "__main__":
    # 处理流域概况知识库
    asyncio.run(process_kb_documents("catchment_basin"))
