"""
模板管理器
管理Web页面生成模板
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json

from ..config.logging_config import get_logger
from ..config.settings import settings

logger = get_logger(__name__)


# 基础HTML模板
BASE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            padding: 20px 0;
            border-bottom: 2px solid #0f4c75;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 28px;
            color: #00d4ff;
            text-shadow: 0 0 10px rgba(0, 212, 255, 0.5);
        }}
        .header .subtitle {{
            font-size: 14px;
            color: #888;
            margin-top: 10px;
        }}
        .content {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .card-title {{
            font-size: 16px;
            color: #00d4ff;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(0, 212, 255, 0.3);
        }}
        .chart-container {{
            width: 100%;
            height: 300px;
        }}
        .data-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .data-table th, .data-table td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .data-table th {{
            color: #00d4ff;
            font-weight: normal;
        }}
        .status-normal {{ color: #4caf50; }}
        .status-warning {{ color: #ff9800; }}
        .status-danger {{ color: #f44336; }}
        .info-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        }}
        .info-label {{
            color: #888;
        }}
        .info-value {{
            color: #fff;
            font-weight: bold;
        }}
        {custom_styles}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle">生成时间: {generate_time}</div>
        </div>
        <div class="content">
            {content}
        </div>
    </div>
    <script>
        {scripts}
    </script>
</body>
</html>
"""


# 洪水预报报告模板
FLOOD_FORECAST_TEMPLATE = """
<div class="card" style="grid-column: span 2;">
    <div class="card-title">📊 流域基本信息</div>
    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px;">
        <div class="info-item">
            <span class="info-label">流域名称</span>
            <span class="info-value">{basin_name}</span>
        </div>
        <div class="info-item">
            <span class="info-label">流域面积</span>
            <span class="info-value">{basin_area} km²</span>
        </div>
        <div class="info-item">
            <span class="info-label">预报时段</span>
            <span class="info-value">{forecast_period}</span>
        </div>
        <div class="info-item">
            <span class="info-label">预警等级</span>
            <span class="info-value {warning_class}">{warning_level}</span>
        </div>
    </div>
</div>

<div class="card">
    <div class="card-title">🌧️ 降雨量趋势</div>
    <div id="rainfall-chart" class="chart-container"></div>
</div>

<div class="card">
    <div class="card-title">📈 水位变化预测</div>
    <div id="water-level-chart" class="chart-container"></div>
</div>

<div class="card">
    <div class="card-title">💧 流量过程线</div>
    <div id="flow-chart" class="chart-container"></div>
</div>

<div class="card">
    <div class="card-title">📋 站点监测数据</div>
    <table class="data-table">
        <thead>
            <tr>
                <th>站点名称</th>
                <th>当前水位(m)</th>
                <th>预报水位(m)</th>
                <th>警戒水位(m)</th>
                <th>状态</th>
            </tr>
        </thead>
        <tbody>
            {station_rows}
        </tbody>
    </table>
</div>
"""


# 应急预案报告模板
EMERGENCY_PLAN_TEMPLATE = """
<div class="card" style="grid-column: span 2;">
    <div class="card-title">⚠️ 预警信息</div>
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
        <div class="info-item">
            <span class="info-label">预警等级</span>
            <span class="info-value {warning_class}">{warning_level}</span>
        </div>
        <div class="info-item">
            <span class="info-label">发布时间</span>
            <span class="info-value">{warning_time}</span>
        </div>
        <div class="info-item">
            <span class="info-label">影响区域</span>
            <span class="info-value">{affected_areas}</span>
        </div>
    </div>
</div>

<div class="card">
    <div class="card-title">📊 风险评估</div>
    <div id="risk-chart" class="chart-container"></div>
</div>

<div class="card">
    <div class="card-title">📈 历史对比</div>
    <div id="history-chart" class="chart-container"></div>
</div>

<div class="card" style="grid-column: span 2;">
    <div class="card-title">📋 响应措施</div>
    <table class="data-table">
        <thead>
            <tr>
                <th>序号</th>
                <th>响应措施</th>
                <th>责任部门</th>
                <th>执行时限</th>
                <th>优先级</th>
            </tr>
        </thead>
        <tbody>
            {response_rows}
        </tbody>
    </table>
</div>

<div class="card" style="grid-column: span 2;">
    <div class="card-title">🏘️ 转移安置方案</div>
    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
        <div>
            <h4 style="color: #00d4ff; margin-bottom: 10px;">需转移人口</h4>
            <div id="evacuation-chart" class="chart-container" style="height: 200px;"></div>
        </div>
        <div>
            <h4 style="color: #00d4ff; margin-bottom: 10px;">安置点信息</h4>
            {shelter_info}
        </div>
    </div>
</div>
"""


class TemplateManager:
    """
    模板管理器
    
    管理各类报告页面模板
    """
    
    _instance: Optional['TemplateManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._templates: Dict[str, str] = {
            'base': BASE_TEMPLATE,
            'flood_forecast': FLOOD_FORECAST_TEMPLATE,
            'emergency_plan': EMERGENCY_PLAN_TEMPLATE
        }
        self._initialized = True
        
        logger.info("模板管理器初始化完成")
    
    def get_template(self, template_name: str) -> Optional[str]:
        """
        获取模板
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板内容或None
        """
        return self._templates.get(template_name)
    
    def register_template(self, name: str, template: str) -> None:
        """
        注册自定义模板
        
        Args:
            name: 模板名称
            template: 模板内容
        """
        self._templates[name] = template
        logger.info(f"注册模板: {name}")
    
    def list_templates(self) -> list:
        """列出所有模板名称"""
        return list(self._templates.keys())
    
    def render_base_template(
        self,
        title: str,
        content: str,
        generate_time: str,
        custom_styles: str = "",
        scripts: str = ""
    ) -> str:
        """
        渲染基础模板
        
        Args:
            title: 页面标题
            content: 页面内容
            generate_time: 生成时间
            custom_styles: 自定义CSS
            scripts: JavaScript脚本
            
        Returns:
            渲染后的HTML
        """
        base = self._templates['base']
        return base.format(
            title=title,
            content=content,
            generate_time=generate_time,
            custom_styles=custom_styles,
            scripts=scripts
        )
    
    def get_warning_class(self, level: str) -> str:
        """获取预警等级对应的CSS类"""
        level_map = {
            'blue': 'status-normal',
            'yellow': 'status-warning', 
            'orange': 'status-warning',
            'red': 'status-danger'
        }
        return level_map.get(level.lower(), 'status-normal')
    
    def generate_chart_script(
        self,
        chart_id: str,
        chart_type: str,
        data: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成ECharts图表脚本
        
        Args:
            chart_id: 图表容器ID
            chart_type: 图表类型 (line, bar, pie, gauge等)
            data: 图表数据
            options: 额外配置选项
            
        Returns:
            JavaScript代码
        """
        base_options = {
            'tooltip': {'trigger': 'axis'},
            'grid': {
                'left': '3%',
                'right': '4%',
                'bottom': '3%',
                'containLabel': True
            }
        }
        
        if chart_type == 'line':
            chart_options = {
                **base_options,
                'xAxis': {
                    'type': 'category',
                    'data': data.get('x_data', []),
                    'axisLine': {'lineStyle': {'color': '#444'}},
                    'axisLabel': {'color': '#888'}
                },
                'yAxis': {
                    'type': 'value',
                    'axisLine': {'lineStyle': {'color': '#444'}},
                    'axisLabel': {'color': '#888'},
                    'splitLine': {'lineStyle': {'color': '#333'}}
                },
                'series': [{
                    'type': 'line',
                    'data': data.get('y_data', []),
                    'smooth': True,
                    'lineStyle': {'color': '#00d4ff'},
                    'areaStyle': {
                        'color': {
                            'type': 'linear',
                            'x': 0, 'y': 0, 'x2': 0, 'y2': 1,
                            'colorStops': [
                                {'offset': 0, 'color': 'rgba(0, 212, 255, 0.3)'},
                                {'offset': 1, 'color': 'rgba(0, 212, 255, 0.05)'}
                            ]
                        }
                    }
                }]
            }
        elif chart_type == 'bar':
            chart_options = {
                **base_options,
                'xAxis': {
                    'type': 'category',
                    'data': data.get('x_data', []),
                    'axisLine': {'lineStyle': {'color': '#444'}},
                    'axisLabel': {'color': '#888'}
                },
                'yAxis': {
                    'type': 'value',
                    'axisLine': {'lineStyle': {'color': '#444'}},
                    'axisLabel': {'color': '#888'},
                    'splitLine': {'lineStyle': {'color': '#333'}}
                },
                'series': [{
                    'type': 'bar',
                    'data': data.get('y_data', []),
                    'itemStyle': {'color': '#00d4ff'}
                }]
            }
        elif chart_type == 'pie':
            chart_options = {
                'tooltip': {'trigger': 'item'},
                'series': [{
                    'type': 'pie',
                    'radius': ['40%', '70%'],
                    'data': data.get('pie_data', []),
                    'label': {'color': '#888'}
                }]
            }
        elif chart_type == 'gauge':
            chart_options = {
                'series': [{
                    'type': 'gauge',
                    'progress': {'show': True},
                    'detail': {'valueAnimation': True, 'color': '#00d4ff'},
                    'data': [{'value': data.get('value', 0), 'name': data.get('name', '')}]
                }]
            }
        else:
            chart_options = base_options
        
        # 合并额外选项
        if options:
            chart_options.update(options)
        
        options_json = json.dumps(chart_options, ensure_ascii=False)
        
        return f"""
        (function() {{
            var chart = echarts.init(document.getElementById('{chart_id}'));
            var option = {options_json};
            chart.setOption(option);
            window.addEventListener('resize', function() {{
                chart.resize();
            }});
        }})();
        """


# 全局模板管理器实例
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """获取模板管理器单例"""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
