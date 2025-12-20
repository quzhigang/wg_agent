
// API Config
const API_URLS = {
    floodResult: 'http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx',
    rainProcess: 'http://10.20.2.153:8089/modelPlatf/model/modelRainArea/getByRsvr'
};

const DEFAULT_PARAMS = {
    planCode: 'model_20250715112532',
    stcd: '31005650'
};

// Main entry point
async function init() {
    updateTime();
    setInterval(updateTime, 1000);

    const conclusionTextDom = document.getElementById('conclusionText');
    if (conclusionTextDom) {
        conclusionTextDom.innerText = "正在获取实时预报数据...";
    }

    try {
        // Fetch data from both APIs
        const [floodData, rainData] = await Promise.all([
            fetchFloodResult(),
            fetchRainProcess()
        ]);

        if (floodData) {
            processAllData(floodData, rainData);
        } else {
            throw new Error("未能获取洪水结果数据");
        }
    } catch (error) {
        console.error("Data loading error:", error);
        if (conclusionTextDom) {
            conclusionTextDom.innerText = "数据获取失败，请检查网络或 API 服务。";
        }
    }

    initMap();
}

async function fetchFloodResult() {
    const url = `${API_URLS.floodResult}?request_type=get_tjdata_result&request_pars=${DEFAULT_PARAMS.planCode}`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
}

async function fetchRainProcess() {
    const url = `${API_URLS.rainProcess}?planCode=${DEFAULT_PARAMS.planCode}&stcd=${DEFAULT_PARAMS.stcd}`;
    try {
        const response = await fetch(url);
        if (!response.ok) return getDefaultRainData();
        const result = await response.json();
        return result.success ? result.data : (result.data || getDefaultRainData());
    } catch (e) {
        console.warn("Rain API failed (possibly CORS). Using default data from js/rain.js.", e);
        return getDefaultRainData();
    }
}

// 从 js/rain.js (window.rain_res) 获取默认降雨数据
function getDefaultRainData() {
    if (window.rain_res && window.rain_res.data && window.rain_res.data.t) {
        const { t, v } = window.rain_res.data;
        return t.map((time, index) => ({
            time: time,
            value: parseFloat(v[index] || 0)
        }));
    }
    console.warn("Default rain data (js/rain.js) not found or invalid format.");
    return [];
}

function processAllData(floodRaw, rainData) {
    const reservoirName = "盘石头水库";
    if (!floodRaw.reservoir_result || !floodRaw.reservoir_result[reservoirName]) {
        console.error(`Data for ${reservoirName} not found.`);
        return;
    }
    const reservoirData = floodRaw.reservoir_result[reservoirName];
    const description = floodRaw.result_desc || "";

    renderChart(reservoirData, rainData);
    renderConclusion(reservoirData, description);
}

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

function renderChart(data, rainData) {
    const chartDom = document.getElementById('chartDiv');
    if (!chartDom) return;

    const myChart = echarts.init(chartDom, null, { renderer: 'svg' });

    // 1. Process Reservoir Data (Inflow, Outflow, Level)
    const timeKeys = Object.keys(data.InQ_Dic).sort();
    const inflowData = timeKeys.map(t => [new Date(t).getTime(), data.InQ_Dic[t]]);
    const outflowData = timeKeys.map(t => [new Date(t).getTime(), data.OutQ_Dic[t]]);
    const waterLevelData = timeKeys.map(t => [new Date(t).getTime(), data.Level_Dic[t]]);

    // 2. Process Rain Data
    let processedRainData = [];
    if (rainData && Array.isArray(rainData)) {
        processedRainData = rainData.map(d => [new Date(d.time).getTime(), d.value]);
    }

    // Helper: Calculate axis range
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

    // Helper: Find peak
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
            show: false // 去掉图表名称
        },
        legend: {
            data: ['降雨量', '入库流量', '出库流量', '库水位'],
            top: 2, // 尽量占用少的高度
            right: 70,
            orient: 'horizontal',
            textStyle: { fontWeight: 'bold', fontSize: 12 },
            itemGap: 15
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
            { top: 35, height: 130, left: 70, right: 70 }, // 降雨图表
            { top: 240, bottom: 65, left: 70, right: 70 } // 进一步增加间距 (240 - (35+130) = 75px)
        ],
        xAxis: [
            {
                type: 'time',
                gridIndex: 0,
                axisLabel: { show: false },
                axisLine: { show: false }, // 去掉底边黑线
                axisTick: { show: false },
                splitLine: { show: true, lineStyle: { type: 'dashed' } }
            },
            {
                type: 'time',
                gridIndex: 1,
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
                    data: [{ coord: peakRain.coord, value: peakRain.coord[1] + 'mm' }],
                    symbol: 'pin',
                    symbolSize: 40
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
                lineStyle: { width: 3, color: 'orangered' },
                markPoint: peakInflow ? {
                    data: [{ coord: peakInflow.coord, value: peakInflow.coord[1] + ' m³/s' }],
                    symbol: 'circle', symbolSize: 8, itemStyle: { color: 'orangered' }
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
                lineStyle: { width: 3, color: 'green' },
                markPoint: peakOutflow ? {
                    data: [{ coord: peakOutflow.coord, value: peakOutflow.coord[1] + ' m³/s' }],
                    symbol: 'circle', symbolSize: 8, itemStyle: { color: 'green' }
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
                lineStyle: { width: 3, color: 'blue', type: 'dashed' },
                markPoint: peakWaterLevel ? {
                    data: [{ coord: peakWaterLevel.coord, value: peakWaterLevel.coord[1] + ' m' }],
                    symbol: 'circle', symbolSize: 8, itemStyle: { color: 'blue' }
                } : {}
            }
        ]
    };

    myChart.clear();
    myChart.setOption(option);

    window.addEventListener('resize', () => {
        myChart.resize();
    });
}

function renderConclusion(data, descText) {
    const textDom = document.getElementById('conclusionText');
    if (textDom) {
        textDom.innerText = descText;
    }

    const statsGrid = document.getElementById('statsGrid');
    if (!statsGrid) return;

    statsGrid.innerHTML = '';

    const metrics = [
        { label: '最高水位', value: data.Max_Level, unit: 'm' },
        { label: '出现时间', value: formatShortTime(data.MaxLevel_Time), unit: '' },
        { label: '峰值入库', value: data.Max_InQ, unit: 'm³/s' },
        { label: '出现时间', value: formatShortTime(data.MaxInQ_Time), unit: '' },
        { label: '峰值出库', value: data.Max_OutQ, unit: 'm³/s' },
        { label: '出现时间', value: formatShortTime(data.MaxOutQ_Time), unit: '' },
        { label: '总入库量', value: data.Total_InVolumn, unit: '万m³' },
        { label: '总出库量', value: data.Total_OutVolumn, unit: '万m³' },
        { label: '期末水位', value: data.EndTime_Level, unit: 'm' },
        { label: '最大库容', value: data.Max_Volumn, unit: '万m³' }
    ];

    metrics.forEach(m => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `
            <div class="stat-label">${m.label}</div>
            <div class="stat-value">${typeof m.value === 'number' ? formatNumber(m.value) : m.value} <span style="font-size:10px; color:#666;">${m.unit}</span></div>
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

// Map initialization
function initMap() {
    require([
        "esri/Map",
        "esri/views/MapView",
        "esri/widgets/BasemapToggle",
        "esri/widgets/DistanceMeasurement2D"
    ], function (Map, MapView, BasemapToggle, DistanceMeasurement2D) {
        const map = new Map({
            basemap: "topo-vector"
        });

        const view = new MapView({
            container: "viewDiv",
            map: map,
            center: [113.4, 35.5], // Approximate center for the region (adjust if needed)
            zoom: 10
        });

        // Add standard widgets
        const toggle = new BasemapToggle({
            view: view,
            nextBasemap: "hybrid"
        });
        view.ui.add(toggle, "top-right");
    });
}

// Start
init();
