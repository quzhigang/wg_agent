"""
更新现有工作流的 display_name 字段
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from src.models.database import SavedWorkflow, SessionLocal, get_engine


def add_display_name_column():
    """添加 display_name 列（如果不存在）"""
    engine = get_engine()
    with engine.connect() as conn:
        # 检查列是否存在
        result = conn.execute(text("""
            SELECT COUNT(*) as cnt FROM information_schema.columns
            WHERE table_name = 'saved_workflows' AND column_name = 'display_name'
        """))
        row = result.fetchone()
        if row[0] == 0:
            print("添加 display_name 列...")
            conn.execute(text("""
                ALTER TABLE saved_workflows
                ADD COLUMN display_name VARCHAR(100) NULL COMMENT '中文显示名称' AFTER name
            """))
            conn.commit()
            print("display_name 列添加成功!")
        else:
            print("display_name 列已存在")


# 工作流名称到中文显示名的映射
DISPLAY_NAME_MAPPING = {
    # 根据工作流的 name 或 sub_intent 来映射中文名
    # 常见的子意图类型
    "realtime_water_level": "实时水位查询",
    "realtime_rainfall": "实时雨量查询",
    "realtime_flow": "实时流量查询",
    "history_water_level": "历史水位查询",
    "history_rainfall": "历史雨量查询",
    "history_flow": "历史流量查询",
    "flood_forecast": "洪水预报",
    "reservoir_info": "水库信息查询",
    "station_info": "站点信息查询",
    "water_regime": "水情查询",
    "rain_regime": "雨情查询",
}


def generate_display_name(workflow):
    """根据工作流信息生成中文显示名"""
    # 优先使用 sub_intent 匹配
    if workflow.sub_intent:
        for key, name in DISPLAY_NAME_MAPPING.items():
            if key in workflow.sub_intent.lower():
                return name

    # 使用 name 匹配
    if workflow.name:
        for key, name in DISPLAY_NAME_MAPPING.items():
            if key in workflow.name.lower():
                return name

    # 使用 description 生成简短名称
    if workflow.description:
        desc = workflow.description
        # 截取前15个字符作为显示名
        if len(desc) > 15:
            return desc[:15] + "..."
        return desc

    # 默认使用 sub_intent
    return f"{workflow.sub_intent or '未知'}工作流"


def main():
    # 先添加列
    add_display_name_column()
    print()

    db = SessionLocal()
    try:
        # 查询所有工作流
        workflows = db.query(SavedWorkflow).all()

        print(f"找到 {len(workflows)} 个工作流")
        print("-" * 60)

        for w in workflows:
            old_display_name = w.display_name

            # 如果已有 display_name 则跳过
            if old_display_name:
                print(f"[跳过] {w.name}: 已有 display_name = {old_display_name}")
                continue

            # 生成新的 display_name
            new_display_name = generate_display_name(w)
            w.display_name = new_display_name

            print(f"[更新] {w.name}")
            print(f"        sub_intent: {w.sub_intent}")
            print(f"        description: {w.description[:50] if w.description else 'N/A'}...")
            print(f"        display_name: {new_display_name}")
            print()

        db.commit()
        print("-" * 60)
        print("更新完成!")

    finally:
        db.close()


if __name__ == "__main__":
    main()
