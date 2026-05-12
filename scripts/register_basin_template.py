"""
全流域洪水预报结果模板注册脚本

将 basin_module 预定义模板注册到数据库，并构建/更新向量索引。
"""

import json
import os
import sys
import uuid

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.config.logging_config import get_logger, setup_logging
from src.models.database import SessionLocal, WebTemplate, init_database
from src.output.template_vector_index import get_template_vector_index


setup_logging()
logger = get_logger(__name__)


BASIN_TEMPLATE = {
    "name": "basin_flood_forecast",
    "display_name": "全流域洪水预报结果展示",
    "description": (
        "用于展示全流域洪水预报结果，基于方案ID直接获取模型结果，综合展示水库、河道和蓄滞洪区三类预报对象。"
        "页面包含流域地图、三类对象特征值列表、交互式过程曲线；点击任一水库、水文站点或蓄滞洪区后，图表区切换展示对应过程。"
        "水库曲线展示降雨、入库流量、出库流量、库水位；河道曲线展示降雨、水位、流量；蓄滞洪区曲线展示启用状态、进出洪流量、滞洪水位、滞洪量和淹没面积。"
    ),
    "template_path": "basin_module/index.html",
    "supported_sub_intents": ["flood_forecast", "data_query", "flood_simulation"],
    "template_type": "full_page",
    "trigger_pattern": (
        "全流域洪水预报 全流域预报结果 流域洪水结果 流域洪水预演 卫共流域洪水预报 "
        "水库河道蓄滞洪区综合展示 方案结果 流域态势 洪水预报结果"
    ),
    "features": ["map", "chart", "basin", "reservoir", "river", "detention", "echarts", "interactive"],
    "priority": 12,
    "required_object_types": ["流域", "全流域", "卫共流域"],
    "replacement_config": {
        "mode": "regex_replace",
        "target_file": "js/main.js",
        "mappings": [
            {
                "context_path": "steps.forecast.planCode",
                "target_key": "DEFAULT_PARAMS.planCode",
                "pattern": r"planCode:\s*['\"][^'\"]*['\"]",
                "replacement_template": "planCode: '{value}'",
                "param_name": "planCode",
                "param_desc": "洪水预报方案ID"
            }
        ],
        "default_values": {
            "DEFAULT_PARAMS.planCode": "model_auto"
        },
        "required_context_keys": [
            "steps.forecast.planCode"
        ]
    }
}


def register_basin_template():
    """注册全流域预报模板并更新向量索引"""
    logger.info("开始注册全流域洪水预报结果模板...")

    init_database()
    db = SessionLocal()
    template_index = get_template_vector_index()

    try:
        name = BASIN_TEMPLATE["name"]
        existing = db.query(WebTemplate).filter(WebTemplate.name == name).first()

        if existing:
            logger.info(f"模板 {name} 已存在，更新数据...")
            existing.display_name = BASIN_TEMPLATE["display_name"]
            existing.description = BASIN_TEMPLATE["description"]
            existing.template_path = BASIN_TEMPLATE["template_path"]
            existing.supported_sub_intents = json.dumps(BASIN_TEMPLATE["supported_sub_intents"], ensure_ascii=False)
            existing.template_type = BASIN_TEMPLATE["template_type"]
            existing.trigger_pattern = BASIN_TEMPLATE["trigger_pattern"]
            existing.features = json.dumps(BASIN_TEMPLATE["features"], ensure_ascii=False)
            existing.priority = BASIN_TEMPLATE["priority"]
            existing.is_active = True
            existing.replacement_config = json.dumps(BASIN_TEMPLATE["replacement_config"], ensure_ascii=False)
            existing.required_object_types = json.dumps(BASIN_TEMPLATE["required_object_types"], ensure_ascii=False)
            db.commit()
            template_id = existing.id
        else:
            logger.info(f"创建新模板: {name}")
            template_id = str(uuid.uuid4())
            template = WebTemplate(
                id=template_id,
                name=name,
                display_name=BASIN_TEMPLATE["display_name"],
                description=BASIN_TEMPLATE["description"],
                template_path=BASIN_TEMPLATE["template_path"],
                supported_sub_intents=json.dumps(BASIN_TEMPLATE["supported_sub_intents"], ensure_ascii=False),
                template_type=BASIN_TEMPLATE["template_type"],
                trigger_pattern=BASIN_TEMPLATE["trigger_pattern"],
                features=json.dumps(BASIN_TEMPLATE["features"], ensure_ascii=False),
                priority=BASIN_TEMPLATE["priority"],
                is_active=True,
                replacement_config=json.dumps(BASIN_TEMPLATE["replacement_config"], ensure_ascii=False),
                required_object_types=json.dumps(BASIN_TEMPLATE["required_object_types"], ensure_ascii=False)
            )
            db.add(template)
            db.commit()

        template_index.index_template(template_id, {
            "name": BASIN_TEMPLATE["name"],
            "display_name": BASIN_TEMPLATE["display_name"],
            "description": BASIN_TEMPLATE["description"],
            "trigger_pattern": BASIN_TEMPLATE["trigger_pattern"],
            "supported_sub_intents": BASIN_TEMPLATE["supported_sub_intents"],
            "template_path": BASIN_TEMPLATE["template_path"],
            "template_type": BASIN_TEMPLATE["template_type"],
            "priority": BASIN_TEMPLATE["priority"],
            "replacement_config": BASIN_TEMPLATE["replacement_config"],
            "required_object_types": BASIN_TEMPLATE["required_object_types"]
        })

        logger.info(f"全流域洪水预报结果模板注册成功，ID: {template_id}")
        return template_id

    except Exception as e:
        logger.error(f"注册全流域模板失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    register_basin_template()
