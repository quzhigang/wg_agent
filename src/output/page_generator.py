"""
页面生成器
生成Web报告页面
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid
import datetime
import json
import os

from ..config.logging_config import get_logger
from ..config.settings import settings
from .templates import get_template_manager, TemplateManager

logger = get_logger(__name__)


class PageGenerator:
    """
    页面生成器
    
    根据数据和模板生成Web报告页面
    """
    
    _instance: Optional['PageGenerator'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._template_manager = get_template_manager()
        self._output_dir = Path(settings.generated_pages_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True
        
        logger.info(f"页面生成器初始化完成，输出目录: {self._output_dir}")
    
    def generate_page(
        self,
        report_type: str,
        data: Dict[str, Any],
        title: Optional[str] = None
    ) -> str:
        """
        生成报告页面
        
        Args:
            report_type: 报告类型 (flood_forecast, emergency_plan等)
            data: 报告数据
            title: 页面标题
            
        Returns:
            生成的页面URL路径
        """
        logger.info(f"生成报告页面: {report_type}")
        
        # 生成页面ID
        page_id = str(uuid.uuid4())[:8]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_{timestamp}_{page_id}.html"
        
        # 根据报告类型生成内容
        if report_type == 'flood_forecast':
            html_content = self._generate_flood_forecast_page(data, title)
        elif report_type in ('auto_forecast', 'manual_forecast'):
            # 自动预报和人工预报结果使用专用模板
            html_content = self._generate_auto_forecast_page(data, title)
        elif report_type == 'emergency_plan':
            html_content = self._generate_emergency_plan_page(data, title)
        else:
            html_content = self._generate_generic_page(data, title or "报告")
        
        # 保存文件
        file_path = self._output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # 返回访问URL
        page_url = f"/pages/{filename}"
        logger.info(f"页面生成成功: {page_url}")
        
        return page_url
    
    def _generate_flood_forecast_page(
        self,
        data: Dict[str, Any],
        title: Optional[str] = None
    ) -> str:
        """生成洪水预报报告页面"""
        
        # 提取数据
        basin_info = data.get('basin_info', {})
        water_level = data.get('water_level', {})
        rainfall = data.get('rainfall', {})
        forecast = data.get('forecast', {})
        
        # 设置标题
        page_title = title or f"{basin_info.get('name', '流域')}洪水预报报告"
        
        # 生成时间
        generate_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 确定预警等级
        warning_level = forecast.get('warning_level', 'blue')
        warning_text = {
            'blue': '蓝色预警',
            'yellow': '黄色预警',
            'orange': '橙色预警',
            'red': '红色预警'
        }.get(warning_level, '无预警')
        warning_class = self._template_manager.get_warning_class(warning_level)
        
        # 生成站点数据表格行
        station_rows = self._generate_station_rows(
            water_level.get('stations', []),
            forecast.get('predictions', [])
        )
        
        # 获取内容模板并填充
        content_template = self._template_manager.get_template('flood_forecast')
        content = content_template.format(
            basin_name=basin_info.get('name', '未知流域'),
            basin_area=basin_info.get('area', '-'),
            forecast_period=forecast.get('period', '72小时'),
            warning_level=warning_text,
            warning_class=warning_class,
            station_rows=station_rows
        )
        
        # 生成图表脚本
        scripts = self._generate_flood_forecast_charts(rainfall, water_level, forecast)
        
        # 渲染完整页面
        return self._template_manager.render_base_template(
            title=page_title,
            content=content,
            generate_time=generate_time,
            scripts=scripts
        )

    def _generate_auto_forecast_page(
        self,
        data: Dict[str, Any],
        title: Optional[str] = None
    ) -> str:
        """生成自动预报结果报告页面"""

        # 提取数据 - 工作流返回的数据结构
        target = data.get('target', {})
        summary = data.get('summary', '')
        forecast_data = data.get('data', {})

        target_type = target.get('type', 'basin')
        target_name = target.get('name', '全流域')

        # 设置标题
        page_title = title or summary or f"{target_name}洪水预报结果"
        generate_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 根据目标类型生成不同的内容
        if target_type == 'reservoir':
            content = self._generate_reservoir_forecast_content(target_name, forecast_data)
        elif target_type == 'station':
            content = self._generate_station_forecast_content(target_name, forecast_data)
        elif target_type == 'detention_basin':
            content = self._generate_detention_forecast_content(target_name, forecast_data)
        else:
            content = self._generate_basin_forecast_content(forecast_data)

        return self._template_manager.render_base_template(
            title=page_title,
            content=content,
            generate_time=generate_time,
            scripts=""
        )

    def _generate_reservoir_forecast_content(
        self,
        reservoir_name: str,
        data: Dict[str, Any]
    ) -> str:
        """生成水库预报结果内容"""

        # 检查是否有错误消息
        if 'message' in data and '未找到' in data.get('message', ''):
            return f'''
            <div class="card" style="grid-column: span 2;">
                <div class="card-title">⚠️ 查询结果</div>
                <div style="padding: 20px; text-align: center; color: #ff6b6b;">
                    {data.get('message', '未找到预报数据')}
                </div>
            </div>
            '''

        content = f'''
        <div class="card" style="grid-column: span 2;">
            <div class="card-title">🏞️ {reservoir_name} 洪水预报结果</div>
            <div style="padding: 20px;">
        '''

        # 基本信息
        if data:
            # 入库流量信息 - 支持多种字段名格式
            inflow_peak = data.get('inflow_peak') or data.get('入库洪峰流量') or data.get('Max_InQ')
            inflow_peak_time = data.get('inflow_peak_time') or data.get('入库洪峰时间') or data.get('MaxInQ_Time')

            # 出库流量信息
            outflow_peak = data.get('outflow_peak') or data.get('出库洪峰流量') or data.get('Max_OutQ')
            outflow_peak_time = data.get('outflow_peak_time') or data.get('出库洪峰时间') or data.get('MaxOutQ_Time')

            # 水位信息
            max_water_level = data.get('max_water_level') or data.get('最高水位') or data.get('Max_Level')
            max_water_level_time = data.get('max_water_level_time') or data.get('最高水位时间') or data.get('MaxLevel_Time')

            # 蓄水量信息
            max_storage = data.get('max_storage') or data.get('最大蓄水量') or data.get('Max_Volumn')

            # 总入库量和总出库量
            total_inflow = data.get('Total_InVolumn') or data.get('总入库量')
            total_outflow = data.get('Total_OutVolumn') or data.get('总出库量')

            # 预报结束时水位和蓄水量
            end_level = data.get('EndTime_Level') or data.get('预报结束水位')
            end_storage = data.get('EndTime_Volumn') or data.get('预报结束蓄水量')

            info_items = []

            if inflow_peak is not None:
                info_items.append(('入库洪峰流量', f'{inflow_peak} m³/s'))
            if inflow_peak_time:
                info_items.append(('入库洪峰时间', str(inflow_peak_time)))
            if outflow_peak is not None:
                info_items.append(('出库洪峰流量', f'{outflow_peak} m³/s'))
            if outflow_peak_time:
                info_items.append(('出库洪峰时间', str(outflow_peak_time)))
            if max_water_level is not None:
                info_items.append(('最高水位', f'{max_water_level} m'))
            if max_water_level_time:
                info_items.append(('最高水位时间', str(max_water_level_time)))
            if max_storage is not None:
                info_items.append(('最大蓄水量', f'{max_storage} 万m³'))
            if total_inflow is not None:
                info_items.append(('总入库量', f'{total_inflow} 万m³'))
            if total_outflow is not None:
                info_items.append(('总出库量', f'{total_outflow} 万m³'))
            if end_level is not None:
                info_items.append(('预报结束水位', f'{end_level} m'))
            if end_storage is not None:
                info_items.append(('预报结束蓄水量', f'{end_storage} 万m³'))

            for label, value in info_items:
                content += f'''
                <div class="info-item">
                    <span class="info-label">{label}</span>
                    <span class="info-value">{value}</span>
                </div>
                '''
        else:
            content += '<p style="color: #888;">暂无预报数据</p>'

        content += '''
            </div>
        </div>
        '''

        return content

    def _generate_station_forecast_content(
        self,
        station_name: str,
        data: Dict[str, Any]
    ) -> str:
        """生成站点预报结果内容"""

        if 'message' in data and '未找到' in data.get('message', ''):
            return f'''
            <div class="card" style="grid-column: span 2;">
                <div class="card-title">⚠️ 查询结果</div>
                <div style="padding: 20px; text-align: center; color: #ff6b6b;">
                    {data.get('message', '未找到预报数据')}
                </div>
            </div>
            '''

        content = f'''
        <div class="card" style="grid-column: span 2;">
            <div class="card-title">📍 {station_name} 洪水预报结果</div>
            <div style="padding: 20px;">
        '''

        if data:
            peak_flow = data.get('peak_flow', data.get('洪峰流量'))
            peak_time = data.get('peak_time', data.get('洪峰时间'))
            peak_level = data.get('peak_level', data.get('洪峰水位'))

            info_items = []
            if peak_flow is not None:
                info_items.append(('洪峰流量', f'{peak_flow} m³/s'))
            if peak_time:
                info_items.append(('洪峰时间', str(peak_time)))
            if peak_level is not None:
                info_items.append(('洪峰水位', f'{peak_level} m'))

            if not info_items:
                for key, value in data.items():
                    if key not in ['message']:
                        info_items.append((key, str(value)))

            for label, value in info_items:
                content += f'''
                <div class="info-item">
                    <span class="info-label">{label}</span>
                    <span class="info-value">{value}</span>
                </div>
                '''
        else:
            content += '<p style="color: #888;">暂无预报数据</p>'

        content += '''
            </div>
        </div>
        '''

        return content

    def _generate_detention_forecast_content(
        self,
        detention_name: str,
        data: Dict[str, Any]
    ) -> str:
        """生成蓄滞洪区预报结果内容"""

        if 'message' in data and '未找到' in data.get('message', ''):
            return f'''
            <div class="card" style="grid-column: span 2;">
                <div class="card-title">⚠️ 查询结果</div>
                <div style="padding: 20px; text-align: center; color: #ff6b6b;">
                    {data.get('message', '未找到预报数据')}
                </div>
            </div>
            '''

        content = f'''
        <div class="card" style="grid-column: span 2;">
            <div class="card-title">🌊 {detention_name} 洪水预报结果</div>
            <div style="padding: 20px;">
        '''

        if data:
            for key, value in data.items():
                if key not in ['message']:
                    content += f'''
                    <div class="info-item">
                        <span class="info-label">{key}</span>
                        <span class="info-value">{value}</span>
                    </div>
                    '''
        else:
            content += '<p style="color: #888;">暂无预报数据</p>'

        content += '''
            </div>
        </div>
        '''

        return content

    def _generate_basin_forecast_content(self, data: Dict[str, Any]) -> str:
        """生成全流域预报结果内容"""

        content = '''
        <div class="card" style="grid-column: span 2;">
            <div class="card-title">🌍 全流域洪水预报结果</div>
            <div style="padding: 20px;">
        '''

        # 处理水库结果
        reservoir_result = data.get('reservoir_result', {})
        if reservoir_result:
            content += '<h4 style="color: #00d4ff; margin: 15px 0 10px;">水库预报结果</h4>'
            for res_name, res_data in reservoir_result.items():
                content += f'<div style="margin-bottom: 15px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px;">'
                content += f'<strong style="color: #00d4ff;">{res_name}</strong>'
                if isinstance(res_data, dict):
                    for key, value in res_data.items():
                        content += f'''
                        <div class="info-item" style="margin-left: 10px;">
                            <span class="info-label">{key}</span>
                            <span class="info-value">{value}</span>
                        </div>
                        '''
                content += '</div>'

        # 处理站点结果
        station_result = data.get('station_result', data.get('stations', []))
        if station_result:
            content += '<h4 style="color: #00d4ff; margin: 15px 0 10px;">站点预报结果</h4>'
            if isinstance(station_result, list):
                for sta in station_result:
                    sta_name = sta.get('name', '未知站点')
                    content += f'<div style="margin-bottom: 15px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px;">'
                    content += f'<strong style="color: #00d4ff;">{sta_name}</strong>'
                    for key, value in sta.items():
                        if key != 'name':
                            content += f'''
                            <div class="info-item" style="margin-left: 10px;">
                                <span class="info-label">{key}</span>
                                <span class="info-value">{value}</span>
                            </div>
                            '''
                    content += '</div>'

        if not reservoir_result and not station_result:
            # 显示原始数据
            for key, value in data.items():
                if isinstance(value, dict):
                    content += f'<h4 style="color: #00d4ff; margin: 15px 0 10px;">{key}</h4>'
                    for k, v in value.items():
                        content += f'''
                        <div class="info-item">
                            <span class="info-label">{k}</span>
                            <span class="info-value">{v}</span>
                        </div>
                        '''
                else:
                    content += f'''
                    <div class="info-item">
                        <span class="info-label">{key}</span>
                        <span class="info-value">{value}</span>
                    </div>
                    '''

        content += '''
            </div>
        </div>
        '''

        return content

    def _generate_emergency_plan_page(
        self,
        data: Dict[str, Any],
        title: Optional[str] = None
    ) -> str:
        """生成应急预案报告页面"""
        
        warning = data.get('warning', {})
        historical = data.get('historical', {})
        vulnerability = data.get('vulnerability', {})
        plan = data.get('plan', {})
        
        page_title = title or "防洪应急预案"
        generate_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        warning_level = warning.get('level', 'yellow')
        warning_text = {
            'blue': '蓝色预警',
            'yellow': '黄色预警',
            'orange': '橙色预警',
            'red': '红色预警'
        }.get(warning_level, '黄色预警')
        warning_class = self._template_manager.get_warning_class(warning_level)
        
        # 生成响应措施表格
        response_rows = self._generate_response_rows(plan.get('measures', []))
        
        # 生成安置点信息
        shelter_info = self._generate_shelter_info(plan.get('shelters', []))
        
        content_template = self._template_manager.get_template('emergency_plan')
        content = content_template.format(
            warning_level=warning_text,
            warning_class=warning_class,
            warning_time=warning.get('time', generate_time),
            affected_areas=', '.join(warning.get('areas', ['暂无'])),
            response_rows=response_rows,
            shelter_info=shelter_info
        )
        
        scripts = self._generate_emergency_plan_charts(vulnerability, historical, plan)
        
        return self._template_manager.render_base_template(
            title=page_title,
            content=content,
            generate_time=generate_time,
            scripts=scripts
        )
    
    def _generate_generic_page(
        self,
        data: Dict[str, Any],
        title: str
    ) -> str:
        """生成通用报告页面"""
        
        generate_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 将数据转换为信息卡片
        content = '<div class="card" style="grid-column: span 2;">'
        content += f'<div class="card-title">📊 {title}</div>'
        content += '<div style="padding: 20px;">'
        
        for key, value in data.items():
            if isinstance(value, dict):
                content += f'<h4 style="color: #00d4ff; margin: 15px 0 10px;">{key}</h4>'
                for k, v in value.items():
                    content += f'''
                    <div class="info-item">
                        <span class="info-label">{k}</span>
                        <span class="info-value">{v}</span>
                    </div>
                    '''
            elif isinstance(value, list):
                content += f'<h4 style="color: #00d4ff; margin: 15px 0 10px;">{key}</h4>'
                content += '<ul style="list-style: none; padding: 0;">'
                for item in value:
                    content += f'<li style="padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,0.1);">{item}</li>'
                content += '</ul>'
            else:
                content += f'''
                <div class="info-item">
                    <span class="info-label">{key}</span>
                    <span class="info-value">{value}</span>
                </div>
                '''
        
        content += '</div></div>'
        
        return self._template_manager.render_base_template(
            title=title,
            content=content,
            generate_time=generate_time,
            scripts=""
        )
    
    def _generate_station_rows(
        self,
        stations: List[Dict[str, Any]],
        predictions: List[Dict[str, Any]]
    ) -> str:
        """生成站点数据表格行"""
        
        if not stations:
            # 使用模拟数据
            stations = [
                {'name': '上游站', 'current': 85.5, 'warning': 90.0},
                {'name': '中游站', 'current': 78.2, 'warning': 85.0},
                {'name': '下游站', 'current': 72.8, 'warning': 80.0}
            ]
        
        # 创建预测数据映射
        pred_map = {p.get('station_name', ''): p for p in predictions}
        
        rows = []
        for station in stations:
            name = station.get('name', '')
            current = station.get('current', station.get('value', 0))
            warning = station.get('warning', station.get('warning_level', 0))
            
            pred = pred_map.get(name, {})
            predicted = pred.get('predicted', current + 2)
            
            # 确定状态
            if predicted >= warning:
                status = '超警'
                status_class = 'status-danger'
            elif predicted >= warning * 0.9:
                status = '接近警戒'
                status_class = 'status-warning'
            else:
                status = '正常'
                status_class = 'status-normal'
            
            rows.append(f'''
            <tr>
                <td>{name}</td>
                <td>{current:.2f}</td>
                <td>{predicted:.2f}</td>
                <td>{warning:.2f}</td>
                <td class="{status_class}">{status}</td>
            </tr>
            ''')
        
        return '\n'.join(rows)
    
    def _generate_response_rows(self, measures: List[Dict[str, Any]]) -> str:
        """生成响应措施表格行"""
        
        if not measures:
            # 使用模拟数据
            measures = [
                {'name': '启动应急响应', 'dept': '应急管理局', 'deadline': '立即', 'priority': '高'},
                {'name': '发布预警信息', 'dept': '气象局', 'deadline': '1小时内', 'priority': '高'},
                {'name': '组织人员转移', 'dept': '各乡镇', 'deadline': '4小时内', 'priority': '高'},
                {'name': '物资调配', 'dept': '民政局', 'deadline': '6小时内', 'priority': '中'},
                {'name': '交通管制', 'dept': '交通局', 'deadline': '2小时内', 'priority': '中'}
            ]
        
        priority_class = {
            '高': 'status-danger',
            '中': 'status-warning',
            '低': 'status-normal'
        }
        
        rows = []
        for i, measure in enumerate(measures, 1):
            priority = measure.get('priority', '中')
            rows.append(f'''
            <tr>
                <td>{i}</td>
                <td>{measure.get('name', '')}</td>
                <td>{measure.get('dept', '')}</td>
                <td>{measure.get('deadline', '')}</td>
                <td class="{priority_class.get(priority, 'status-normal')}">{priority}</td>
            </tr>
            ''')
        
        return '\n'.join(rows)
    
    def _generate_shelter_info(self, shelters: List[Dict[str, Any]]) -> str:
        """生成安置点信息"""
        
        if not shelters:
            shelters = [
                {'name': '第一中学', 'capacity': 500, 'current': 0},
                {'name': '体育馆', 'capacity': 1000, 'current': 0},
                {'name': '社区中心', 'capacity': 200, 'current': 0}
            ]
        
        html = '<div style="max-height: 200px; overflow-y: auto;">'
        for shelter in shelters:
            capacity = shelter.get('capacity', 0)
            current = shelter.get('current', 0)
            usage = (current / capacity * 100) if capacity > 0 else 0
            
            html += f'''
            <div style="margin-bottom: 10px; padding: 10px; background: rgba(255,255,255,0.05); border-radius: 5px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>{shelter.get('name', '')}</span>
                    <span>{current}/{capacity}人</span>
                </div>
                <div style="background: #333; height: 6px; border-radius: 3px; overflow: hidden;">
                    <div style="width: {usage}%; height: 100%; background: #00d4ff;"></div>
                </div>
            </div>
            '''
        html += '</div>'
        
        return html
    
    def _generate_flood_forecast_charts(
        self,
        rainfall: Dict[str, Any],
        water_level: Dict[str, Any],
        forecast: Dict[str, Any]
    ) -> str:
        """生成洪水预报图表脚本"""
        
        scripts = []
        
        # 降雨量图表
        rainfall_data = rainfall.get('data', [])
        if not rainfall_data:
            # 模拟数据
            rainfall_data = {
                'x_data': ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
                'y_data': [5, 12, 25, 18, 8, 3]
            }
        scripts.append(self._template_manager.generate_chart_script(
            'rainfall-chart', 'bar', rainfall_data
        ))
        
        # 水位图表
        wl_data = water_level.get('data', {})
        if not wl_data:
            wl_data = {
                'x_data': ['Day1', 'Day2', 'Day3', 'Day4', 'Day5'],
                'y_data': [75.5, 78.2, 82.1, 85.5, 83.2]
            }
        scripts.append(self._template_manager.generate_chart_script(
            'water-level-chart', 'line', wl_data
        ))
        
        # 流量图表
        flow_data = forecast.get('flow_data', {})
        if not flow_data:
            flow_data = {
                'x_data': ['Day1', 'Day2', 'Day3', 'Day4', 'Day5'],
                'y_data': [1200, 1500, 2100, 2800, 2400]
            }
        scripts.append(self._template_manager.generate_chart_script(
            'flow-chart', 'line', flow_data
        ))
        
        return '\n'.join(scripts)
    
    def _generate_emergency_plan_charts(
        self,
        vulnerability: Dict[str, Any],
        historical: Dict[str, Any],
        plan: Dict[str, Any]
    ) -> str:
        """生成应急预案图表脚本"""
        
        scripts = []
        
        # 风险评估饼图
        risk_data = vulnerability.get('risk_data', {})
        if not risk_data:
            risk_data = {
                'pie_data': [
                    {'value': 30, 'name': '高风险区'},
                    {'value': 45, 'name': '中风险区'},
                    {'value': 25, 'name': '低风险区'}
                ]
            }
        scripts.append(self._template_manager.generate_chart_script(
            'risk-chart', 'pie', risk_data
        ))
        
        # 历史对比图
        history_data = historical.get('comparison', {})
        if not history_data:
            history_data = {
                'x_data': ['2019', '2020', '2021', '2022', '2023'],
                'y_data': [85.2, 92.1, 78.5, 88.3, 95.0]
            }
        scripts.append(self._template_manager.generate_chart_script(
            'history-chart', 'bar', history_data
        ))
        
        # 转移人口图
        evac_data = plan.get('evacuation_data', {})
        if not evac_data:
            evac_data = {
                'pie_data': [
                    {'value': 1200, 'name': '已转移'},
                    {'value': 800, 'name': '待转移'},
                    {'value': 3000, 'name': '无需转移'}
                ]
            }
        scripts.append(self._template_manager.generate_chart_script(
            'evacuation-chart', 'pie', evac_data
        ))
        
        return '\n'.join(scripts)
    
    def get_page_path(self, page_url: str) -> Path:
        """根据URL获取页面文件路径"""
        filename = page_url.split('/')[-1]
        return self._output_dir / filename
    
    def delete_page(self, page_url: str) -> bool:
        """删除生成的页面"""
        try:
            file_path = self.get_page_path(page_url)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"删除页面: {page_url}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除页面失败: {e}")
            return False
    
    def list_pages(self) -> List[Dict[str, Any]]:
        """列出所有生成的页面"""
        pages = []
        for file in self._output_dir.glob('*.html'):
            stat = file.stat()
            pages.append({
                'filename': file.name,
                'url': f"/pages/{file.name}",
                'size': stat.st_size,
                'created': datetime.datetime.fromtimestamp(stat.st_ctime).isoformat()
            })
        return sorted(pages, key=lambda x: x['created'], reverse=True)

    async def save_html_content(
        self,
        html_content: str,
        title: str = ""
    ) -> str:
        """
        保存HTML内容到文件（用于动态模板复用）

        Args:
            html_content: HTML内容
            title: 页面标题

        Returns:
            生成的页面URL
        """
        import re

        # 生成文件名
        page_id = str(uuid.uuid4())[:8]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"reused_{timestamp}_{page_id}.html"

        # 如果需要更新标题
        if title:
            html_content = re.sub(
                r'<title>.*?</title>',
                f'<title>{title}</title>',
                html_content
            )

        # 保存文件
        file_path = self._output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        # 返回访问URL
        page_url = f"/pages/{filename}"
        logger.info(f"动态模板复用页面保存成功: {page_url}")

        return page_url

    async def generate_page_with_template(
        self,
        template_info: Dict[str, Any],
        data: Dict[str, Any],
        title: str = "",
        workflow_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        使用预定义模板生成页面

        核心逻辑：
        1. 预定义模板（is_dynamic=False）：直接修改模板的 main.js 参数，返回模板固定路径
        2. 动态模板（is_dynamic=True）：复制模板并注入数据
        3. 如果有 replacement_config + workflow_context，使用 TemplateConfigurator

        Args:
            template_info: 模板信息，包含 template_path, name, replacement_config, is_dynamic 等
            data: 要注入的数据
            title: 页面标题
            workflow_context: 工作流上下文数据

        Returns:
            生成的页面URL
        """
        import re

        template_path = template_info.get('template_path', '')
        template_name = template_info.get('name', 'template')
        replacement_config = template_info.get('replacement_config')
        is_dynamic = template_info.get('is_dynamic', False)

        logger.info(f"使用模板生成页面: {template_name}, 模板路径: {template_path}, is_dynamic: {is_dynamic}")

        # 方式1：如果有 replacement_config 且有 workflow_context，使用配置器
        if replacement_config and workflow_context:
            try:
                return await self._generate_with_configurator(
                    template_path=template_path,
                    replacement_config=replacement_config,
                    workflow_context=workflow_context
                )
            except Exception as e:
                logger.warning(f"配置器模式失败，回退到其他逻辑: {e}")

        # 方式2：预定义模板（非动态），直接修改 main.js 参数，返回固定路径
        if not is_dynamic and data:
            try:
                return await self._update_predefined_template(
                    template_info=template_info,
                    data=data
                )
            except Exception as e:
                logger.warning(f"预定义模板参数更新失败，回退到复制模式: {e}")

        # 方式3：回退到复制模板文件并注入数据（旧逻辑）
        return await self._generate_with_copy(
            template_info=template_info,
            data=data,
            title=title
        )

    async def _generate_with_configurator(
        self,
        template_path: str,
        replacement_config: Dict[str, Any],
        workflow_context: Dict[str, Any]
    ) -> str:
        """
        使用配置器模式生成页面

        直接修改模板文件中的配置值，不复制模板。
        """
        from ..utils.template_configurator import get_template_configurator
        from ..utils.workflow_context import WorkflowContext

        logger.info("使用配置器模式生成页面")

        # 从字典恢复 WorkflowContext
        context = WorkflowContext()
        context.from_dict(workflow_context)

        # 使用配置器注入数据
        configurator = get_template_configurator()
        page_url = configurator.configure(
            template_path=template_path,
            context=context,
            replacement_config=replacement_config
        )

        logger.info(f"配置器模式生成页面成功: {page_url}")
        return page_url

    async def _update_predefined_template(
        self,
        template_info: Dict[str, Any],
        data: Dict[str, Any]
    ) -> str:
        """
        更新预定义模板的参数（不复制模板）

        直接修改模板目录下的 main.js 文件中的 DEFAULT_PARAMS，
        然后返回模板的固定访问路径。

        Args:
            template_info: 模板信息
            data: 包含要注入的参数数据

        Returns:
            模板的固定访问URL
        """
        import re
        import time

        template_path = template_info.get('template_path', '')
        template_name = template_info.get('name', 'template')

        logger.info(f"更新预定义模板参数: {template_name}")

        # 1. 确定模板目录
        template_base_dir = Path(settings.web_templates_dir)
        template_html_path = template_base_dir / template_path

        if not template_html_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")

        template_dir = template_html_path.parent
        main_js_path = template_dir / 'js' / 'main.js'

        if not main_js_path.exists():
            raise FileNotFoundError(f"main.js 文件不存在: {main_js_path}")

        # 2. 读取 main.js 内容
        with open(main_js_path, 'r', encoding='utf-8') as f:
            js_content = f.read()

        # 3. 从 data 中提取需要更新的参数
        # 支持的参数映射：data 中的字段 -> main.js 中的 DEFAULT_PARAMS 字段
        param_mappings = {
            'planCode': ['planCode', 'plan_code'],  # data 中可能的字段名
            'stcd': ['stcd', 'Stcd', 'station_code'],
            'reservoirName': ['reservoirName', 'ResName', 'reservoir_name', 'name'],
            'token': ['token', 'auth_token', 'Token']
        }

        # 从 data 中提取参数值
        params_to_update = {}

        # 尝试从 data 的不同层级提取数据
        forecast_data = data.get('data', data)  # 可能在 data.data 中
        target_info = data.get('target', {})

        for js_param, data_keys in param_mappings.items():
            for key in data_keys:
                # 先从 forecast_data 中查找
                if key in forecast_data:
                    params_to_update[js_param] = forecast_data[key]
                    break
                # 再从 target_info 中查找
                if key in target_info:
                    params_to_update[js_param] = target_info[key]
                    break
                # 最后从顶层 data 中查找
                if key in data:
                    params_to_update[js_param] = data[key]
                    break

        if not params_to_update:
            logger.warning("未找到可更新的参数，跳过模板更新")
            # 返回模板固定路径 - 根据服务器静态文件挂载配置
            # res_module 挂载在 /ui/res_module
            # 添加时间戳参数防止浏览器缓存
            cache_buster = int(time.time() * 1000)
            template_dir_name = template_html_path.parent.name
            if template_dir_name == "res_module":
                return f"/ui/res_module/index.html?_t={cache_buster}"
            else:
                # 其他模板使用通用路径（如果有挂载的话）
                return f"/ui/{template_dir_name}/index.html?_t={cache_buster}"

        logger.info(f"准备更新参数: {list(params_to_update.keys())}")

        # 4. 使用正则表达式更新 DEFAULT_PARAMS 中的值
        modified = False
        for param_name, param_value in params_to_update.items():
            # 处理不同类型的值
            if isinstance(param_value, str):
                # 字符串值需要加引号，并转义内部的单引号
                escaped_value = param_value.replace("'", "\\'")
                value_str = f"'{escaped_value}'"
            elif isinstance(param_value, bool):
                value_str = 'true' if param_value else 'false'
            elif param_value is None:
                value_str = 'null'
            else:
                value_str = str(param_value)

            # 匹配 DEFAULT_PARAMS 中的参数定义
            # 关键：使用 [^'\n]* 或 [^"\n]* 来匹配值，确保不跨行
            # 支持格式: paramName: 'value' 或 paramName: "value"
            # 注意：不使用 re.DOTALL，确保只在单行内匹配
            pattern = rf"({param_name}\s*:\s*)(['\"])([^'\"\n]*)\2(\s*[,}}/])"

            def replacer(match):
                prefix = match.group(1)
                quote = match.group(2)  # 保持原有的引号类型
                suffix = match.group(4)
                # 如果原来是双引号，转换 value_str 的引号
                if quote == '"':
                    inner_value = param_value.replace('"', '\\"') if isinstance(param_value, str) else str(param_value)
                    return f'{prefix}"{inner_value}"{suffix}'
                return f"{prefix}{value_str}{suffix}"

            new_content, count = re.subn(pattern, replacer, js_content)
            if count > 0:
                js_content = new_content
                modified = True
                logger.info(f"更新参数 {param_name} = {value_str[:50]}...")

        # 5. 写回 main.js
        if modified:
            with open(main_js_path, 'w', encoding='utf-8') as f:
                f.write(js_content)
            logger.info(f"预定义模板参数更新完成: {main_js_path}")

            # 5.1 更新 index.html 中 main.js 的引用，添加时间戳防止缓存
            index_html_path = template_dir / 'index.html'
            if index_html_path.exists():
                cache_ts = int(time.time() * 1000)
                with open(index_html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                # 替换 main.js 引用，添加或更新时间戳参数
                # 匹配 js/main.js 或 js/main.js?_t=xxx
                html_content = re.sub(
                    r'(src=["\']js/main\.js)(\?_t=\d+)?(["\'])',
                    rf'\1?_t={cache_ts}\3',
                    html_content
                )
                with open(index_html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logger.info(f"更新 index.html 中 main.js 引用的缓存时间戳: {cache_ts}")
        else:
            logger.warning("未能匹配到任何参数进行更新")

        # 6. 返回模板的固定访问路径 - 根据服务器静态文件挂载配置
        # res_module 挂载在 /ui/res_module
        # 添加时间戳参数防止浏览器缓存
        cache_buster = int(time.time() * 1000)
        template_dir_name = template_html_path.parent.name
        if template_dir_name == "res_module":
            page_url = f"/ui/res_module/index.html?_t={cache_buster}"
        else:
            # 其他模板使用通用路径（如果有挂载的话）
            page_url = f"/ui/{template_dir_name}/index.html?_t={cache_buster}"
        logger.info(f"预定义模板复用成功: {page_url}")

        return page_url

    async def _generate_with_copy(
        self,
        template_info: Dict[str, Any],
        data: Dict[str, Any],
        title: str = ""
    ) -> str:
        """
        使用复制模式生成页面（旧逻辑）

        复制模板文件到输出目录，并注入数据到 HTML。
        """
        import re
        import shutil

        template_path = template_info.get('template_path', '')
        template_name = template_info.get('name', 'template')

        try:
            # 1. 确定模板目录和文件
            template_base_dir = Path(settings.web_templates_dir)
            template_html_path = template_base_dir / template_path

            if not template_html_path.exists():
                logger.error(f"模板文件不存在: {template_html_path}")
                raise FileNotFoundError(f"模板文件不存在: {template_path}")

            template_dir = template_html_path.parent

            # 2. 读取模板HTML
            with open(template_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            # 3. 生成唯一输出目录
            page_id = str(uuid.uuid4())[:8]
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            output_dir_name = f"{template_name}_{timestamp}_{page_id}"
            output_dir = self._output_dir / output_dir_name
            output_dir.mkdir(parents=True, exist_ok=True)

            # 4. 复制模板资源文件 (css, js, images等)
            for subdir in ['css', 'js', 'images', 'fonts']:
                src_dir = template_dir / subdir
                if src_dir.exists():
                    shutil.copytree(src_dir, output_dir / subdir, dirs_exist_ok=True)

            # 5. 构建数据注入脚本
            data_script = f"""
    <script>
        window.PAGE_DATA = {json.dumps(data, ensure_ascii=False, indent=2)};
    </script>
"""

            # 6. 在 </head> 之前注入数据脚本
            if '</head>' in html_content:
                html_content = html_content.replace('</head>', f'{data_script}\n</head>')
            else:
                # 如果没有 </head>，在第一个 <script> 之前注入
                html_content = data_script + html_content

            # 7. 修改标题
            if title:
                html_content = re.sub(
                    r'<title>.*?</title>',
                    f'<title>{title}</title>',
                    html_content
                )

            # 8. 修正资源路径（相对路径保持不变，因为资源已复制）
            # 不需要修改，因为资源文件已经复制到同级目录

            # 9. 保存生成的页面
            output_html = output_dir / 'index.html'
            with open(output_html, 'w', encoding='utf-8') as f:
                f.write(html_content)

            # 10. 返回访问URL
            page_url = f"/static/pages/{output_dir_name}/index.html"
            logger.info(f"模板页面生成成功: {page_url}")

            return page_url

        except Exception as e:
            logger.error(f"使用模板生成页面失败: {e}")
            raise


# 全局页面生成器实例
_page_generator: Optional[PageGenerator] = None


def get_page_generator() -> PageGenerator:
    """获取页面生成器单例"""
    global _page_generator
    if _page_generator is None:
        _page_generator = PageGenerator()
    return _page_generator


async def generate_report_page(
    report_type: str,
    data: Dict[str, Any],
    title: Optional[str] = None,
    template: Optional[str] = None,
    user_message: str = "",
    sub_intent: str = "",
    workflow_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    生成报告页面的便捷函数

    优先尝试匹配预定义Web模板，匹配成功则套用模板，否则动态生成页面。

    Args:
        report_type: 报告类型
        data: 报告数据
        title: 页面标题
        template: 模板名称（可选，用于指定特定模板）
        user_message: 用户原始问题（用于模板匹配）
        sub_intent: 业务子意图（用于模板匹配）
        workflow_context: 工作流上下文数据（用于配置器模式）

    Returns:
        页面URL
    """
    generator = get_page_generator()

    # 1. 尝试匹配预定义Web模板
    try:
        from .template_match_service import get_template_match_service

        template_service = get_template_match_service()

        # 构建执行摘要用于模板匹配
        execution_summary = _build_execution_summary(report_type, data)

        # 如果没有传入user_message，尝试从data中提取
        if not user_message:
            target = data.get('target', {})
            target_name = target.get('name', '')
            summary = data.get('summary', '')
            user_message = summary or f"{target_name}预报结果"

        # 如果没有传入sub_intent，根据report_type推断
        if not sub_intent:
            sub_intent = _infer_sub_intent(report_type)

        logger.info(f"尝试匹配预定义模板 - user_message: {user_message[:50]}..., sub_intent: {sub_intent}")

        # 从 workflow_context 提取参数摘要（分为对象识别参数和工作流参数）
        entity_params, workflow_params = _build_available_params(workflow_context, data)

        # 执行模板匹配
        matched_template = await template_service.match_template(
            user_message=user_message,
            sub_intent=sub_intent,
            entity_params=entity_params,
            workflow_params=workflow_params
        )

        # 如果匹配到模板且置信度足够高，使用模板生成页面
        if matched_template and matched_template.get('confidence', 0) >= 0.6:
            logger.info(f"匹配到预定义模板: {matched_template.get('display_name')}, 置信度: {matched_template.get('confidence')}")

            # 准备模板数据（旧逻辑使用）
            template_data = _prepare_template_data(report_type, data, matched_template)

            # 使用模板生成页面（支持新旧两种模式）
            page_url = await generator.generate_page_with_template(
                template_info=matched_template,
                data=template_data,
                title=title or data.get('summary', ''),
                workflow_context=workflow_context  # 传递工作流上下文
            )

            # 更新模板使用计数
            template_service.increment_use_count(matched_template.get('id'), success=True)

            logger.info(f"使用预定义模板生成页面成功: {page_url}")
            return page_url

        logger.info("未匹配到合适的预定义模板，使用动态生成")

    except Exception as e:
        logger.warning(f"模板匹配失败，回退到动态生成: {e}")

    # 2. 回退：使用内置方法动态生成页面
    return generator.generate_page(report_type, data, title)


def _build_execution_summary(report_type: str, data: Dict[str, Any]) -> str:
    """构建执行摘要用于模板匹配"""
    target = data.get('target', {})
    target_type = target.get('type', '')
    target_name = target.get('name', '')
    summary = data.get('summary', '')

    parts = []
    if summary:
        parts.append(summary)
    if target_name:
        parts.append(f"目标: {target_name}")
    if target_type:
        type_map = {
            'reservoir': '水库',
            'station': '站点',
            'detention_basin': '蓄滞洪区',
            'basin': '流域'
        }
        parts.append(f"类型: {type_map.get(target_type, target_type)}")
    if report_type:
        parts.append(f"报告类型: {report_type}")

    return " ".join(parts)


def _build_available_params(workflow_context: Optional[Dict[str, Any]], data: Dict[str, Any]) -> tuple[str, str]:
    """
    从 workflow_context 和 data 中提取参数摘要，分为两类：
    1. 对象识别参数（来自实体解析阶段：数据库查询+知识库查询+LLM匹配）
    2. 工作流参数（来自工作流执行结果）

    兼容两种工作流上下文结构：
    1. WorkflowContext 类结构: steps.login.token, steps.forecast.planCode, steps.extract.stcd
    2. 简单字典结构: auth_token, plan_id, results.extracted_result

    Args:
        workflow_context: 工作流上下文数据
        data: 报告数据

    Returns:
        (entity_params, workflow_params) 元组
    """
    entity_params = []  # 对象识别参数（实体解析阶段）
    workflow_params = []  # 工作流参数（工作流执行结果）

    if workflow_context:
        steps = workflow_context.get('steps', {})

        # ========== 对象识别参数（来自实体解析阶段）==========
        # stcd 应该从实体解析阶段获取（工作流执行前的3步曲：数据库查询+知识库查询+LLM匹配）
        stcd = None
        # 方式1（优先）: 从 workflow_context.inputs.entities 获取（实体解析阶段的结果）
        inputs = workflow_context.get('inputs', {})
        entities = inputs.get('entities', {})
        if entities and isinstance(entities, dict):
            stcd = entities.get('stcd') or entities.get('Stcd')
        # 方式2: WorkflowContext 类结构（备用）
        if not stcd:
            extract_step = steps.get('extract', {})
            stcd = extract_step.get('stcd') or extract_step.get('Stcd')

        if stcd:
            entity_params.append(f"- stcd: {stcd} (站点代码)")

        # reservoirName 来自实体解析阶段
        target_name = None
        # 方式1: WorkflowContext 类结构
        parse_step = steps.get('parse_target', {})
        target_name = parse_step.get('target_name')
        # 方式2: 从 session_params 提取
        if not target_name:
            session_params = workflow_context.get('session_params', {})
            ft = session_params.get('forecast_target', {})
            if ft:
                target_name = ft.get('name')

        if target_name:
            entity_params.append(f"- reservoirName: {target_name} (预报目标名称)")

        # ========== 工作流参数（来自工作流执行结果）==========
        # token 来自登录认证步骤
        token = None
        # 方式1: WorkflowContext 类结构
        login_step = steps.get('login', {})
        if login_step.get('token'):
            token = login_step.get('token')
        # 方式2: 简单字典结构
        if not token and workflow_context.get('auth_token'):
            token = workflow_context.get('auth_token')

        if token:
            workflow_params.append("- token: 已获取 (来自登录认证)")

        # planCode 来自预报方案步骤
        plan_code = None
        # 方式1: WorkflowContext 类结构
        forecast_step = steps.get('forecast', {})
        plan_code = forecast_step.get('planCode') or forecast_step.get('plan_code')
        # 方式2: 简单字典结构
        if not plan_code and workflow_context.get('plan_id'):
            plan_code = workflow_context.get('plan_id')

        if plan_code:
            workflow_params.append(f"- planCode: {plan_code} (来自预报方案)")

    # 从 data 中提取信息
    if data:
        target = data.get('target', {})
        if target:
            target_type = target.get('type', '')
            target_name_from_data = target.get('name', '')
            if target_type:
                entity_params.append(f"- forecast_target_type: {target_type}")
            if target_name_from_data and not any('reservoirName' in p for p in entity_params):
                entity_params.append(f"- reservoirName: {target_name_from_data} (来自报告数据)")

        # 从 data 中提取 stcd（兼容大小写）
        stcd_from_data = data.get('stcd') or data.get('Stcd')
        if stcd_from_data and not any('stcd' in p for p in entity_params):
            entity_params.append(f"- stcd: {stcd_from_data} (来自报告数据)")

    # 格式化输出
    entity_params_str = "\n".join(entity_params) if entity_params else "无"
    workflow_params_str = "\n".join(workflow_params) if workflow_params else "无"

    return entity_params_str, workflow_params_str


def _infer_sub_intent(report_type: str) -> str:
    """根据报告类型推断业务子意图"""
    intent_map = {
        'auto_forecast': 'flood_forecast',
        'manual_forecast': 'flood_forecast',
        'flood_forecast': 'flood_forecast',
        'emergency_plan': 'emergency_response',
        'data_query': 'data_query'
    }
    return intent_map.get(report_type, 'flood_forecast')


def _prepare_template_data(
    report_type: str,
    data: Dict[str, Any],
    template_info: Dict[str, Any]
) -> Dict[str, Any]:
    """准备模板所需的数据"""
    template_name = template_info.get('name', '')
    target = data.get('target', {})
    forecast_data = data.get('data', {})

    # 基础数据
    template_data = {
        "report_type": report_type,
        "target": target,
        "summary": data.get('summary', ''),
        "raw_data": forecast_data
    }

    # 根据模板类型准备特定数据
    if template_name == 'res_flood_resultshow':
        # 水库洪水预报结果展示模板
        target_name = target.get('name', '')
        template_data["reservoir_name"] = target_name
        template_data["reservoir_code"] = forecast_data.get('Stcd', '')

        # 关键指标
        template_data["max_level"] = forecast_data.get('Max_Level')
        template_data["max_level_time"] = forecast_data.get('MaxLevel_Time')
        template_data["max_inflow"] = forecast_data.get('Max_InQ')
        template_data["max_inflow_time"] = forecast_data.get('MaxInQ_Time')
        template_data["max_outflow"] = forecast_data.get('Max_OutQ')
        template_data["max_outflow_time"] = forecast_data.get('MaxOutQ_Time')
        template_data["max_storage"] = forecast_data.get('Max_Volumn')
        template_data["total_inflow"] = forecast_data.get('Total_InVolumn')
        template_data["total_outflow"] = forecast_data.get('Total_OutVolumn')
        template_data["end_level"] = forecast_data.get('EndTime_Level')
        template_data["end_storage"] = forecast_data.get('EndTime_Volumn')

        # 构建模板期望的 reservoir_result 结构
        # 模板 JavaScript 期望: pageData.reservoir_result = { InQ_Dic, OutQ_Dic, Level_Dic, ... }
        template_data["reservoir_result"] = {
            "Stcd": forecast_data.get('Stcd', ''),
            "Max_Level": forecast_data.get('Max_Level'),
            "MaxLevel_Time": forecast_data.get('MaxLevel_Time'),
            "Max_InQ": forecast_data.get('Max_InQ'),
            "MaxInQ_Time": forecast_data.get('MaxInQ_Time'),
            "Max_OutQ": forecast_data.get('Max_OutQ'),
            "MaxOutQ_Time": forecast_data.get('MaxOutQ_Time'),
            "Max_Volumn": forecast_data.get('Max_Volumn'),
            "Total_InVolumn": forecast_data.get('Total_InVolumn'),
            "Total_OutVolumn": forecast_data.get('Total_OutVolumn'),
            "EndTime_Level": forecast_data.get('EndTime_Level'),
            "EndTime_Volumn": forecast_data.get('EndTime_Volumn'),
            # 时序数据（用于图表渲染）
            "InQ_Dic": forecast_data.get('InQ_Dic', {}),
            "OutQ_Dic": forecast_data.get('OutQ_Dic', {}),
            "Level_Dic": forecast_data.get('Level_Dic', {}),
            "Volumn_Dic": forecast_data.get('Volumn_Dic', {})
        }

        # 预报结果描述
        template_data["result_desc"] = data.get('summary', '')

        # 降雨数据（如果有）
        template_data["rain_data"] = forecast_data.get('rain_data', [])

        # 保留旧字段兼容性
        template_data["inflow_series"] = forecast_data.get('InQ_Dic', {})
        template_data["outflow_series"] = forecast_data.get('OutQ_Dic', {})
        template_data["level_series"] = forecast_data.get('Level_Dic', {})
        template_data["storage_series"] = forecast_data.get('Volumn_Dic', {})

    return template_data
