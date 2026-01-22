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
        title: str = ""
    ) -> str:
        """
        使用预定义模板生成页面

        Args:
            template_info: 模板信息，包含 template_path, name 等
            data: 要注入的数据
            title: 页面标题

        Returns:
            生成的页面URL
        """
        import re
        import shutil

        template_path = template_info.get('template_path', '')
        template_name = template_info.get('name', 'template')

        logger.info(f"使用模板生成页面: {template_name}, 模板路径: {template_path}")

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
    template: Optional[str] = None
) -> str:
    """
    生成报告页面的便捷函数

    Args:
        report_type: 报告类型
        data: 报告数据
        title: 页面标题
        template: 模板名称（可选，用于指定特定模板）

    Returns:
        页面URL
    """
    generator = get_page_generator()
    # template参数目前保留用于未来扩展，当前根据report_type自动选择模板
    return generator.generate_page(report_type, data, title)
