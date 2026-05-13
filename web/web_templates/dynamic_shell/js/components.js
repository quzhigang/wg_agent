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
        this.registerComponent('Carousel', this.renderCarousel);

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

                // 设置行高度 - 确保子元素也能继承高度
                if (rowConfig.height) {
                    rowEl.style.height = rowConfig.height;
                    rowEl.style.minHeight = rowConfig.height;
                    rowEl.style.maxHeight = rowConfig.height;
                }

                container.appendChild(rowEl);

                // 渲染列中的组件
                for (const colConfig of cols) {
                    const colEl = document.createElement('div');
                    colEl.className = 'grid-col';
                    colEl.style.minWidth = '0'; // 防止Echarts溢出
                    colEl.style.minHeight = '0'; // 防止内容溢出
                    colEl.style.overflow = 'hidden'; // 防止内容溢出

                    // 如果行有固定高度，列也需要限制高度
                    if (rowConfig.height) {
                        colEl.style.height = '100%';
                        colEl.style.maxHeight = '100%';
                    }

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

    // 辅助：获取对象路径值（支持数组索引，如 "documents[0].metadata.images[0]"）
    getValueByPath(obj, path) {
        if (!path) return obj;
        // 将 path 拆分为 token，支持 . 和 [index] 格式
        // 例如: "retrieval.documents[0].metadata.images[0]"
        // 拆分为: ["retrieval", "documents", "0", "metadata", "images", "0"]
        const tokens = path.replace(/\[(\d+)\]/g, '.$1').split('.');
        return tokens.reduce((o, k) => {
            if (o === null || o === undefined) return undefined;
            return o[k];
        }, obj);
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

    normalizeLatexUnits(text) {
        if (!text) return text;

        return String(text)
            .replace(/\$\s*([^$]*?)\\mathrm\{m\}\s*\^\s*\{3\}\s*\/\s*\\mathrm\{s\}([^$]*?)\s*\$/g, '$1m³/s$2')
            .replace(/\$\s*([^$]*?)\\mathrm\{m\^\{3\}\}\s*\/\s*\\mathrm\{s\}([^$]*?)\s*\$/g, '$1m³/s$2')
            .replace(/\$\s*([^$]*?)\\mathrm\{km\}\s*\^\s*\{2\}([^$]*?)\s*\$/g, '$1km²$2')
            .replace(/\$\s*([^$]*?)\\mathrm\{m\}\s*\^\s*\{3\}([^$]*?)\s*\$/g, '$1m³$2')
            .replace(/\$\s*([^$]*?)\\mathrm\{m\^\{3\}\}([^$]*?)\s*\$/g, '$1m³$2')
            .replace(/\$\s*([^$]*?)\\mathrm\{mm\}([^$]*?)\s*\$/g, '$1mm$2')
            .replace(/\$\s*([^$]*?)\\mathrm\{m\}([^$]*?)\s*\$/g, '$1m$2')
            .replace(/\\cdot/g, '\u00B7')
            .replace(/\{\\sim\}|\\sim/g, '~')
            .replace(/\{\}/g, '')
            .replace(/\\mathrm\{\^\{\\prime\}([0-9]+)\}/g, '$1')
            .replace(/\^\{\\mathrm\{,\}\\mathrm\{\}\}/g, '')
            .replace(/\^\{\\mathrm\{,\}\\mathrm\{\}?\}?/g, '')
            .replace(/\^\{[^}]*\\[a-zA-Z]+[^}]*\}/g, '')
            .replace(/\\mathrm\{([a-zA-Z]+)\}/g, '$1')
            .replace(/\^\{\\star\}/g, '')
            .replace(/\^\{\\prime\\prime\}/g, '')
            .replace(/\^\{\\prime\}/g, '')
            .replace(/\^\{[0-9,，'"\s]*\}/g, '')
            .replace(/\$/g, '');
    }

    renderHtmlContent(container, data, config) {
        let content = data || config.content || '';
        if (Array.isArray(content)) {
            content = content.join('\n');
        }
        content = this.normalizeLatexUnits(content);

        // 检测是否为Markdown格式（包含##、**、- 等标记）
        const isMarkdown = /^#{1,6}\s|^\*\*|^-\s|^>\s|\n#{1,6}\s|\n-\s|\*\*[^*]+\*\*/.test(content);

        if (isMarkdown && typeof marked !== 'undefined') {
            // 使用marked.js渲染Markdown
            container.innerHTML = `<div class="html-content markdown-body">${marked.parse(content)}</div>`;
        } else {
            container.innerHTML = `<div class="html-content">${content}</div>`;
        }
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

        // 最大显示行数，默认10行，超出滚动
        const maxRows = config.maxRows || 10;
        const rowHeight = 40; // 每行高度约40px
        const headerHeight = 44; // 表头高度
        const maxHeight = headerHeight + (maxRows * rowHeight);
        const needScroll = tableData.length > maxRows;

        let html = `<div class="table-wrapper" style="max-height: ${maxHeight}px; overflow-y: ${needScroll ? 'auto' : 'hidden'}; border-radius: 8px;">`;
        html += '<table class="simple-table"><thead><tr>';
        finalCols.forEach(c => {
            const label = c.title || c.label || c.key;
            html += `<th>${label}</th>`;
        });
        html += '</tr></thead><tbody>';

        tableData.forEach(row => {
            html += '<tr>';
            finalCols.forEach(c => {
                const key = c.dataIndex || c.key;
                let value = row[key];
                if (value === undefined && key && key.endsWith('_display')) {
                    const displayFallbacks = {
                        storage_display: 'storage_10k_m3',
                        outflow_display: 'outflow_m3_s',
                        inflow_display: 'inflow_m3_s',
                        water_level_display: 'water_level_m'
                    };
                    const fallbackKey = displayFallbacks[key] || key.replace('_display', '');
                    value = row[fallbackKey];
                }
                if (value === undefined || value === null || value === '') {
                    value = '缺测';
                }
                html += `<td>${value}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    async renderEcharts(container, data, config) {
        container.style.width = '100%';
        container.style.height = '100%';
        container.style.minHeight = '200px';
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
        // 3. config 顶层直接包含 xAxis/yAxis/series (LLM 常见生成格式)
        let option = config.option || config.options || {};

        // 如果 option 为空，但 config 顶层有 xAxis/yAxis/series，则从顶层提取
        if (Object.keys(option).length === 0) {
            if (config.xAxis || config.yAxis || config.series) {
                option = {
                    xAxis: config.xAxis,
                    yAxis: config.yAxis,
                    series: config.series,
                    legend: config.legend,
                    tooltip: config.tooltip,
                    grid: config.grid
                };
            }
        }

        // 获取图表类型
        const chartType = config.chartType || config.chart_type || 'line';

        // ========== 处理 series 内部的 data_source 绑定 ==========
        // LLM 可能在 series[].data_source 或 series[].data 中配置数据绑定
        if (option.series && Array.isArray(option.series)) {
            for (let i = 0; i < option.series.length; i++) {
                const series = option.series[i];
                // 格式1: series.data_source (推荐格式)
                if (series.data_source && series.data_source.type === 'context') {
                    // 从 context 中获取数据
                    const seriesData = this.getValueByPath(this.data.context, series.data_source.path);
                    if (seriesData) {
                        series.data = seriesData;
                    }
                    delete series.data_source; // 清理 data_source 配置
                }
                // 格式2: series.data 是一个 data_source 对象 (LLM 有时会生成这种格式)
                // 例如: { data: { type: "context", path: "discharge_curve" } }
                else if (series.data && typeof series.data === 'object' && series.data.type === 'context') {
                    const seriesData = this.getValueByPath(this.data.context, series.data.path);
                    if (seriesData) {
                        series.data = seriesData;
                    } else {
                        series.data = []; // 如果没有数据，设置为空数组
                    }
                }
            }
        }

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
        } else if (processedData && Array.isArray(processedData)) {
            // 如果 data 是数组（如泄流曲线 [[x,y], [x,y], ...]），直接注入到 series
            if (!option.series || option.series.length === 0) {
                option.series = [{ type: chartType, data: processedData }];
            } else if (Array.isArray(option.series) && option.series.length > 0 && !option.series[0].data) {
                option.series[0].data = processedData;
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

        // ========== 坐标轴自适应：根据实际数据自动计算 min/max ==========
        // 针对 [[x, y], [x, y], ...] 格式的数据（如泄流曲线）
        this._autoScaleAxes(option);

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

    /**
     * 坐标轴自适应：根据 series 数据自动计算 xAxis/yAxis 的 min/max
     * 支持 [[x, y], [x, y], ...] 格式的数据（如泄流曲线、散点图）
     */
    _autoScaleAxes(option) {
        if (!option.series || !Array.isArray(option.series)) return;

        let allXValues = [];
        let allYValues = [];

        // 遍历所有 series，收集数据点
        option.series.forEach(series => {
            const data = series.data;
            if (!data || !Array.isArray(data)) return;

            data.forEach(point => {
                // 支持多种数据格式
                if (Array.isArray(point) && point.length >= 2) {
                    // [[x, y], [x, y], ...] 格式
                    const x = parseFloat(point[0]);
                    const y = parseFloat(point[1]);
                    if (!isNaN(x)) allXValues.push(x);
                    if (!isNaN(y)) allYValues.push(y);
                } else if (typeof point === 'object' && point !== null) {
                    // [{ value: [x, y] }, ...] 或 [{ x: ..., y: ... }, ...] 格式
                    if (Array.isArray(point.value) && point.value.length >= 2) {
                        const x = parseFloat(point.value[0]);
                        const y = parseFloat(point.value[1]);
                        if (!isNaN(x)) allXValues.push(x);
                        if (!isNaN(y)) allYValues.push(y);
                    } else if (point.x !== undefined && point.y !== undefined) {
                        const x = parseFloat(point.x);
                        const y = parseFloat(point.y);
                        if (!isNaN(x)) allXValues.push(x);
                        if (!isNaN(y)) allYValues.push(y);
                    }
                }
            });
        });

        // 如果收集到了数据点，计算并设置坐标轴范围
        if (allXValues.length > 0 && allYValues.length > 0) {
            const xMin = Math.min(...allXValues);
            const xMax = Math.max(...allXValues);
            const yMin = Math.min(...allYValues);
            const yMax = Math.max(...allYValues);

            // 添加 10% 的边距，使图表更美观
            const xPadding = (xMax - xMin) * 0.1 || 1;
            const yPadding = (yMax - yMin) * 0.1 || 1;

            // 设置 xAxis 范围（仅当 xAxis.type 为 'value' 时）
            if (option.xAxis && option.xAxis.type === 'value') {
                option.xAxis.min = Math.floor(xMin - xPadding);
                option.xAxis.max = Math.ceil(xMax + xPadding);
                // 确保 min 不小于 0（对于流量等非负数据）
                if (option.xAxis.min < 0 && xMin >= 0) {
                    option.xAxis.min = 0;
                }
            }

            // 设置 yAxis 范围（仅当 yAxis.type 为 'value' 时）
            if (option.yAxis && option.yAxis.type === 'value') {
                option.yAxis.min = Math.floor((yMin - yPadding) * 10) / 10; // 保留一位小数
                option.yAxis.max = Math.ceil((yMax + yPadding) * 10) / 10;
            }

            console.log(`[Echarts] 坐标轴自适应: X[${option.xAxis?.min}, ${option.xAxis?.max}], Y[${option.yAxis?.min}, ${option.yAxis?.max}]`);
        }
    }

    renderGISMap(container, data, config) {
        console.log('[GISMap] Rendering map, data:', data, 'config:', config);

        // 1. 设置容器ID（ArcGIS要求容器必须有ID）
        const mapDivId = 'viewDiv_' + Math.random().toString(36).substr(2, 9);
        const mapDiv = document.createElement('div');
        mapDiv.id = mapDivId;
        mapDiv.style.width = '100%';
        mapDiv.style.height = '100%';
        mapDiv.style.minHeight = '200px';
        mapDiv.classList.add('gis-map-container');
        container.appendChild(mapDiv);

        // 2. 加载 ArcGIS 模块 - 使用 Portal WebMap (与预定义模板一致)
        require([
            "esri/WebMap",
            "esri/Map",
            "esri/views/MapView",
            "esri/config",
            "esri/layers/GraphicsLayer",
            "esri/Graphic"
        ], (WebMap, Map, MapView, esriConfig, GraphicsLayer, Graphic) => {
            console.log('[GISMap] ArcGIS modules loaded successfully');

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

            // 3. 创建视图 - 固定缩放级别为10
            const zoom = config.zoom || 10;  // 默认缩放级别为10
            // center 支持多种来源：
            // 1. data (从 data_source 绑定，可能是数组 [lng, lat] 或对象 {center: [lng, lat]})
            // 2. config.center (静态配置)
            let center = [114.057818, 35.826884];  // 默认河南省中心
            if ((!data || !data.markers) && window.PAGE_DATA && window.PAGE_DATA.context) {
                const ctx = window.PAGE_DATA.context;
                const summary = ctx.tool_results?.sum_reservoir_current_outflow?.data;
                const infoList = ctx.tool_results?.get_reservoir_info?.data || [];
                if (summary && Array.isArray(summary.reservoirs) && Array.isArray(infoList)) {
                    const infoByStcd = new Map(infoList.map(item => [String(item.stcd || ''), item]));
                    const markers = summary.reservoirs
                        .map(row => {
                            const info = infoByStcd.get(String(row.stcd || '')) || {};
                            const lng = Number(row.longitude ?? info.longitude ?? info.lgtd);
                            const lat = Number(row.latitude ?? info.latitude ?? info.lttd);
                            if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
                            const outflow = row.outflow_m3_s ?? row.outflow_display ?? '缺测';
                            return {
                                lng,
                                lat,
                                name: row.name,
                                title: row.name,
                                status: row.outflow_m3_s == null ? 'warning' : 'normal',
                                content: `规模：${row.scale_name || ''}<br>当前库容：${row.storage_10k_m3 ?? '缺测'}万m³<br>当前出流：${outflow}m³/s<br>数据时间：${row.data_time || '--'}`
                            };
                        })
                        .filter(Boolean);
                    if (markers.length) {
                        data = {
                            name: '卫共流域大型、中型水库',
                            center: [
                                markers.reduce((sum, item) => sum + item.lng, 0) / markers.length,
                                markers.reduce((sum, item) => sum + item.lat, 0) / markers.length
                            ],
                            markers
                        };
                    }
                }
            }
            if (data) {
                if (Array.isArray(data) && data.length === 2) {
                    center = data;  // data 直接是 [lng, lat]
                } else if (data.center && Array.isArray(data.center)) {
                    center = data.center;  // data 是 { center: [lng, lat] }
                } else if (data.longitude && data.latitude) {
                    center = [data.longitude, data.latitude];
                }
            } else if (config.center) {
                center = config.center;
            }

            const view = new MapView({
                container: mapDivId,
                map: webmap,
                zoom: zoom,
                center: center
            });

            // 4. 添加标记图层
            const graphicsLayer = new GraphicsLayer();
            const addReservoirMarkers = (map) => {
                map.add(graphicsLayer);

                // ========== 自动在中心点添加标记和文字标注 ==========
                // 获取标注名称：多种来源尝试
                let labelText = config.label || '';

                // 1. 从 data 中获取
                if (!labelText && data) {
                    labelText = data.name || data.title || data.stnm || '';
                }

                // 2. 从全局 pageData.context 获取
                if (!labelText && window.PAGE_DATA && window.PAGE_DATA.context) {
                    const ctx = window.PAGE_DATA.context;
                    // 从 intent.entities 中获取对象名称
                    if (ctx.intent && ctx.intent.entities) {
                        labelText = ctx.intent.entities['关键词'] || ctx.intent.entities['object'] || ctx.intent.entities['name'] || '';
                    }
                }

                // 3. 从 geo_info 中获取（如果有 name 字段）
                if (!labelText && window.PAGE_DATA && window.PAGE_DATA.context && window.PAGE_DATA.context.geo_info) {
                    labelText = window.PAGE_DATA.context.geo_info.name || '';
                }

                // 4. 从 parsed_info_table 中查找名称字段
                if (!labelText && window.PAGE_DATA && window.PAGE_DATA.context && window.PAGE_DATA.context.parsed_info_table) {
                    const infoTable = window.PAGE_DATA.context.parsed_info_table;
                    for (const item of infoTable) {
                        if (item.label && (item.label.includes('名称') || item.label.includes('name') || item.label === 'name')) {
                            labelText = item.value;
                            break;
                        }
                    }
                }

                console.log('[GISMap] labelText:', labelText, 'center:', center);

                // 如果有有效的中心坐标（非默认值），添加中心点标记
                const isCustomCenter = !(center[0] === 114.057818 && center[1] === 35.826884);
                if (isCustomCenter) {
                    const centerPoint = {
                        type: "point",
                        longitude: center[0],
                        latitude: center[1]
                    };

                    // 圆形标记样式 - 科技感青色（减小尺寸）
                    const centerMarkerSymbol = {
                        type: "simple-marker",
                        style: "circle",
                        color: [0, 212, 255, 0.9],  // 青色填充
                        size: 8,  // 减小到8px
                        outline: {
                            color: [255, 255, 255, 1],  // 白色边框
                            width: 2
                        }
                    };

                    // 添加圆形标记
                    const centerMarkerGraphic = new Graphic({
                        geometry: centerPoint,
                        symbol: centerMarkerSymbol
                    });
                    graphicsLayer.add(centerMarkerGraphic);

                    // 添加白色文字标注
                    // 如果没有获取到标注文本，使用默认文本
                    const displayText = labelText || '当前位置';
                    const textSymbol = {
                        type: "text",
                        text: displayText,
                        color: [255, 255, 255, 1],  // 白色文字
                        haloColor: [0, 0, 0, 0.9],  // 黑色光晕（提高可读性）
                        haloSize: 2,
                        font: {
                            size: 12,
                            weight: "bold",
                            family: "Microsoft YaHei, sans-serif"
                        },
                        yoffset: -15  // 文字在标记下方
                    };

                    const textGraphic = new Graphic({
                        geometry: centerPoint,
                        symbol: textSymbol
                    });
                    graphicsLayer.add(textGraphic);

                    console.log('[GISMap] Added marker and label:', displayText);
                }

                // ========== 处理额外的标记点 ==========
                // 支持两种数据来源：
                // 1. config.markers (新格式，直接在 props 中)
                // 2. data (旧格式，通过 data_source 获取)
                const markers = (config.markers && config.markers.length)
                    ? config.markers
                    : ((data && data.markers) || []);

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
            };
            webmap.when(() => addReservoirMarkers(webmap)).catch((error) => {
                console.warn('[GISMap] Portal WebMap load failed, fallback to standard basemap:', error);
                const fallbackMap = new Map({ basemap: "topo-vector" });
                view.map = fallbackMap;
                addReservoirMarkers(fallbackMap);
            });
        });
    }

    // ========== 媒体类组件 ==========

    /**
     * 渲染图片组件
     * config: { src: "图片URL", alt: "描述", fit: "cover|contain|fill", caption: "图片说明" }
     * data: 可以是字符串(URL)或对象{src, url}
     */
    renderImage(container, data, config) {
        // 支持多种数据格式：
        // 1. data 是字符串（直接是URL）
        // 2. data 是对象 { src: "..." } 或 { url: "..." }
        // 3. config.src 静态配置
        let src = '';
        if (typeof data === 'string') {
            src = data;
        } else if (data && typeof data === 'object') {
            src = data.src || data.url || '';
        }
        src = src || config.src || '';

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
     * 支持两种视频流格式：
     * 1. HTTP/HTTPS 视频流 - 使用标准 HTML5 <video> 标签
     * 2. WebSocket 视频流 (ws://, wss://) - 使用海康H5播放器
     */
    renderVideo(container, data, config) {
        // 支持多种数据格式获取视频URL
        let src = '';
        if (typeof data === 'string') {
            src = data;
        } else if (data && typeof data === 'object') {
            src = data.src || data.url || '';
        }
        src = src || config.src || '';

        const poster = config.poster || '';
        const autoplay = config.autoplay !== false; // 默认自动播放
        const controls = config.controls !== false;

        // 检测是否是 WebSocket 视频流
        const isWebSocketStream = src.startsWith('ws://') || src.startsWith('wss://');

        if (isWebSocketStream) {
            // WebSocket 视频流 - 使用海康H5播放器
            this._renderHikvisionVideo(container, src, config);
        } else if (src) {
            // 标准 HTTP 视频流 - 使用 HTML5 video 标签
            container.innerHTML = `
                <div class="video-component" style="width: 100%; height: 100%; min-height: 200px;">
                    <video ${controls ? 'controls' : ''} ${autoplay ? 'autoplay muted' : ''} ${poster ? `poster="${poster}"` : ''}
                           style="width: 100%; height: 100%; border-radius: 8px; background: #0a1628;">
                        <source src="${src}" type="video/mp4">
                        您的浏览器不支持视频播放
                    </video>
                </div>
            `;
        } else {
            // 没有视频源
            container.innerHTML = `
                <div class="video-component" style="width: 100%; height: 100%; min-height: 200px; display: flex; align-items: center; justify-content: center; background: #0a1628; border-radius: 8px;">
                    <div style="text-align: center; color: #a0aec0;">
                        <div style="font-size: 48px; margin-bottom: 12px;">📹</div>
                        <div>暂无视频源</div>
                    </div>
                </div>
            `;
        }
    }

    /**
     * 渲染海康威视H5播放器视频流
     * 使用海康JSPlugin播放WebSocket视频流
     */
    _renderHikvisionVideo(container, wsUrl, config) {
        // 转换视频流URL格式
        // API返回格式: ws://10.20.2.98:559/openUrl/vsigXXXXXX
        // 实际需要格式: ws://171.8.64.181:559/openUrl/vsigXXXXXX (替换内网IP为外网IP)
        const convertedUrl = this._convertVideoStreamUrl(wsUrl);
        console.log('[Video] Original URL:', wsUrl);
        console.log('[Video] Converted URL:', convertedUrl);

        const playerId = 'video_player_' + Math.random().toString(36).substr(2, 9);

        container.innerHTML = `
            <div class="video-component hk-video" style="width: 100%; height: 100%; min-height: 300px; position: relative; background: #0a1628; border-radius: 8px; overflow: hidden;">
                <div id="${playerId}" class="hk-player" style="width: 100%; height: 100%;"></div>
                <div class="video-loading" style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #00d4ff; text-align: center; z-index: 10;">
                    <div class="loading-spinner" style="width: 40px; height: 40px; border: 3px solid rgba(0, 212, 255, 0.3); border-top-color: #00d4ff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 12px;"></div>
                    <div>正在连接视频流...</div>
                </div>
                <div class="video-error" style="display: none; position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: #ef4444; text-align: center; z-index: 10;">
                    <div style="font-size: 48px; margin-bottom: 12px;">⚠️</div>
                    <div class="error-msg">视频流连接失败</div>
                    <button class="retry-btn" style="margin-top: 12px; padding: 8px 16px; background: #00d4ff; border: none; border-radius: 4px; color: white; cursor: pointer;">重试</button>
                </div>
            </div>
            <style>
                @keyframes spin { to { transform: rotate(360deg); } }
            </style>
        `;

        const loadingEl = container.querySelector('.video-loading');
        const errorEl = container.querySelector('.video-error');
        const retryBtn = container.querySelector('.retry-btn');

        // 加载海康播放器并初始化（使用 requestAnimationFrame 确保 DOM 渲染完成）
        this._loadHikvisionPlayer().then(() => {
            // 等待下一帧确保 DOM 已渲染
            requestAnimationFrame(() => {
                setTimeout(() => {
                    this._initHikvisionPlayer(playerId, convertedUrl, loadingEl, errorEl, config);
                }, 100);
            });
        }).catch(err => {
            console.error('[Video] Failed to load Hikvision player:', err);
            loadingEl.style.display = 'none';
            errorEl.style.display = 'block';
            errorEl.querySelector('.error-msg').textContent = '播放器加载失败';
        });

        // 重试按钮事件
        retryBtn.onclick = () => {
            loadingEl.style.display = 'block';
            errorEl.style.display = 'none';
            this._initHikvisionPlayer(playerId, convertedUrl, loadingEl, errorEl, config);
        };
    }

    /**
     * 动态加载海康H5播放器SDK
     * 注意：需要临时禁用 AMD 检测，因为 ArcGIS API 使用 Dojo loader
     */
    _loadHikvisionPlayer() {
        return new Promise((resolve, reject) => {
            // 检查是否已加载
            if (typeof window.JSPlugin !== 'undefined') {
                resolve();
                return;
            }

            // 临时禁用 AMD 检测：只删除 define.amd 属性，不删除 define 函数
            // h5player 检测的是 "function"==typeof define && define.amd
            // 这样既不影响 ArcGIS 的模块加载，又能让 h5player 使用全局变量模式
            const originalAmd = window.define && window.define.amd;
            if (window.define) {
                window.define.amd = undefined;
            }

            // 加载海康播放器SDK
            const script = document.createElement('script');
            script.src = './libs/hk/h5player.min.js';
            script.onload = () => {
                console.log('[Video] Hikvision H5 Player script loaded');
                // 恢复 AMD 标识
                if (window.define && originalAmd) {
                    window.define.amd = originalAmd;
                }

                // 检查 JSPlugin 是否成功挂载到 window
                if (typeof window.JSPlugin !== 'undefined') {
                    console.log('[Video] JSPlugin is available');
                    resolve();
                } else {
                    console.error('[Video] JSPlugin not found after loading');
                    reject(new Error('JSPlugin not found after loading'));
                }
            };
            script.onerror = () => {
                // 恢复 AMD 标识
                if (window.define && originalAmd) {
                    window.define.amd = originalAmd;
                }
                console.error('[Video] Failed to load Hikvision H5 Player');
                reject(new Error('Failed to load Hikvision H5 Player'));
            };
            document.head.appendChild(script);
        });
    }

    /**
     * 初始化海康播放器并播放视频
     */
    _initHikvisionPlayer(playerId, wsUrl, loadingEl, errorEl, config) {
        console.log('[Video] Initializing Hikvision player:', playerId, wsUrl);

        // 检查 JSPlugin 是否可用
        if (typeof window.JSPlugin === 'undefined') {
            console.error('[Video] JSPlugin is not defined');
            loadingEl.style.display = 'none';
            errorEl.style.display = 'block';
            errorEl.querySelector('.error-msg').textContent = '播放器SDK未加载';
            return;
        }

        // 检查 DOM 元素是否存在
        const playerEl = document.getElementById(playerId);
        if (!playerEl) {
            console.error('[Video] Player container not found:', playerId);
            loadingEl.style.display = 'none';
            errorEl.style.display = 'block';
            errorEl.querySelector('.error-msg').textContent = '播放器容器未找到';
            return;
        }

        // 确保容器有明确的宽高
        const rect = playerEl.getBoundingClientRect();
        console.log('[Video] Player container size:', rect.width, 'x', rect.height);
        if (rect.width === 0 || rect.height === 0) {
            // 设置默认尺寸
            playerEl.style.width = '100%';
            playerEl.style.height = '400px';
            console.log('[Video] Set default container size');
        }

        try {
            console.log('[Video] Creating JSPlugin instance...');
            // 创建播放器实例
            const player = new window.JSPlugin({
                szId: playerId,
                iMaxSplit: 1,
                iCurrentSplit: 1,
                openDebug: true,
                szBasePath: './libs/hk/',
                oStyle: { borderSelect: '#00d4ff' }
            });
            console.log('[Video] JSPlugin instance created successfully');

            // 存储播放器实例以便后续控制
            window._hkPlayers = window._hkPlayers || {};
            window._hkPlayers[playerId] = player;

            // 绑定首帧显示事件
            window.firstFrameDisplay = () => {
                console.log('[Video] First frame displayed');
                loadingEl.style.display = 'none';
                errorEl.style.display = 'none';
            };

            // 播放视频
            console.log('[Video] Calling JS_Play with URL:', wsUrl);
            player.JS_Play(wsUrl, { playURL: wsUrl, mode: 0 }, 0).then(() => {
                console.log('[Video] Play started successfully');
            }).catch((e) => {
                console.error('[Video] Play failed:', e);
                loadingEl.style.display = 'none';
                errorEl.style.display = 'block';
                errorEl.querySelector('.error-msg').textContent = '视频播放失败: ' + (e.message || '未知错误');
            });

            // 设置超时检测
            setTimeout(() => {
                if (loadingEl.style.display !== 'none') {
                    console.warn('[Video] Connection timeout');
                    loadingEl.style.display = 'none';
                    errorEl.style.display = 'block';
                    errorEl.querySelector('.error-msg').textContent = '连接超时，请重试';
                }
            }, 15000);

        } catch (err) {
            console.error('[Video] Hikvision player initialization error:', err);
            console.error('[Video] Error stack:', err.stack);
            loadingEl.style.display = 'none';
            errorEl.style.display = 'block';
            errorEl.querySelector('.error-msg').textContent = '播放器初始化失败: ' + (err.message || '未知错误');
        }
    }

    /**
     * 转换视频流URL格式
     * 将API返回的内网URL转换为实际可用的外网URL格式
     */
    _convertVideoStreamUrl(url) {
        // 替换内网IP为外网IP
        // ws://10.20.2.98:559/openUrl/xxx -> ws://171.8.64.181:559/openUrl/xxx
        let convertedUrl = url.replace('//10.20.2.98:559/', '//171.8.64.181:559/');
        return convertedUrl;
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

    /**
     * 渲染轮播图组件
     * config: { images: [{ src, alt, caption }] 或 ["url1", "url2"], autoplay: true, interval: 3000 }
     */
    renderCarousel(container, data, config) {
        const images = config.images || data || [];
        const autoplay = config.autoplay !== false;
        const interval = config.interval || 3000;
        const carouselId = 'carousel_' + Math.random().toString(36).substr(2, 9);

        if (images.length === 0) {
            container.innerHTML = '<div class="empty-carousel">暂无图片</div>';
            return;
        }

        // 构建轮播图HTML
        let html = `
            <div class="carousel-component" id="${carouselId}" style="position: relative; width: 100%; height: 100%; overflow: hidden; border-radius: 8px;">
                <div class="carousel-inner" style="display: flex; transition: transform 0.5s ease; height: 100%;">
        `;

        images.forEach((img, index) => {
            const src = typeof img === 'string' ? img : (img.src || img.url);
            const alt = (typeof img === 'object' ? img.alt : '') || `图片${index + 1}`;
            const caption = typeof img === 'object' ? (img.caption || '') : '';

            html += `
                <div class="carousel-slide" data-index="${index}" style="min-width: 100%; height: 100%; position: relative;">
                    <img src="${src}" alt="${alt}"
                         style="width: 100%; height: 100%; object-fit: contain; background: #0a1628;"
                         onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22400%22 height=%22300%22><rect fill=%22%231e3a5f%22 width=%22400%22 height=%22300%22/><text fill=%22%2300d4ff%22 x=%2250%%22 y=%2250%%22 text-anchor=%22middle%22>图片加载失败</text></svg>'">
                    ${caption ? `<div class="carousel-caption" style="position: absolute; bottom: 0; left: 0; right: 0; background: linear-gradient(transparent, rgba(0,0,0,0.8)); color: #e0e6ed; padding: 20px 16px 12px; font-size: 14px;">${caption}</div>` : ''}
                </div>
            `;
        });

        html += `
                </div>
                <!-- 左右箭头 -->
                <button class="carousel-prev" style="position: absolute; left: 10px; top: 50%; transform: translateY(-50%); background: rgba(0,212,255,0.3); border: 1px solid rgba(0,212,255,0.5); color: #00d4ff; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; font-size: 18px; transition: all 0.3s;">‹</button>
                <button class="carousel-next" style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: rgba(0,212,255,0.3); border: 1px solid rgba(0,212,255,0.5); color: #00d4ff; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; font-size: 18px; transition: all 0.3s;">›</button>
                <!-- 指示器 -->
                <div class="carousel-indicators" style="position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px;">
        `;

        images.forEach((_, index) => {
            html += `<span class="carousel-dot" data-index="${index}" style="width: 10px; height: 10px; border-radius: 50%; background: ${index === 0 ? '#00d4ff' : 'rgba(255,255,255,0.4)'}; cursor: pointer; transition: all 0.3s; box-shadow: ${index === 0 ? '0 0 8px #00d4ff' : 'none'};"></span>`;
        });

        html += `
                </div>
            </div>
        `;

        container.innerHTML = html;

        // 轮播逻辑
        const carousel = container.querySelector(`#${carouselId}`);
        const inner = carousel.querySelector('.carousel-inner');
        const dots = carousel.querySelectorAll('.carousel-dot');
        const prevBtn = carousel.querySelector('.carousel-prev');
        const nextBtn = carousel.querySelector('.carousel-next');
        let currentIndex = 0;
        let autoplayTimer = null;

        const goToSlide = (index) => {
            if (index < 0) index = images.length - 1;
            if (index >= images.length) index = 0;
            currentIndex = index;
            inner.style.transform = `translateX(-${currentIndex * 100}%)`;
            dots.forEach((dot, i) => {
                dot.style.background = i === currentIndex ? '#00d4ff' : 'rgba(255,255,255,0.4)';
                dot.style.boxShadow = i === currentIndex ? '0 0 8px #00d4ff' : 'none';
            });
        };

        const startAutoplay = () => {
            if (autoplay && images.length > 1) {
                autoplayTimer = setInterval(() => goToSlide(currentIndex + 1), interval);
            }
        };

        const stopAutoplay = () => {
            if (autoplayTimer) {
                clearInterval(autoplayTimer);
                autoplayTimer = null;
            }
        };

        // 事件绑定
        prevBtn.addEventListener('click', () => { stopAutoplay(); goToSlide(currentIndex - 1); startAutoplay(); });
        nextBtn.addEventListener('click', () => { stopAutoplay(); goToSlide(currentIndex + 1); startAutoplay(); });
        dots.forEach(dot => {
            dot.addEventListener('click', () => { stopAutoplay(); goToSlide(parseInt(dot.dataset.index)); startAutoplay(); });
        });

        // 悬停暂停
        carousel.addEventListener('mouseenter', stopAutoplay);
        carousel.addEventListener('mouseleave', startAutoplay);

        // 按钮悬停效果
        [prevBtn, nextBtn].forEach(btn => {
            btn.addEventListener('mouseenter', () => { btn.style.background = 'rgba(0,212,255,0.6)'; btn.style.boxShadow = '0 0 15px rgba(0,212,255,0.5)'; });
            btn.addEventListener('mouseleave', () => { btn.style.background = 'rgba(0,212,255,0.3)'; btn.style.boxShadow = 'none'; });
        });

        // 启动自动播放
        startAutoplay();
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
    async renderTabs(container, data, config) {
        const tabs = config.tabs || [];

        // 为每个tab生成key（如果没有的话）
        tabs.forEach((tab, index) => {
            if (!tab.key) {
                tab.key = `tab_${index}`;
            }
        });

        const defaultTab = config.defaultTab || (tabs[0] && tabs[0].key);

        // 设置容器为flex布局，确保内容区域能撑满
        container.style.cssText = 'display: flex; flex-direction: column; height: 100%;';

        // 创建标签头
        const headerEl = document.createElement('div');
        headerEl.className = 'tabs-header';
        headerEl.style.cssText = 'display: flex; border-bottom: 1px solid #1e3a5f; flex-shrink: 0;';

        tabs.forEach(tab => {
            const isActive = tab.key === defaultTab;
            const tabItem = document.createElement('div');
            tabItem.className = 'tab-item';
            tabItem.dataset.tab = tab.key;
            tabItem.style.cssText = `padding: 10px 20px; cursor: pointer; color: ${isActive ? '#00d4ff' : '#a0aec0'}; border-bottom: 2px solid ${isActive ? '#00d4ff' : 'transparent'}; transition: all 0.3s;`;
            tabItem.textContent = tab.label || tab.title || tab.key;
            headerEl.appendChild(tabItem);
        });

        container.appendChild(headerEl);

        // 创建内容区域 - 使用 flex: 1 撑满剩余空间
        const contentEl = document.createElement('div');
        contentEl.className = 'tabs-content';
        contentEl.style.cssText = 'flex: 1; overflow: hidden; position: relative; min-height: 200px;';
        container.appendChild(contentEl);

        // 存储需要延迟 resize 的 echarts 实例
        const echartsInstances = [];

        // 渲染每个标签页的内容
        for (const tab of tabs) {
            const panelEl = document.createElement('div');
            panelEl.className = 'tab-panel';
            panelEl.dataset.tab = tab.key;
            panelEl.style.cssText = `display: ${tab.key === defaultTab ? 'block' : 'none'}; height: 100%; overflow: auto;`;
            contentEl.appendChild(panelEl);

            // 判断 content 类型：如果是对象且有 type 字段，则作为嵌套组件渲染
            const content = tab.content;
            if (content && typeof content === 'object' && content.type) {
                // 嵌套组件渲染
                const renderer = this.components[content.type];
                if (renderer) {
                    const bodyEl = document.createElement('div');
                    bodyEl.className = 'nested-component-body';
                    // 对于 Echarts 组件，设置明确的最小高度
                    if (content.type === 'Echarts') {
                        bodyEl.style.cssText = 'width: 100%; height: 100%; min-height: 250px;';
                    } else {
                        bodyEl.style.cssText = 'height: 100%;';
                    }
                    panelEl.appendChild(bodyEl);

                    // 解析嵌套组件的 data_source（支持 data_source 和 dataSource 两种命名）
                    let nestedData = null;
                    const dataSourceConfig = content.data_source || content.dataSource;
                    if (dataSourceConfig) {
                        try {
                            nestedData = await this.resolveDataSource(dataSourceConfig);
                        } catch (e) {
                            console.error(`Failed to resolve data_source for nested component:`, e);
                        }
                    }

                    // 调用对应组件的渲染函数
                    await renderer(bodyEl, nestedData, content);
                } else {
                    panelEl.innerHTML = `<div class="error">Unknown component type: ${content.type}</div>`;
                }
            } else if (typeof content === 'string') {
                // 检查是否是组件引用（引用 PAGE_CONFIG.components 中的其他组件）
                const referencedComponent = window.PAGE_CONFIG?.components?.[content];
                if (referencedComponent && referencedComponent.type) {
                    // 渲染引用的组件
                    const refRenderer = this.componentRenderers[referencedComponent.type];
                    if (refRenderer) {
                        const bodyEl = document.createElement('div');
                        bodyEl.className = 'tab-body';
                        if (referencedComponent.type === 'Echarts') {
                            bodyEl.style.cssText = 'width: 100%; height: 100%; min-height: 250px;';
                        } else {
                            bodyEl.style.cssText = 'height: 100%;';
                        }
                        panelEl.appendChild(bodyEl);

                        // 解析引用组件的 data_source
                        let refData = null;
                        const refDataSourceConfig = referencedComponent.data_source || referencedComponent.dataSource;
                        if (refDataSourceConfig) {
                            try {
                                refData = await this.resolveDataSource(refDataSourceConfig);
                            } catch (e) {
                                console.error(`Failed to resolve data_source for referenced component ${content}:`, e);
                            }
                        }
                        await refRenderer(bodyEl, refData, referencedComponent);
                    } else {
                        panelEl.innerHTML = `<div class="error">Unknown component type: ${referencedComponent.type}</div>`;
                    }
                } else {
                    // 普通字符串内容直接显示
                    panelEl.innerHTML = content;
                }
            } else {
                panelEl.innerHTML = '';
            }
        }

        // 标签切换事件 - 切换时触发 echarts resize
        headerEl.querySelectorAll('.tab-item').forEach(el => {
            el.addEventListener('click', () => {
                const key = el.dataset.tab;
                headerEl.querySelectorAll('.tab-item').forEach(t => {
                    t.style.color = t.dataset.tab === key ? '#00d4ff' : '#a0aec0';
                    t.style.borderBottomColor = t.dataset.tab === key ? '#00d4ff' : 'transparent';
                });
                contentEl.querySelectorAll('.tab-panel').forEach(p => {
                    p.style.display = p.dataset.tab === key ? 'block' : 'none';
                    // 切换到该面板时，触发 echarts resize
                    if (p.dataset.tab === key) {
                        const echartsContainer = p.querySelector('.echarts-container');
                        if (echartsContainer) {
                            const chart = echarts.getInstanceByDom(echartsContainer);
                            if (chart) {
                                setTimeout(() => chart.resize(), 100);
                            }
                        }
                    }
                });
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
