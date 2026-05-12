// API 配置
const API_URLS = {
    floodResult: 'http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx',
    rainProcess: 'http://10.20.2.153/api/basin/modelPlatf/model/modelRainArea/getByRsvr',
    stationInfo: '/proxy/mike11/station_info',
    mapLocation: '/proxy/map/location'
};

// 全流域模板只依赖方案ID获取结果。token 可选，用于部分受保护接口。
const DEFAULT_PARAMS = {
    planCode: 'model_20260127101007',
    token: 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjEzMzk1NTA0Njc5Mzk2MzkyOTksImFjY291bnQiOiJhZG1pbiIsInV1aWQiOiI1YTdlMjU1OC0zYmQwLTQ5NTMtYTNkMy0xY2NjZGVmOGY1MDkiLCJyZW1lbWJlck1lIjpmYWxzZSwiZXhwaXJhdGlvbkRhdGUiOjE3NzkxODE2ODYyMTgsImNhVG9rZW4iOm51bGwsIm90aGVycyI6bnVsbCwic3ViIjoiMTMzOTU1MDQ2NzkzOTYzOTI5OSIsImlhdCI6MTc3ODU3Njg4NiwiZXhwIjoxNzc5MTgxNjg2fQ.p0yWuyNq1lxVxBYyrczJie10K1d6N6OYHRkxSAmGGpt5IYYFD_megCprbqIgfc5YFmeM1rDwCFbKkoLFAfVJTw'
};

const state = {
    raw: null,
    reservoirs: [],
    reaches: [],
    detentions: [],
    activeType: 'reservoir',
    activeItem: null,
    chart: null,
    mapView: null,
    graphicsLayer: null,
    markerIndex: new Map(),
    locationIndex: new Map(),
    locationLoading: new Set(),
    stationInfoList: [],
    stationInfoByStcd: new Map(),
    stationInfoByName: new Map(),
    planName: ''
};

const TYPE_LABEL = {
    reservoir: '水库',
    reach: '河道',
    detention: '蓄滞洪区'
};

async function init() {
    bindTabs();
    renderLoading();
    initMap();

    try {
        const [floodData, stationInfoList, planName] = await Promise.all([
            fetchFloodResult(),
            fetchStationInfo(),
            fetchPlanName()
        ]);
        if (!floodData) throw new Error('未获取到方案结果');

        state.raw = floodData;
        state.stationInfoList = stationInfoList;
        state.planName = resolvePlanName(planName, floodData);
        buildStationInfoIndex(stationInfoList);
        buildCollections(floodData);
        renderSummary();
        renderFeatureList();
        selectInitialItem();
        const mapStatus = document.getElementById('mapStatus');
        if (mapStatus) mapStatus.textContent = '待定位';
        updateFeatureStatus();
    } catch (error) {
        console.error('全流域预报结果加载失败:', error);
        renderError(error.message);
    }
}

function bindTabs() {
    document.querySelectorAll('.tab-button').forEach((button) => {
        button.addEventListener('click', () => {
            state.activeType = button.dataset.type;
            document.querySelectorAll('.tab-button').forEach(b => b.classList.toggle('active', b === button));
            renderFeatureList();
            selectInitialItem();
        });
    });
}

function renderLoading() {
    const featureList = document.getElementById('featureList');
    if (featureList) {
        featureList.innerHTML = '<div class="loading-state">正在获取全流域洪水预报结果...</div>';
    }
    renderSummaryCards([
        { type: 'plan', title: '方案名称', value: '加载中' },
        { title: '水库预警', lines: [{ label: '超汛限', value: '--', unit: '座' }, { label: '超防洪高', value: '--', unit: '座' }] },
        { title: '河道预警', lines: [{ label: '超警戒', value: '--', unit: '处' }, { label: '超保证', value: '--', unit: '处' }] },
        { title: '蓄滞洪区预警', lines: [{ label: '启用', value: '--', unit: '处' }, { label: '未启用', value: '--', unit: '处' }] }
    ]);
}

function renderError(message) {
    const featureList = document.getElementById('featureList');
    if (featureList) {
        featureList.innerHTML = `<div class="empty-state">数据获取失败：${escapeHtml(message)}</div>`;
    }
    const chart = getChart();
    chart.setOption({
        backgroundColor: 'transparent',
        title: {
            text: '暂无可展示数据',
            subtext: message,
            left: 'center',
            top: 'center',
            textStyle: { color: '#e4eef6', fontSize: 18 },
            subtextStyle: { color: '#8ea8bb', fontSize: 13 }
        }
    }, true);
}

async function fetchFloodResult() {
    const isHistoryAutoPlan = DEFAULT_PARAMS.planCode.includes('_auto_');
    const requestType = isHistoryAutoPlan ? 'get_history_autoforcast_res' : 'get_tjdata_result';
    const url = `${API_URLS.floodResult}?request_type=${requestType}&request_pars=${encodeURIComponent(DEFAULT_PARAMS.planCode)}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error(`结果接口异常: ${response.status}`);
    return await response.json();
}

async function fetchStationInfo() {
    try {
        const headers = { 'Accept': '*/*' };
        if (DEFAULT_PARAMS.token) headers.Authorization = DEFAULT_PARAMS.token;
        const response = await fetch(API_URLS.stationInfo, { headers, cache: 'no-cache' });
        if (!response.ok) {
            console.warn(`站点信息接口异常: ${response.status}`);
            return [];
        }
        const result = await response.json();
        return Array.isArray(result) ? result : [];
    } catch (error) {
        console.warn('站点信息获取失败:', error);
        return [];
    }
}

async function fetchPlanName() {
    if (DEFAULT_PARAMS.planCode === 'model_auto') return '最新自动预报方案';

    try {
        const url = `${API_URLS.floodResult}?request_type=get_models&request_pars=wg_mike11`;
        const response = await fetch(url, { cache: 'no-cache' });
        if (!response.ok) return DEFAULT_PARAMS.planCode;

        const result = await response.json();
        const directPlanName = result?.[DEFAULT_PARAMS.planCode]?.plan_name;
        if (directPlanName) return directPlanName;

        const models = normalizeModelList(result);
        const match = models.find(model => {
            const code = pickFirst(model, [
                'PlanCode', 'planCode', 'plan_code', 'Plan_Code',
                'Code', 'code', 'ID', 'Id', 'id',
                'Model_Code', 'modelCode', 'model_code'
            ]);
            return String(code || '') === DEFAULT_PARAMS.planCode;
        });

        return match?.plan_name || DEFAULT_PARAMS.planCode;
    } catch (error) {
        console.warn('方案名称获取失败:', error);
        return DEFAULT_PARAMS.planCode;
    }
}

function normalizeModelList(value) {
    if (Array.isArray(value)) return value;
    if (!value || typeof value !== 'object') return [];

    const candidates = [
        value.data,
        value.result,
        value.rows,
        value.records,
        value.list,
        value.data?.records,
        value.data?.rows,
        value.data?.list,
        value.result?.records,
        value.result?.rows,
        value.result?.list
    ];

    for (const candidate of candidates) {
        if (Array.isArray(candidate)) return candidate;
    }

    return Object.entries(value)
        .filter(([, item]) => item && typeof item === 'object' && !Array.isArray(item))
        .map(([planCode, item]) => ({ plan_code: planCode, ...item }));
}

function resolvePlanName(candidate, floodData) {
    return candidate || DEFAULT_PARAMS.planCode;
}

async function fetchRainProcess(stcd) {
    if (!stcd) return [];

    const url = `${API_URLS.rainProcess}?planCode=${encodeURIComponent(DEFAULT_PARAMS.planCode)}&stcd=${encodeURIComponent(stcd)}`;
    try {
        const headers = { 'Accept': '*/*' };
        if (DEFAULT_PARAMS.token) headers.Authorization = DEFAULT_PARAMS.token;
        const response = await fetch(url, { method: 'GET', headers, mode: 'cors', cache: 'no-cache' });
        if (!response.ok) return [];
        const result = await response.json();
        if (result.success && result.data && result.data.t) {
            return result.data.t.map((time, index) => ({
                time,
                value: Number(result.data.v[index] || 0)
            }));
        }
    } catch (error) {
        console.warn('降雨过程获取失败:', error);
    }
    return [];
}

function buildCollections(raw) {
    const reservoirResult = asObject(raw.reservoir_result);
    const reachResult = asObject(raw.reachsection_result);
    const detentionResult = asObject(raw.floodblq_result);

    state.reservoirs = Object.entries(reservoirResult).map(([name, data]) => ({
        type: 'reservoir',
        name,
        stcd: data.Stcd || data.stcd || data.Code || '',
        stationInfo: findStationInfo(data.Stcd || data.stcd || data.Code || '', name),
        data
    })).sort((a, b) => num(b.data.Max_Level) - num(a.data.Max_Level));

    state.reaches = Object.entries(reachResult).map(([name, data]) => ({
        type: 'reach',
        name,
        stcd: data.Stcd || data.stcd || data.Code || '',
        stationInfo: findStationInfo(data.Stcd || data.stcd || data.Code || '', name),
        data
    })).sort((a, b) => num(b.data.Max_Discharge || b.data.Max_Qischarge || b.data.Max_Q) - num(a.data.Max_Discharge || a.data.Max_Qischarge || a.data.Max_Q));

    state.detentions = Object.entries(detentionResult).map(([name, data]) => ({
        type: 'detention',
        name: data.Name || name,
        stcd: data.Stcd || data.stcd || '',
        data
    })).sort((a, b) => num(b.data.Max_Volumn) - num(a.data.Max_Volumn));
}

function renderSummary() {
    const enabledDetentions = state.detentions.filter(item => isDetentionEnabled(item.data)).length;
    const disabledDetentions = state.detentions.length - enabledDetentions;
    const reservoirWarnings = calcReservoirWarnings();
    const reachWarnings = calcReachWarnings();
    renderSummaryCards([
        { type: 'plan', title: '方案名称', value: state.planName || DEFAULT_PARAMS.planCode },
        {
            title: '水库预警',
            lines: [
                { label: '超汛限', value: reservoirWarnings.overFloodLimit, unit: '座', level: reservoirWarnings.overFloodLimit ? 'warning' : '' },
                { label: '超防洪高', value: reservoirWarnings.overFloodHigh, unit: '座', level: reservoirWarnings.overFloodHigh ? 'danger' : '' }
            ]
        },
        {
            title: '河道预警',
            lines: [
                { label: '超警戒', value: reachWarnings.overWarning, unit: '处', level: reachWarnings.overWarning ? 'warning' : '' },
                { label: '超保证', value: reachWarnings.overGuarantee, unit: '处', level: reachWarnings.overGuarantee ? 'danger' : '' }
            ]
        },
        {
            title: '蓄滞洪区预警',
            lines: [
                { label: '启用', value: enabledDetentions, unit: '处', level: enabledDetentions ? 'warning' : '' },
                { label: '未启用', value: disabledDetentions, unit: '处' }
            ]
        }
    ]);

    const title = document.getElementById('pageTitle');
    if (title && state.raw?.result_desc) title.textContent = '全流域洪水预报结果';

}

function renderSummaryCards(items) {
    const summary = document.getElementById('summaryMetrics');
    if (!summary) return;

    summary.innerHTML = items.map(item => {
        if (item.type === 'plan') {
            return `
                <div class="summary-card plan">
                    <div class="label accent">${escapeHtml(item.title)}</div>
                    <div class="value" title="${escapeHtml(item.value)}">${escapeHtml(formatValue(item.value))}</div>
                </div>
            `;
        }

        return `
            <div class="summary-card">
                <div class="label accent">${escapeHtml(item.title)}</div>
                <div class="summary-lines">
                    ${(item.lines || []).map(line => `
                        <div class="summary-line ${escapeHtml(line.level || '')}">
                            <span class="line-label">${escapeHtml(line.label)}</span>
                            <span class="divider">|</span>
                            <span class="metric">${escapeHtml(formatValue(line.value))}<span class="unit">${escapeHtml(line.unit || '')}</span></span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }).join('');
}

function updateFeatureStatus() {
    const el = document.getElementById('featureStatus');
    if (!el) return;
    el.textContent = `${state.reservoirs.length}座水库 / ${state.reaches.length}处河道 / ${state.detentions.length}处蓄滞洪区`;
}

function renderFeatureList() {
    const featureList = document.getElementById('featureList');
    if (!featureList) return;

    const items = getCurrentItems();
    if (!items.length) {
        featureList.innerHTML = `<div class="empty-state">暂无${TYPE_LABEL[state.activeType]}预报结果</div>`;
        return;
    }

    featureList.innerHTML = items.map((item) => renderFeatureCard(item)).join('');
    featureList.querySelectorAll('.feature-card').forEach((card) => {
        card.addEventListener('click', () => {
            const item = items[Number(card.dataset.index)];
            selectItem(item);
        });
    });
}

function renderFeatureCard(item) {
    const index = getCurrentItems().indexOf(item);
    const active = state.activeItem === item ? ' active' : '';
    const metrics = getFeatureMetrics(item);

    return `
        <div class="feature-card${active}" data-index="${index}">
            <div class="feature-card-title">
                <div class="feature-name">${escapeHtml(item.name)}</div>
                <span class="feature-tag">${TYPE_LABEL[item.type]}</span>
            </div>
            <div class="feature-kpis">
                ${metrics.map(m => `
                    <div class="feature-kpi">
                        <span class="k">${escapeHtml(m.label)}</span>
                        <span class="v ${m.tone ? escapeHtml(m.tone) : ''}">${escapeHtml(formatValue(m.value))}${m.unit && m.value !== undefined && m.value !== null && m.value !== '' ? `<span class="unit">${escapeHtml(m.unit)}</span>` : ''}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

function getFeatureMetrics(item) {
    const d = item.data || {};
    if (item.type === 'reservoir') {
        return [
            { label: '最高水位', value: d.Max_Level, unit: 'm' },
            { label: '入库洪峰', value: d.Max_InQ, unit: 'm3/s' },
            { label: '峰现时间', value: formatShortTime(d.MaxInQ_Time || d.MaxQ_AtTime || d.MaxLevel_Time), unit: '' },
            { label: '警戒类型', value: getReservoirWarningType(item), unit: '', tone: getWarningToneClass(getReservoirWarningType(item)) }
        ];
    }
    if (item.type === 'reach') {
        return [
            { label: '最高水位', value: d.Max_Level || d.Max_Z, unit: 'm' },
            { label: '洪峰流量', value: d.Max_Discharge || d.Max_Qischarge || d.Max_Q, unit: 'm3/s' },
            { label: '峰现时间', value: formatShortTime(d.MaxQ_AtTime || d.MaxZ_Time || d.MaxLevel_Time), unit: '' },
            { label: '警戒类型', value: getReachWarningType(item), unit: '', tone: getWarningToneClass(getReachWarningType(item)) }
        ];
    }
    return [
        { label: '最高水位', value: d.Max_Level || '--', unit: d.Max_Level ? 'm' : '' },
        { label: '最大滞洪量', value: d.Max_Volumn, unit: '万m3' },
        { label: '启用时间', value: formatShortTime(d.Start_FloodTime), unit: '' },
        { label: '启用类型', value: isDetentionEnabled(d) ? '启用' : '未启用', unit: '', tone: getWarningToneClass(isDetentionEnabled(d) ? '启用' : '未启用') }
    ];
}

function getStatusClass(item) {
    if (item.type === 'reservoir') {
        const maxLevel = forecastLevel(item);
        const floodHigh = thresholdValue(item.stationInfo?.Level2 || item.data.Flood_High_Level);
        const floodLimit = thresholdValue(item.stationInfo?.Level1 || item.data.Flood_Limit_Level);
        if (floodHigh && maxLevel > floodHigh) return 'danger';
        if (floodLimit && maxLevel > floodLimit) return 'warning';
    }
    if (item.type === 'reach') {
        const maxLevel = forecastLevel(item);
        const guarantee = thresholdValue(item.stationInfo?.Level3 || item.data.Guarantee_Level || item.data.Level3);
        const warning = thresholdValue(item.stationInfo?.Level1 || item.data.Warning_Level || item.data.Level1);
        if (guarantee && maxLevel > guarantee) return 'danger';
        if (warning && maxLevel > warning) return 'warning';
    }
    if (item.type === 'detention' && isDetentionEnabled(item.data)) return 'warning';
    return '';
}

function getReservoirWarningType(item) {
    const maxLevel = forecastLevel(item);
    const floodHigh = thresholdValue(item.stationInfo?.Level2 || item.data.Flood_High_Level);
    const floodLimit = thresholdValue(item.stationInfo?.Level1 || item.data.Flood_Limit_Level);
    if (floodHigh && maxLevel > floodHigh) return '超防洪高';
    if (floodLimit && maxLevel > floodLimit) return '超汛限';
    return '正常';
}

function getReachWarningType(item) {
    const maxLevel = forecastLevel(item);
    const guarantee = thresholdValue(item.stationInfo?.Level3 || item.data.Guarantee_Level || item.data.Level3);
    const warning = thresholdValue(item.stationInfo?.Level1 || item.data.Warning_Level || item.data.Level1);
    if (guarantee && maxLevel > guarantee) return '超保证';
    if (warning && maxLevel > warning) return '超警戒';
    return '正常';
}

function selectInitialItem() {
    const items = getCurrentItems();
    selectItem(items[0] || null);
}

async function selectItem(item) {
    state.activeItem = item;
    renderFeatureList();
    renderDetailMetrics(item);
    focusMapMarker(item);
    locateSelectedItem(item);

    if (!item) {
        renderError('当前分类没有可展示对象');
        return;
    }

    const title = document.getElementById('chartTitle');
    const subtitle = document.getElementById('chartSubtitle');
    if (title) title.textContent = `${item.name}过程曲线`;
    if (subtitle) subtitle.textContent = TYPE_LABEL[item.type];

    const chart = getChart();
    chart.showLoading('default', {
        text: '正在绘制过程曲线...',
        color: '#22d3ee',
        textColor: '#8ea8bb',
        maskColor: 'rgba(8, 19, 31, 0.55)'
    });

    try {
        if (item.type === 'reservoir') {
            const rainData = await fetchRainProcess(item.stcd);
            renderReservoirChart(item.data, rainData);
        } else if (item.type === 'reach') {
            const rainData = await fetchRainProcess(item.stcd);
            renderReachChart(item.data, rainData);
        } else {
            renderDetentionChart(item.data);
        }
    } catch (error) {
        console.error('图表渲染失败:', error);
        renderError(error.message);
    } finally {
        chart.hideLoading();
    }
}

function renderDetailMetrics(item) {
    const container = document.getElementById('detailMetrics');
    if (!container) return;

    if (!item) {
        container.innerHTML = '';
        return;
    }

    let metrics;
    const d = item.data || {};
    if (item.type === 'reservoir') {
        metrics = [
            ['最高水位', d.Max_Level, 'm'],
            ['入库洪峰', d.Max_InQ, 'm3/s'],
            ['峰现时间', formatShortTime(d.MaxInQ_Time || d.MaxQ_AtTime || d.MaxLevel_Time), ''],
            ['警戒类型', getReservoirWarningType(item), '']
        ];
    } else if (item.type === 'reach') {
        metrics = [
            ['最高水位', d.Max_Level || d.Max_Z, 'm'],
            ['洪峰流量', d.Max_Discharge || d.Max_Qischarge || d.Max_Q, 'm3/s'],
            ['峰现时间', formatShortTime(d.MaxQ_AtTime || d.MaxZ_Time || d.MaxLevel_Time), ''],
            ['警戒类型', getReachWarningType(item), '']
        ];
    } else {
        metrics = [
            ['最高水位', d.Max_Level || '--', d.Max_Level ? 'm' : ''],
            ['最大滞洪量', d.Max_Volumn, '万m3'],
            ['启用时间', formatShortTime(d.Start_FloodTime), ''],
            ['启用类型', isDetentionEnabled(d) ? '启用' : '未启用', '']
        ];
    }

    container.innerHTML = metrics.map(([label, value, unit]) => `
        <div class="detail-chip">
            <span class="label accent">${escapeHtml(label)}</span>
            <span class="value ${escapeHtml(getWarningToneClass(value))}">${escapeHtml(formatValue(value))}${unit ? `<span class="unit">${escapeHtml(unit)}</span>` : ''}</span>
        </div>
    `).join('');
}

function renderReservoirChart(data, rainData) {
    const timeKeys = objectKeys(data.InQ_Dic || data.OutQ_Dic || data.Level_Dic);
    const inflowData = seriesFromMap(data.InQ_Dic, timeKeys);
    const outflowData = seriesFromMap(data.OutQ_Dic, timeKeys);
    const waterLevelData = seriesFromMap(data.Level_Dic, timeKeys);
    const processedRainData = rainSeries(rainData);

    const option = buildRainFlowLevelOption({
        legend: ['降雨量', '入库流量', '出库流量', '库水位', '汛限水位', '防洪高水位'],
        rainData: processedRainData,
        flowSeries: [
            { name: '入库流量', data: inflowData, color: '#fb7185' },
            { name: '出库流量', data: outflowData, color: '#4ade80' }
        ],
        levelSeries: [
            { name: '库水位', data: waterLevelData, color: '#22d3ee', fill: true }
        ],
        markLines: [
            { name: '汛限水位', value: getActiveThreshold('Level1', data.Flood_Limit_Level), color: '#fbbf24' },
            { name: '防洪高水位', value: getActiveThreshold('Level2', data.Flood_High_Level), color: '#fb7185', selected: false }
        ].filter(m => m.value !== undefined && m.value !== null && m.value !== '' && Number(m.value) > 0)
    });

    getChart().setOption(option, true);
}

function renderReachChart(data, rainData) {
    const zMap = data.Level_Dic || data.Z_Dic || {};
    const qMap = data.Discharge_Dic || data.Q_Dic || data.InQ_Dic || data.OutQ_Dic || {};
    const timeKeys = objectKeys(zMap).length ? objectKeys(zMap) : objectKeys(qMap);
    const waterLevelData = seriesFromMap(zMap, timeKeys);
    const flowData = seriesFromMap(qMap, timeKeys);
    const processedRainData = rainSeries(rainData);

    const option = buildRainFlowLevelOption({
        legend: ['降雨量', '水位', '流量', '警戒水位', '保证水位'],
        rainData: processedRainData,
        flowSeries: [
            { name: '流量', data: flowData, color: '#4ade80' }
        ],
        levelSeries: [
            { name: '水位', data: waterLevelData, color: '#22d3ee', fill: true }
        ],
        markLines: [
            { name: '警戒水位', value: getActiveThreshold('Level1', data.Warning_Level || data.Level1), color: '#fbbf24' },
            { name: '保证水位', value: getActiveThreshold('Level3', data.Guarantee_Level || data.Level3), color: '#fb7185', selected: false }
        ].filter(m => m.value !== undefined && m.value !== null && m.value !== '' && Number(m.value) > 0)
    });

    getChart().setOption(option, true);
}

function renderDetentionChart(data) {
    const levelMap = data.Level_Dic || {};
    const volumeMap = data.Vomumn_Dic || data.Volumn_Dic || data.Volume_Dic || {};
    const areaMap = data.Area_Dic || {};
    const inQMap = data.Total_InQ_Dic || flattenGateMap(data.InQ_Dic);
    const outQMap = data.Total_OutQ_Dic || flattenGateMap(data.OutQ_Dic);
    const stateMap = data.Xzhq_State_Dic || {};
    const timeKeys = uniqueSortedKeys([levelMap, volumeMap, areaMap, inQMap, outQMap, stateMap]);

    const levelData = seriesFromMap(levelMap, timeKeys);
    const volumeData = seriesFromMap(volumeMap, timeKeys);
    const areaData = seriesFromMap(areaMap, timeKeys);
    const inQData = seriesFromMap(inQMap, timeKeys);
    const outQData = seriesFromMap(outQMap, timeKeys);
    const stateData = stateSeriesFromMap(stateMap, timeKeys);

    const allTimes = [
        ...levelData,
        ...volumeData,
        ...areaData,
        ...inQData,
        ...outQData
    ].map(d => d[0]);

    const minTime = allTimes.length ? Math.min(...allTimes) : undefined;
    const maxTime = allTimes.length ? Math.max(...allTimes) : undefined;
    const flowRange = calcAxisRange([inQData, outQData], 50, 10);
    const levelRange = calcAxisRange([levelData], 1, 1);
    const volumeRange = calcAxisRange([volumeData], 100, 50);

    getChart().setOption({
        backgroundColor: 'transparent',
        legend: {
            data: ['启用状态', '总进洪流量', '总出洪流量', '滞洪水位', '滞洪量', '淹没面积'],
            top: 8,
            right: 20,
            textStyle: { color: '#8ea8bb', fontSize: 12 },
            selected: { '淹没面积': false }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            backgroundColor: 'rgba(8, 19, 31, 0.94)',
            borderColor: 'rgba(34, 211, 238, 0.36)',
            textStyle: { color: '#e4eef6' }
        },
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        grid: [
            { top: 42, height: 76, left: 70, right: 86 },
            { top: 162, bottom: 62, left: 70, right: 86 }
        ],
        xAxis: [
            {
                type: 'time',
                gridIndex: 0,
                min: minTime,
                max: maxTime,
                axisLabel: { show: false },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } }
            },
            {
                type: 'time',
                gridIndex: 1,
                min: minTime,
                max: maxTime,
                axisLabel: { color: '#c0c8d0', fontSize: 12, formatter: '{MM}/{dd}\n{HH}:{mm}' },
                axisLine: { lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } }
            }
        ],
        yAxis: [
            {
                type: 'value',
                name: '启用',
                gridIndex: 0,
                min: 0,
                max: 1,
                interval: 1,
                axisLabel: { color: '#c0c8d0', formatter: value => value ? '启用' : '未启用' },
                axisLine: { lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: false }
            },
            {
                type: 'value',
                name: '流量(m3/s)',
                gridIndex: 1,
                min: flowRange.min,
                max: flowRange.max,
                axisLabel: { color: '#c0c8d0', fontSize: 12 },
                axisLine: { lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } }
            },
            {
                type: 'value',
                name: '水位(m)',
                gridIndex: 1,
                position: 'right',
                min: levelRange.min,
                max: levelRange.max,
                axisLabel: { color: '#c0c8d0', fontSize: 12 },
                axisLine: { lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: false }
            },
            {
                type: 'value',
                name: '量/面积',
                gridIndex: 1,
                position: 'right',
                offset: 48,
                min: 0,
                max: Math.max(volumeRange.max, calcAxisRange([areaData], 100, 50).max),
                axisLabel: { color: '#c0c8d0', fontSize: 12 },
                axisLine: { lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: false }
            }
        ],
        series: [
            { name: '启用状态', type: 'line', xAxisIndex: 0, yAxisIndex: 0, data: stateData, step: 'end', symbol: 'none', lineStyle: { width: 2, color: '#fbbf24' }, areaStyle: { color: 'rgba(251,191,36,0.22)' } },
            { name: '总进洪流量', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: inQData, smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#fb7185' } },
            { name: '总出洪流量', type: 'line', xAxisIndex: 1, yAxisIndex: 1, data: outQData, smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#4ade80' } },
            { name: '滞洪水位', type: 'line', xAxisIndex: 1, yAxisIndex: 2, data: levelData, smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#22d3ee' }, areaStyle: { color: 'rgba(34,211,238,0.14)' } },
            { name: '滞洪量', type: 'line', xAxisIndex: 1, yAxisIndex: 3, data: volumeData, smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#60a5fa' } },
            { name: '淹没面积', type: 'line', xAxisIndex: 1, yAxisIndex: 3, data: areaData, smooth: true, symbol: 'none', lineStyle: { width: 2, color: '#a78bfa' } }
        ]
    }, true);
}

function buildRainFlowLevelOption({ legend, rainData, flowSeries, levelSeries, markLines }) {
    const allTimestamps = [
        ...rainData,
        ...flowSeries.flatMap(s => s.data),
        ...levelSeries.flatMap(s => s.data)
    ].map(d => d[0]);
    const minTime = allTimestamps.length ? Math.min(...allTimestamps) : undefined;
    const maxTime = allTimestamps.length ? Math.max(...allTimestamps) : undefined;
    const rainRange = calcAxisRange([rainData], 10, 5);
    const flowRange = calcAxisRange(flowSeries.map(s => s.data), 50, 10);
    const levelRange = calcAxisRange(levelSeries.map(s => s.data), 5, 2, markLines.map(m => num(m.value)).filter(Boolean));

    const selected = {};
    markLines.forEach(m => {
        if (m.selected === false) selected[m.name] = false;
    });

    return {
        backgroundColor: 'transparent',
        legend: {
            data: legend,
            top: 8,
            right: 20,
            textStyle: { color: '#8ea8bb', fontSize: 12 },
            itemGap: 14,
            selected
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            backgroundColor: 'rgba(8, 19, 31, 0.94)',
            borderColor: 'rgba(34, 211, 238, 0.36)',
            textStyle: { color: '#e4eef6' }
        },
        axisPointer: { link: [{ xAxisIndex: 'all' }], label: { backgroundColor: '#334155' } },
        grid: [
            { top: 42, height: 104, left: 70, right: 76 },
            { top: 200, bottom: 58, left: 70, right: 76 }
        ],
        xAxis: [
            { type: 'time', gridIndex: 0, min: minTime, max: maxTime, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } } },
            { type: 'time', gridIndex: 1, min: minTime, max: maxTime, axisLabel: { color: '#c0c8d0', fontSize: 12, formatter: '{MM}/{dd}\n{HH}:{mm}' }, axisLine: { lineStyle: { color: '#c0c8d0' } }, splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } } }
        ],
        yAxis: [
            { type: 'value', name: '降雨(mm)', gridIndex: 0, inverse: true, min: 0, max: rainRange.max, nameGap: 28, nameLocation: 'middle', axisLabel: { color: '#c0c8d0', fontSize: 12 }, axisLine: { show: true, lineStyle: { color: '#c0c8d0' } }, splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } } },
            { type: 'value', name: '流量(m3/s)', gridIndex: 1, min: flowRange.min, max: flowRange.max, nameGap: 34, nameLocation: 'middle', axisLabel: { color: '#c0c8d0', fontSize: 12 }, axisLine: { show: true, lineStyle: { color: '#c0c8d0' } }, splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } } },
            { type: 'value', name: '水位(m)', gridIndex: 1, position: 'right', min: levelRange.min, max: levelRange.max, axisLabel: { color: '#c0c8d0', fontSize: 12 }, axisLine: { show: true, lineStyle: { color: '#c0c8d0' } }, splitLine: { show: false } }
        ],
        series: [
            {
                name: '降雨量',
                type: 'bar',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: rainData,
                itemStyle: { color: '#5470c6' },
                markPoint: peakMark(rainData, '#fbbf24', 'mm')
            },
            ...flowSeries.map(s => ({
                name: s.name,
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: s.data,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 2, color: s.color },
                itemStyle: { color: s.color },
                markPoint: peakMark(s.data, s.color, 'm3/s')
            })),
            ...levelSeries.map(s => ({
                name: s.name,
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: s.data,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 2, color: s.color },
                itemStyle: { color: s.color },
                areaStyle: s.fill ? { color: 'rgba(34,211,238,0.14)' } : undefined,
                markPoint: peakMark(s.data, s.color, 'm')
            })),
            ...markLines.map(m => ({
                name: m.name,
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: [],
                itemStyle: { color: m.color },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{
                        yAxis: Number(m.value),
                        lineStyle: { color: m.color, width: 1, type: 'dashed' },
                        label: { show: true, position: 'insideEndTop', formatter: `${m.name} ${m.value}m`, color: m.color }
                    }]
                }
            }))
        ]
    };
}

function peakMark(data, color, unit) {
    if (!data || !data.length) return {};
    const peak = data.reduce((best, item) => Number(item[1]) > Number(best[1]) ? item : best, data[0]);
    return {
        data: [{ coord: peak, value: `${formatNumber(peak[1])} ${unit}` }],
        symbol: 'circle',
        symbolSize: 7,
        itemStyle: { color },
        label: {
            show: true,
            position: 'top',
            color,
            fontWeight: 'bold',
            fontSize: 12,
            textBorderColor: 'rgba(4, 12, 20, 0.95)',
            textBorderWidth: 3,
            textShadowColor: 'rgba(0, 0, 0, 0.75)',
            textShadowBlur: 4
        }
    };
}

function initMap() {
    require([
        'esri/WebMap',
        'esri/views/MapView',
        'esri/portal/Portal',
        'esri/layers/GraphicsLayer'
    ], function (WebMap, MapView, Portal, GraphicsLayer) {
        const portal = new Portal({
            url: 'https://map.slt.henan.gov.cn/geoscene'
        });

        const webmap = new WebMap({
            portalItem: {
                id: '0217daabff7a4b45a0cca3f975efa7f3',
                portal
            }
        });

        const graphicsLayer = new GraphicsLayer({ title: '预报对象' });
        webmap.add(graphicsLayer);
        state.graphicsLayer = graphicsLayer;

        state.mapView = new MapView({
            container: 'viewDiv',
            map: webmap,
            center: [114.057818, 35.826884],
            zoom: 9
        });

        state.mapView.when(() => {
            const status = document.getElementById('mapStatus');
            if (status) status.textContent = '已加载';
            locateSelectedItem(state.activeItem);
            state.mapView.on('click', async (event) => {
                const hit = await state.mapView.hitTest(event);
                const result = hit.results.find(r => r.graphic?.attributes?.itemKey);
                if (result) {
                    const item = findItemByKey(result.graphic.attributes.itemKey);
                    if (item) {
                        state.activeType = item.type;
                        document.querySelectorAll('.tab-button').forEach(b => b.classList.toggle('active', b.dataset.type === item.type));
                        selectItem(item);
                    }
                }
            });
        });
    });
}

async function loadMapMarkers() {
    if (!state.graphicsLayer) {
        setTimeout(loadMapMarkers, 500);
        return;
    }

    const candidates = [
        ...state.reservoirs.slice(0, 40),
        ...state.reaches.slice(0, 60)
    ].filter(item => item.stcd);

    for (const item of candidates) {
        const refTable = item.type === 'reservoir' ? 'geo_res_base' : 'geo_st_base';
        const location = await fetchMapLocation(refTable, item.stcd);
        if (location) addMapMarker(item, location);
    }

    const status = document.getElementById('mapStatus');
    if (status) status.textContent = `${state.markerIndex.size}个对象`;
}

async function fetchMapLocation(refTable, stcd) {
    try {
        const params = new URLSearchParams({ ref_table: refTable, stcd });
        const headers = { 'Accept': '*/*' };
        if (DEFAULT_PARAMS.token) headers.Authorization = DEFAULT_PARAMS.token;
        const response = await fetch(`${API_URLS.mapLocation}?${params}`, { headers, cache: 'no-cache' });
        if (!response.ok) return null;
        const result = await response.json();
        if (result.success && result.longitude && result.latitude) {
            return { longitude: Number(result.longitude), latitude: Number(result.latitude) };
        }
    } catch (error) {
        console.warn('坐标获取失败:', stcd, error);
    }
    return null;
}

function addMapMarker(item, location) {
    require(['esri/Graphic'], function (Graphic) {
        const color = item.type === 'reservoir' ? [34, 211, 238, 0.9] : [74, 222, 128, 0.9];
        const graphic = new Graphic({
            geometry: {
                type: 'point',
                longitude: location.longitude,
                latitude: location.latitude
            },
            symbol: {
                type: 'simple-marker',
                style: item.type === 'reservoir' ? 'circle' : 'diamond',
                color,
                size: item === state.activeItem ? 14 : 10,
                outline: { color: [255, 255, 255, 0.9], width: 1 }
            },
            attributes: {
                itemKey: makeItemKey(item),
                name: item.name,
                type: item.type
            },
            popupTemplate: {
                title: item.name,
                content: `${TYPE_LABEL[item.type]}洪水预报结果`
            }
        });
        state.graphicsLayer.add(graphic);
        state.markerIndex.set(makeItemKey(item), graphic);
        focusMapMarker(state.activeItem, false);
    });
}

function focusMapMarker(item, goTo = true) {
    if (!item || !state.mapView) return;
    const key = makeItemKey(item);
    const graphic = state.markerIndex.get(key);
    state.markerIndex.forEach((g) => {
        const markerItem = findItemByKey(g.attributes.itemKey);
        const baseColor = markerItem?.type === 'reservoir' ? [34, 211, 238, 0.9] : [74, 222, 128, 0.9];
        g.symbol = { ...g.symbol, size: g === graphic ? 15 : 10, color: baseColor };
    });
    if (graphic && goTo) state.mapView.goTo({ target: graphic.geometry, zoom: 12 }).catch(() => {});
}

async function locateSelectedItem(item) {
    if (!item || item.type === 'detention' || !item.stcd || !state.mapView) return;

    const key = makeItemKey(item);
    if (state.markerIndex.has(key)) {
        focusMapMarker(item);
        return;
    }
    if (state.locationLoading.has(key)) return;

    state.locationLoading.add(key);
    try {
        const refTable = item.type === 'reservoir' ? 'geo_res_base' : 'geo_st_base';
        const location = state.locationIndex.get(key) || await fetchMapLocation(refTable, item.stcd);
        if (!location) return;

        state.locationIndex.set(key, location);
        addMapMarker(item, location);
        if (state.mapView) {
            state.mapView.goTo({ center: [location.longitude, location.latitude], zoom: 12 }).catch(() => {});
        }
    } finally {
        state.locationLoading.delete(key);
    }
}

function getCurrentItems() {
    if (state.activeType === 'reservoir') return state.reservoirs;
    if (state.activeType === 'reach') return state.reaches;
    return state.detentions;
}

function makeItemKey(item) {
    return `${item.type}:${item.name}`;
}

function findItemByKey(key) {
    return [...state.reservoirs, ...state.reaches, ...state.detentions].find(item => makeItemKey(item) === key);
}

function buildStationInfoIndex(list) {
    state.stationInfoByStcd = new Map();
    state.stationInfoByName = new Map();

    (Array.isArray(list) ? list : []).forEach(info => {
        const stcd = String(info?.Stcd || info?.stcd || '').trim();
        const name = normalizeName(info?.Name || info?.name || '');
        if (stcd) state.stationInfoByStcd.set(stcd, info);
        if (name) state.stationInfoByName.set(name, info);
    });
}

function findStationInfo(stcd, name) {
    const key = String(stcd || '').trim();
    if (key && state.stationInfoByStcd.has(key)) return state.stationInfoByStcd.get(key);

    const normalizedName = normalizeName(name);
    if (normalizedName && state.stationInfoByName.has(normalizedName)) return state.stationInfoByName.get(normalizedName);

    return null;
}

function calcReservoirWarnings() {
    return state.reservoirs.reduce((acc, item) => {
        const maxLevel = forecastLevel(item);
        const floodLimit = thresholdValue(item.stationInfo?.Level1 || item.data.Flood_Limit_Level);
        const floodHigh = thresholdValue(item.stationInfo?.Level2 || item.data.Flood_High_Level);

        if (floodLimit && maxLevel > floodLimit) acc.overFloodLimit += 1;
        if (floodHigh && maxLevel > floodHigh) acc.overFloodHigh += 1;
        return acc;
    }, { overFloodLimit: 0, overFloodHigh: 0 });
}

function calcReachWarnings() {
    return state.reaches.reduce((acc, item) => {
        const maxLevel = forecastLevel(item);
        const warning = thresholdValue(item.stationInfo?.Level1 || item.data.Warning_Level || item.data.Level1);
        const guarantee = thresholdValue(item.stationInfo?.Level3 || item.data.Guarantee_Level || item.data.Level3);

        if (warning && maxLevel > warning) acc.overWarning += 1;
        if (guarantee && maxLevel > guarantee) acc.overGuarantee += 1;
        return acc;
    }, { overWarning: 0, overGuarantee: 0 });
}

function getActiveThreshold(field, fallback) {
    const info = state.activeItem?.stationInfo || {};
    return thresholdValue(info[field] || fallback);
}

function thresholdValue(value) {
    const n = Number(value);
    return Number.isFinite(n) && n > 0 ? n : null;
}

function getWarningToneClass(value) {
    if (value === '超防洪高' || value === '超保证' || value === '启用') return 'tone-orange';
    if (value === '超汛限' || value === '超警戒') return 'tone-yellow';
    return 'tone-normal';
}

function forecastLevel(item) {
    return num(item?.data?.Max_Level || item?.data?.Max_Z);
}

function normalizeName(value) {
    return String(value || '').replace(/[（(].*?[）)]/g, '').replace(/\s+/g, '').trim();
}

function pickFirst(source, keys) {
    if (!source) return '';
    for (const key of keys) {
        const value = source[key];
        if (value !== undefined && value !== null && value !== '') return value;
    }
    return '';
}

function getChart() {
    if (!state.chart) {
        state.chart = echarts.init(document.getElementById('chartDiv'), null, { renderer: 'svg' });
        window.addEventListener('resize', () => state.chart.resize());
    }
    return state.chart;
}

function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function objectKeys(map) {
    return Object.keys(asObject(map)).filter(key => key !== '...').sort((a, b) => new Date(a) - new Date(b));
}

function uniqueSortedKeys(maps) {
    return [...new Set(maps.flatMap(map => objectKeys(map)))].sort((a, b) => new Date(a) - new Date(b));
}

function seriesFromMap(map, keys) {
    const source = asObject(map);
    return (keys || objectKeys(source))
        .filter(t => source[t] !== undefined && source[t] !== null && source[t] !== '')
        .map(t => [new Date(t).getTime(), Number(source[t])])
        .filter(d => !Number.isNaN(d[0]) && !Number.isNaN(d[1]));
}

function rainSeries(rainData) {
    return Array.isArray(rainData)
        ? rainData.map(d => [new Date(d.time).getTime(), Number(d.value)]).filter(d => !Number.isNaN(d[0]) && !Number.isNaN(d[1]))
        : [];
}

function flattenGateMap(value) {
    if (!value || typeof value !== 'object') return {};
    const totals = {};
    Object.values(value).forEach(series => {
        if (!series || typeof series !== 'object') return;
        Object.entries(series).forEach(([time, val]) => {
            if (time === '...') return;
            totals[time] = (totals[time] || 0) + Number(val || 0);
        });
    });
    return totals;
}

function stateSeriesFromMap(map, keys) {
    const source = asObject(map);
    return (keys || objectKeys(source)).map(t => {
        const value = source[t];
        const enabled = typeof value === 'string' ? !value.includes('未') : Boolean(value);
        return [new Date(t).getTime(), enabled ? 1 : 0];
    }).filter(d => !Number.isNaN(d[0]));
}

function calcAxisRange(dataList, interval, padding = 1, extraValues = []) {
    const values = [
        ...dataList.flatMap(list => (list || []).map(d => Number(d[1]))),
        ...extraValues.map(Number)
    ].filter(v => !Number.isNaN(v));
    if (!values.length) return { min: 0, max: interval };
    const min = Math.min(...values);
    const max = Math.max(...values);
    return {
        min: Math.floor(min / interval) * interval,
        max: Math.ceil((max + padding) / interval) * interval
    };
}

function isDetentionEnabled(data) {
    const value = data?.Xzhq_State;
    if (typeof value === 'string') return !value.includes('未');
    return Boolean(value);
}

function num(value) {
    const n = Number(value);
    return Number.isNaN(n) ? 0 : n;
}

function formatValue(value) {
    if (value === undefined || value === null || value === '') return '--';
    if (typeof value === 'number') return formatNumber(value);
    return String(value);
}

function formatNumber(value) {
    const n = Number(value);
    if (Number.isNaN(n)) return value;
    if (Math.abs(n) >= 1000) return n.toFixed(0);
    if (Math.abs(n) >= 100) return n.toFixed(1);
    return n.toFixed(2).replace(/\.?0+$/, '');
}

function formatShortTime(timeStr) {
    if (!timeStr) return '--';
    const date = new Date(String(timeStr).replace(/\//g, '-'));
    if (Number.isNaN(date.getTime())) return timeStr;
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    return `${m}/${d} ${h}:${min}`;
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }[char]));
}

init();
