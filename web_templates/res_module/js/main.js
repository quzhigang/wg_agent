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
    // updateTime();
    // setInterval(updateTime, 1000);

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
    // const url = `${API_URLS.floodResult}?request_type=get_tjdata_result&request_pars=${DEFAULT_PARAMS.planCode}`;
    // 使用模拟数据，因为内网API可能不可访问
    return new Promise(resolve => {
        setTimeout(() => {
            resolve({
                reservoir_result: {
                    "盘石头水库": {
                        Max_Level: 105.23,
                        MaxLevel_Time: "2025-07-16 14:00:00",
                        Max_InQ: 2150.5,
                        MaxInQ_Time: "2025-07-16 08:30:00",
                        Max_OutQ: 1800.0,
                        MaxOutQ_Time: "2025-07-16 10:00:00",
                        Total_InVolumn: 4500.0,
                        Total_OutVolumn: 3800.0,
                        EndTime_Level: 102.5,
                        Max_Volumn: 6000.0,
                        InQ_Dic: generateTimeSeriesData(24, 1000, 2500),
                        OutQ_Dic: generateTimeSeriesData(24, 800, 2000),
                        Level_Dic: generateTimeSeriesData(24, 100, 108)
                    }
                },
                result_desc: "盘石头水库洪水预报：预计未来24小时内，库水位将出现上涨过程，最高水位105.23m，相应库容6000万m³。建议加强巡查，做好调度准备。"
            });
        }, 1000);
    });
}

function generateTimeSeriesData(hours, min, max) {
    const data = {};
    const now = new Date();
    for (let i = 0; i < hours; i++) {
        const time = new Date(now.getTime() + i * 3600000);
        const timeStr = time.toISOString().replace('T', ' ').substring(0, 19);
        data[timeStr] = min + Math.random() * (max - min);
    }
    return data;
}

async function fetchRainProcess() {
    // const url = `${API_URLS.rainProcess}?planCode=${DEFAULT_PARAMS.planCode}&stcd=${DEFAULT_PARAMS.stcd}`;
    // return fetch(url).then(res => res.json()).then(res => res.success ? res.data : getDefaultRainData());
    return getDefaultRainData();
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
    // 返回模拟数据
    const mockData = [];
    const now = new Date();
    for(let i=0; i<24; i++) {
        mockData.push({
            time: new Date(now.getTime() + i * 3600000).toISOString(),
            value: Math.random() * 20
        });
    }
    return mockData;
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

    const option = {
        backgroundColor: '#fff',
        title: {
            show: false
        },
        legend: {
            data: ['降雨量', '入库流量', '出库流量', '库水位'],
            top: 2,
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
            { top: 35, height: 100, left: 70, right: 70 },
            { top: 160, bottom: 40, left: 70, right: 70 }
        ],
        xAxis: [
            {
                type: 'time',
                gridIndex: 0,
                axisLabel: { show: false },
                axisLine: { show: false },
                axisTick: { show: false },
                splitLine: { show: true, lineStyle: { type: 'dashed' } }
            },
            {
                type: 'time',
                gridIndex: 1,
                axisLabel: {
                    fontWeight: 'bold',
                    formatter: '{MM}/{dd}\n{HH}:{mm}'
                },
                axisLine: { lineStyle: { color: '#333' } },
                splitLine: { show: true, lineStyle: { type: 'dashed' } }
            }
        ],
        yAxis: [
            {
                type: 'value',
                name: '降雨(mm)',
                gridIndex: 0,
                inverse: true,
                axisLine: { show: true }
            },
            {
                type: 'value',
                name: '流量(m³/s)',
                gridIndex: 1,
                axisLine: { show: true }
            },
            {
                type: 'value',
                name: '水位(m)',
                gridIndex: 1,
                position: 'right',
                axisLine: { show: true }
            }
        ],
        series: [
            {
                name: '降雨量',
                type: 'bar',
                xAxisIndex: 0,
                yAxisIndex: 0,
                data: processedRainData,
                itemStyle: { color: '#5470c6' }
            },
            {
                name: '入库流量',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: inflowData,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 3, color: 'orangered' }
            },
            {
                name: '出库流量',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: outflowData,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 3, color: 'green' }
            },
            {
                name: '库水位',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: waterLevelData,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 3, color: 'blue', type: 'dashed' }
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
        "esri/widgets/BasemapToggle"
    ], function (Map, MapView, BasemapToggle) {
        const map = new Map({
            basemap: "topo-vector"
        });

        const view = new MapView({
            container: "viewDiv",
            map: map,
            center: [113.4, 35.5], // Approximate center for the region
            zoom: 10
        });

        const toggle = new BasemapToggle({
            view: view,
            nextBasemap: "hybrid"
        });
        view.ui.add(toggle, "top-right");
    });
}

// Start
init();
