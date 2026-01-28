
// API 配置
const API_URLS = {
    floodResult: 'http://172.16.16.253/wg_modelserver/hd_mike11server/Model_Ser.ashx',
    rainProcess: 'http://10.20.2.153/api/basin/modelPlatf/model/modelRainArea/getByRsvr',
    currentStatus: 'http://10.20.2.153/api/basin/rwdb/river/last',
    // 使用本地代理接口解决CORS问题
    stationInfo: '/proxy/mike11/station_info',
    sectionData: '/proxy/mike11/section_data'
};

// 本模板所需参数，包括方案名称、站点名称、站点stcd和认证Token
const DEFAULT_PARAMS = {
    planCode: 'model_20260127101007',
    stcd: '31004900',
    reservoirName: '修武', // 统一定义站点名称
    token: 'eyJhbGciOiJIUzUxMiJ9.eyJ1c2VySWQiOjEzMzk1NTA0Njc5Mzk2MzkyOTksImFjY291bnQiOiJhZG1pbiIsInV1aWQiOiI4ZDE0ODA3Yi02Y2RkLTQxYzItYmRlOS1mMWMzZmZhMjMxZmMiLCJyZW1lbWJlck1lIjpmYWxzZSwiZXhwaXJhdGlvbkRhdGUiOjE3NzAxNjczOTk5NjAsImNhVG9rZW4iOm51bGwsIm90aGVycyI6bnVsbCwic3ViIjoiMTMzOTU1MDQ2NzkzOTYzOTI5OSIsImlhdCI6MTc2OTU2MjU5OSwiZXhwIjoxNzcwMTY3Mzk5fQ.eVJ9kRMwhoWfHQCyXnFynSFieSQrU8Mh256wCOJEB87a79fuIj_h6mk1G_djbyvq2kU76l2DVZbJExDSxhsSsQ' // 认证Token
};

// 主入口函数
async function init() {
    const statsGrid = document.getElementById('statsGrid');

    try {
        // 显示加载状态
        if (statsGrid) {
            statsGrid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 30px; text-align: center; color: var(--accent-cyan);">
                    <div style="font-size: 16px;">正在获取实时预报数据...</div>
                </div>
            `;
        }

        // 全部采用 API 获取，增加站点信息获取
        const [floodData, rainData, currentStatus, stationInfoList] = await Promise.all([
            fetchFloodResult(),
            fetchRainProcess(),
            fetchCurrentStatus(),
            fetchStationInfo()
        ]);

        console.log('API 返回的洪水数据:', floodData);
        console.log('API 返回的站点信息:', stationInfoList);

        if (floodData) {
            processAllData(floodData, rainData, currentStatus, stationInfoList);
        } else {
            throw new Error("未能获取洪水结果数据");
        }
    } catch (error) {
        console.error("数据加载错误:", error);
        if (statsGrid) {
            statsGrid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 20px; text-align: center; color: #ff6b6b;">
                    <div style="font-size: 16px; margin-bottom: 10px;">数据获取失败</div>
                    <div style="font-size: 12px; color: #a0aec0;">${error.message}</div>
                </div>
            `;
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
 * 获取站点信息列表
 * 用于获取预报站点的 Reach 和 Chainage 属性
 * 通过本地代理接口调用，解决CORS问题
 */
async function fetchStationInfo() {
    const url = API_URLS.stationInfo;
    try {
        const headers = { 'Accept': '*/*' };
        if (DEFAULT_PARAMS.token) {
            headers['Authorization'] = DEFAULT_PARAMS.token;
        }
        const response = await fetch(url, {
            method: 'GET',
            headers: headers,
            cache: 'no-cache'
        });
        if (!response.ok) {
            console.error(`站点信息接口响应异常: ${response.status} ${response.statusText}`);
            return [];
        }
        return await response.json();
    } catch (e) {
        console.warn("获取站点信息失败:", e);
        return [];
    }
}

/**
 * 获取断面地形数据
 * 通过本地代理接口调用，解决CORS问题
 * @param {string} reach - 河道名称 (如 "DSH")
 * @param {number} chainage - 桩号 (如 64250.0)
 * @returns {Promise<Array>} - 断面地形数据 [[偏心距, 高程], ...]
 */
async function fetchSectionData(reach, chainage) {
    const url = `${API_URLS.sectionData}?reach=${reach}&chainage=${chainage}`;
    try {
        const headers = { 'Accept': '*/*' };
        if (DEFAULT_PARAMS.token) {
            headers['Authorization'] = DEFAULT_PARAMS.token;
        }
        const response = await fetch(url, {
            method: 'GET',
            headers: headers,
            cache: 'no-cache'
        });
        if (!response.ok) {
            console.error(`断面地形接口响应异常: ${response.status} ${response.statusText}`);
            return null;
        }
        return await response.json();
    } catch (e) {
        console.warn("获取断面地形数据失败:", e);
        return null;
    }
}

/**
 * 模糊匹配站点名称
 * 处理 "修武站"、"修武"、"修武水文站"、"修武水位站" 等变体
 * @param {Object} dataDict - 数据字典，key 为站点名称
 * @param {string} targetName - 目标站点名称
 * @returns {{key: string, data: Object}|null} - 匹配到的 key 和数据，或 null
 */
function fuzzyMatchStation(dataDict, targetName) {
    if (!dataDict || !targetName) return null;

    // 1. 精确匹配
    if (dataDict[targetName]) {
        return { key: targetName, data: dataDict[targetName] };
    }

    // 2. 提取核心名称（去除常见后缀）
    const suffixes = ['站', '水文站', '水位站', '流量站', '水库', '闸', '断面'];
    let coreName = targetName;
    for (const suffix of suffixes) {
        if (targetName.endsWith(suffix)) {
            coreName = targetName.slice(0, -suffix.length);
            break;
        }
    }

    // 3. 遍历数据字典进行模糊匹配
    for (const key of Object.keys(dataDict)) {
        // 提取字典中 key 的核心名称
        let keyCore = key;
        for (const suffix of suffixes) {
            if (key.endsWith(suffix)) {
                keyCore = key.slice(0, -suffix.length);
                break;
            }
        }

        // 核心名称匹配
        if (coreName === keyCore || coreName === key || targetName === keyCore) {
            return { key: key, data: dataDict[key] };
        }

        // 包含关系匹配（核心名称互相包含）
        if (coreName.includes(keyCore) || keyCore.includes(coreName)) {
            return { key: key, data: dataDict[key] };
        }
    }

    return null;
}

/**
 * 处理并展示所有数据
 * @param {Object} floodRaw - 洪水预报原始数据
 * @param {Array} rainData - 降雨数据
 * @param {Object} currentStatus - 当前实测水情
 * @param {Array} stationInfoList - 站点信息列表
 */
async function processAllData(floodRaw, rainData, currentStatus, stationInfoList) {
    const stationName = DEFAULT_PARAMS.reservoirName; // 此时实际上是河道站名
    const targetStcd = DEFAULT_PARAMS.stcd;

    console.log('=== 开始处理数据 ===');
    console.log('目标站点名称:', stationName);
    console.log('目标站点stcd:', targetStcd);
    console.log('原始数据结构:', Object.keys(floodRaw));
    console.log('reachsection_result 存在:', !!floodRaw.reachsection_result);
    console.log('reservoir_result 存在:', !!floodRaw.reservoir_result);

    if (floodRaw.reachsection_result) {
        console.log('可用河道断面:', Object.keys(floodRaw.reachsection_result));
    }

    // 从站点信息列表中查找当前站点（通过stcd匹配）
    let currentStationInfo = null;
    if (stationInfoList && Array.isArray(stationInfoList)) {
        currentStationInfo = stationInfoList.find(s => s.Stcd === targetStcd);
        console.log('匹配到的站点信息:', currentStationInfo);
    }

    // 使用模糊匹配查找站点数据
    let stationData = null;
    let matchedKey = stationName;

    // 优先从河道断面结果中查找
    if (floodRaw.reachsection_result) {
        const match = fuzzyMatchStation(floodRaw.reachsection_result, stationName);
        if (match) {
            stationData = match.data;
            matchedKey = match.key;
            console.log('从 reachsection_result 匹配成功:', matchedKey);
        }
    }

    // 如果河道断面没找到，尝试从水库结果中查找
    if (!stationData && floodRaw.reservoir_result) {
        const match = fuzzyMatchStation(floodRaw.reservoir_result, stationName);
        if (match) {
            stationData = match.data;
            matchedKey = match.key;
            console.log('从 reservoir_result 匹配成功:', matchedKey);
        }
    }

    // 动态更新页面标题（使用实际匹配到的名称）
    const titleDom = document.getElementById('conclusionTitle');
    if (titleDom) {
        titleDom.innerText = `${matchedKey}洪水预报结果`;
    }

    if (!stationData) {
        console.error(`未找到 ${stationName} 的数据。可用的河道断面:`,
            floodRaw.reachsection_result ? Object.keys(floodRaw.reachsection_result) : '无');

        // 在 statsGrid 中显示错误信息
        const statsGrid = document.getElementById('statsGrid');
        if (statsGrid) {
            const availableStations = floodRaw.reachsection_result ? Object.keys(floodRaw.reachsection_result).join('、') : '无';
            statsGrid.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 20px; text-align: center; color: #ff6b6b;">
                    <div style="font-size: 16px; margin-bottom: 10px;">未找到"${stationName}"的数据</div>
                    <div style="font-size: 12px; color: #a0aec0;">可用站点: ${availableStations}</div>
                </div>
            `;
        }
        return;
    }

    console.log(`成功匹配站点: "${stationName}" -> "${matchedKey}"`);
    console.log('站点数据字段:', Object.keys(stationData));
    console.log('Max_Level:', stationData.Max_Level);
    console.log('Max_Discharge:', stationData.Max_Discharge);
    console.log('Level_Dic:', stationData.Level_Dic);
    console.log('Discharge_Dic:', stationData.Discharge_Dic);

    const description = floodRaw.result_desc || "";

    // 先渲染特征值，确保即使图表出错也能显示
    renderConclusion(stationData, description, currentStatus);

    // 图表渲染用 try-catch 包裹，避免影响特征值展示
    try {
        renderProcessChart(stationData, rainData, currentStationInfo);
    } catch (e) {
        console.error('渲染过程曲线失败:', e);
    }

    // 获取断面地形数据并渲染断面图
    try {
        let sectionProfile = null;
        if (currentStationInfo && currentStationInfo.Reach && currentStationInfo.Chainage !== undefined) {
            console.log(`正在获取断面地形数据: Reach=${currentStationInfo.Reach}, Chainage=${currentStationInfo.Chainage}`);
            sectionProfile = await fetchSectionData(currentStationInfo.Reach, currentStationInfo.Chainage);
            console.log('获取到的断面地形数据:', sectionProfile);
        } else {
            console.warn('未找到站点的Reach和Chainage信息，无法获取断面地形数据');
        }
        renderSectionChart(stationData, sectionProfile, currentStationInfo, currentStatus);
    } catch (e) {
        console.error('渲染断面图失败:', e);
        renderSectionChart(stationData, null, currentStationInfo, currentStatus);
    }
}

/**
 * 渲染水位流量过程曲线 (左侧) - 上部倒放降雨柱状图，下部水位流量曲线
 * @param {Object} data - 洪水预报数据
 * @param {Array} rainData - 降雨数据
 * @param {Object} stationInfo - 站点信息，包含警戒水位等
 */
function renderProcessChart(data, rainData, stationInfo) {
    const chartDom = document.getElementById('processChart');
    if (!chartDom) return;

    const myChart = echarts.init(chartDom, null, { renderer: 'svg' });

    // 1. 处理过程数据 - 适配河道断面数据格式
    const zMap = data.Level_Dic || data.Z_Dic || {};
    const qMap = data.Discharge_Dic || data.Q_Dic || data.InQ_Dic || data.OutQ_Dic || {};

    const zMapSafe = (typeof zMap === 'object' && zMap !== null) ? zMap : {};
    const qMapSafe = (typeof qMap === 'object' && qMap !== null) ? qMap : {};

    const timeKeys = Object.keys(zMapSafe).length > 0 ? Object.keys(zMapSafe).sort() : Object.keys(qMapSafe).sort();
    const waterLevelData = timeKeys.map(t => [new Date(t).getTime(), zMapSafe[t]]).filter(d => d[1] !== undefined);
    const flowData = timeKeys.map(t => [new Date(t).getTime(), qMapSafe[t]]).filter(d => d[1] !== undefined);

    console.log('水位数据点数:', waterLevelData.length);
    console.log('流量数据点数:', flowData.length);

    // 2. 处理降雨数据
    let processedRainData = [];
    if (rainData && Array.isArray(rainData)) {
        processedRainData = rainData.map(d => [new Date(d.time).getTime(), d.value]);
    }

    // 3. 计算统一的时间范围（并集）
    const allTimestamps = [
        ...waterLevelData.map(d => d[0]),
        ...flowData.map(d => d[0]),
        ...processedRainData.map(d => d[0])
    ];

    let minTime = undefined, maxTime = undefined;
    if (allTimestamps.length > 0) {
        minTime = Math.min(...allTimestamps);
        maxTime = Math.max(...allTimestamps);
    }

    // 4. 获取警戒水位（从站点信息的Level1属性）
    const warningZ = stationInfo && stationInfo.Level1 ? parseFloat(stationInfo.Level1) : null;
    console.log('警戒水位 Level1:', warningZ);

    // 5. 计算轴范围（考虑警戒水位）
    const calcAxisRange = (dataList, interval, padding = 1, extraValues = []) => {
        const values = [
            ...dataList.flatMap(list => list.map(d => d[1])).filter(v => !isNaN(v)),
            ...extraValues.filter(v => v !== null && !isNaN(v))
        ];
        if (values.length === 0) return { min: 0, max: interval };
        const min = Math.min(...values);
        const max = Math.max(...values);
        return {
            min: Math.floor(min / interval) * interval,
            max: Math.ceil((max + padding) / interval) * interval
        };
    };

    const rainRange = calcAxisRange([processedRainData], 10, 5);
    const flowRange = calcAxisRange([flowData], 50, 10);
    // 水位轴范围需要考虑警戒水位
    const waterLevelRange = calcAxisRange([waterLevelData], 5, 2, [warningZ]);

    // 6. 寻找峰值
    const findPeak = (data) => {
        if (!data || data.length === 0) return null;
        let peak = data[0];
        for (let i = 1; i < data.length; i++) {
            if (data[i][1] > peak[1]) peak = data[i];
        }
        return { coord: peak };
    };

    const peakRain = findPeak(processedRainData);
    const peakWaterLevel = findPeak(waterLevelData);
    const peakFlow = findPeak(flowData);

    // 7. 构建水位曲线的markLine（警戒水位线）
    const waterLevelMarkLine = warningZ ? {
        silent: true,
        symbol: 'none',
        label: {
            show: true,
            position: 'insideEndTop',
            formatter: '警戒 ' + warningZ + 'm',
            color: '#ffc107',
            fontSize: 12,
            fontWeight: 'bold'
        },
        data: [{
            yAxis: warningZ,
            lineStyle: { color: '#ffc107', type: 'dashed', width: 1 }
        }]
    } : {};

    const option = {
        backgroundColor: 'transparent',
        legend: {
            data: ['降雨量', '水位', '流量'],
            top: 5,
            right: 20,
            textStyle: { color: '#a0aec0', fontSize: 12 },
            itemGap: 15
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
            { top: 35, height: 130, left: 70, right: 70 },  // 上部降雨图
            { top: 240, bottom: 65, left: 70, right: 70 }   // 下部水位流量图
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
                axisLabel: {
                    color: '#c0c8d0',
                    fontSize: 12,
                    fontWeight: 'bold',
                    formatter: '{MM}/{dd}\n{HH}:{mm}'
                },
                axisLine: { lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } }
            }
        ],
        yAxis: [
            {
                type: 'value',
                name: '降雨(mm)',
                nameTextStyle: { color: '#c0c8d0', fontSize: 13, fontWeight: 'bold' },
                gridIndex: 0,
                inverse: true,  // 倒放
                min: 0,
                max: rainRange.max,
                axisLabel: { color: '#c0c8d0', fontSize: 12, fontWeight: 'bold' },
                axisLine: { show: true, lineStyle: { color: '#c0c8d0' } },
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } }
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
                splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } }
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
                        offset: [0, 10],
                        color: '#5470c6',
                        fontWeight: 'bold',
                        fontSize: 13,
                        formatter: '{c}mm'
                    }
                } : {}
            },
            {
                name: '水位',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 2,
                data: waterLevelData,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 2, color: '#00d4ff' },
                itemStyle: { color: '#00d4ff' },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: 'rgba(0, 212, 255, 0.2)' },
                        { offset: 1, color: 'rgba(0, 212, 255, 0)' }
                    ])
                },
                markPoint: peakWaterLevel ? {
                    data: [{ coord: peakWaterLevel.coord, value: peakWaterLevel.coord[1] + ' m' }],
                    symbol: 'circle', symbolSize: 8,
                    itemStyle: { color: '#00d4ff' },
                    label: { show: true, position: 'top', fontWeight: 'bold', fontSize: 13, color: '#00d4ff' }
                } : {},
                markLine: waterLevelMarkLine
            },
            {
                name: '流量',
                type: 'line',
                xAxisIndex: 1,
                yAxisIndex: 1,
                data: flowData,
                smooth: true,
                symbol: 'none',
                lineStyle: { width: 2, color: '#4ade80' },
                itemStyle: { color: '#4ade80' },
                markPoint: peakFlow ? {
                    data: [{ coord: peakFlow.coord, value: peakFlow.coord[1] + ' m³/s' }],
                    symbol: 'circle', symbolSize: 8,
                    itemStyle: { color: '#4ade80' },
                    label: { show: true, position: 'top', fontWeight: 'bold', fontSize: 13, color: '#4ade80' }
                } : {}
            }
        ]
    };

    myChart.clear();
    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}

/**
 * 渲染河道断面图 (右侧)
 * @param {Object} data - 洪水预报数据
 * @param {Array} sectionProfile - 断面地形数据 [[偏心距, 高程], ...]
 * @param {Object} stationInfo - 站点信息，包含警戒水位等
 * @param {Object} currentStatus - 当前实测水情数据
 */
function renderSectionChart(data, sectionProfile, stationInfo, currentStatus) {
    const chartDom = document.getElementById('sectionChart');
    if (!chartDom) return;

    const myChart = echarts.init(chartDom, null, { renderer: 'svg' });

    // 如果没有断面地形数据，显示提示信息
    if (!sectionProfile || sectionProfile.length === 0) {
        myChart.setOption({
            backgroundColor: 'transparent',
            title: {
                text: '暂无断面地形数据',
                left: 'center',
                top: 'center',
                textStyle: { color: '#a0aec0', fontSize: 14 }
            }
        });
        return;
    }

    // 获取预报最高水位
    const forecastMaxZ = data.Max_Level || data.Max_Z || 79;

    // 获取当前实测水位
    const currentZ = currentStatus ? (currentStatus.rz || currentStatus.z) : null;

    // 从站点信息获取警戒水位和保证水位
    // Level1: 警戒水位, Level3: 保证水位
    const warningZ = stationInfo && stationInfo.Level1 ? parseFloat(stationInfo.Level1) : null;
    const guaranteeZ = stationInfo && stationInfo.Level3 ? parseFloat(stationInfo.Level3) : null;

    // 计算横轴范围：根据断面偏心距最小最大值，按10向前后取整
    const xValues = sectionProfile.map(pt => pt[0]);
    const xMin = Math.floor(Math.min(...xValues) / 10) * 10;
    const xMax = Math.ceil(Math.max(...xValues) / 10) * 10;

    // 计算预报最高水位线与地形的交点
    const forecastWaterLevelData = calculateWaterLevelInChannel(sectionProfile, forecastMaxZ);

    // 计算当前水位线与地形的交点
    const currentWaterLevelData = currentZ ? calculateWaterLevelInChannel(sectionProfile, currentZ) : [];

    // 构建水位标线数据（警戒水位用黄色，保证水位用红色）
    const markLineData = [];
    if (warningZ && warningZ > 0) {
        markLineData.push({
            yAxis: warningZ,
            name: '警戒水位',
            lineStyle: { color: '#ffc107', type: 'dashed', width: 1 },
            label: {
                show: true,
                position: 'insideEndTop',
                formatter: '警戒 ' + warningZ + 'm',
                color: '#ffc107',
                fontSize: 12,
                fontWeight: 'bold'
            }
        });
    }
    if (guaranteeZ && guaranteeZ > 0) {
        markLineData.push({
            yAxis: guaranteeZ,
            name: '保证水位',
            lineStyle: { color: '#f44336', type: 'dashed', width: 1 },
            label: {
                show: true,
                position: 'insideEndTop',
                formatter: '保证 ' + guaranteeZ + 'm',
                color: '#f44336',
                fontSize: 12,
                fontWeight: 'bold'
            }
        });
    }

    // 构建系列数据
    const series = [
        {
            name: '断面地形',
            type: 'line',
            data: sectionProfile,
            smooth: false,
            symbol: 'none',
            lineStyle: { color: '#8b4513', width: 2 },
            areaStyle: { color: '#5d3a1a' },
            markLine: markLineData.length > 0 ? {
                silent: true,
                symbol: 'none',
                data: markLineData
            } : {}
        }
    ];

    // 添加当前水位线（蓝色实线，带渐变填充）
    if (currentWaterLevelData.length > 0) {
        // 计算水位线中心点坐标
        const currentCenterX = (currentWaterLevelData[0][0] + currentWaterLevelData[1][0]) / 2;
        series.push({
            name: '当前水位',
            type: 'line',
            data: currentWaterLevelData,
            symbol: 'none',
            lineStyle: { color: '#00d4ff', width: 2, type: 'solid' },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
                    { offset: 1, color: 'rgba(0, 212, 255, 0.1)' }
                ])
            },
            markPoint: {
                data: [{ coord: [currentCenterX, currentZ], value: currentZ + 'm' }],
                symbol: 'circle',
                symbolSize: 6,
                itemStyle: { color: '#00d4ff' },
                label: {
                    show: true,
                    position: 'top',
                    formatter: '当前 ' + currentZ + 'm',
                    color: '#00d4ff',
                    fontSize: 12,
                    fontWeight: 'bold'
                }
            }
        });
    }

    // 添加预报最高水位线（青色虚线，无填充）
    if (forecastWaterLevelData.length > 0) {
        // 计算水位线中心点坐标
        const forecastCenterX = (forecastWaterLevelData[0][0] + forecastWaterLevelData[1][0]) / 2;
        series.push({
            name: '预报最高水位',
            type: 'line',
            data: forecastWaterLevelData,
            symbol: 'none',
            lineStyle: { color: '#00ffcc', width: 2, type: 'dashed' },
            markPoint: {
                data: [{ coord: [forecastCenterX, forecastMaxZ], value: forecastMaxZ + 'm' }],
                symbol: 'circle',
                symbolSize: 6,
                itemStyle: { color: '#00ffcc' },
                label: {
                    show: true,
                    position: 'top',
                    formatter: '预报 ' + forecastMaxZ + 'm',
                    color: '#00ffcc',
                    fontSize: 12,
                    fontWeight: 'bold'
                }
            }
        });
    }

    const option = {
        backgroundColor: 'transparent',
        tooltip: { trigger: 'axis' },
        legend: {
            data: ['断面地形', '当前水位', '预报最高水位'],
            top: 5,
            right: 20,
            textStyle: { color: '#a0aec0', fontSize: 11 },
            itemGap: 10
        },
        grid: { top: 40, bottom: 40, left: 60, right: 30 },
        xAxis: {
            type: 'value',
            name: '距离(m)',
            min: xMin,
            max: xMax,
            nameTextStyle: { color: '#c0c8d0', fontSize: 13, fontWeight: 'bold' },
            axisLabel: { color: '#c0c8d0', fontSize: 12, fontWeight: 'bold' },
            axisLine: { lineStyle: { color: '#c0c8d0' } },
            splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } }
        },
        yAxis: {
            type: 'value',
            name: '高程(m)',
            nameTextStyle: { color: '#c0c8d0', fontSize: 13, fontWeight: 'bold' },
            scale: true,
            axisLabel: { color: '#c0c8d0', fontSize: 12, fontWeight: 'bold' },
            axisLine: { show: true, lineStyle: { color: '#c0c8d0' } },
            splitLine: { show: true, lineStyle: { type: 'dashed', color: 'rgba(255,255,255,0.1)' } }
        },
        series: series
    };

    myChart.setOption(option);
    window.addEventListener('resize', () => myChart.resize());
}

/**
 * 计算水位线在河道内的部分
 * 找到水位线与地形断面的左右交点，只返回交点之间的水位数据
 * @param {Array} sectionProfile - 断面地形数据 [[偏心距, 高程], ...]
 * @param {number} waterLevel - 水位高程
 * @returns {Array} - 裁剪后的水位线数据
 */
function calculateWaterLevelInChannel(sectionProfile, waterLevel) {
    if (!sectionProfile || sectionProfile.length < 2) return [];

    // 找到所有与水位线相交的点
    const intersections = [];

    for (let i = 0; i < sectionProfile.length - 1; i++) {
        const [x1, y1] = sectionProfile[i];
        const [x2, y2] = sectionProfile[i + 1];

        // 检查这条线段是否与水位线相交
        if ((y1 <= waterLevel && y2 >= waterLevel) || (y1 >= waterLevel && y2 <= waterLevel)) {
            // 计算交点的x坐标（线性插值）
            if (y1 === y2) {
                // 水平线段，取中点
                intersections.push((x1 + x2) / 2);
            } else {
                const x = x1 + (waterLevel - y1) * (x2 - x1) / (y2 - y1);
                intersections.push(x);
            }
        }
    }

    // 如果没有交点或只有一个交点，返回空数组（水位低于地形最低点或高于最高点）
    if (intersections.length < 2) {
        return [];
    }

    // 取最左和最右的交点作为水位线的边界
    const leftX = Math.min(...intersections);
    const rightX = Math.max(...intersections);

    // 生成水位线数据：从左交点到右交点
    return [
        [leftX, waterLevel],
        [rightX, waterLevel]
    ];
}

/**
 * 渲染侧边栏结论与指标
 */
function renderConclusion(data, descText, currentStatus) {
    const textDom = document.getElementById('conclusionText');
    if (textDom) textDom.innerText = descText;

    const statsGrid = document.getElementById('statsGrid');
    if (!statsGrid) return;

    statsGrid.innerHTML = '';

    const icons = {
        waterLevel: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L12 22M12 2L8 6M12 2L16 6"/><path d="M4 12h16" stroke-dasharray="2,2"/><path d="M6 18c1.5-1.5 3-2 6-2s4.5.5 6 2"/></svg>`,
        flow: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 4L12 20M12 20L6 14M12 20L18 14"/><path d="M4 8h4M16 8h4"/></svg>`,
        time: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>`,
        flood: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17h18M5 12h14M7 7h10"/></svg>`
    };

    // 预报数据指标
    const forecastMetrics = [
        { label: '预报最高水位', value: data.Max_Level || data.Max_Z, unit: 'm', icon: icons.waterLevel },
        { label: '预报洪峰流量', value: data.Max_Qischarge || data.Max_Discharge || data.Max_Q || data.Max_InQ, unit: 'm³/s', icon: icons.flow },
        { label: '洪峰到达时间', value: formatShortTime(data.MaxQ_AtTime || data.MaxZ_Time || data.MaxInQ_Time), unit: '', icon: icons.time },
        { label: '总过洪量', value: data.Total_Flood, unit: '万m³', icon: icons.flood }
    ];

    // 实测数据指标
    const realtimeMetrics = [
        { label: '当前水位', value: currentStatus ? (currentStatus.rz || currentStatus.z) : '--', unit: 'm', icon: icons.waterLevel },
        { label: '当前流量', value: currentStatus ? (currentStatus.q || currentStatus.otq || currentStatus.inq) : '--', unit: 'm³/s', icon: icons.flow }
    ];

    // 渲染预报数据部分
    forecastMetrics.forEach(m => {
        const card = document.createElement('div');
        card.className = 'stat-card';
        card.innerHTML = `
            <div class="stat-icon">${m.icon}</div>
            <div class="stat-info">
                <div class="stat-label">${m.label}</div>
                <div class="stat-value">${typeof m.value === 'number' ? formatNumber(m.value) : (m.value || '--')}<span class="unit">${m.unit}</span></div>
            </div>
        `;
        statsGrid.appendChild(card);
    });

    // 添加分隔标识
    const divider = document.createElement('div');
    divider.className = 'stats-divider';
    divider.innerHTML = '<span>当前实测数据</span>';
    statsGrid.appendChild(divider);

    // 渲染实测数据部分
    realtimeMetrics.forEach(m => {
        const card = document.createElement('div');
        card.className = 'stat-card highlight-card';
        card.innerHTML = `
            <div class="stat-icon">${m.icon}</div>
            <div class="stat-info">
                <div class="stat-label">${m.label}</div>
                <div class="stat-value">${typeof m.value === 'number' ? formatNumber(m.value) : (m.value || '--')}<span class="unit">${m.unit}</span></div>
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
    return `${m}-${d} ${h}:${min}`;
}

function formatNumber(num) {
    return (typeof num === 'number') ? parseFloat(num.toFixed(2)) : num;
}

/**
 * 初始化地图
 */
function initMap() {
    require([
        "esri/WebMap",
        "esri/views/MapView",
        "esri/portal/Portal"
    ], function (WebMap, MapView, Portal) {
        const portal = new Portal({ url: "https://map.slt.henan.gov.cn/geoscene" });
        const webmap = new WebMap({ portalItem: { id: "0217daabff7a4b45a0cca3f975efa7f3", portal: portal } });
        const view = new MapView({
            container: "viewDiv",
            map: webmap,
            center: [114.057818, 35.826884],
            zoom: 10
        });
    });
}

// 启动
init();
