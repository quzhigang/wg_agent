"""
站点编码查询工具
根据站点名称快速获取站点编码(stcd)，支持模糊匹配
数据来源：MySQL数据库 monitor_stations 表
"""

from typing import List, Optional
import pymysql
from .base import BaseTool, ToolCategory, ToolParameter, ToolResult
from .registry import register_tool
from ..config.settings import settings
from ..config.logging_config import get_logger

logger = get_logger(__name__)


def get_db_connection():
    """获取数据库连接"""
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


class StationLookupTool(BaseTool):
    """
    站点编码查询工具
    根据站点名称快速获取站点编码(stcd)，支持精确匹配和模糊匹配
    """

    @property
    def name(self) -> str:
        return "lookup_station_code"

    @property
    def description(self) -> str:
        return "根据站点名称查询站点编码(stcd)，支持精确匹配和模糊匹配，可用于水雨情实时数据查询前获取站点编码"

    @property
    def category(self) -> ToolCategory:
        return ToolCategory.BASIN_INFO

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="station_name",
                type="string",
                description="站点名称，支持模糊匹配（如输入'淇门'可匹配'淇门'、'淇门东街断面'等）",
                required=True
            ),
            ToolParameter(
                name="station_type",
                type="string",
                description="站点类型过滤（可选）：河道水文站、水库水文站、工程安全监测、墒情站、闸站监测、AI监测站点、雨量站",
                required=False
            ),
            ToolParameter(
                name="exact_match",
                type="boolean",
                description="是否精确匹配，默认False（模糊匹配）",
                required=False,
                default=False
            )
        ]

    async def execute(self, **kwargs) -> ToolResult:
        station_name = kwargs.get('station_name', '').strip()
        station_type = kwargs.get('station_type') or None  # 空字符串也视为None
        exact_match = kwargs.get('exact_match', False)

        if not station_name:
            return ToolResult(success=False, error="站点名称不能为空")

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 构建查询SQL
            if exact_match:
                sql = "SELECT stcd, stnm, station_type FROM monitor_stations WHERE stnm = %s"
                params = [station_name]
            else:
                # 模糊匹配：站点名称包含查询词，或查询词包含站点名称
                sql = """
                    SELECT stcd, stnm, station_type
                    FROM monitor_stations
                    WHERE stnm LIKE %s OR %s LIKE CONCAT('%%', stnm, '%%')
                """
                params = [f"%{station_name}%", station_name]

            # 类型过滤
            if station_type:
                sql += " AND station_type = %s"
                params.append(station_type)

            # 排序：优先精确匹配，其次按名称长度（短的优先）
            sql += " ORDER BY CASE WHEN stnm = %s THEN 0 ELSE 1 END, LENGTH(stnm) LIMIT 20"
            params.append(station_name)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            cursor.close()
            conn.close()

            if not rows:
                return ToolResult(
                    success=True,
                    data={"message": f"未找到匹配'{station_name}'的站点", "stcd": None, "stnm": None},
                    metadata={"query": station_name, "count": 0}
                )

            # 转换结果格式
            results = [
                {"stnm": row["stnm"], "stcd": row["stcd"], "type": row["station_type"]}
                for row in rows
            ]

            return ToolResult(
                success=True,
                data={
                    "stcd": results[0]["stcd"],  # 第一个匹配的站点编码，方便直接引用
                    "stnm": results[0]["stnm"],  # 第一个匹配的站点名称
                    "stations": results          # 完整匹配列表
                },
                metadata={"query": station_name, "count": len(results)}
            )

        except Exception as e:
            logger.error(f"查询站点编码失败: {e}")
            return ToolResult(success=False, error=f"查询失败: {str(e)}")


# 注册工具
register_tool(StationLookupTool())
