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
        # 合并数据
        data = {
            "static": static_data,
            "context": context_data or {},
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
