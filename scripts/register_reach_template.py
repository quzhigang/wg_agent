"""
河道站洪水预报结果模板注册脚本

该脚本用于将 reach_module 模板注册到数据库中，并构建其向量索引。
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

# 定义河道模板数据
REACH_TEMPLATE = {
    "name": "reach_flood_forecast",
    "display_name": "河道洪水预报结果展示",
    "description": "用于展示河道、干流站点的洪水预报结果。包含地图定位、水位流量过程曲线（双轴）、河道断面地形及实时水位动态图。集成关键指标展示，适用于河系调度与河道防洪监测。",
    "template_path": "reach_module/index.html",
    "supported_sub_intents": ["flood_forecast", "data_query"],
    "template_type": "full_page",
    "trigger_pattern": "河道洪水预报 河系水位 流量计 断面地形 水文站预报 洪峰流量 河道断面 断面水情 修武站 卫河 淇河 沁河",
    "features": ["map", "chart", "cross_section", "dual_axis", "river", "echarts"],
    "priority": 10,
    "required_object_types": ["河道", "水文站", "水位站"],
    "replacement_config": {
        "mode": "regex_replace",
        "target_file": "js/main.js",
        "mappings": [
            {
                "context_path": "steps.login.token",
                "target_key": "DEFAULT_PARAMS.token",
                "pattern": r"token:\s*['\"][^'\"]*['\"]",
                "replacement_template": "token: '{value}'",
                "param_name": "token",
                "param_desc": "登录认证令牌"
            },
            {
                "context_path": "steps.forecast.planCode",
                "target_key": "DEFAULT_PARAMS.planCode",
                "pattern": r"planCode:\s*['\"][^'\"]*['\"]",
                "replacement_template": "planCode: '{value}'",
                "param_name": "planCode",
                "param_desc": "预报方案ID"
            },
            {
                "context_path": "steps.extract.base_stcd",
                "target_key": "DEFAULT_PARAMS.stcd",
                "pattern": r"stcd:\s*['\"][^'\"]*['\"]",
                "replacement_template": "stcd: '{value}'",
                "param_name": "stcd",
                "param_desc": "水文/水位站码"
            },
            {
                "context_path": "steps.parse_target.target_name",
                "target_key": "DEFAULT_PARAMS.reservoirName",
                "pattern": r"reservoirName:\s*['\"][^'\"]*['\"]",
                "replacement_template": "reservoirName: '{value}'",
                "param_name": "object_name",
                "param_desc": "对象名称（河道/水文站名称）"
            }
        ],
        "default_values": {
            "DEFAULT_PARAMS.token": "__TOKEN_PLACEHOLDER__",
            "DEFAULT_PARAMS.planCode": "__PLANCODE_PLACEHOLDER__",
            "DEFAULT_PARAMS.stcd": "__STCD_PLACEHOLDER__",
            "DEFAULT_PARAMS.reservoirName": "__STATION_PLACEHOLDER__"
        },
        "required_context_keys": [
            "steps.login.token",
            "steps.forecast.planCode"
        ]
    }
}

def register_reach_template():
    """注册河道模板并更新索引"""
    logger.info("开始注册河道预报模板...")
    
    # 初始化数据库
    init_database()
    db = SessionLocal()
    template_index = get_template_vector_index()
    
    try:
        name = REACH_TEMPLATE["name"]
        # 检查是否已存在
        existing = db.query(WebTemplate).filter(WebTemplate.name == name).first()
        
        if existing:
            logger.info(f"模板 {name} 已存在，更新数据...")
            existing.display_name = REACH_TEMPLATE["display_name"]
            existing.description = REACH_TEMPLATE["description"]
            existing.template_path = REACH_TEMPLATE["template_path"]
            existing.supported_sub_intents = json.dumps(REACH_TEMPLATE["supported_sub_intents"], ensure_ascii=False)
            existing.template_type = REACH_TEMPLATE["template_type"]
            existing.trigger_pattern = REACH_TEMPLATE["trigger_pattern"]
            existing.features = json.dumps(REACH_TEMPLATE["features"], ensure_ascii=False)
            existing.priority = REACH_TEMPLATE["priority"]
            existing.is_active = True
            existing.replacement_config = json.dumps(REACH_TEMPLATE["replacement_config"], ensure_ascii=False)
            existing.required_object_types = json.dumps(REACH_TEMPLATE["required_object_types"], ensure_ascii=False)
            
            db.commit()
            template_id = existing.id
        else:
            logger.info(f"创建新模板: {name}")
            template_id = str(uuid.uuid4())
            template = WebTemplate(
                id=template_id,
                name=name,
                display_name=REACH_TEMPLATE["display_name"],
                description=REACH_TEMPLATE["description"],
                template_path=REACH_TEMPLATE["template_path"],
                supported_sub_intents=json.dumps(REACH_TEMPLATE["supported_sub_intents"], ensure_ascii=False),
                template_type=REACH_TEMPLATE["template_type"],
                trigger_pattern=REACH_TEMPLATE["trigger_pattern"],
                features=json.dumps(REACH_TEMPLATE["features"], ensure_ascii=False),
                priority=REACH_TEMPLATE["priority"],
                is_active=True,
                replacement_config=json.dumps(REACH_TEMPLATE["replacement_config"], ensure_ascii=False),
                required_object_types=json.dumps(REACH_TEMPLATE["required_object_types"], ensure_ascii=False)
            )
            db.add(template)
            db.commit()
            
        # 更新/添加向量索引
        template_index.index_template(template_id, {
            "name": REACH_TEMPLATE["name"],
            "display_name": REACH_TEMPLATE["display_name"],
            "description": REACH_TEMPLATE["description"],
            "trigger_pattern": REACH_TEMPLATE["trigger_pattern"],
            "supported_sub_intents": REACH_TEMPLATE["supported_sub_intents"],
            "template_path": REACH_TEMPLATE["template_path"],
            "template_type": REACH_TEMPLATE["template_type"],
            "priority": REACH_TEMPLATE["priority"],
            "replacement_config": REACH_TEMPLATE["replacement_config"],
            "required_object_types": REACH_TEMPLATE["required_object_types"]
        })
        
        logger.info(f"河道预报模板注册成功！ID: {template_id}")
        
    except Exception as e:
        logger.error(f"注册模板失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    register_reach_template()
