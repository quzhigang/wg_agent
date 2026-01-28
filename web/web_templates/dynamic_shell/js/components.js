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

        // 注册内置组件 - 数据展示类
        this.registerComponent('InfoCard', this.renderInfoCard);
        this.registerComponent('StatCard', this.renderStatCard);
        this.registerComponent('Echarts', this.renderEcharts);
        this.registerComponent('SimpleTable', this.renderSimpleTable);
        this.registerComponent('HtmlContent', this.renderHtmlContent);
        this.registerComponent('GISMap', this.renderGISMap);

        // 注册内置组件 - 媒体类
        this.registerComponent('Image', this.renderImage);
        this.registerComponent('Video', this.renderVideo);
        this.registerComponent('Gallery', this.renderGallery);

        // 注册内置组件 - 交互类
        this.registerComponent('ActionBar', this.renderActionBar);

        // 注册内置组件 - 表单类
        this.registerComponent('Radio', this.renderRadio);
        this.registerComponent('Checkbox', this.renderCheckbox);
        this.registerComponent('Select', this.renderSelect);
        this.registerComponent('Switch', this.renderSwitch);

        // 注册内置组件 - 导航/布局类
        this.registerComponent('Tabs', this.renderTabs);
        this.registerComponent('List', this.renderList);
        this.registerComponent('Divider', this.renderDivider);
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
        // 优先使用传入的 data，其次使用 config.data，最后使用 config 本身
        const displayData = data || config.data || config;
        if (typeof displayData === 'object') {
            for (const [k, v] of Object.entries(displayData)) {
                // 跳过非显示字段
                if (['title', 'type', 'data', 'data_source', 'style'].includes(k)) continue;
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
        container.classList.add('echarts-container');

        const chart = echarts.init(container);

        // ========== 深色科技风格默认主题配置 ==========
        const darkTechTheme = {
            backgroundColor: 'transparent',
            textStyle: { color: '#e0e6ed' },
            title: {
                textStyle: { color: '#00d4ff', fontSize: 16, fontWeight: 'bold' },
                subtextStyle: { color: '#a0aec0' }
            },
            legend: {
                textStyle: { color: '#a0aec0' },
                pageTextStyle: { color: '#a0aec0' }
            },
            tooltip: {
                backgroundColor: 'rgba(13, 27, 42, 0.95)',
                borderColor: '#1e3a5f',
                textStyle: { color: '#e0e6ed' },
                extraCssText: 'box-shadow: 0 4px 20px rgba(0, 212, 255, 0.2);'
            },
            xAxis: {
                axisLine: { lineStyle: { color: '#1e3a5f' } },
                axisLabel: { color: '#a0aec0' },
                splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } }
            },
            yAxis: {
                axisLine: { lineStyle: { color: '#1e3a5f' } },
                axisLabel: { color: '#a0aec0' },
                splitLine: { lineStyle: { color: 'rgba(30, 58, 95, 0.5)' } }
            },
            // 深色科技风格配色序列
            color: ['#00d4ff', '#7c3aed', '#10b981', '#f59e0b', '#ef4444', '#ec4899']
        };

        // ========== 数据格式转换 ==========
        // 支持字典格式数据: { "2026/01/27 18:00:00": 78.54, ... }
        // 转换为 ECharts 需要的格式: { x_data: [...], y_data: [...] }
        let processedData = data;
        if (data && typeof data === 'object' && !Array.isArray(data) && !data.series && !data.x_data) {
            // 检查是否是字典格式 (键是时间字符串，值是数字)
            const keys = Object.keys(data);
            if (keys.length > 0 && typeof data[keys[0]] === 'number') {
                // 转换字典为 x_data 和 y_data
                processedData = {
                    x_data: keys.map(k => {
                        // 简化时间显示格式: "2026/01/27 18:00:00" -> "01/27 18:00"
                        const match = k.match(/(\d{2})\/(\d{2})\s+(\d{2}:\d{2})/);
                        return match ? `${match[1]}/${match[2]} ${match[3]}` : k;
                    }),
                    y_data: keys.map(k => data[k])
                };
            }
        }

        // 支持两种配置格式：
        // 1. config.option (新格式，直接是 ECharts option)
        // 2. config.options (旧格式)
        let option = config.option || config.options || {};

        // 获取图表类型
        const chartType = config.chartType || config.chart_type || 'line';

        // 如果有处理后的数据，注入到 option 中
        if (processedData && (processedData.x_data || processedData.y_data)) {
            // 设置 xAxis 数据
            if (processedData.x_data) {
                if (!option.xAxis) option.xAxis = {};
                if (typeof option.xAxis === 'object' && !Array.isArray(option.xAxis)) {
                    option.xAxis.data = processedData.x_data;
                }
            }
            // 设置 series 数据
            if (processedData.y_data) {
                if (!option.series || option.series.length === 0) {
                    option.series = [{ type: chartType, data: processedData.y_data }];
                } else if (Array.isArray(option.series) && option.series.length > 0) {
                    option.series[0].data = processedData.y_data;
                }
            }
        } else if (processedData) {
            // 如果提供了其他格式的 data，尝试将数据注入到 option 中
            if (processedData.series) {
                option.series = processedData.series;
            }
            if (processedData.xAxis) {
                option.xAxis = processedData.xAxis;
            }
        }

        // 为线形图添加渐变填充效果
        if (chartType === 'line' && option.series && option.series.length > 0) {
            option.series.forEach(s => {
                if (!s.lineStyle) s.lineStyle = { color: '#00d4ff', width: 2 };
                if (!s.areaStyle) {
                    s.areaStyle = {
                        color: {
                            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                            colorStops: [
                                { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
                                { offset: 1, color: 'rgba(0, 212, 255, 0.05)' }
                            ]
                        }
                    };
                }
                if (!s.itemStyle) s.itemStyle = { color: '#00d4ff', borderColor: '#0a1628', borderWidth: 2 };
                if (!s.smooth) s.smooth = true;
            });
        }

        // 深度合并主题配置 (用户配置优先)
        const finalOption = this._deepMerge(darkTechTheme, option);

        chart.setOption(finalOption);
        window.addEventListener('resize', () => chart.resize());
    }

    // 辅助：深度合并对象
    _deepMerge(target, source) {
        const result = { ...target };
        for (const key of Object.keys(source)) {
            if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                result[key] = this._deepMerge(result[key] || {}, source[key]);
            } else {
                result[key] = source[key];
            }
        }
        return result;
    }

    renderGISMap(container, data, config) {
        // 1. 设置容器ID（ArcGIS要求容器必须有ID）
        const mapDivId = 'viewDiv_' + Math.random().toString(36).substr(2, 9);
        const mapDiv = document.createElement('div');
        mapDiv.id = mapDivId;
        mapDiv.style.width = '100%';
        mapDiv.style.height = '100%';
        mapDiv.style.minHeight = '400px';
        mapDiv.classList.add('gis-map-container');
        container.appendChild(mapDiv);

        // 2. 加载 ArcGIS 模块 - 使用 Portal WebMap (与预定义模板一致)
        require([
            "esri/WebMap",
            "esri/views/MapView",
            "esri/config",
            "esri/layers/GraphicsLayer",
            "esri/Graphic"
        ], (WebMap, MapView, esriConfig, GraphicsLayer, Graphic) => {

            // ========== 使用固定的 Portal WebMap (河南省水利厅地图服务) ==========
            // 配置Portal地址
            esriConfig.portalUrl = "https://map.slt.henan.gov.cn/geoscene";

            // 使用固定的 Portal WebMap ID (与预定义模板 res_module 一致)
            const portalItemId = config.portalItemId || "0217daabff7a4b45a0cca3f975efa7f3";

            const webmap = new WebMap({
                portalItem: {
                    id: portalItemId
                }
            });

            // 3. 创建视图
            const view = new MapView({
                container: mapDivId,
                map: webmap
            });

            // 4. 添加标记图层
            const graphicsLayer = new GraphicsLayer();
            webmap.when(() => {
                webmap.add(graphicsLayer);

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

                        // ========== 深色科技风格标记样式 ==========
                        // 根据状态设置颜色 (科技感配色)
                        const statusColors = {
                            'normal': [0, 212, 255, 0.8],     // 青色 (--accent-cyan)
                            'warning': [245, 158, 11, 0.8],   // 橙色
                            'danger': [239, 68, 68, 0.8],     // 红色
                            'info': [124, 58, 237, 0.8],      // 紫色 (--accent-purple)
                            'success': [16, 185, 129, 0.8]    // 绿色
                        };
                        const markerColor = statusColors[item.status] || [0, 212, 255, 0.8]; // 默认青色

                        const markerSymbol = {
                            type: "simple-marker",
                            color: markerColor,
                            size: item.size || 12,
                            outline: {
                                color: [0, 212, 255, 1],  // 青色发光边框
                                width: 2
                            }
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
        });
    }

    // ========== 媒体类组件 ==========

    /**
     * 渲染图片组件
     * config: { src: "图片URL", alt: "描述", fit: "cover|contain|fill", caption: "图片说明" }
     */
    renderImage(container, data, config) {
        const src = config.src || data?.src || data?.url || '';
        const alt = config.alt || config.title || '图片';
        const fit = config.fit || 'cover';
        const caption = config.caption || '';

        container.innerHTML = `
            <div class="image-component">
                <img src="${src}" alt="${alt}" 
                     style="width: 100%; height: 100%; object-fit: ${fit}; border-radius: 8px;"
                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22150%22><rect fill=%22%231e3a5f%22 width=%22200%22 height=%22150%22/><text fill=%22%2300d4ff%22 x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22>图片加载失败</text></svg>'">
                ${caption ? `<div class="image-caption">${caption}</div>` : ''}
            </div>
        `;
    }

    /**
     * 渲染视频组件
     * config: { src: "视频URL", poster: "封面图", autoplay: false, controls: true }
     */
    renderVideo(container, data, config) {
        const src = config.src || data?.src || data?.url || '';
        const poster = config.poster || '';
        const autoplay = config.autoplay ? 'autoplay muted' : '';
        const controls = config.controls !== false ? 'controls' : '';

        container.innerHTML = `
            <div class="video-component">
                <video ${controls} ${autoplay} ${poster ? `poster="${poster}"` : ''}
                       style="width: 100%; height: 100%; border-radius: 8px; background: #0a1628;">
                    <source src="${src}" type="video/mp4">
                    您的浏览器不支持视频播放
                </video>
            </div>
        `;
    }

    /**
     * 渲染图片画廊组件
     * config: { images: [{ src, alt, caption }], columns: 3, gap: "8px" }
     */
    renderGallery(container, data, config) {
        const images = config.images || data || [];
        const columns = config.columns || 3;
        const gap = config.gap || '8px';

        let html = `<div class="gallery-component" style="display: grid; grid-template-columns: repeat(${columns}, 1fr); gap: ${gap};">`;

        images.forEach((img, index) => {
            const src = typeof img === 'string' ? img : (img.src || img.url);
            const alt = img.alt || `图片${index + 1}`;
            const caption = img.caption || '';

            html += `
                <div class="gallery-item" style="position: relative; overflow: hidden; border-radius: 8px; cursor: pointer;"
                     onclick="window.open('${src}', '_blank')">
                    <img src="${src}" alt="${alt}" 
                         style="width: 100%; height: 150px; object-fit: cover; transition: transform 0.3s;">
                    ${caption ? `<div class="gallery-caption" style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); color: #e0e6ed; padding: 4px 8px; font-size: 12px;">${caption}</div>` : ''}
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;

        // 添加悬停效果
        container.querySelectorAll('.gallery-item img').forEach(img => {
            img.addEventListener('mouseenter', () => img.style.transform = 'scale(1.05)');
            img.addEventListener('mouseleave', () => img.style.transform = 'scale(1)');
        });
    }

    // ========== 交互类组件 ==========

    /**
     * 渲染操作按钮栏
     * config: { buttons: [{ label, action, type, icon, url }], align: "center|left|right" }
     * action 类型: "link" (跳转), "download" (下载), "callback" (自定义回调)
     */
    renderActionBar(container, data, config) {
        const buttons = config.buttons || [];
        const align = config.align || 'center';

        let html = `<div class="action-bar" style="display: flex; gap: 12px; justify-content: ${align}; flex-wrap: wrap; padding: 8px 0;">`;

        buttons.forEach((btn, index) => {
            const label = btn.label || btn.text || '按钮';
            const type = btn.type || 'primary'; // primary, secondary, danger
            const icon = btn.icon || '';

            // 按钮样式根据类型
            const typeStyles = {
                primary: 'background: linear-gradient(135deg, #00d4ff, #0099cc); color: white;',
                secondary: 'background: transparent; border: 1px solid #00d4ff; color: #00d4ff;',
                danger: 'background: linear-gradient(135deg, #ef4444, #dc2626); color: white;',
                success: 'background: linear-gradient(135deg, #10b981, #059669); color: white;'
            };
            const style = typeStyles[type] || typeStyles.primary;

            // 处理不同的 action 类型
            let clickHandler = '';
            if (btn.action === 'link' && btn.url) {
                clickHandler = `onclick="window.open('${btn.url}', '${btn.target || '_blank'}')"`;
            } else if (btn.action === 'download' && btn.url) {
                clickHandler = `onclick="window.location.href='${btn.url}'"`;
            } else if (btn.callback) {
                // 支持自定义回调函数名
                clickHandler = `onclick="${btn.callback}()"`;
            }

            html += `
                <button class="action-btn action-btn-${type}" ${clickHandler}
                        style="${style} padding: 10px 20px; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s; box-shadow: 0 2px 10px rgba(0, 212, 255, 0.2);">
                    ${icon ? `<span style="margin-right: 6px;">${icon}</span>` : ''}${label}
                </button>
            `;
        });

        html += '</div>';
        container.innerHTML = html;

        // 添加悬停效果
        container.querySelectorAll('.action-btn').forEach(btn => {
            btn.addEventListener('mouseenter', () => {
                btn.style.transform = 'translateY(-2px)';
                btn.style.boxShadow = '0 4px 15px rgba(0, 212, 255, 0.4)';
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.transform = 'translateY(0)';
                btn.style.boxShadow = '0 2px 10px rgba(0, 212, 255, 0.2)';
            });
        });
    }

    // ========== 表单类组件 ==========

    /** 渲染单选按钮组 */
    renderRadio(container, data, config) {
        const name = config.name || 'radio_' + Math.random().toString(36).substr(2, 6);
        const options = config.options || data || [];
        const defaultValue = config.defaultValue || '';

        let html = `<div class="radio-group" style="display: flex; gap: 16px; flex-wrap: wrap;">`;
        options.forEach((opt, i) => {
            const value = typeof opt === 'object' ? opt.value : opt;
            const label = typeof opt === 'object' ? opt.label : opt;
            const checked = value === defaultValue ? 'checked' : '';
            html += `<label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: #e0e6ed;">
                <input type="radio" name="${name}" value="${value}" ${checked} style="accent-color: #00d4ff;">
                <span>${label}</span></label>`;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    /** 渲染多选勾选框 */
    renderCheckbox(container, data, config) {
        const name = config.name || 'checkbox_' + Math.random().toString(36).substr(2, 6);
        const options = config.options || data || [];
        const defaultValues = config.defaultValues || [];

        let html = `<div class="checkbox-group" style="display: flex; gap: 16px; flex-wrap: wrap;">`;
        options.forEach((opt, i) => {
            const value = typeof opt === 'object' ? opt.value : opt;
            const label = typeof opt === 'object' ? opt.label : opt;
            const checked = (opt.checked || defaultValues.includes(value)) ? 'checked' : '';
            html += `<label style="display: flex; align-items: center; gap: 8px; cursor: pointer; color: #e0e6ed;">
                <input type="checkbox" name="${name}" value="${value}" ${checked} style="accent-color: #00d4ff;">
                <span>${label}</span></label>`;
        });
        html += '</div>';
        container.innerHTML = html;
    }

    /** 渲染下拉选择框 */
    renderSelect(container, data, config) {
        const options = config.options || data || [];
        const defaultValue = config.defaultValue || '';
        const placeholder = config.placeholder || '请选择';

        let html = `<select style="width: 100%; padding: 10px; background: rgba(13,27,42,0.9); border: 1px solid #1e3a5f; border-radius: 8px; color: #e0e6ed;">
            <option value="" disabled ${!defaultValue ? 'selected' : ''}>${placeholder}</option>`;
        options.forEach(opt => {
            const value = typeof opt === 'object' ? opt.value : opt;
            const label = typeof opt === 'object' ? opt.label : opt;
            html += `<option value="${value}" ${value === defaultValue ? 'selected' : ''}>${label}</option>`;
        });
        html += '</select>';
        container.innerHTML = html;
    }

    /** 渲染开关按钮 */
    renderSwitch(container, data, config) {
        const name = config.name || 'switch_' + Math.random().toString(36).substr(2, 6);
        const checked = config.checked || config.defaultValue || false;
        const label = config.label || '';
        const onText = config.onText || '开';
        const offText = config.offText || '关';

        const switchId = name + '_input';

        container.innerHTML = `
            <div class="switch-container" style="display: flex; align-items: center; gap: 12px;">
                ${label ? `<span class="switch-label" style="color: #e0e6ed;">${label}</span>` : ''}
                <label class="switch-wrapper" for="${switchId}" style="position: relative; display: inline-block; width: 56px; height: 28px; cursor: pointer;">
                    <input type="checkbox" id="${switchId}" name="${name}" ${checked ? 'checked' : ''}
                           style="opacity: 0; width: 0; height: 0;">
                    <span class="switch-slider" style="
                        position: absolute; top: 0; left: 0; right: 0; bottom: 0;
                        background: ${checked ? 'linear-gradient(135deg, #00d4ff, #0099cc)' : '#1e3a5f'};
                        border-radius: 28px; transition: all 0.3s;
                        box-shadow: ${checked ? '0 0 12px rgba(0, 212, 255, 0.5)' : 'inset 0 2px 4px rgba(0,0,0,0.3)'};
                    "></span>
                    <span class="switch-knob" style="
                        position: absolute; height: 22px; width: 22px;
                        left: ${checked ? '31px' : '3px'}; bottom: 3px;
                        background: white; border-radius: 50%;
                        transition: all 0.3s; box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    "></span>
                </label>
                <span class="switch-status" style="color: ${checked ? '#00d4ff' : '#a0aec0'}; font-size: 13px; min-width: 24px;">
                    ${checked ? onText : offText}
                </span>
            </div>
        `;

        // 添加切换事件
        const input = container.querySelector('input');
        const slider = container.querySelector('.switch-slider');
        const knob = container.querySelector('.switch-knob');
        const status = container.querySelector('.switch-status');

        input.addEventListener('change', () => {
            const isChecked = input.checked;
            slider.style.background = isChecked ? 'linear-gradient(135deg, #00d4ff, #0099cc)' : '#1e3a5f';
            slider.style.boxShadow = isChecked ? '0 0 12px rgba(0, 212, 255, 0.5)' : 'inset 0 2px 4px rgba(0,0,0,0.3)';
            knob.style.left = isChecked ? '31px' : '3px';
            status.style.color = isChecked ? '#00d4ff' : '#a0aec0';
            status.textContent = isChecked ? onText : offText;
        });
    }

    /** 渲染标签页切换 */
    renderTabs(container, data, config) {
        const tabs = config.tabs || [];
        const defaultTab = config.defaultTab || (tabs[0] && tabs[0].key);

        let headerHtml = `<div class="tabs-header" style="display: flex; border-bottom: 1px solid #1e3a5f; margin-bottom: 16px;">`;
        tabs.forEach(tab => {
            const isActive = tab.key === defaultTab;
            headerHtml += `<div class="tab-item" data-tab="${tab.key}" style="padding: 10px 20px; cursor: pointer; color: ${isActive ? '#00d4ff' : '#a0aec0'}; border-bottom: 2px solid ${isActive ? '#00d4ff' : 'transparent'};">${tab.label}</div>`;
        });
        headerHtml += '</div><div class="tabs-content">';
        tabs.forEach(tab => {
            headerHtml += `<div class="tab-panel" data-tab="${tab.key}" style="display: ${tab.key === defaultTab ? 'block' : 'none'};">${tab.content || ''}</div>`;
        });
        headerHtml += '</div>';
        container.innerHTML = headerHtml;

        container.querySelectorAll('.tab-item').forEach(el => {
            el.addEventListener('click', () => {
                const key = el.dataset.tab;
                container.querySelectorAll('.tab-item').forEach(t => { t.style.color = t.dataset.tab === key ? '#00d4ff' : '#a0aec0'; t.style.borderBottomColor = t.dataset.tab === key ? '#00d4ff' : 'transparent'; });
                container.querySelectorAll('.tab-panel').forEach(p => { p.style.display = p.dataset.tab === key ? 'block' : 'none'; });
            });
        });
    }

    /** 渲染简单列表 */
    renderList(container, data, config) {
        const items = config.items || data || [];
        const ordered = config.ordered || false;
        const tag = ordered ? 'ol' : 'ul';

        let html = `<${tag} style="margin: 0; padding-left: 20px; color: #e0e6ed;">`;
        items.forEach(item => {
            const text = typeof item === 'object' ? item.text : item;
            const link = item.link || '';
            const content = link ? `<a href="${link}" target="_blank" style="color: #00d4ff;">${text}</a>` : text;
            html += `<li style="padding: 6px 0; border-bottom: 1px solid rgba(30,58,95,0.5);">${content}</li>`;
        });
        html += `</${tag}>`;
        container.innerHTML = html;
    }

    /** 渲染分割线 */
    renderDivider(container, data, config) {
        const text = config.text || '';
        const color = config.color || '#1e3a5f';

        if (text) {
            container.innerHTML = `<div style="display: flex; align-items: center; margin: 16px 0;"><div style="flex: 1; height: 1px; background: ${color};"></div><span style="padding: 0 16px; color: #a0aec0;">${text}</span><div style="flex: 1; height: 1px; background: ${color};"></div></div>`;
        } else {
            container.innerHTML = `<hr style="border: none; border-top: 1px solid ${color}; margin: 16px 0;">`;
        }
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
