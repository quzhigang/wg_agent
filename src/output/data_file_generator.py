"""
数据文件生成器

生成动态页面所需的 config.js 和 data.js 文件。

config.js: 包含 PAGE_CONFIG 配置（布局、组件、API配置）
data.js: 包含静态数据（无法通过API获取的数据或需要二次处理的数据）
"""

from typing import Dict, Any, Optional, List
from pathlib import Path
import json
from datetime import datetime

from ..config.logging_config import get_logger

logger = get_logger(__name__)


class DataFileGenerator:
    """
    数据文件生成器

    负责生成动态页面所需的配置文件和数据文件。

    生成的文件：
    1. config.js - 包含 PAGE_CONFIG 配置
       - meta: 页面元信息（标题、描述、生成时间）
       - layout: 布局配置（grid/flex/single）
       - components: 组件配置（类型、数据源、样式）
       - api_config: API配置（URL、参数、认证）

    2. data.js - 包含静态数据
       - 无法通过API获取的数据
       - 需要二次处理的数据
       - 使用 window.PAGE_DATA = {...} 格式
    """

    def __init__(self, output_dir: Path):
        """
        初始化生成器

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_config_js(
        self,
        page_config: Dict[str, Any],
        filename: str = "config.js"
    ) -> Path:
        """
        生成 config.js 文件

        Args:
            page_config: PAGE_CONFIG 配置字典
            filename: 输出文件名

        Returns:
            生成的文件路径
        """
        # 确保必要的字段存在
        config = self._ensure_config_structure(page_config)

        # 生成 JavaScript 内容
        js_content = self._generate_config_js_content(config)

        # 写入文件
        file_path = self.output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(js_content)

        logger.info(f"生成 config.js: {file_path}")
        return file_path

    def generate_data_js(
        self,
        static_data: Dict[str, Any],
        context_data: Optional[Dict[str, Any]] = None,
        filename: str = "data.js"
    ) -> Path:
        """
        生成 data.js 文件

        Args:
            static_data: 静态数据字典
            context_data: 上下文数据（可选）
            filename: 输出文件名

        Returns:
            生成的文件路径
        """
        # 预处理上下文数据，提取结构化信息供组件使用
        processed_context = self._preprocess_context_data(context_data) if context_data else {}

        # 合并数据
        data = {
            "static": static_data,
            "context": processed_context,
            "generated_at": datetime.now().isoformat()
        }

        # 生成 JavaScript 内容
        js_content = self._generate_data_js_content(data)

        # 写入文件
        file_path = self.output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(js_content)

        logger.info(f"生成 data.js: {file_path}")
        return file_path

    def _preprocess_context_data(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        预处理上下文数据，提取结构化信息供组件使用

        从多个数据源提取：
        1. 检索文档（retrieval.documents）：图片URL、表格数据、关键属性
        2. 工具调用结果（execution.tool_calls）：视频监控、闸站参数等业务数据

        Args:
            context: 原始上下文数据

        Returns:
            预处理后的上下文数据
        """
        import re

        # 如果已经预处理过（存在预处理标记），直接返回
        if context.get('_preprocessed'):
            return context

        # 复制原始数据
        processed = context.copy()
        processed['_preprocessed'] = True  # 添加预处理标记

        # ========== 1. 从工具调用结果中提取业务数据 ==========
        execution = context.get('execution', {})
        tool_calls = execution.get('tool_calls', [])

        if tool_calls:
            tool_data = self._extract_tool_call_data(tool_calls)
            processed.update(tool_data)

        # ========== 2. 提取检索文档中的结构化数据 ==========
        retrieval = context.get('retrieval', {})
        documents = retrieval.get('documents', [])

        if documents:
            # 1. 收集所有图片URL
            all_images = []
            for doc in documents:
                metadata = doc.get('metadata', {})
                images = metadata.get('images', [])
                all_images.extend(images)

            # 2. 解析文档内容，提取结构化信息
            parsed_info = []
            for doc in documents:
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})

                # 解析 Markdown 格式的键值对（如 "- **key**: value"）
                kv_pattern = r'-\s*\*\*([^*]+)\*\*[：:]\s*(.+?)(?=\n|$)'
                matches = re.findall(kv_pattern, content)

                for key, value in matches:
                    # 跳过一些不需要展示的字段
                    skip_keys = ['id', 'update_time', '模型实例']
                    if key.strip().lower() not in [k.lower() for k in skip_keys]:
                        parsed_info.append({
                            'label': key.strip(),
                            'value': value.strip()
                        })

            # 3. 提取地理坐标（用于地图组件）
            geo_info = self._extract_geo_info(documents)

            # 4. 提取泄流曲线数据（用于图表组件）
            discharge_curve = self._extract_discharge_curve(documents)

            # 5. 提取关键指标（用于 StatCard 组件）
            key_metrics = self._extract_key_metrics(parsed_info)

            # 6. 添加预处理后的数据到 context（合并而非覆盖）
            # 合并图片列表
            if 'all_images' not in processed:
                processed['all_images'] = []
            processed['all_images'].extend(all_images)

            # 合并表格数据（知识库数据追加到工具调用数据之后）
            if 'parsed_info_table' not in processed:
                processed['parsed_info_table'] = []
            processed['parsed_info_table'].extend(parsed_info)

            # 合并地理信息（优先使用知识库数据，因为通常更准确）
            if geo_info:
                processed['geo_info'] = geo_info

            # 合并泄流曲线
            if discharge_curve:
                processed['discharge_curve'] = discharge_curve

            # 合并关键指标（知识库数据优先）
            if key_metrics:
                if 'key_metrics' not in processed:
                    processed['key_metrics'] = {}
                # 知识库数据覆盖工具调用数据（知识库数据通常更完整）
                processed['key_metrics'].update(key_metrics)

        return processed

    def _extract_tool_call_data(self, tool_calls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从工具调用结果中提取业务数据

        根据工具名称提取特定类型的数据，供页面组件使用。
        支持的工具类型：
        - get_camera_list: 视频监控摄像头列表
        - lookup_station_code: 站点编码查询结果
        - 其他工具: 通用数据提取

        Args:
            tool_calls: 工具调用记录列表

        Returns:
            提取的业务数据字典
        """
        extracted = {}

        for tool_call in tool_calls:
            tool_name = tool_call.get('tool_name', '')
            success = tool_call.get('success', False)
            output = tool_call.get('output_result')

            if not success or not output:
                continue

            # 根据工具名称提取特定数据
            if tool_name == 'get_camera_list':
                # 视频监控摄像头列表
                camera_list = self._extract_camera_list(output)
                if camera_list:
                    extracted['camera_list'] = camera_list
                    # 提取第一个摄像头的名称
                    if camera_list and len(camera_list) > 0:
                        first_camera = camera_list[0]
                        extracted['default_camera_name'] = first_camera.get('name', '')

            elif tool_name == 'query_camera_preview':
                # 视频监控预览流地址
                video_url = self._extract_video_url(output)
                if video_url:
                    extracted['default_video_url'] = video_url

            elif tool_name == 'lookup_station_code':
                # 站点编码查询结果
                station_info = self._extract_station_info(output)
                if station_info:
                    extracted['station_info'] = station_info

            elif tool_name in ['get_gate_station_params', 'get_reservoir_params', 'get_pump_station_params']:
                # 闸站/水库/泵站参数查询结果
                params_data = self._extract_params_data(tool_name, output)
                if params_data:
                    extracted['params_data'] = params_data
                    # 同时提取为表格格式（兼容现有模板）
                    if 'parsed_info_table' not in extracted:
                        extracted['parsed_info_table'] = []
                    extracted['parsed_info_table'].extend(params_data.get('table_data', []))

            elif tool_name == 'get_realtime_water_level':
                # 实时水位数据
                water_level_data = self._extract_water_level_data(output)
                if water_level_data:
                    extracted['water_level_data'] = water_level_data

            # ========== 实时监测数据工具处理 ==========
            elif tool_name == 'query_river_last':
                # 河道最新水情数据
                realtime_data = self._extract_realtime_monitor_data(output, 'river')
                if realtime_data:
                    self._merge_realtime_data(extracted, realtime_data)

            elif tool_name == 'query_reservoir_last':
                # 水库最新水情数据
                realtime_data = self._extract_realtime_monitor_data(output, 'reservoir')
                if realtime_data:
                    self._merge_realtime_data(extracted, realtime_data)

            elif tool_name in ['query_rain_process', 'query_rain_statistics', 'query_rain_sum']:
                # 雨情数据
                realtime_data = self._extract_realtime_monitor_data(output, 'rain')
                if realtime_data:
                    self._merge_realtime_data(extracted, realtime_data)

            elif tool_name in ['query_ai_water_last', 'query_ai_water_process']:
                # AI水情监测数据
                realtime_data = self._extract_realtime_monitor_data(output, 'ai_water')
                if realtime_data:
                    self._merge_realtime_data(extracted, realtime_data)

            elif tool_name in ['query_ai_rain_last', 'query_ai_rain_process']:
                # AI雨情监测数据
                realtime_data = self._extract_realtime_monitor_data(output, 'ai_rain')
                if realtime_data:
                    self._merge_realtime_data(extracted, realtime_data)

            # 通用处理：将所有成功的工具调用结果按工具名存储
            # 这样页面可以通过 data_source: { type: "context", path: "tool_results.{tool_name}" } 访问
            if 'tool_results' not in extracted:
                extracted['tool_results'] = {}
            extracted['tool_results'][tool_name] = output

        return extracted

    def _extract_camera_list(self, output: Any) -> List[Dict[str, Any]]:
        """
        提取视频监控摄像头列表

        Args:
            output: 工具输出结果（get_camera_list 返回的数据）

        Returns:
            摄像头列表，每个元素包含 code, name, stcd 等字段
        """
        # 处理 ToolResult 结构
        if isinstance(output, dict) and 'data' in output:
            data = output.get('data')
            if isinstance(data, list):
                return self._extract_camera_list(data)
            return []

        if isinstance(output, list):
            # 直接是列表格式
            return [
                {
                    'code': item.get('code', ''),
                    # API 返回的名称字段可能是 stnm, title, name
                    'name': item.get('stnm') or item.get('title') or item.get('name', ''),
                    'stcd': item.get('stcd', ''),
                    'type': item.get('type', ''),
                    'status': 'online' if item.get('aiEnable') == '1' else 'normal'
                }
                for item in output
            ]
        return []

    def _extract_video_url(self, output: Any) -> str:
        """
        从 query_camera_preview 结果中提取视频流 URL

        Args:
            output: 工具输出结果

        Returns:
            视频流 URL
        """
        # 处理 ToolResult 结构: {success: true, data: {msg, code, data: {url}}}
        if isinstance(output, dict):
            # 先检查是否是 ToolResult 结构
            if 'data' in output and isinstance(output.get('data'), dict):
                inner_data = output['data']
                # 检查内层 data 结构: {msg, code, data: {url}}
                if 'data' in inner_data and isinstance(inner_data.get('data'), dict):
                    return inner_data['data'].get('url', '')
                # 或者直接有 url 字段
                if 'url' in inner_data:
                    return inner_data.get('url', '')
            # 直接有 url 字段
            if 'url' in output:
                return output.get('url', '')
        return ''

    def _extract_station_info(self, output: Any) -> Optional[Dict[str, Any]]:
        """
        提取站点信息

        处理 lookup_station_code 工具的返回格式：
        {success: true, data: {stcd: "xxx", stnm: "xxx", stations: [...]}}

        Args:
            output: 工具输出结果

        Returns:
            站点信息字典
        """
        # 处理 ToolResult 结构
        if isinstance(output, dict):
            # 检查是否是 ToolResult 格式
            if 'data' in output and isinstance(output.get('data'), dict):
                data = output['data']
                return {
                    'stcd': data.get('stcd', ''),
                    'name': data.get('stnm', ''),
                    'type': '',
                    'location': '',
                    'stations': data.get('stations', [])
                }
            # 直接是数据格式
            return {
                'stcd': output.get('stcd', ''),
                'name': output.get('stnm', output.get('name', '')),
                'type': output.get('type', ''),
                'location': output.get('location', '')
            }
        elif isinstance(output, list) and len(output) > 0:
            return self._extract_station_info(output[0])
        return None

    def _extract_params_data(self, tool_name: str, output: Any) -> Optional[Dict[str, Any]]:
        """
        提取参数数据（闸站、水库、泵站等）

        Args:
            tool_name: 工具名称
            output: 工具输出结果

        Returns:
            参数数据字典，包含原始数据和表格格式数据
        """
        if not isinstance(output, dict):
            return None

        # 将字典转换为表格格式
        table_data = []
        for key, value in output.items():
            # 跳过一些不需要展示的字段
            skip_keys = ['id', 'update_time', 'create_time', 'stcd']
            if key.lower() not in skip_keys and value is not None:
                table_data.append({
                    'label': key,
                    'value': str(value)
                })

        return {
            'raw': output,
            'table_data': table_data
        }

    def _extract_water_level_data(self, output: Any) -> Optional[Dict[str, Any]]:
        """
        提取实时水位数据

        Args:
            output: 工具输出结果

        Returns:
            水位数据字典
        """
        if isinstance(output, dict):
            return {
                'current_level': output.get('z', output.get('level', '')),
                'time': output.get('tm', output.get('time', '')),
                'stcd': output.get('stcd', '')
            }
        return None

    def _extract_realtime_monitor_data(self, output: Any, data_type: str) -> Optional[Dict[str, Any]]:
        """
        从实时监测数据工具结果中提取结构化数据

        支持的数据类型：
        - river: 河道水情（z水位, q流量, tm时间, lgtd/lttd坐标, stnm站名, rvnm河流名）
        - reservoir: 水库水情（z水位, w蓄水量, inq入库流量, outq出库流量）
        - rain: 雨情（drp时段降水, dyp日降水, stnm站名）
        - ai_water: AI水情监测
        - ai_rain: AI雨情监测

        Args:
            output: 工具输出结果（ToolResult格式）
            data_type: 数据类型

        Returns:
            包含 parsed_info_table, geo_info, key_metrics 的字典
        """
        # 处理 ToolResult 结构: {success: true, data: [...]}
        data = output
        if isinstance(output, dict):
            if 'data' in output:
                data = output.get('data')

        # 如果是列表，取第一条记录（单站点查询）
        if isinstance(data, list):
            if len(data) == 0:
                return None
            data = data[0]

        if not isinstance(data, dict):
            return None

        result = {
            'parsed_info_table': [],
            'geo_info': {},
            'key_metrics': {}
        }

        # 根据数据类型定义字段映射
        if data_type == 'river':
            # 河道水情字段映射
            field_mappings = {
                'stnm': '站点名称',
                'stcd': '站点编码',
                'rvnm': '河流名称',
                'z': '水位',
                'q': '流量',
                'tm': '数据时间',
                'wptn': '水势',
                'wrz': '警戒水位',
                'grz': '保证水位',
                'obhtz': '超警水位',
                'lgtd': '经度',
                'lttd': '纬度'
            }
            # 关键指标映射（用于StatCard）
            metric_mappings = {
                'z': 'water_level',
                'q': 'flow',
                'tm': 'data_time',
                'wptn': 'water_trend',
                'wrz': 'warning_level',
                'grz': 'guarantee_level'
            }

        elif data_type == 'reservoir':
            # 水库水情字段映射
            field_mappings = {
                'stnm': '水库名称',
                'stcd': '站点编码',
                'z': '库水位',
                'w': '蓄水量',
                'inq': '入库流量',
                'outq': '出库流量',
                'tm': '数据时间',
                'fsltdz': '汛限水位',
                'normz': '正常蓄水位',
                'ddz': '死水位',
                'lgtd': '经度',
                'lttd': '纬度'
            }
            metric_mappings = {
                'z': 'water_level',
                'w': 'storage',
                'inq': 'inflow',
                'outq': 'outflow',
                'tm': 'data_time',
                'fsltdz': 'flood_limit_level'
            }

        elif data_type == 'rain':
            # 雨情字段映射
            field_mappings = {
                'stnm': '站点名称',
                'stcd': '站点编码',
                'drp': '时段降水量',
                'intv': '时段长度',
                'dyp': '日降水量',
                'tm': '数据时间',
                'lgtd': '经度',
                'lttd': '纬度'
            }
            metric_mappings = {
                'drp': 'period_rainfall',
                'dyp': 'daily_rainfall',
                'tm': 'data_time'
            }

        elif data_type in ['ai_water', 'ai_rain']:
            # AI监测数据字段映射
            field_mappings = {
                'stnm': '站点名称',
                'stcd': '站点编码',
                'z': '水位',
                'drp': '时段降水量',
                'tm': '数据时间',
                'lgtd': '经度',
                'lttd': '纬度'
            }
            metric_mappings = {
                'z': 'water_level',
                'drp': 'period_rainfall',
                'tm': 'data_time'
            }
        else:
            return None

        # 1. 提取表格数据（parsed_info_table）
        for field_key, field_label in field_mappings.items():
            value = data.get(field_key)
            if value is not None and value != '':
                # 格式化显示值
                display_value = str(value)
                if field_key == 'tm' and isinstance(value, str):
                    # 时间格式化
                    display_value = value
                elif field_key in ['z', 'q', 'w', 'inq', 'outq', 'drp', 'dyp']:
                    # 数值格式化
                    try:
                        display_value = f"{float(value):.2f}"
                    except (ValueError, TypeError):
                        display_value = str(value)

                result['parsed_info_table'].append({
                    'label': field_label,
                    'value': display_value
                })

        # 2. 提取地理坐标（geo_info）
        lgtd = data.get('lgtd')
        lttd = data.get('lttd')
        if lgtd is not None and lttd is not None:
            try:
                lng = float(lgtd)
                lat = float(lttd)
                # 验证是否在中国范围内
                if 73 <= lng <= 136 and 18 <= lat <= 54:
                    result['geo_info'] = {
                        'latitude': lat,
                        'longitude': lng,
                        'center': [lng, lat],
                        'name': data.get('stnm', '')
                    }
            except (ValueError, TypeError):
                pass

        # 3. 提取关键指标（key_metrics）
        for field_key, metric_key in metric_mappings.items():
            value = data.get(field_key)
            if value is not None and value != '':
                result['key_metrics'][metric_key] = value

        return result

    def _merge_realtime_data(self, extracted: Dict[str, Any], realtime_data: Dict[str, Any]) -> None:
        """
        将实时监测数据合并到已提取的数据中

        采用合并策略而非替换，确保与知识库检索数据兼容

        Args:
            extracted: 已提取的数据字典（会被修改）
            realtime_data: 实时监测数据
        """
        # 合并 parsed_info_table（追加到现有列表）
        if 'parsed_info_table' not in extracted:
            extracted['parsed_info_table'] = []
        extracted['parsed_info_table'].extend(realtime_data.get('parsed_info_table', []))

        # 合并 geo_info（如果现有为空则使用新数据）
        if not extracted.get('geo_info') and realtime_data.get('geo_info'):
            extracted['geo_info'] = realtime_data['geo_info']

        # 合并 key_metrics（合并字典，新数据优先）
        if 'key_metrics' not in extracted:
            extracted['key_metrics'] = {}
        extracted['key_metrics'].update(realtime_data.get('key_metrics', {}))

    def _extract_geo_info(self, documents: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        从文档中提取地理坐标信息

        支持多种坐标格式：
        1. 经纬度格式（latitude/longitude, 纬度/经度, lgtd/lttd）
        2. 投影坐标格式（坐标X/坐标Y）- 自动转换为经纬度

        Args:
            documents: 文档列表

        Returns:
            地理信息字典，包含 latitude, longitude, center, name
        """
        import re

        for doc in documents:
            content = doc.get('content', '')

            # 提取对象名称（用于地图标注）
            name = ''
            name_match = re.search(r'\*{0,2}(?:name|名称|stnm)\*{0,2}[：:*]+\s*(.+?)(?:\n|$)', content, re.IGNORECASE)
            if name_match:
                name = name_match.group(1).strip()

            # 方式1：匹配 latitude/纬度 和 longitude/经度 格式
            # 支持普通格式和 markdown 加粗格式（如 **latitude:** 35.740422）
            # 注意：markdown格式中冒号后可能还有星号，如 **latitude:** 中的 :**
            lat_match = re.search(r'\*{0,2}(?:latitude|纬度)\*{0,2}[：:*]+\s*([\d.]+)', content, re.IGNORECASE)
            lng_match = re.search(r'\*{0,2}(?:longitude|经度)\*{0,2}[：:*]+\s*([\d.]+)', content, re.IGNORECASE)

            if lat_match and lng_match:
                lat = float(lat_match.group(1))
                lng = float(lng_match.group(1))
                # 验证是否为有效的经纬度范围（中国范围）
                if 73 <= lng <= 136 and 18 <= lat <= 54:
                    return {
                        'latitude': lat,
                        'longitude': lng,
                        'center': [lng, lat],
                        'name': name
                    }

            # 方式2：匹配 lgtd/lttd 格式（水利系统常用）
            # 支持普通格式和 markdown 加粗格式
            lgtd_match = re.search(r'\*{0,2}(?:lgtd|经度)\*{0,2}[：:*]+\s*([\d.]+)', content, re.IGNORECASE)
            lttd_match = re.search(r'\*{0,2}(?:lttd|纬度)\*{0,2}[：:*]+\s*([\d.]+)', content, re.IGNORECASE)

            if lgtd_match and lttd_match:
                lng = float(lgtd_match.group(1))
                lat = float(lttd_match.group(1))
                if 73 <= lng <= 136 and 18 <= lat <= 54:
                    return {
                        'latitude': lat,
                        'longitude': lng,
                        'center': [lng, lat],
                        'name': name
                    }

            # 方式3：匹配投影坐标格式（坐标X/坐标Y）
            # 水利系统常用高斯-克吕格投影坐标
            # 支持普通格式和 markdown 加粗格式
            x_match = re.search(r'\*{0,2}(?:坐标X|X坐标|x)\*{0,2}[：:*]+\s*([\d.]+)', content, re.IGNORECASE)
            y_match = re.search(r'\*{0,2}(?:坐标Y|Y坐标|y)\*{0,2}[：:*]+\s*([\d.]+)', content, re.IGNORECASE)

            if x_match and y_match:
                x = float(x_match.group(1))
                y = float(y_match.group(1))
                # 尝试将投影坐标转换为经纬度
                geo_result = self._convert_projection_to_latlon(x, y)
                if geo_result:
                    geo_result['name'] = name
                    return geo_result

        return None

    def _convert_projection_to_latlon(self, x: float, y: float) -> Optional[Dict[str, Any]]:
        """
        将投影坐标（CGCS 2000 114E 3度带投影）转换为经纬度

        本项目所有投影坐标统一使用 CGCS 2000 114E 投影坐标系（3度带，中央经线114度）

        Args:
            x: X坐标（东向坐标）
            y: Y坐标（北向坐标）

        Returns:
            地理信息字典，包含 latitude, longitude, center
        """
        import math

        # CGCS2000 椭球参数
        a = 6378137.0  # 长半轴
        f = 1 / 298.257222101  # 扁率
        b = a * (1 - f)  # 短半轴
        e2 = (a * a - b * b) / (a * a)  # 第一偏心率的平方
        e12 = (a * a - b * b) / (b * b)  # 第二偏心率的平方

        # 本项目统一使用 CGCS 2000 114E 投影坐标系（3度带，中央经线114度）
        central_meridian = 114
        x_offset = x

        # 添加500km偏移（高斯投影的假东坐标）
        x_offset = x_offset - 500000

        # 高斯-克吕格反算
        try:
            # 底点纬度迭代计算
            M = y  # 子午线弧长
            mu = M / (a * (1 - e2 / 4 - 3 * e2 * e2 / 64 - 5 * e2 * e2 * e2 / 256))

            e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))

            phi1 = mu + (3 * e1 / 2 - 27 * e1 * e1 * e1 / 32) * math.sin(2 * mu) \
                   + (21 * e1 * e1 / 16 - 55 * e1 * e1 * e1 * e1 / 32) * math.sin(4 * mu) \
                   + (151 * e1 * e1 * e1 / 96) * math.sin(6 * mu) \
                   + (1097 * e1 * e1 * e1 * e1 / 512) * math.sin(8 * mu)

            # 计算辅助参数
            N1 = a / math.sqrt(1 - e2 * math.sin(phi1) * math.sin(phi1))
            T1 = math.tan(phi1) * math.tan(phi1)
            C1 = e12 * math.cos(phi1) * math.cos(phi1)
            R1 = a * (1 - e2) / math.pow(1 - e2 * math.sin(phi1) * math.sin(phi1), 1.5)
            D = x_offset / N1

            # 计算纬度
            lat_rad = phi1 - (N1 * math.tan(phi1) / R1) * (
                D * D / 2
                - (5 + 3 * T1 + 10 * C1 - 4 * C1 * C1 - 9 * e12) * D * D * D * D / 24
                + (61 + 90 * T1 + 298 * C1 + 45 * T1 * T1 - 252 * e12 - 3 * C1 * C1) * D * D * D * D * D * D / 720
            )

            # 计算经度
            lon_rad = math.radians(central_meridian) + (
                D
                - (1 + 2 * T1 + C1) * D * D * D / 6
                + (5 - 2 * C1 + 28 * T1 - 3 * C1 * C1 + 8 * e12 + 24 * T1 * T1) * D * D * D * D * D / 120
            ) / math.cos(phi1)

            # 转换为度
            lat = math.degrees(lat_rad)
            lng = math.degrees(lon_rad)

            # 验证结果是否在中国范围内
            if 73 <= lng <= 136 and 18 <= lat <= 54:
                logger.info(f"投影坐标转换成功: ({x}, {y}) -> ({lng:.6f}, {lat:.6f})")
                return {
                    'latitude': round(lat, 6),
                    'longitude': round(lng, 6),
                    'center': [round(lng, 6), round(lat, 6)]
                }
            else:
                logger.warning(f"转换后的坐标超出中国范围: ({lng}, {lat})")
                return None

        except Exception as e:
            logger.error(f"投影坐标转换失败: {e}")
            return None

    def _extract_discharge_curve(self, documents: List[Dict[str, Any]]) -> Optional[List[List[float]]]:
        """
        从文档中提取泄流曲线数据

        Args:
            documents: 文档列表

        Returns:
            泄流曲线数据 [[流量, 水位], ...]
        """
        import re
        import json

        for doc in documents:
            content = doc.get('content', '')

            # 匹配泄流曲线数据格式：[[0,58],[20,58.86],...]
            # 关键词：水位和流量的关系、泄流曲线
            # 支持 Markdown 格式 **字段名**: 值
            curve_pattern = r'\*\*[^*]*(?:水位和流量的关系|泄流曲线)[^*]*\*\*[：:]\s*(\[\[[\d.,\s\[\]]+\]\])'
            match = re.search(curve_pattern, content)

            if match:
                try:
                    curve_data = json.loads(match.group(1))
                    return curve_data
                except json.JSONDecodeError:
                    continue

        return None

    def _extract_key_metrics(self, parsed_info: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        从解析后的信息中提取关键指标（用于 StatCard）

        Args:
            parsed_info: 解析后的键值对列表

        Returns:
            关键指标字典
        """
        # 定义需要提取的关键指标及其映射
        metric_mappings = {
            '设计流量': 'design_flow',
            '闸底高程': 'bottom_elevation',
            '闸孔数': 'gate_count',
            '闸孔数量': 'gate_count',
            'now_state': 'current_state',
            '当前状态': 'current_state',
            '单孔净宽': 'gate_width',
            '闸门高度': 'gate_height',
            '闸顶高程': 'top_elevation',
            '库容': 'capacity',
            '总库容': 'total_capacity',
            '正常蓄水位': 'normal_level',
            '汛限水位': 'flood_limit_level',
            '设计洪水位': 'design_flood_level',
            '校核洪水位': 'check_flood_level',
            '坝顶高程': 'dam_crest_elevation',
            '坝长': 'dam_length',
            '坝高': 'dam_height',
            '流域面积': 'catchment_area',
        }

        key_metrics = {}
        for item in parsed_info:
            label = item.get('label', '')
            value = item.get('value', '')

            if label in metric_mappings:
                metric_key = metric_mappings[label]
                key_metrics[metric_key] = value

        return key_metrics

    def _ensure_config_structure(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        确保配置结构完整

        Args:
            config: 原始配置

        Returns:
            完整的配置结构
        """
        # 默认 meta
        if "meta" not in config:
            config["meta"] = {}
        config["meta"].setdefault("title", "动态页面")
        config["meta"].setdefault("description", "")
        config["meta"].setdefault("generated_at", datetime.now().isoformat())

        # 默认 layout
        if "layout" not in config:
            config["layout"] = {
                "type": "grid",
                "rows": [{"cols": ["main_content"]}]
            }

        # 默认 components
        if "components" not in config:
            config["components"] = {}

        # 默认 api_config
        if "api_config" not in config:
            config["api_config"] = {}

        return config

    def _generate_config_js_content(self, config: Dict[str, Any]) -> str:
        """
        生成 config.js 文件内容

        Args:
            config: PAGE_CONFIG 配置

        Returns:
            JavaScript 文件内容
        """
        # 将配置转换为 JSON 字符串
        config_json = json.dumps(config, ensure_ascii=False, indent=2)

        # 生成 JavaScript 内容
        js_content = f"""/**
 * 页面配置文件
 * 自动生成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 *
 * PAGE_CONFIG 结构说明:
 * - meta: 页面元信息（标题、描述、生成时间）
 * - layout: 布局配置（type: grid/flex/single）
 * - components: 组件配置（类型、数据源、样式）
 * - api_config: API配置（URL、参数、认证）
 * - static_data: 静态数据（可选）
 * - context_data: 上下文数据（可选）
 */

window.PAGE_CONFIG = {config_json};

// 配置加载完成事件
if (typeof window.onPageConfigLoaded === 'function') {{
    window.onPageConfigLoaded(window.PAGE_CONFIG);
}}
"""
        return js_content

    def _generate_data_js_content(self, data: Dict[str, Any]) -> str:
        """
        生成 data.js 文件内容

        Args:
            data: 数据字典

        Returns:
            JavaScript 文件内容
        """
        # 将数据转换为 JSON 字符串
        data_json = json.dumps(data, ensure_ascii=False, indent=2)

        # 生成 JavaScript 内容
        js_content = f"""/**
 * 页面数据文件
 * 自动生成于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 *
 * PAGE_DATA 结构说明:
 * - static: 静态数据（无法通过API获取的数据）
 * - context: 上下文数据（对话过程中收集的数据）
 * - generated_at: 生成时间
 */

window.PAGE_DATA = {data_json};

// 数据加载完成事件
if (typeof window.onPageDataLoaded === 'function') {{
    window.onPageDataLoaded(window.PAGE_DATA);
}}
"""
        return js_content

    def generate_all(
        self,
        page_config: Dict[str, Any],
        static_data: Optional[Dict[str, Any]] = None,
        context_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Path]:
        """
        生成所有数据文件

        Args:
            page_config: PAGE_CONFIG 配置
            static_data: 静态数据（可选）
            context_data: 上下文数据（可选）

        Returns:
            生成的文件路径字典 {"config": Path, "data": Path}
        """
        result = {}

        # 生成 config.js
        result["config"] = self.generate_config_js(page_config)

        # 如果有静态数据或上下文数据，生成 data.js
        if static_data or context_data:
            result["data"] = self.generate_data_js(
                static_data=static_data or {},
                context_data=context_data
            )

        return result


class APIConfigBuilder:
    """
    API配置构建器

    帮助构建 PAGE_CONFIG 中的 api_config 部分。
    """

    def __init__(self):
        self._apis: Dict[str, Dict[str, Any]] = {}

    def add_api(
        self,
        name: str,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        auth_type: Optional[str] = None,
        data_path: Optional[str] = None,
        transform: Optional[str] = None
    ) -> 'APIConfigBuilder':
        """
        添加API配置

        Args:
            name: API名称（用于组件引用）
            url: API URL
            method: HTTP方法
            params: 请求参数
            headers: 请求头
            auth_type: 认证类型 (bearer/basic/none)
            data_path: 响应数据路径（如 "data.items"）
            transform: 数据转换器名称

        Returns:
            self（支持链式调用）
        """
        self._apis[name] = {
            "url": url,
            "method": method,
            "params": params or {},
            "headers": headers or {},
            "auth_type": auth_type,
            "data_path": data_path,
            "transform": transform
        }
        return self

    def build(self) -> Dict[str, Dict[str, Any]]:
        """
        构建API配置

        Returns:
            API配置字典
        """
        return self._apis.copy()


class ComponentConfigBuilder:
    """
    组件配置构建器

    帮助构建 PAGE_CONFIG 中的 components 部分。
    """

    # 支持的组件类型
    COMPONENT_TYPES = [
        "InfoCard",      # 信息卡片（键值对展示）
        "Echarts",       # ECharts图表
        "SimpleTable",   # 简单表格
        "GISMap",        # GIS地图
        "HtmlContent",   # HTML内容
        "Timeline",      # 时间线
        "StatCard",      # 统计卡片
        "ProgressBar",   # 进度条
    ]

    def __init__(self):
        self._components: Dict[str, Dict[str, Any]] = {}

    def add_info_card(
        self,
        name: str,
        title: str,
        data_source: Dict[str, Any],
        style: Optional[Dict[str, Any]] = None
    ) -> 'ComponentConfigBuilder':
        """
        添加信息卡片组件

        Args:
            name: 组件名称
            title: 卡片标题
            data_source: 数据源配置
            style: 样式配置

        Returns:
            self
        """
        self._components[name] = {
            "type": "InfoCard",
            "title": title,
            "data_source": data_source,
            "style": style or {}
        }
        return self

    def add_echarts(
        self,
        name: str,
        title: str,
        chart_type: str,
        data_source: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None,
        style: Optional[Dict[str, Any]] = None
    ) -> 'ComponentConfigBuilder':
        """
        添加ECharts图表组件

        Args:
            name: 组件名称
            title: 图表标题
            chart_type: 图表类型 (line/bar/pie/scatter/radar)
            data_source: 数据源配置
            options: ECharts配置选项
            style: 样式配置

        Returns:
            self
        """
        self._components[name] = {
            "type": "Echarts",
            "title": title,
            "chart_type": chart_type,
            "data_source": data_source,
            "options": options or {},
            "style": style or {}
        }
        return self

    def add_table(
        self,
        name: str,
        title: str,
        columns: List[Dict[str, str]],
        data_source: Dict[str, Any],
        style: Optional[Dict[str, Any]] = None
    ) -> 'ComponentConfigBuilder':
        """
        添加表格组件

        Args:
            name: 组件名称
            title: 表格标题
            columns: 列配置 [{"key": "name", "label": "名称"}, ...]
            data_source: 数据源配置
            style: 样式配置

        Returns:
            self
        """
        self._components[name] = {
            "type": "SimpleTable",
            "title": title,
            "columns": columns,
            "data_source": data_source,
            "style": style or {}
        }
        return self

    def add_html_content(
        self,
        name: str,
        title: str,
        data_source: Dict[str, Any],
        style: Optional[Dict[str, Any]] = None
    ) -> 'ComponentConfigBuilder':
        """
        添加HTML内容组件

        Args:
            name: 组件名称
            title: 标题
            data_source: 数据源配置
            style: 样式配置

        Returns:
            self
        """
        self._components[name] = {
            "type": "HtmlContent",
            "title": title,
            "data_source": data_source,
            "style": style or {}
        }
        return self

    def add_gis_map(
        self,
        name: str,
        title: str,
        data_source: Dict[str, Any],
        map_options: Optional[Dict[str, Any]] = None,
        style: Optional[Dict[str, Any]] = None
    ) -> 'ComponentConfigBuilder':
        """
        添加GIS地图组件

        Args:
            name: 组件名称
            title: 标题
            data_source: 数据源配置
            map_options: 地图配置选项
            style: 样式配置

        Returns:
            self
        """
        self._components[name] = {
            "type": "GISMap",
            "title": title,
            "data_source": data_source,
            "map_options": map_options or {},
            "style": style or {}
        }
        return self

    def add_stat_card(
        self,
        name: str,
        title: str,
        data_source: Dict[str, Any],
        unit: str = "",
        icon: Optional[str] = None,
        style: Optional[Dict[str, Any]] = None
    ) -> 'ComponentConfigBuilder':
        """
        添加统计卡片组件

        Args:
            name: 组件名称
            title: 标题
            data_source: 数据源配置
            unit: 单位
            icon: 图标
            style: 样式配置

        Returns:
            self
        """
        self._components[name] = {
            "type": "StatCard",
            "title": title,
            "data_source": data_source,
            "unit": unit,
            "icon": icon,
            "style": style or {}
        }
        return self

    def build(self) -> Dict[str, Dict[str, Any]]:
        """
        构建组件配置

        Returns:
            组件配置字典
        """
        return self._components.copy()


class LayoutBuilder:
    """
    布局配置构建器

    帮助构建 PAGE_CONFIG 中的 layout 部分。
    """

    def __init__(self, layout_type: str = "grid"):
        """
        初始化布局构建器

        Args:
            layout_type: 布局类型 (grid/flex/single)
        """
        self._layout = {
            "type": layout_type,
            "rows": []
        }

    def add_row(
        self,
        cols: List[str],
        height: str = "auto",
        gap: str = "16px"
    ) -> 'LayoutBuilder':
        """
        添加一行

        Args:
            cols: 列中的组件名称列表
            height: 行高度
            gap: 列间距

        Returns:
            self
        """
        self._layout["rows"].append({
            "cols": cols,
            "height": height,
            "gap": gap
        })
        return self

    def set_gap(self, gap: str) -> 'LayoutBuilder':
        """
        设置行间距

        Args:
            gap: 间距值

        Returns:
            self
        """
        self._layout["gap"] = gap
        return self

    def set_padding(self, padding: str) -> 'LayoutBuilder':
        """
        设置内边距

        Args:
            padding: 内边距值

        Returns:
            self
        """
        self._layout["padding"] = padding
        return self

    def build(self) -> Dict[str, Any]:
        """
        构建布局配置

        Returns:
            布局配置字典
        """
        return self._layout.copy()


class PageConfigBuilder:
    """
    PAGE_CONFIG 完整配置构建器

    整合 LayoutBuilder、ComponentConfigBuilder、APIConfigBuilder。
    """

    def __init__(self, title: str, description: str = ""):
        """
        初始化配置构建器

        Args:
            title: 页面标题
            description: 页面描述
        """
        self._config = {
            "meta": {
                "title": title,
                "description": description,
                "generated_at": datetime.now().isoformat()
            },
            "layout": {},
            "components": {},
            "api_config": {},
            "static_data": {},
            "context_data": {}
        }

    def set_layout(self, layout: Dict[str, Any]) -> 'PageConfigBuilder':
        """设置布局配置"""
        self._config["layout"] = layout
        return self

    def set_components(self, components: Dict[str, Dict[str, Any]]) -> 'PageConfigBuilder':
        """设置组件配置"""
        self._config["components"] = components
        return self

    def set_api_config(self, api_config: Dict[str, Dict[str, Any]]) -> 'PageConfigBuilder':
        """设置API配置"""
        self._config["api_config"] = api_config
        return self

    def set_static_data(self, static_data: Dict[str, Any]) -> 'PageConfigBuilder':
        """设置静态数据"""
        self._config["static_data"] = static_data
        return self

    def set_context_data(self, context_data: Dict[str, Any]) -> 'PageConfigBuilder':
        """设置上下文数据"""
        self._config["context_data"] = context_data
        return self

    def build(self) -> Dict[str, Any]:
        """
        构建完整的 PAGE_CONFIG

        Returns:
            PAGE_CONFIG 配置字典
        """
        return self._config.copy()
