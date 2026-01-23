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
            rows.forEach(async (rowConfig) => {
                const rowEl = document.createElement('div');
                rowEl.className = 'grid-row';
                rowEl.style.display = 'grid';
                rowEl.style.gap = rowConfig.gap || '16px';

                // 计算列
                const cols = rowConfig.cols || [];
                // 默认均分
                const colCount = cols.length;
                rowEl.style.gridTemplateColumns = `repeat(${colCount}, 1fr)`;

                if (rowConfig.height) {
                    rowEl.style.height = rowConfig.height;
                }

                container.appendChild(rowEl);

                // 渲染列中的组件
                for (const componentKey of cols) {
                    const colEl = document.createElement('div');
                    colEl.className = 'grid-col';
                    colEl.style.minWidth = '0'; // 防止Echarts溢出
                    rowEl.appendChild(colEl);

                    await this.loadAndRenderComponent(componentKey, colEl);
                }
            });
        }
    }

    // 加载并渲染组件
    async loadAndRenderComponent(componentKey, container) {
        const componentConfig = this.config.components[componentKey];
        if (!componentConfig) {
            container.innerHTML = `<div class="error">Component ${componentKey} not found</div>`;
            return;
        }

        // 1. 获取数据
        let data = null;
        try {
            data = await this.resolveDataSource(componentConfig.data_source);
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
            if (componentConfig.title) {
                const titleEl = document.createElement('div');
                titleEl.className = 'component-title';
                titleEl.innerText = componentConfig.title;
                wrapper.appendChild(titleEl);
            }

            const body = document.createElement('div');
            body.className = 'component-body';
            wrapper.appendChild(body);
            container.appendChild(wrapper);

            // 调用渲染函数
            await renderer(body, data, componentConfig);
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
        if (typeof data === 'object') {
            for (const [k, v] of Object.entries(data)) {
                content += `
                    <div class="info-item">
                        <span class="label">${k}</span>
                        <span class="value">${v}</span>
                    </div>
                `;
            }
        } else {
            content = `<div class="value">${data}</div>`;
        }
        container.innerHTML = `<div class="info-card-grid">${content}</div>`;
    }

    renderStatCard(container, data, config) {
        // data 可能是单个值或对象
        // 如果是对象，寻找 value, unit, label
        let value = data;
        let unit = config.unit || '';

        if (typeof data === 'object' && data !== null) {
            value = data.value || data.val || '--';
            unit = data.unit || unit;
        }

        container.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${value}<span class="unit">${unit}</span></div>
                ${config.icon ? `<div class="stat-icon">${config.icon}</div>` : ''}
            </div>
        `;
    }

    renderHtmlContent(container, data, config) {
        container.innerHTML = `<div class="html-content">${data}</div>`;
    }

    renderSimpleTable(container, data, config) {
        if (!Array.isArray(data)) {
            container.innerHTML = "Not a list";
            return;
        }

        const columns = config.columns || [];
        // 如果未配置列，自动推断
        const finalCols = columns.length > 0 ? columns :
            Object.keys(data[0] || {}).map(k => ({ key: k, label: k }));

        let html = '<table class="simple-table"><thead><tr>';
        finalCols.forEach(c => html += `<th>${c.label}</th>`);
        html += '</tr></thead><tbody>';

        data.forEach(row => {
            html += '<tr>';
            finalCols.forEach(c => {
                html += `<td>${row[c.key] || ''}</td>`;
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

        let option = config.options || {};

        // 如果只有数据源，自动生成简单的 option
        if (!config.options && config.chart_type) {
            // 简单的自动适配逻辑
            // 假设 data 是该图表需要的数据格式
            // 这里仅作示例，实际情况需要更复杂的转换逻辑
            option = {
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: data.x_data || [] },
                yAxis: { type: 'value' },
                series: [{
                    type: config.chart_type,
                    data: data.y_data || data.series || []
                }]
            };
        } else if (config.options) {
            // 如果提供了options，尝试将数据注入到options中
            // 假设 data 可以覆盖 options 中的 dataset 或 series
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

            const mapOptions = config.map_options || {};

            // 3. 创建地图
            const map = new Map({
                basemap: mapOptions.basemap || "topo-vector" // hybrid, satellite, topo-vector
            });

            // 4. 创建视图
            const view = new MapView({
                container: mapDivId,
                map: map,
                center: mapOptions.center || [113.4, 35.5], // 默认以卫共流域为中心
                zoom: mapOptions.zoom || 9
            });

            // 5. 添加底图切换
            const toggle = new BasemapToggle({
                view: view,
                nextBasemap: "hybrid"
            });
            view.ui.add(toggle, "top-right");

            // 6. 渲染通过数据传入的图形
            if (data) {
                const graphicsLayer = new GraphicsLayer();
                map.add(graphicsLayer);

                // 处理列表数据
                const items = Array.isArray(data) ? data : [data];

                items.forEach(item => {
                    // 尝试识别经纬度字段
                    const lng = item.lng || item.longitude || item.long || item.lgtd || item.经度;
                    const lat = item.lat || item.latitude || item.lttd || item.纬度;

                    if (lng && lat) {
                        const point = {
                            type: "point",
                            longitude: parseFloat(lng),
                            latitude: parseFloat(lat)
                        };

                        const markerSymbol = {
                            type: "simple-marker",
                            color: [33, 150, 243], // Blue
                            outline: { color: [255, 255, 255], width: 1 }
                        };

                        const pointGraphic = new Graphic({
                            geometry: point,
                            symbol: markerSymbol,
                            attributes: item,
                            popupTemplate: {
                                title: item.name || item.stnm || "Location",
                                content: this._generatePopupContent(item)
                            }
                        });

                        graphicsLayer.add(pointGraphic);
                    }
                });
            }
        });
    }

    _generatePopupContent(item) {
        let content = "<table class='esri-widget__table'>";
        for (const [key, value] of Object.entries(item)) {
            // 排除太长的字段或对象
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
