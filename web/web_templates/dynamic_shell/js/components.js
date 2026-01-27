/**
 * 动态页面核心组件库
 * 负责解析 PAGE_CONFIG 并渲染页面
 */

class DynamicPageEngine {
    constructor() {
        this.config = window.PAGE_CONFIG || {};
        this.data = window.PAGE_DATA || { static: {}, context: {} };
        this.components = {}; // 组件注册表
        this.apiCache = {};   // API缓存

        // 注册内置组件
        this.registerComponent('InfoCard', this.renderInfoCard);
        this.registerComponent('StatCard', this.renderStatCard);
        this.registerComponent('Echarts', this.renderEcharts);
        this.registerComponent('SimpleTable', this.renderSimpleTable);
        this.registerComponent('HtmlContent', this.renderHtmlContent);
        this.registerComponent('GISMap', this.renderGISMap);
    }

    // 注册组件渲染函数
    registerComponent(type, renderFunc) {
        this.components[type] = renderFunc.bind(this);
    }

    // 初始化页面
    async init() {
        console.log("Initializing Dynamic Page...");

        // 1. 设置元信息
        if (this.config.meta) {
            document.title = this.config.meta.title || "动态页面";
            const metaDesc = document.querySelector('meta[name="description"]');
            if (metaDesc && this.config.meta.description) {
                metaDesc.content = this.config.meta.description;
            }
        }

        // 2. 渲染布局
        const container = document.getElementById('app');
        if (!container) {
            console.error("Root container #app not found");
            return;
        }

        await this.renderLayout(this.config.layout, container);
    }

    // 渲染布局
    async renderLayout(layout, container) {
        if (!layout) return;

        if (layout.type === 'grid') {
            const rows = layout.rows || [];
            for (const rowConfig of rows) {
                const rowEl = document.createElement('div');
                rowEl.className = 'grid-row';
                rowEl.style.display = 'grid';
                rowEl.style.gap = rowConfig.gutter ? `${rowConfig.gutter}px` : (rowConfig.gap || '16px');
                rowEl.style.marginBottom = '16px';

                // 应用行样式
                if (rowConfig.style) {
                    Object.assign(rowEl.style, rowConfig.style);
                }

                // 计算列
                const cols = rowConfig.cols || [];

                // 检查 cols 格式：可能是字符串数组或对象数组
                // 对象格式: { span: 6, component_key: "xxx" }
                // 字符串格式: "xxx"
                const hasSpan = cols.length > 0 && typeof cols[0] === 'object' && cols[0].span !== undefined;

                if (hasSpan) {
                    // 使用 span 计算 grid-template-columns (基于24栅格系统)
                    const gridCols = cols.map(col => `${(col.span / 24) * 100}%`).join(' ');
                    rowEl.style.gridTemplateColumns = gridCols;
                } else {
                    // 默认均分
                    const colCount = cols.length;
                    rowEl.style.gridTemplateColumns = `repeat(${colCount}, 1fr)`;
                }

                if (rowConfig.height) {
                    rowEl.style.height = rowConfig.height;
                }

                container.appendChild(rowEl);

                // 渲染列中的组件
                for (const colConfig of cols) {
                    const colEl = document.createElement('div');
                    colEl.className = 'grid-col';
                    colEl.style.minWidth = '0'; // 防止Echarts溢出
                    rowEl.appendChild(colEl);

                    // 获取组件key：支持对象格式和字符串格式
                    // LLM可能生成 component_key 或 component 字段
                    const componentKey = typeof colConfig === 'object'
                        ? (colConfig.component_key || colConfig.component)
                        : colConfig;

                    if (componentKey) {
                        await this.loadAndRenderComponent(componentKey, colEl);
                    }
                }
            }
        }
    }

    // 加载并渲染组件
    async loadAndRenderComponent(componentKey, container) {
        const componentConfig = this.config.components[componentKey];
        if (!componentConfig) {
            container.innerHTML = `<div class="error">Component ${componentKey} not found</div>`;
            return;
        }

        // 支持两种配置格式：
        // 1. 新格式: { type: "xxx", props: { title: "...", ... } }
        // 2. 旧格式: { type: "xxx", title: "...", data_source: {...} }
        const props = componentConfig.props || componentConfig;
        const title = props.title || componentConfig.title;

        // 1. 获取数据
        let data = null;
        try {
            // 优先从 data_source 获取数据，否则使用 props 中的静态数据
            if (componentConfig.data_source) {
                data = await this.resolveDataSource(componentConfig.data_source);
            } else if (props.dataSource) {
                // SimpleTable 等组件直接在 props 中提供 dataSource
                data = props.dataSource;
            }
        } catch (e) {
            console.error(`Failed to load data for ${componentKey}:`, e);
            container.innerHTML = `<div class="error">Data load failed: ${e.message}</div>`;
            return;
        }

        // 2. 渲染组件
        const renderer = this.components[componentConfig.type];
        if (renderer) {
            // 创建组件容器
            const wrapper = document.createElement('div');
            wrapper.className = `component-wrapper component-${componentConfig.type.toLowerCase()}`;
            Object.assign(wrapper.style, componentConfig.style || {});

            // 添加标题
            if (title) {
                const titleEl = document.createElement('div');
                titleEl.className = 'component-title';
                titleEl.innerText = title;
                wrapper.appendChild(titleEl);
            }

            const body = document.createElement('div');
            body.className = 'component-body';
            wrapper.appendChild(body);
            container.appendChild(wrapper);

            // 调用渲染函数，传入 props 作为配置
            await renderer(body, data, props);
        } else {
            container.innerHTML = `<div class="error">Unknown component type: ${componentConfig.type}</div>`;
        }
    }

    // 解析数据源
    async resolveDataSource(sourceConfig) {
        if (!sourceConfig) return null;

        if (sourceConfig.type === 'static' || sourceConfig.type === 'static_value') {
            return sourceConfig.value;
        }

        if (sourceConfig.type === 'context') {
            // 从 data.js 的 context 中获取
            // 支持 context.xxx.yyy 路径
            if (sourceConfig.mapping) {
                // 映射模式: { "key": "path" }
                const result = {};
                for (const [k, path] of Object.entries(sourceConfig.mapping)) {
                    result[k] = this.getValueByPath(this.data.context, path) || this.getValueByPath(window, path);
                }
                return result;
            } else if (sourceConfig.path) {
                return this.getValueByPath(this.data.context, sourceConfig.path);
            }
            return this.data.context; // 默认返回全部
        }

        if (sourceConfig.type === 'api') {
            const apiName = sourceConfig.api_name;
            const apiCfg = this.config.api_config[apiName];
            if (!apiCfg) throw new Error(`API ${apiName} not configured`);

            return await this.fetchApiData(apiCfg);
        }

        return null;
    }

    // 执行API请求
    async fetchApiData(apiCfg) {
        // 1. 替换参数
        const url = this.substituteTemplate(apiCfg.url, this.data.context);
        const method = apiCfg.method || 'GET';
        const headers = apiCfg.headers || {};

        let body = undefined;
        let queryParams = '';

        if (apiCfg.params) {
            const resolvedParams = {};
            for (const [k, v] of Object.entries(apiCfg.params)) {
                resolvedParams[k] = this.substituteTemplate(v, this.data.context);
            }

            if (method === 'GET') {
                queryParams = '?' + new URLSearchParams(resolvedParams).toString();
            } else {
                body = JSON.stringify(resolvedParams);
                headers['Content-Type'] = 'application/json';
            }
        }

        // 2. 发起请求
        const finalUrl = url + queryParams;

        // 简单缓存
        const cacheKey = `${method}:${finalUrl}`;
        if (this.apiCache[cacheKey]) return this.apiCache[cacheKey];

        const res = await fetch(finalUrl, { method, headers, body });
        if (!res.ok) throw new Error(`API ${finalUrl} failed: ${res.status}`);

        const json = await res.json();

        // 3. 提取数据
        let result = json;
        if (apiCfg.data_path) {
            result = this.getValueByPath(json, apiCfg.data_path);
        }

        this.apiCache[cacheKey] = result;
        return result;
    }

    // 辅助：获取对象路径值
    getValueByPath(obj, path) {
        if (!path) return obj;
        return path.split('.').reduce((o, k) => (o || {})[k], obj);
    }

    // 辅助：模板替换
    substituteTemplate(template, context) {
        if (typeof template !== 'string') return template;
        return template.replace(/\{([^}]+)\}/g, (match, key) => {
            // 支持 context.xxx 和 xxx (默认为context)
            let path = key.trim();
            if (path.startsWith('context.')) {
                path = path.substring(8);
            }
            const val = this.getValueByPath(context, path);
            return val !== undefined ? val : match;
        });
    }

    // --- 组件渲染实现 ---

    renderInfoCard(container, data, config) {
        let content = '';
        // 优先使用 config 中的数据，其次使用传入的 data
        const displayData = data || config;
        if (typeof displayData === 'object') {
            for (const [k, v] of Object.entries(displayData)) {
                // 跳过非显示字段
                if (['title', 'type'].includes(k)) continue;
                content += `
                    <div class="info-item">
                        <span class="label">${k}</span>
                        <span class="value">${v}</span>
                    </div>
                `;
            }
        } else {
            content = `<div class="value">${displayData}</div>`;
        }
        container.innerHTML = `<div class="info-card-grid">${content}</div>`;
    }

    renderStatCard(container, data, config) {
        // config 就是 props，直接从中获取值
        // 支持两种格式：
        // 1. props 格式: { value: "72.45", unit: "m", ... }
        // 2. data 格式: data 是值，config 包含 unit 等
        let value = config.value !== undefined ? config.value : (data || '--');
        let unit = config.unit || '';
        let description = config.description || '';
        let trend = config.trend || '';
        let status = config.status || 'normal';
        let color = config.color || '';
        let precision = config.precision;

        // 如果 data 是对象，尝试从中提取
        if (typeof data === 'object' && data !== null) {
            value = data.value || data.val || value;
            unit = data.unit || unit;
        }

        // 格式化数值
        if (precision !== undefined && !isNaN(parseFloat(value))) {
            value = parseFloat(value).toFixed(precision);
        }

        // 状态颜色
        const statusColors = {
            'normal': '#52c41a',
            'warning': '#faad14',
            'danger': '#f5222d',
            'info': '#1890ff'
        };
        const valueColor = color || statusColors[status] || '#333';

        // 趋势图标
        const trendIcons = {
            'up': '↑',
            'down': '↓',
            'stable': '→'
        };
        const trendIcon = trendIcons[trend] || '';

        container.innerHTML = `
            <div class="stat-card">
                <div class="stat-value" style="color: ${valueColor}">
                    ${value}<span class="unit">${unit}</span>
                    ${trendIcon ? `<span class="trend trend-${trend}">${trendIcon}</span>` : ''}
                </div>
                ${description ? `<div class="stat-description">${description}</div>` : ''}
            </div>
        `;
    }

    renderHtmlContent(container, data, config) {
        const content = data || config.content || '';
        container.innerHTML = `<div class="html-content">${content}</div>`;
    }

    renderSimpleTable(container, data, config) {
        // 数据来源：优先使用传入的 data，其次使用 config.dataSource
        const tableData = data || config.dataSource || [];

        if (!Array.isArray(tableData) || tableData.length === 0) {
            container.innerHTML = '<div class="empty-table">暂无数据</div>';
            return;
        }

        // 列配置：支持两种格式
        // 1. { title: "xxx", dataIndex: "xxx", key: "xxx" }
        // 2. { label: "xxx", key: "xxx" }
        const columns = config.columns || [];
        const finalCols = columns.length > 0 ? columns :
            Object.keys(tableData[0] || {}).map(k => ({ key: k, title: k, dataIndex: k }));

        let html = '<table class="simple-table"><thead><tr>';
        finalCols.forEach(c => {
            const label = c.title || c.label || c.key;
            html += `<th>${label}</th>`;
        });
        html += '</tr></thead><tbody>';

        tableData.forEach(row => {
            html += '<tr>';
            finalCols.forEach(c => {
                const key = c.dataIndex || c.key;
                html += `<td>${row[key] !== undefined ? row[key] : ''}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';
        container.innerHTML = html;
    }

    renderEcharts(container, data, config) {
        container.style.width = '100%';
        container.style.height = '100%';
        container.style.minHeight = '300px';

        const chart = echarts.init(container);

        // 支持两种配置格式：
        // 1. config.option (新格式，直接是 ECharts option)
        // 2. config.options (旧格式)
        let option = config.option || config.options || {};

        // 如果只有数据源，自动生成简单的 option
        if (Object.keys(option).length === 0 && config.chart_type) {
            option = {
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: data?.x_data || [] },
                yAxis: { type: 'value' },
                series: [{
                    type: config.chart_type,
                    data: data?.y_data || data?.series || []
                }]
            };
        } else if (data) {
            // 如果提供了 data，尝试将数据注入到 option 中
            if (data.series) {
                option.series = data.series;
            }
            if (data.xAxis) {
                option.xAxis = data.xAxis;
            }
        }

        chart.setOption(option);
        window.addEventListener('resize', () => chart.resize());
    }

    renderGISMap(container, data, config) {
        // 1. 设置容器ID（ArcGIS要求容器必须有ID）
        const mapDivId = 'viewDiv_' + Math.random().toString(36).substr(2, 9);
        const mapDiv = document.createElement('div');
        mapDiv.id = mapDivId;
        mapDiv.style.width = '100%';
        mapDiv.style.height = '100%';
        mapDiv.style.minHeight = '400px';
        container.appendChild(mapDiv);

        // 2. 加载 ArcGIS 模块
        require([
            "esri/Map",
            "esri/views/MapView",
            "esri/widgets/BasemapToggle",
            "esri/layers/GraphicsLayer",
            "esri/Graphic"
        ], (Map, MapView, BasemapToggle, GraphicsLayer, Graphic) => {

            // 支持两种配置格式：
            // 1. 新格式: config.center, config.zoom, config.markers
            // 2. 旧格式: config.map_options.center, config.map_options.zoom
            const mapOptions = config.map_options || config;
            const center = mapOptions.center || config.center || [113.4, 35.5];
            const zoom = mapOptions.zoom || config.zoom || 9;

            // 3. 创建地图
            const map = new Map({
                basemap: mapOptions.basemap || "topo-vector"
            });

            // 4. 创建视图
            const view = new MapView({
                container: mapDivId,
                map: map,
                center: center,
                zoom: zoom
            });

            // 5. 添加底图切换
            const toggle = new BasemapToggle({
                view: view,
                nextBasemap: "hybrid"
            });
            view.ui.add(toggle, "top-right");

            // 6. 渲染标记点
            const graphicsLayer = new GraphicsLayer();
            map.add(graphicsLayer);

            // 支持两种数据来源：
            // 1. config.markers (新格式，直接在 props 中)
            // 2. data (旧格式，通过 data_source 获取)
            const markers = config.markers || (Array.isArray(data) ? data : (data ? [data] : []));

            markers.forEach(item => {
                // 尝试识别经纬度字段
                // 新格式: { position: [lng, lat], title: "xxx" }
                // 旧格式: { lng: xxx, lat: xxx, name: "xxx" }
                let lng, lat;
                if (item.position && Array.isArray(item.position)) {
                    [lng, lat] = item.position;
                } else {
                    lng = item.lng || item.longitude || item.long || item.lgtd || item.经度;
                    lat = item.lat || item.latitude || item.lttd || item.纬度;
                }

                if (lng && lat) {
                    const point = {
                        type: "point",
                        longitude: parseFloat(lng),
                        latitude: parseFloat(lat)
                    };

                    // 根据状态设置颜色
                    const statusColors = {
                        'normal': [82, 196, 26],    // 绿色
                        'warning': [250, 173, 20],  // 黄色
                        'danger': [245, 34, 45],    // 红色
                        'info': [24, 144, 255]      // 蓝色
                    };
                    const markerColor = statusColors[item.status] || [33, 150, 243];

                    const markerSymbol = {
                        type: "simple-marker",
                        color: markerColor,
                        outline: { color: [255, 255, 255], width: 1 }
                    };

                    const pointGraphic = new Graphic({
                        geometry: point,
                        symbol: markerSymbol,
                        attributes: item,
                        popupTemplate: {
                            title: item.title || item.name || item.stnm || "Location",
                            content: item.content || this._generatePopupContent(item)
                        }
                    });

                    graphicsLayer.add(pointGraphic);
                }
            });
        });
    }

    _generatePopupContent(item) {
        let content = "<table class='esri-widget__table'>";
        for (const [key, value] of Object.entries(item)) {
            // 排除非显示字段
            if (['position', 'status', 'title', 'content'].includes(key)) continue;
            if (typeof value !== 'object' && String(value).length < 50) {
                content += `<tr><th>${key}</th><td>${value}</td></tr>`;
            }
        }
        content += "</table>";
        return content;
    }
}

// 启动
window.addEventListener('DOMContentLoaded', () => {
    const engine = new DynamicPageEngine();
    engine.init();
});
