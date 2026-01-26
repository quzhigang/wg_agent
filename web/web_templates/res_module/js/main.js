
// API 配置
const API_URLS = {
    floodResult: 'http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx',
    rainProcess: 'http://10.20.2.153/api/basin/modelPlatf/model/modelRainArea/getByRsvr',
    currentStatus: 'http://10.20.2.153/api/basin/rwdb/rsvr/last'
};

// 本模板所需参数，包括方案名称、水库名称、水库stcd和认证Token
const DEFAULT_PARAMS = {
    planCode: 'model_20250702121848',
    stcd: '31005650',
    reservoirName: '盘石头水库', // 统一定义水库名称
    token: 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjEzMzk1NTA0Njc5Mzk2MzkyOTksImFjY291bnQiOiJhZG1pbiIsInV1aWQiOiI4YjUwYzg1Ni04YWVmLTQ0ODQtYjlkNi1hNjVjNTJmMmM5NDAiLCJyZW1lbWJlck1lIjpmYWxzZSwiZXhwaXJhdGlvbkRhdGUiOjE3NzAwMjkzOTAxMjIsImNhVG9rZW4iOm51bGwsIm90aGVycyI6bnVsbCwic3ViIjoiMTMzOTU1MDQ2NzkzOTYzOTI5OSIsImlhdCI6MTc2OTQyNDU5MCwiZXhwIjoxNzcwMDI5MzkwfQ.xAGV7AJFZLM22_JYqv7aHLlCI_KRPgdDHCNtkLjvoTeoMY2Xhm2ol2fJfxXPKw8WQt1AblQUfzlG4fPdLBU88A' // 认证Token
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
            processAllData(floodData, rainData, currentStatus);
        } else {
            throw new Error("未能获取洪水结果数据");
        }
    } catch (error) {
        console.error("数据加载错误:", error);
        if (conclusionTextDom) {
            conclusionTextDom.innerText = "数据获取失败，请检查网络或 API 服务。";
        }
    }

    initMap();
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
 * 处理并展示所有数据
 */
function processAllData(floodRaw, rainData, currentStatus) {
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

    renderChart(reservoirData, rainData);
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
function renderChart(data, rainData) {
    const chartDom = document.getElementById('chartDiv');
    if (!chartDom) return;

    const myChart = echarts.init(chartDom, null, { renderer: 'svg' });

    // 1. 处理水库数据 (流量, 水位)
    const timeKeys = Object.keys(data.InQ_Dic).sort();
    const inflowData = timeKeys.map(t => [new Date(t).getTime(), data.InQ_Dic[t]]);
    const outflowData = timeKeys.map(t => [new Date(t).getTime(), data.OutQ_Dic[t]]);
    const waterLevelData = timeKeys.map(t => [new Date(t).getTime(), data.Level_Dic[t]]);

    // 2. 处理降雨数据
    let processedRainData = [];
    if (rainData && Array.isArray(rainData)) {
        processedRainData = rainData.map(d => [new Date(d.time).getTime(), d.value]);
    }

    // 3. 计算统一的时间范围（并集）
    const allTimestamps = [
        ...inflowData.map(d => d[0]),
        ...outflowData.map(d => d[0]),
        ...waterLevelData.map(d => d[0]),
        ...processedRainData.map(d => d[0])
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
    const flowRange = calcAxisRange([inflowData, outflowData], 50, 10);
    const waterLevelRange = calcAxisRange([waterLevelData], 5, 2);

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
        backgroundColor: '#fff',
        title: {
            show: false
        },
        legend: {
            data: ['降雨量', '入库流量', '出库流量', '库水位', '汛限水位', '防洪高水位'],
            top: 2,
            right: 70,
            orient: 'horizontal',
            textStyle: { fontWeight: 'bold', fontSize: 12 },
            itemGap: 15,
            selected: {
                '防洪高水位': false
            }
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'cross' }
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
                splitLine: { show: true, lineStyle: { type: 'dashed' } }
            },
            {
                type: 'time',
                gridIndex: 1,
                min: minTime,
                max: maxTime,
                axisLabel: {
                    fontWeight: 'bold',
                    formatter: '{MM}/{dd}\n{HH}:{mm}',
                    interval: 12 * 3600 * 1000
                },
                axisLine: { lineStyle: { color: '#333' } },
                splitLine: { show: true, lineStyle: { type: 'dashed' } }
            }
        ],
        yAxis: [
            {
                type: 'value',
                name: '降雨(mm)',
                nameTextStyle: { fontWeight: 'bold' },
                gridIndex: 0,
                inverse: true,
                min: 0,
                max: rainRange.max,
                axisLabel: { fontWeight: 'bold' },
                axisLine: { show: true, lineStyle: { color: 'black' } }
            },
            {
                type: 'value',
                name: '流量(m³/s)',
                nameTextStyle: { fontWeight: 'bold' },
                gridIndex: 1,
                min: flowRange.min,
                max: flowRange.max,
                axisLabel: { fontWeight: 'bold' },
                axisLine: { show: true, lineStyle: { color: 'black' } }
            },
            {
                type: 'value',
                name: '水位(m)',
                nameTextStyle: { fontWeight: 'bold' },
                gridIndex: 1,
                position: 'right',
                min: waterLevelRange.min,
                max: waterLevelRange.max,
                axisLabel: { fontWeight: 'bold' },
                axisLine: { show: true, lineStyle: { color: 'black' } }
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
                        formatter: '{c}mm'
                    }
                } : {}
            },
            {
                name: '入库流量',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: inflowData,
                smooth: true,
                symbol: 'none',
                itemStyle: { color: 'orange' },
                lineStyle: { width: 3, color: 'orange' },
                markPoint: peakInflow ? {
                    data: [{ coord: peakInflow.coord, value: peakInflow.coord[1] + ' m³/s' }],
                    symbol: 'circle', symbolSize: 6,
                    itemStyle: { color: 'orange' },
                    label: { show: true, position: 'top', fontWeight: 'bold' }
                } : {}
            },
            {
                name: '出库流量',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: outflowData,
                smooth: true,
                symbol: 'none',
                itemStyle: { color: 'green' },
                lineStyle: { width: 3, color: 'green' },
                markPoint: peakOutflow ? {
                    data: [{ coord: peakOutflow.coord, value: peakOutflow.coord[1] + ' m³/s' }],
                    symbol: 'circle', symbolSize: 6,
                    itemStyle: { color: 'green' },
                    label: { show: true, position: 'top', fontWeight: 'bold' }
                } : {}
            },
            {
                name: '库水位',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: waterLevelData,
                smooth: true,
                symbol: 'none',
                itemStyle: { color: 'blue' },
                lineStyle: { width: 3, color: 'blue', type: 'dashed' },
                markPoint: peakWaterLevel ? {
                    data: [{ coord: peakWaterLevel.coord, value: peakWaterLevel.coord[1] + ' m' }],
                    symbol: 'circle', symbolSize: 6,
                    itemStyle: { color: 'blue' },
                    label: { show: true, position: 'top', fontWeight: 'bold' }
                } : {}
            },
            {
                name: '汛限水位',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: [],
                itemStyle: { color: 'red' },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{
                        yAxis: 248,
                        lineStyle: { color: 'red', width: 1, type: [10, 5, 2, 5] },
                        label: { show: true, position: 'insideEndTop', formatter: '汛限水位 248m' }
                    }]
                }
            },
            {
                name: '防洪高水位',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: [],
                itemStyle: { color: 'red' },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{
                        yAxis: 270,
                        lineStyle: { color: 'red', width: 1, type: [10, 5, 2, 5] },
                        label: { show: true, position: 'insideEndTop', formatter: '防洪高水位 270m' }
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

function formatShortTime(timeStr) {
    if (!timeStr) return '--';
    const date = new Date(timeStr);
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
 * 初始化地图
 */
function initMap() {
    require([
        "esri/Map",
        "esri/views/MapView",
        "esri/widgets/BasemapToggle"
    ], function (Map, MapView, BasemapToggle) {
        const map = new Map({
            basemap: "topo-vector"
        });

        const view = new MapView({
            container: "viewDiv",
            map: map,
            center: [113.4, 35.5],
            zoom: 10
        });

        const toggle = new BasemapToggle({
            view: view,
            nextBasemap: "hybrid"
        });
        view.ui.add(toggle, "top-right");
    });
}

// 启动
init();
