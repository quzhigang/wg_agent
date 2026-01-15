"""
站点数据导入脚本
从监测站点基础信息文档中解析站点数据并导入MySQL数据库
"""

import re
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pymysql
from src.config.settings import settings


# 文档目录
DOC_DIR = project_root / "开发资料" / "知识库文档" / "3、监测站点" / "监测站点基础信息"

# 站点类型映射
STATION_TYPE_MAP = {
    "河道水文站.md": "河道水文站",
    "水库水文站.md": "水库水文站",
    "AI监测站点.md": "AI监测站点",
    "工程安全监测.md": "工程安全监测",
    "墒情站.md": "墒情站",
    "闸站监测.md": "闸站监测",
    "雨量站.md": "雨量站",
    "视频监测.md": "视频监测",
    "取水监测.md": "取水监测",
    "无人机.md": "无人机",
}


def create_table(cursor):
    """创建站点表"""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitor_stations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            stcd VARCHAR(50) NOT NULL COMMENT '站点编码',
            stnm VARCHAR(100) NOT NULL COMMENT '站点名称',
            station_type VARCHAR(50) NOT NULL COMMENT '站点类型',
            lgtd DECIMAL(12, 6) NULL COMMENT '经度',
            lttd DECIMAL(12, 6) NULL COMMENT '纬度',
            rvnm VARCHAR(100) NULL COMMENT '河流名称',
            stlc VARCHAR(200) NULL COMMENT '具体位置',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_stcd_type (stcd, station_type),
            INDEX idx_stnm (stnm),
            INDEX idx_type (station_type)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='监测站点基础信息表'
    """)
    print("表 monitor_stations 创建成功（或已存在）")


def parse_markdown_stations(content: str, station_type: str) -> List[Dict]:
    """
    解析Markdown格式的站点数据
    格式: ### 站点名称 (序号) + - **字段:** 值
    """
    stations = []

    # 根据站点类型确定字段名
    if station_type == "水库水文站":
        name_field = "res_name"
        code_field = "stcd"
    elif station_type == "闸站监测":
        name_field = "name"
        code_field = "code"
    elif station_type == "取水监测":
        name_field = "name"
        code_field = "code"
    else:
        name_field = "stnm"
        code_field = "stcd"

    # 按站点分割（使用 ### 或 记录 作为分隔）
    # 匹配 ### xxx 或 ### 记录 xxx
    sections = re.split(r'\n###\s+', content)

    for section in sections[1:]:  # 跳过第一个（文档头部）
        if not section.strip():
            continue

        # 提取字段 - 逐行解析，避免空值导致的匹配错误
        fields = {}
        for line in section.split('\n'):
            line = line.strip()
            # 匹配 - **字段:** 值 格式
            match = re.match(r'^-\s+\*\*(\w+):\*\*\s*(.*)$', line)
            if match:
                field_name = match.group(1).strip()
                field_value = match.group(2).strip()
                if field_value:  # 只保存非空值
                    fields[field_name] = field_value

        # 获取站点名称和编码
        stnm = fields.get(name_field, "").strip()
        stcd = fields.get(code_field, "").strip()

        if not stnm or not stcd:
            continue

        # 获取其他字段
        lgtd = fields.get("lgtd") or fields.get("longitude")
        lttd = fields.get("lttd") or fields.get("latitude")
        rvnm = fields.get("rvnm") or fields.get("loc_rv_nm") or fields.get("atriver")
        stlc = fields.get("stlc") or fields.get("res_loc") or fields.get("location")

        station = {
            "stcd": stcd,
            "stnm": stnm,
            "station_type": station_type,
            "lgtd": float(lgtd) if lgtd else None,
            "lttd": float(lttd) if lttd else None,
            "rvnm": rvnm,
            "stlc": stlc,
        }
        stations.append(station)

    return stations


def parse_table_stations(content: str, station_type: str) -> List[Dict]:
    """
    解析表格格式的站点数据（墒情站）
    格式: 空格分隔的表格，最后几列是 stcd stnm sttp
    """
    stations = []
    lines = content.split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 检测是否是数据行（以数字开头，如 0.0, 1.0 等）
        if not re.match(r'^\d+\.0\s+', line):
            continue

        # 使用正则匹配：找到 stcd stnm sttp 模式
        # stcd 格式：310A开头 或 311A开头 或 414A开头 或 3.xxx科学计数法 或 4.xxx科学计数法
        # stnm 在 stcd 后面，sttp 在最后（如 SS）
        match = re.search(r'(3\d{2}[A-Z]\d+|4\d{2}[A-Z]\d+|3\.\d+e\d+|4\.\d+e\d+)\s+(\S+)\s+(SS|PP|RR|ZQ)\s*$', line)
        if not match:
            continue

        stcd = match.group(1)
        stnm = match.group(2)

        # 查找经纬度（lng lat 格式为 11x.xxx 35.xxx 或 36.xxx）
        lng = None
        lat = None
        coord_match = re.search(r'(11[234]\.\d+)\s+(3[456]\.\d+)', line)
        if coord_match:
            lng = float(coord_match.group(1))
            lat = float(coord_match.group(2))

        station = {
            "stcd": stcd,
            "stnm": stnm,
            "station_type": station_type,
            "lgtd": lng,
            "lttd": lat,
            "rvnm": None,
            "stlc": None,
        }
        stations.append(station)

    return stations


def parse_drone_stations(content: str, station_type: str) -> List[Dict]:
    """
    解析无人机数据（JSON嵌套格式）
    从 gateway 和 drone 字段中提取 callsign 和 sn
    """
    import json
    stations = []

    # 按记录分割
    sections = re.split(r'\n###\s+', content)

    for section in sections[1:]:
        if not section.strip():
            continue

        # 提取 gateway 和 drone 的 JSON 数据
        for device_type in ['gateway', 'drone']:
            # 匹配 - **gateway:** { ... } 或 - **drone:** { ... }
            pattern = rf'-\s+\*\*{device_type}:\*\*\s*(\{{[\s\S]*?\n\}})'
            match = re.search(pattern, section)
            if match:
                try:
                    json_str = match.group(1)
                    data = json.loads(json_str)
                    sn = data.get('sn', '')
                    callsign = data.get('callsign', '')

                    if sn and callsign:
                        station = {
                            "stcd": sn,
                            "stnm": callsign,
                            "station_type": station_type,
                            "lgtd": None,
                            "lttd": None,
                            "rvnm": None,
                            "stlc": None,
                        }
                        stations.append(station)
                except json.JSONDecodeError:
                    continue

    return stations


def parse_file(filepath: Path, station_type: str) -> List[Dict]:
    """解析单个文件"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if station_type == "墒情站":
        return parse_table_stations(content, station_type)
    elif station_type == "无人机":
        return parse_drone_stations(content, station_type)
    else:
        return parse_markdown_stations(content, station_type)


def insert_stations(cursor, stations: List[Dict]):
    """批量插入站点数据"""
    sql = """
        INSERT INTO monitor_stations (stcd, stnm, station_type, lgtd, lttd, rvnm, stlc)
        VALUES (%(stcd)s, %(stnm)s, %(station_type)s, %(lgtd)s, %(lttd)s, %(rvnm)s, %(stlc)s)
        ON DUPLICATE KEY UPDATE
            stnm = VALUES(stnm),
            lgtd = VALUES(lgtd),
            lttd = VALUES(lttd),
            rvnm = VALUES(rvnm),
            stlc = VALUES(stlc)
    """

    for station in stations:
        try:
            cursor.execute(sql, station)
        except Exception as e:
            print(f"  插入失败: {station['stnm']} ({station['stcd']}): {e}")


def main():
    """主函数"""
    print("=" * 60)
    print("站点数据导入脚本")
    print("=" * 60)

    # 连接数据库
    conn = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset='utf8mb4'
    )

    try:
        cursor = conn.cursor()

        # 创建表
        create_table(cursor)
        conn.commit()

        # 统计
        total_count = 0

        # 遍历所有文档
        for filename, station_type in STATION_TYPE_MAP.items():
            filepath = DOC_DIR / filename
            if not filepath.exists():
                print(f"文件不存在: {filepath}")
                continue

            print(f"\n处理: {filename}")
            stations = parse_file(filepath, station_type)
            print(f"  解析到 {len(stations)} 个站点")

            if stations:
                insert_stations(cursor, stations)
                total_count += len(stations)
                print(f"  插入/更新完成")

        conn.commit()

        # 查询统计
        cursor.execute("SELECT station_type, COUNT(*) FROM monitor_stations GROUP BY station_type")
        print("\n" + "=" * 60)
        print("数据库站点统计:")
        print("-" * 40)
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} 个")

        cursor.execute("SELECT COUNT(*) FROM monitor_stations")
        db_total = cursor.fetchone()[0]
        print("-" * 40)
        print(f"  总计: {db_total} 个站点")
        print("=" * 60)

    finally:
        conn.close()

    print("\n导入完成!")


if __name__ == "__main__":
    main()
