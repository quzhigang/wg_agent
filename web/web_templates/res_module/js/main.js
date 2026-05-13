
// API 配置
const API_URLS = {
    floodResult: 'http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx',
    rainProcess: 'http://10.20.2.153/api/basin/modelPlatf/model/modelRainArea/getByRsvr',
    currentStatus: 'http://10.20.2.153/api/basin/rwdb/rsvr/last',
    mapLocation: '/proxy/map/location',
    reservoirProcess: '/proxy/hydro/reservoir_process'
};

// 本模板所需参数，包括方案名称、水库名称、水库stcd和认证Token
const DEFAULT_PARAMS = {
    planCode: 'model_20260513135722',
    stcd: '31005650',
    reservoirName: '盘石头水库', // 统一定义水库名称
    token: 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjEzMzk1NTA0Njc5Mzk2MzkyOTksImFjY291bnQiOiJhZG1pbiIsInV1aWQiOiJjNTZhMmVmMS1iOTlmLTQ0MzItODhmZi05ODc5ODk0ODY2ZDMiLCJyZW1lbWJlck1lIjpmYWxzZSwiZXhwaXJhdGlvbkRhdGUiOjE3NzkyNTYyOTI2NzUsImNhVG9rZW4iOm51bGwsIm90aGVycyI6bnVsbCwic3ViIjoiMTMzOTU1MDQ2NzkzOTYzOTI5OSIsImlhdCI6MTc3ODY1MTQ5MiwiZXhwIjoxNzc5MjU2MjkyfQ.6HbLHqMgFWE_ccSTKNcY5MbwZQXYQboSAhXs9OMluCdKN1wxraVXGGUiW4XD6CCE2yOm4-XNKx5KwJBAzRq6Cg' // 认证Token
};

// 主入口函数
async function init() {
    updateTime();
    setInterval(updateTime, 1000);

    const conclusionTextDom = document.getElementById('conclusionText');

    try {
        if (conclusionTextDom) {
            conclusionTextDom.innerText = "正在获取实时预报数据...";
        }

        // 全部采用 API 获取
        const [floodData, rainData, currentStatus] = await Promise.all([
            fetchFloodResult(),
            fetchRainProcess(),
            fetchCurrentStatus()
        ]);

        if (floodData) {
            await processAllData(floodData, rainData, currentStatus);
        } else {
            throw new Error("未能获取洪水结果数据");
        }
    } catch (error) {
        console.error("数据加载错误:", error);
        if (conclusionTextDom) {
            conclusionTextDom.innerText = "数据获取失败，请检查网络或 API 服务。";
        }
    }

    // 获取水库坐标用于地图定位
    const location = await fetchReservoirLocation();
    initMap(location);
}

/**
 * 获取洪水预报结果
 */
async function fetchFloodResult() {
    // 判断是否为历史自动预报方案（方案ID包含"_auto_"字符串）
    const isHistoryAutoPlan = DEFAULT_PARAMS.planCode.includes('_auto_');

    let url;
    if (isHistoryAutoPlan) {
        // 历史自动预报使用 get_history_autoforcast_res 接口
        url = `${API_URLS.floodResult}?request_type=get_history_autoforcast_res&request_pars=${DEFAULT_PARAMS.planCode}`;
    } else {
        // 自动预报、人工预报使用 get_tjdata_result 接口
        url = `${API_URLS.floodResult}?request_type=get_tjdata_result&request_pars=${DEFAULT_PARAMS.planCode}`;
    }

    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP 错误! 状态码: ${response.status}`);
    return await response.json();
}

/**
 * 获取降雨过程，附带认证 Token
 */
async function fetchRainProcess() {
    const url = `${API_URLS.rainProcess}?planCode=${DEFAULT_PARAMS.planCode}&stcd=${DEFAULT_PARAMS.stcd}`;
    try {
        const headers = {
            'Accept': '*/*'
        };

        if (DEFAULT_PARAMS.token) {
            // 根据成功案例，这里不需要加 "Bearer " 前缀，直接发送纯 Token
            headers['Authorization'] = DEFAULT_PARAMS.token;
        }

        const response = await fetch(url, {
            method: 'GET',
            headers: headers,
            mode: 'cors',
            cache: 'no-cache'
        });

        if (!response.ok) {
            console.error(`降雨接口响应异常: ${response.status} ${response.statusText}`);
            return [];
        }

        const result = await response.json();
        if (result.success && result.data && result.data.t) {
            // 将 t (时间数组) 和 v (值数组) 组合成 [{time, value}, ...] 格式
            return result.data.t.map((time, index) => ({
                time: time,
                value: parseFloat(result.data.v[index] || 0)
            }));
        }
        return [];
    } catch (e) {
        console.warn("降雨接口请求失败:", e);
        return [];
    }
}

function isLatestAutoForecast() {
    return DEFAULT_PARAMS.planCode === 'model_auto';
}

async function fetchObservedProcess(forecastStartTime) {
    if (!isLatestAutoForecast() || !DEFAULT_PARAMS.stcd || !forecastStartTime) return [];

    const startTimestamp = toTimestamp(forecastStartTime);
    if (!Number.isFinite(startTimestamp)) return [];

    const params = new URLSearchParams({
        stcd: DEFAULT_PARAMS.stcd,
        start_time: formatDateTime(startTimestamp - 48 * 60 * 60 * 1000),
        end_time: formatDateTime(startTimestamp)
    });

    try {
        const headers = { 'Accept': '*/*' };
        if (DEFAULT_PARAMS.token) headers.Authorization = DEFAULT_PARAMS.token;
        const response = await fetch(`${API_URLS.reservoirProcess}?${params}`, { headers, cache: 'no-cache' });
        if (!response.ok) return [];
        const result = await response.json();
        return extractProcessRows(result)
            .map(row => normalizeObservedReservoirRow(row))
            .filter(row => row.time && Number.isFinite(row.timestamp) && row.timestamp <= startTimestamp)
            .sort((a, b) => a.timestamp - b.timestamp);
    } catch (error) {
        console.warn("获取水库实测过程失败:", error);
        return [];
    }
}

/**
 * 获取最新实时水情信息
 */
async function fetchCurrentStatus() {
    const url = `${API_URLS.currentStatus}?stcd=${DEFAULT_PARAMS.stcd}`;
    try {
        const headers = { 'Accept': '*/*' };
        if (DEFAULT_PARAMS.token) {
            headers['Authorization'] = DEFAULT_PARAMS.token;
        }
        const response = await fetch(url, { headers });
        if (!response.ok) return null;
        const result = await response.json();
        return (result.success && result.data && result.data.length > 0) ? result.data[0] : null;
    } catch (e) {
        console.warn("获取实时水情失败:", e);
        return null;
    }
}

/**
 * 获取水库坐标信息
 * 通过代理接口根据 stcd 查询水库的空间坐标
 * @returns {Promise<{longitude: number, latitude: number}|null>} 经纬度坐标或null
 */
async function fetchReservoirLocation() {
    try {
        const params = new URLSearchParams({
            'ref_table': 'geo_res_base',
            'stcd': DEFAULT_PARAMS.stcd
        });

        const headers = { 'Accept': '*/*' };
        if (DEFAULT_PARAMS.token) {
            headers['Authorization'] = DEFAULT_PARAMS.token;
        }

        const response = await fetch(`${API_URLS.mapLocation}?${params}`, {
            method: 'GET',
            headers: headers,
            cache: 'no-cache'
        });

        if (!response.ok) {
            console.warn("获取水库坐标接口响应异常:", response.status);
            return null;
        }

        const result = await response.json();
        if (result.success && result.longitude && result.latitude) {
            console.log(`获取到水库坐标: 经度=${result.longitude}, 纬度=${result.latitude}`);
            return { longitude: result.longitude, latitude: result.latitude };
        }

        console.warn("未找到水库坐标数据:", result.message);
        return null;
    } catch (e) {
        console.warn("获取水库坐标失败:", e);
        return null;
    }
}

/**
 * 处理并展示所有数据
 */
async function processAllData(floodRaw, rainData, currentStatus) {
    const reservoirName = DEFAULT_PARAMS.reservoirName;

    // 动态更新页面标题
    const titleDom = document.getElementById('conclusionTitle');
    if (titleDom) {
        titleDom.innerText = `${reservoirName}洪水预报结果`;
    }

    if (!floodRaw.reservoir_result || !floodRaw.reservoir_result[reservoirName]) {
        console.error(`未找到 ${reservoirName} 的数据。`);
        return;
    }
    const reservoirData = floodRaw.reservoir_result[reservoirName];
    const description = floodRaw.result_desc || "";
    const observedData = await fetchObservedProcess(getForecastStartTime(reservoirData));

    renderChart(reservoirData, rainData, observedData);
    renderConclusion(reservoirData, description, currentStatus);
}

/**
 * 更新当前显示时间
 */
function updateTime() {
    const now = new Date();
    const timeString = now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
    const timeDiv = document.getElementById('currentTime');
    if (timeDiv) {
        timeDiv.innerText = `当前时间: ${timeString}`;
    }
}

/**
 * 渲染图表
 */
function renderChart(data, rainData, observedData = []) {
    const chartDom = document.getElementById('chartDiv');
    if (!chartDom) return;

    const myChart = echarts.init(chartDom, null, { renderer: 'svg' });

    // 1. 处理水库数据 (流量, 水位)
    const timeKeys = objectKeys(data.InQ_Dic || data.OutQ_Dic || data.Level_Dic);
    const inflowData = seriesFromMap(data.InQ_Dic, timeKeys);
    const outflowData = seriesFromMap(data.OutQ_Dic, timeKeys);
    const waterLevelData = seriesFromMap(data.Level_Dic, timeKeys);
    const forecastStartTime = getForecastStartTime(data);
    const useObservedSplit = isLatestAutoForecast() && observedData.length > 0 && forecastStartTime;
    const observedSeries = useObservedSplit ? buildObservedReservoirSeries(observedData) : null;
    const flowSeries = [
        ...splitForecastSeries({ name: '入库流量', data: inflowData, observedData: observedSeries?.inflow, color: '#fb7185' }),
        ...splitForecastSeries({ name: '出库流量', data: outflowData, observedData: observedSeries?.outflow, color: '#4ade80' })
    ];
    const levelSeries = splitForecastSeries({ name: '库水位', data: waterLevelData, observedData: observedSeries?.level, color: '#00d4ff', fill: true });

    // 2. 处理降雨数据
    let processedRainData = [];
    if (rainData && Array.isArray(rainData)) {
        processedRainData = rainData.map(d => [toTimestamp(d.time), d.value]).filter(d => Number.isFinite(d[0]) && Number.isFinite(Number(d[1])));
    }

    // 3. 计算统一的时间范围（并集）
    const allTimestamps = [
        ...flowSeries.flatMap(s => s.data.map(d => d[0])),
        ...levelSeries.flatMap(s => s.data.map(d => d[0])),
        ...processedRainData.map(d => d[0]),
        ...(useObservedSplit ? [toTimestamp(forecastStartTime)] : [])
    ];

    let minTime = undefined;
    let maxTime = undefined;

    if (allTimestamps.length > 0) {
        minTime = Math.min(...allTimestamps);
        maxTime = Math.max(...allTimestamps);
    }

    // 计算轴范围
    const calcAxisRange = (dataList, interval, padding = 1) => {
        const values = dataList.flatMap(list => list.map(d => d[1])).filter(v => !isNaN(v));
        if (values.length === 0) return { min: 0, max: interval };
        const min = Math.min(...values);
        const max = Math.max(...values);
        return {
            min: Math.floor(min / interval) * interval,
            max: Math.ceil((max + padding) / interval) * interval
        };
    };

    const rainRange = calcAxisRange([processedRainData], 10, 5);
    const flowRange = calcAxisRange(flowSeries.map(s => s.data), 50, 10);
    const waterLevelRange = calcAxisRange(levelSeries.map(s => s.data), 5, 2);

    // 寻找峰值
    const findPeak = (data) => {
        if (!data || data.length === 0) return null;
        let peak = data[0];
        for (let i = 1; i < data.length; i++) {
            if (data[i][1] > peak[1]) peak = data[i];
        }
        return { coord: peak };
    };

    const peakRain = findPeak(processedRainData);
    const peakInflow = findPeak(inflowData);
    const peakOutflow = findPeak(outflowData);
    const peakWaterLevel = findPeak(waterLevelData);

    const option = {
        backgroundColor: 'transparent',
        legend: {
            data: ['降雨量', '入库流量', '出库流量', '库水位', '汛限水位', '防洪高水位'],
            top: 5,
            right: 20,
            textStyle: { color: '#a0aec0', fontSize: 12 },
            itemGap: 15,
            selected: {
                '防洪高水位': false
            }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' },
            backgroundColor: 'rgba(13, 27, 42, 0.9)',
            borderColor: 'rgba(0, 212, 255, 0.3)',
            textStyle: { color: '#e0e6ed' }
        },
        axisPointer: {
            link: [{ xAxisIndex: 'all' }],
            label: { backgroundColor: '#777' }
        },
        grid: [
            { top: 35, height: 130, left: 70, right: 70 },
            { top: 240, bottom: 65, left: 70, right: 70 }
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
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255, 255, 255, 0.1)' } }
            },
            {
                type: 'time',
                gridIndex: 1,
                min: minTime,
                max: maxTime,
                axisLabel: {
                    color: '#c0c8d0',
                    fontSize: 12,
                    fontWeight: 'bold',
                    formatter: '{MM}/{dd}\n{HH}:{mm}',
                    interval: 12 * 3600 * 1000
                },
                axisLine: { lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255, 255, 255, 0.1)' } }
            }
        ],
        yAxis: [
            {
                type: 'value',
                name: '降雨(mm)',
                nameTextStyle: { color: '#c0c8d0', fontSize: 13, fontWeight: 'bold' },
                gridIndex: 0,
                inverse: true,
                min: 0,
                max: rainRange.max,
                axisLabel: { color: '#c0c8d0', fontSize: 12, fontWeight: 'bold' },
                axisLine: { show: true, lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255, 255, 255, 0.1)' } }
            },
            {
                type: 'value',
                name: '流量(m³/s)',
                nameTextStyle: { color: '#c0c8d0', fontSize: 13, fontWeight: 'bold' },
                gridIndex: 1,
                min: flowRange.min,
                max: flowRange.max,
                axisLabel: { color: '#c0c8d0', fontSize: 12, fontWeight: 'bold' },
                axisLine: { show: true, lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255, 255, 255, 0.1)' } }
            },
            {
                type: 'value',
                name: '水位(m)',
                nameTextStyle: { color: '#c0c8d0', fontSize: 13, fontWeight: 'bold' },
                gridIndex: 1,
                position: 'right',
                min: waterLevelRange.min,
                max: waterLevelRange.max,
                axisLabel: { color: '#c0c8d0', fontSize: 12, fontWeight: 'bold' },
                axisLine: { show: true, lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: false }
            }
        ],
        series: [
            {
                name: '降雨量',
                type: 'bar',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: processedRainData,
                itemStyle: { color: '#5470c6' },
                markPoint: peakRain ? {
                    data: [{ coord: peakRain.coord, value: peakRain.coord[1] }],
                    symbol: 'none',
                    label: {
                        show: true,
                        position: 'top',
                        offset: [0, 10], // 向下偏移 10 像素，确保不被柱子压住
                        color: '#5470c6',
                        fontWeight: 'bold',
                        fontSize: 13,
                        formatter: '{c}mm'
                    }
                } : {}
            },
            ...flowSeries.map(s => buildLineSeries(s, 1, s.name === '入库流量' ? peakInflow : peakOutflow, ' m³/s')),
            ...levelSeries.map(s => buildLineSeries(s, 2, peakWaterLevel, ' m')),
            ...(useObservedSplit ? [buildForecastSplitLine(forecastStartTime)] : []),
            {
                name: '汛限水位',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: [],
                itemStyle: { color: '#fbbf24' },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{
                        yAxis: 248,
                        lineStyle: { color: '#fbbf24', width: 1, type: [10, 5, 2, 5] },
                        label: { show: true, position: 'insideEndTop', formatter: '汛限水位 248m', color: '#fbbf24' }
                    }]
                }
            },
            {
                name: '防洪高水位',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: [],
                itemStyle: { color: '#f44336' },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{
                        yAxis: 270,
                        lineStyle: { color: '#f44336', width: 1, type: [10, 5, 2, 5] },
                        label: { show: true, position: 'insideEndTop', formatter: '防洪高水位 270m', color: '#f44336' }
                    }]
                }
            }
        ]
    };

    myChart.clear();
    myChart.setOption(option);

    window.addEventListener('resize', () => {
        myChart.resize();
    });
}

function buildLineSeries(series, yAxisIndex, peak, unit) {
    return {
        name: series.name,
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex,
        data: series.data,
        smooth: true,
        symbol: 'none',
        itemStyle: { color: series.color },
        lineStyle: { width: 2, color: series.color, type: series.lineType || 'solid' },
        areaStyle: series.fill ? {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0, 212, 255, 0.2)' },
                { offset: 1, color: 'rgba(0, 212, 255, 0)' }
            ])
        } : undefined,
        markPoint: series.showPeak === false || !peak ? {} : {
            data: [{ coord: peak.coord, value: peak.coord[1] + unit }],
            symbol: 'circle',
            symbolSize: 8,
            itemStyle: { color: series.color },
            label: { show: true, position: 'top', fontWeight: 'bold', fontSize: 13, color: series.color }
        }
    };
}

function splitForecastSeries(series) {
    if (!series.observedData || !series.observedData.length) return [{ ...series }];
    const forecastData = Array.isArray(series.data) ? series.data : [];
    const observedData = connectObservedToForecast(series.observedData, forecastData);
    return [
        { ...series, data: observedData, lineType: 'solid', showPeak: false },
        { ...series, data: forecastData, lineType: 'dashed' }
    ];
}

function connectObservedToForecast(observedData, forecastData) {
    if (!observedData.length || !forecastData.length) return observedData;
    const connected = [...observedData];
    const firstForecast = forecastData[0];
    const lastObserved = connected[connected.length - 1];
    if (firstForecast && lastObserved && firstForecast[0] !== lastObserved[0]) {
        connected.push([firstForecast[0], lastObserved[1]]);
    }
    return connected;
}

function buildForecastSplitLine(splitTime) {
    return {
        name: '预报起点',
        type: 'line',
        xAxisIndex: 1,
        yAxisIndex: 2,
        data: [],
        tooltip: { show: false },
        markLine: {
            silent: true,
            symbol: 'none',
            data: [{
                xAxis: toTimestamp(splitTime),
                lineStyle: { color: 'rgba(255, 255, 255, 0.42)', width: 1, type: 'dashed' },
                label: { show: true, position: 'insideEndTop', formatter: '预报起点', color: '#c0c8d0' }
            }]
        }
    };
}

/**
 * 渲染结论及统计数据
 */
function renderConclusion(data, descText, currentStatus) {
    const textDom = document.getElementById('conclusionText');
    if (textDom) {
        textDom.innerText = descText;
    }

    const statsGrid = document.getElementById('statsGrid');
    if (!statsGrid) return;

    statsGrid.innerHTML = '';

    const icons = {
        waterLevel: `<svg viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="2">
            <path d="M12 2L12 22M12 2L8 6M12 2L16 6"/>
            <path d="M4 12h16" stroke-dasharray="2,2"/>
            <path d="M6 18c1.5-1.5 3-2 6-2s4.5.5 6 2"/>
        </svg>`,
        time: `<svg viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 6v6l4 2"/>
        </svg>`,
        inflow: `<svg viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="2">
            <path d="M12 4L12 20M12 20L6 14M12 20L18 14"/>
            <path d="M4 8h4M16 8h4"/>
        </svg>`,
        outflow: `<svg viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="2">
            <path d="M12 20L12 4M12 4L6 10M12 4L18 10"/>
            <path d="M4 16h4M16 16h4"/>
        </svg>`,
        volume: `<svg viewBox="0 0 24 24" fill="none" stroke="#2196F3" stroke-width="2">
            <ellipse cx="12" cy="6" rx="8" ry="3"/>
            <path d="M4 6v12c0 1.66 3.58 3 8 3s8-1.34 8-3V6"/>
            <path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/>
        </svg>`
    };

    // 预报统计指标
    const forecastMetrics = [
        { label: '最高水位', value: data.Max_Level, unit: 'm', icon: icons.waterLevel },
        { label: '最高水位时间', value: formatShortTime(data.MaxLevel_Time), unit: '', icon: icons.time },
        { label: '入库洪峰', value: data.Max_InQ, unit: 'm³/s', icon: icons.inflow },
        { label: '洪峰出现时间', value: formatShortTime(data.MaxInQ_Time), unit: '', icon: icons.time },
        { label: '累计入库', value: data.Total_InVolumn, unit: '万m³', icon: icons.volume },
        { label: '累计出库', value: data.Total_OutVolumn, unit: '万m³', icon: icons.volume }
    ];

    // 实时水情指标 (来自新接口)
    const realtimeMetrics = [
        { label: '当前水位', value: currentStatus ? currentStatus.rz : '--', unit: 'm', icon: icons.waterLevel, isHighlight: true },
        { label: '当前出库', value: currentStatus ? currentStatus.otq : '--', unit: 'm³/s', icon: icons.outflow, isHighlight: true }
    ];

    // 渲染预报部分
    forecastMetrics.forEach(m => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `
            <div class="stat-icon">${m.icon}</div>
            <div class="stat-info">
                <div class="stat-label">${m.label}</div>
                <div class="stat-value">${typeof m.value === 'number' ? formatNumber(m.value) : m.value}<span class="unit">${m.unit}</span></div>
            </div>
        `;
        statsGrid.appendChild(card);
    });

    // 添加分隔标识
    const divider = document.createElement('div');
    divider.className = 'stats-divider';
    divider.innerHTML = '<span>当前实测数据</span>';
    statsGrid.appendChild(divider);

    // 渲染实时水情部分
    realtimeMetrics.forEach(m => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `
            <div class="stat-icon">${m.icon}</div>
            <div class="stat-info">
                <div class="stat-label">${m.label}</div>
                <div class="stat-value">${typeof m.value === 'number' ? formatNumber(m.value) : m.value}<span class="unit">${m.unit}</span></div>
            </div>
        `;
        statsGrid.appendChild(card);
    });
}

function objectKeys(map) {
    return Object.keys(asObject(map)).filter(key => key !== '...').sort((a, b) => toTimestamp(a) - toTimestamp(b));
}

function seriesFromMap(map, keys) {
    const source = asObject(map);
    return (keys || objectKeys(source))
        .filter(t => source[t] !== undefined && source[t] !== null && source[t] !== '')
        .map(t => [toTimestamp(t), Number(source[t])])
        .filter(d => Number.isFinite(d[0]) && Number.isFinite(d[1]));
}

function asObject(value) {
    return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function getForecastStartTime(data) {
    const timeKeys = objectKeys(data?.InQ_Dic || data?.OutQ_Dic || data?.Level_Dic);
    return timeKeys[0] || data?.ForecastStartTime || data?.StartTime || null;
}

function extractProcessRows(result) {
    if (Array.isArray(result)) return result;
    const candidates = [
        result?.data,
        result?.result,
        result?.rows,
        result?.records,
        result?.list,
        result?.data?.records,
        result?.data?.rows,
        result?.data?.list,
        result?.result?.records,
        result?.result?.rows,
        result?.result?.list
    ];
    return candidates.find(Array.isArray) || [];
}

function normalizeObservedReservoirRow(row) {
    const time = pickFirst(row, ['tm', 'TM', 'time', 'Time', 'dataTime', 'data_time']);
    return {
        time,
        timestamp: toTimestamp(time),
        level: pickFirst(row, ['rz', 'RZ', 'z', 'Z']),
        inflow: pickFirst(row, ['inq', 'INQ', 'inQ', 'InQ']),
        outflow: pickFirst(row, ['otq', 'OTQ', 'outq', 'OutQ'])
    };
}

function buildObservedReservoirSeries(rows) {
    return {
        level: observedSeries(rows, 'level'),
        inflow: observedSeries(rows, 'inflow'),
        outflow: observedSeries(rows, 'outflow')
    };
}

function observedSeries(rows, field) {
    return (rows || [])
        .filter(row => row[field] !== undefined && row[field] !== null && row[field] !== '')
        .map(row => [row.timestamp, Number(row[field])])
        .filter(d => Number.isFinite(d[0]) && Number.isFinite(d[1]));
}

function pickFirst(source, keys) {
    if (!source) return '';
    for (const key of keys) {
        const value = source[key];
        if (value !== undefined && value !== null && value !== '') return value;
    }
    return '';
}

function toTimestamp(value) {
    if (value instanceof Date) return value.getTime();
    if (typeof value === 'number') return value;
    if (!value) return NaN;
    const normalized = String(value).replace(/\//g, '-');
    let timestamp = new Date(normalized).getTime();
    if (!Number.isNaN(timestamp)) return timestamp;
    const compactMatch = normalized.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$/);
    if (compactMatch) {
        const [, y, m, d, h, min, s] = compactMatch;
        timestamp = new Date(`${y}-${m}-${d} ${h}:${min}:${s}`).getTime();
    }
    return timestamp;
}

function formatDateTime(value) {
    const date = new Date(value);
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    const h = String(date.getHours()).padStart(2, '0');
    const min = String(date.getMinutes()).padStart(2, '0');
    const s = String(date.getSeconds()).padStart(2, '0');
    return `${y}-${m}-${d} ${h}:${min}:${s}`;
}

function formatShortTime(timeStr) {
    if (!timeStr) return '--';
    const date = new Date(String(timeStr).replace(/\//g, '-'));
    if (isNaN(date.getTime())) return timeStr;
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const d = date.getDate().toString().padStart(2, '0');
    const h = date.getHours().toString().padStart(2, '0');
    const min = date.getMinutes().toString().padStart(2, '0');
    return `${m}/${d} ${h}:${min}`;
}

function formatNumber(num) {
    if (typeof num === 'number') {
        return parseFloat(num.toFixed(2));
    }
    return num;
}

/**
 * 初始化地图 - 加载Portal WebMap
 * @param {Object|null} location - 定位坐标 {longitude, latitude}，为null时使用默认坐标
 */
function initMap(location) {
    require([
        "esri/WebMap",
        "esri/views/MapView",
        "esri/portal/Portal"
    ], function (WebMap, MapView, Portal) {
        // 创建Portal实例
        const portal = new Portal({
            url: "https://map.slt.henan.gov.cn/geoscene"
        });

        // 使用Portal WebMap ID加载地图
        const webmap = new WebMap({
            portalItem: {
                id: "0217daabff7a4b45a0cca3f975efa7f3",
                portal: portal
            }
        });

        // 根据是否有坐标决定地图中心和缩放级别
        const center = location ? [location.longitude, location.latitude] : [114.057818, 35.826884];
        const zoom = location ? 13 : 10;

        const view = new MapView({
            container: "viewDiv",
            map: webmap,
            center: center,
            zoom: zoom
        });
    });
}

// 启动
init();
