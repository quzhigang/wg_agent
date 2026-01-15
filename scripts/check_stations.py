# -*- coding: utf-8 -*-
"""查询站点信息脚本"""

import sys
sys.path.insert(0, 'c:\\Users\\15257\\Desktop\\wg_agent')

import pymysql
from src.config.settings import settings

def main():
    conn = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    # 查询修武相关站点
    cursor.execute("SELECT stcd, stnm, station_type FROM monitor_stations WHERE stnm LIKE '%修武%' LIMIT 10")
    print('=== 修武相关站点 ===')
    for row in cursor.fetchall():
        print(f"{row['stnm']} | {row['stcd']} | {row['station_type']}")

    # 查看站点类型有哪些
    cursor.execute('SELECT DISTINCT station_type FROM monitor_stations')
    print()
    print('=== 站点类型列表 ===')
    for row in cursor.fetchall():
        print(f"- {row['station_type']}")

    conn.close()

if __name__ == '__main__':
    main()
