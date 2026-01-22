"""
模板预览用的模拟数据

为各种模板类型提供预览时使用的示例数据
"""

from datetime import datetime, timedelta
from typing import Dict, Any


def _generate_time_series(start_time: datetime, hours: int, interval_hours: int = 1) -> list:
    """生成时间序列"""
    times = []
    current = start_time
    for _ in range(hours // interval_hours):
        times.append(current.strftime("%Y-%m-%d %H:%M:%S"))
        current += timedelta(hours=interval_hours)
    return times


def _generate_flow_data(times: list, base: float, peak: float, peak_index: int) -> dict:
    """生成流量时序数据"""
    data = {}
    n = len(times)
    for i, t in enumerate(times):
        # 简单的抛物线模拟
        if i <= peak_index:
            ratio = i / peak_index if peak_index > 0 else 1
            value = base + (peak - base) * ratio
        else:
            ratio = (i - peak_index) / (n - peak_index) if n > peak_index else 1
            value = peak - (peak - base) * ratio * 0.8
        data[t] = round(value, 2)
    return data


def _generate_level_data(times: list, base: float, peak: float, peak_index: int) -> dict:
    """生成水位时序数据"""
    data = {}
    n = len(times)
    for i, t in enumerate(times):
        if i <= peak_index:
            ratio = i / peak_index if peak_index > 0 else 1
            value = base + (peak - base) * ratio
        else:
            ratio = (i - peak_index) / (n - peak_index) if n > peak_index else 1
            value = peak - (peak - base) * ratio * 0.5
        data[t] = round(value, 2)
    return data


# 各模板的模拟数据
MOCK_DATA: Dict[str, Dict[str, Any]] = {
    # 水库洪水预报结果展示模板
    "res_flood_forecast": {
        "reservoir_name": "示例水库",
        "plan_code": "preview_demo_001",
        "reservoir_result": {
            "InQ_Dic": {},  # 将在运行时生成
            "OutQ_Dic": {},
            "Level_Dic": {},
            "Max_Level": 252.5,
            "MaxLevel_Time": "",
            "Max_InQ": 1850,
            "MaxInQ_Time": "",
            "Max_OutQ": 1200,
            "MaxOutQ_Time": "",
            "Max_Volumn": 15800,
            "Total_InVolumn": 8500,
            "Total_OutVolumn": 7200,
            "EndTime_Level": 249.8,
            "EndTime_Volumn": 12500
        },
        "rain_data": [],  # 将在运行时生成
        "result_desc": "这是模板预览的示例数据。根据预报方案计算，示例水库最高水位252.5m，入库洪峰流量1850m³/s，出库洪峰流量1200m³/s。水库调度后，预报结束时水位249.8m，蓄水量12500万m³。"
    },

    # 站点洪水预报结果展示模板（预留）
    "station_flood_forecast": {
        "station_name": "示例站点",
        "plan_code": "preview_demo_002",
        "station_result": {
            "Q_Dic": {},
            "Level_Dic": {},
            "Max_Qischarge": 2500,
            "MaxQ_AtTime": "",
            "Max_Level": 85.5,
            "Total_Flood": 5600,
            "Stcd": "31005650",
            "SectionName": "示例断面"
        },
        "result_desc": "这是站点预报模板预览的示例数据。"
    },

    # 蓄滞洪区预报结果展示模板（预留）
    "detention_basin_forecast": {
        "detention_name": "示例蓄滞洪区",
        "plan_code": "preview_demo_003",
        "detention_result": {
            "Xzhq_State": "启用",
            "Max_InQ": 800,
            "Total_InVolumn": 3500,
            "Max_Level": 45.2,
            "InQ_Dic": {},
            "Level_Dic": {}
        },
        "result_desc": "这是蓄滞洪区预报模板预览的示例数据。"
    }
}


def get_mock_data(template_name: str) -> Dict[str, Any]:
    """
    获取指定模板的模拟数据

    Args:
        template_name: 模板名称（英文标识）

    Returns:
        模拟数据字典
    """
    if template_name not in MOCK_DATA:
        # 返回通用模拟数据
        return {
            "title": "模板预览",
            "message": f"模板 {template_name} 暂无预设模拟数据",
            "preview_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    # 复制模拟数据
    import copy
    data = copy.deepcopy(MOCK_DATA[template_name])

    # 生成动态时序数据
    now = datetime.now()
    start_time = now - timedelta(hours=24)
    times = _generate_time_series(start_time, 72, 1)
    peak_index = 24  # 洪峰在第24小时

    if template_name == "res_flood_forecast":
        # 生成水库预报数据
        result = data["reservoir_result"]
        result["InQ_Dic"] = _generate_flow_data(times, 200, 1850, peak_index)
        result["OutQ_Dic"] = _generate_flow_data(times, 150, 1200, peak_index + 3)
        result["Level_Dic"] = _generate_level_data(times, 248.0, 252.5, peak_index + 2)
        result["MaxLevel_Time"] = times[peak_index + 2]
        result["MaxInQ_Time"] = times[peak_index]
        result["MaxOutQ_Time"] = times[peak_index + 3]

        # 生成降雨数据
        rain_times = _generate_time_series(start_time, 48, 1)
        rain_peak = 12
        data["rain_data"] = []
        for i, t in enumerate(rain_times):
            if i <= rain_peak:
                value = 2 + (25 - 2) * (i / rain_peak)
            else:
                value = 25 * (1 - (i - rain_peak) / (len(rain_times) - rain_peak)) ** 2
            data["rain_data"].append({
                "time": t,
                "value": round(max(0, value), 1)
            })

    elif template_name == "station_flood_forecast":
        result = data["station_result"]
        result["Q_Dic"] = _generate_flow_data(times, 500, 2500, peak_index)
        result["Level_Dic"] = _generate_level_data(times, 82.0, 85.5, peak_index + 1)
        result["MaxQ_AtTime"] = times[peak_index]

    elif template_name == "detention_basin_forecast":
        result = data["detention_result"]
        result["InQ_Dic"] = _generate_flow_data(times[24:48], 0, 800, 12)
        result["Level_Dic"] = _generate_level_data(times[24:48], 42.0, 45.2, 14)

    return data


def get_available_mock_templates() -> list:
    """
    获取所有可用的模拟数据模板名称

    Returns:
        模板名称列表
    """
    return list(MOCK_DATA.keys())
