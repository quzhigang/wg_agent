"""
初始化Web模板数据脚本

将预定义的模板注册到数据库和向量索引中
"""

import sys
import os
import json
import uuid

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.models.database import WebTemplate, SessionLocal, init_database
from src.output.template_vector_index import get_template_vector_index
from src.config.logging_config import setup_logging, get_logger

# 初始化日志
setup_logging()
logger = get_logger(__name__)


# 初始模板数据
INITIAL_TEMPLATES = [
    {
        "name": "res_flood_resultshow",
        "display_name": "单一水库的洪水预报、预演结果展示",
        "description": "用于展示单一水库的洪水预报、预演结果，包含地图定位、该水库入库/出库流量曲线、水位变化图表、关键指标卡片。支持动态数据注入，可展示任意水库的预报预演结果。",
        "template_path": "res_module/index.html",
        "supported_sub_intents": ["flood_forecast", "data_query"],
        "template_type": "full_page",
        "trigger_pattern": "单一水库预报预演结果 洪水预报 洪水预演 入库流量 出库流量 水位变化 预报方案结果 水库水情 水库洪水 盘石头水库 水库调度",
        "features": ["map", "chart", "realtime", "reservoir", "echarts"],
        "priority": 10
    },
    # 预留：站点洪水预报模板
    # {
    #     "name": "station_flood_forecast",
    #     "display_name": "站点洪水预报结果展示",
    #     "description": "用于展示河道站点洪水预报结果，包含流量过程线、水位变化、洪峰信息等。",
    #     "template_path": "station_module/index.html",
    #     "supported_sub_intents": ["flood_forecast", "data_query"],
    #     "template_type": "full_page",
    #     "trigger_pattern": "站点预报 河道水位 洪峰流量 断面流量 水文站",
    #     "features": ["chart", "station", "echarts"],
    #     "priority": 8
    # },
    # 预留：蓄滞洪区预报模板
    # {
    #     "name": "detention_basin_forecast",
    #     "display_name": "蓄滞洪区预报结果展示",
    #     "description": "用于展示蓄滞洪区预报结果，包含进洪流量、蓄水量、淹没范围等信息。",
    #     "template_path": "detention_module/index.html",
    #     "supported_sub_intents": ["flood_forecast", "flood_simulation"],
    #     "template_type": "full_page",
    #     "trigger_pattern": "蓄滞洪区 分洪 滞洪 进洪 淹没",
    #     "features": ["map", "chart", "detention"],
    #     "priority": 8
    # },
]


def init_templates():
    """初始化模板数据"""
    logger.info("开始初始化Web模板数据...")

    # 初始化数据库
    init_database()

    db = SessionLocal()
    template_index = get_template_vector_index()

    try:
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for tpl_data in INITIAL_TEMPLATES:
            name = tpl_data["name"]

            # 检查是否已存在
            existing = db.query(WebTemplate).filter(WebTemplate.name == name).first()

            if existing:
                # 更新现有模板
                logger.info(f"模板 {name} 已存在，更新数据...")
                existing.display_name = tpl_data["display_name"]
                existing.description = tpl_data["description"]
                existing.template_path = tpl_data["template_path"]
                existing.supported_sub_intents = json.dumps(tpl_data["supported_sub_intents"], ensure_ascii=False)
                existing.template_type = tpl_data["template_type"]
                existing.trigger_pattern = tpl_data["trigger_pattern"]
                existing.features = json.dumps(tpl_data["features"], ensure_ascii=False)
                existing.priority = tpl_data["priority"]
                existing.is_active = True

                db.commit()

                # 更新向量索引
                template_index.index_template(existing.id, {
                    "name": existing.name,
                    "display_name": existing.display_name,
                    "description": existing.description,
                    "trigger_pattern": existing.trigger_pattern,
                    "supported_sub_intents": tpl_data["supported_sub_intents"],
                    "template_path": existing.template_path,
                    "template_type": existing.template_type,
                    "priority": existing.priority
                })

                updated_count += 1
            else:
                # 创建新模板
                logger.info(f"创建新模板: {name}")
                template_id = str(uuid.uuid4())

                template = WebTemplate(
                    id=template_id,
                    name=name,
                    display_name=tpl_data["display_name"],
                    description=tpl_data["description"],
                    template_path=tpl_data["template_path"],
                    supported_sub_intents=json.dumps(tpl_data["supported_sub_intents"], ensure_ascii=False),
                    template_type=tpl_data["template_type"],
                    trigger_pattern=tpl_data["trigger_pattern"],
                    features=json.dumps(tpl_data["features"], ensure_ascii=False),
                    priority=tpl_data["priority"],
                    is_active=True
                )

                db.add(template)
                db.commit()

                # 添加到向量索引
                template_index.index_template(template_id, {
                    "name": name,
                    "display_name": tpl_data["display_name"],
                    "description": tpl_data["description"],
                    "trigger_pattern": tpl_data["trigger_pattern"],
                    "supported_sub_intents": tpl_data["supported_sub_intents"],
                    "template_path": tpl_data["template_path"],
                    "template_type": tpl_data["template_type"],
                    "priority": tpl_data["priority"]
                })

                created_count += 1

        logger.info(f"模板初始化完成: 创建 {created_count} 个, 更新 {updated_count} 个, 跳过 {skipped_count} 个")

        # 显示向量索引统计
        stats = template_index.get_stats()
        logger.info(f"向量索引统计: {stats}")

    except Exception as e:
        logger.error(f"初始化模板失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def rebuild_vector_index():
    """重建向量索引"""
    logger.info("重建模板向量索引...")
    template_index = get_template_vector_index()
    count = template_index.rebuild_index_from_db()
    logger.info(f"向量索引重建完成，共索引 {count} 个模板")


def list_templates():
    """列出所有模板"""
    db = SessionLocal()
    try:
        templates = db.query(WebTemplate).all()
        print(f"\n{'='*60}")
        print(f"共 {len(templates)} 个模板:")
        print(f"{'='*60}")
        for tpl in templates:
            status = "✓ 启用" if tpl.is_active else "✗ 禁用"
            print(f"\n[{tpl.id[:8]}] {tpl.display_name}")
            print(f"  名称: {tpl.name}")
            print(f"  路径: {tpl.template_path}")
            print(f"  子意图: {tpl.supported_sub_intents}")
            print(f"  优先级: {tpl.priority}")
            print(f"  状态: {status}")
            print(f"  使用次数: {tpl.use_count}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Web模板初始化工具")
    parser.add_argument("--rebuild", action="store_true", help="重建向量索引")
    parser.add_argument("--list", action="store_true", help="列出所有模板")
    args = parser.parse_args()

    if args.rebuild:
        rebuild_vector_index()
    elif args.list:
        list_templates()
    else:
        init_templates()
