// ============================================================
// ECharts 图表初始化 — AI Content Tool
// ============================================================

var chartInstances = {};

/**
 * 初始化所有图表，绑定数据。
 * @param {Object} data - 来自 /api/stats 的统计数据
 */
function initCharts(data) {
    if (!data) return;

    initStyleChart(data.style_counts || {});
    initProductChart(data.product_counts || {});
    initTrendChart(data.daily_trend || {});
}

/**
 * 柱状图：各风格 Prompt 生成数量
 */
function initStyleChart(styleCounts) {
    var dom = document.getElementById('chartStyle');
    if (!dom) return;

    if (!chartInstances.style) {
        chartInstances.style = echarts.init(dom);
        new ResizeObserver(function() {
            chartInstances.style.resize();
        }).observe(dom.parentElement);
    }

    var names = Object.keys(styleCounts);
    var values = Object.values(styleCounts);

    var option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            axisPointer: { type: 'shadow' },
            backgroundColor: 'rgba(22, 33, 62, 0.9)',
            borderColor: '#2A3A5E',
            textStyle: { color: '#FFFFFF', fontSize: 12 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '12%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: names.length ? names : ['暂无数据'],
            axisLabel: {
                color: '#A0B0C8',
                fontSize: 12,
                rotate: names.length > 4 ? 15 : 0
            },
            axisLine: { lineStyle: { color: '#2A3A5E' } },
            axisTick: { alignWithLabel: true }
        },
        yAxis: {
            type: 'value',
            minInterval: 1,
            axisLabel: { color: '#A0B0C8' },
            splitLine: { lineStyle: { color: '#1E2A4A', type: 'dashed' } },
            axisLine: { show: false }
        },
        series: [{
            type: 'bar',
            data: values.length ? values : [0],
            itemStyle: {
                borderRadius: [4, 4, 0, 0],
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: '#3A6FB5' },
                    { offset: 1, color: '#2B579A' }
                ])
            },
            emphasis: {
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: '#4A8FD5' },
                        { offset: 1, color: '#3A6FB5' }
                    ])
                }
            },
            animationDuration: 800,
            animationEasing: 'elasticOut'
        }],
        // 图例在底部
        legend: {
            bottom: 0,
            textStyle: { color: '#A0B0C8', fontSize: 12 }
        }
    };

    chartInstances.style.setOption(option, true);
}

/**
 * 饼图：各产品 Prompt 占比
 */
function initProductChart(productCounts) {
    var dom = document.getElementById('chartProduct');
    if (!dom) return;

    if (!chartInstances.product) {
        chartInstances.product = echarts.init(dom);
        new ResizeObserver(function() {
            chartInstances.product.resize();
        }).observe(dom.parentElement);
    }

    var entries = Object.entries(productCounts);
    var pieData = entries.map(function(e) {
        return { name: e[0], value: e[1] };
    });

    if (!pieData.length) {
        pieData = [{ name: '暂无数据', value: 1 }];
    }

    var option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)',
            backgroundColor: 'rgba(22, 33, 62, 0.9)',
            borderColor: '#2A3A5E',
            textStyle: { color: '#FFFFFF', fontSize: 12 }
        },
        series: [{
            type: 'pie',
            radius: ['35%', '65%'],
            center: ['50%', '45%'],
            avoidLabelOverlap: true,
            padAngle: 2,
            itemStyle: {
                borderRadius: 6,
                borderColor: '#16213E',
                borderWidth: 2
            },
            label: {
                show: true,
                color: '#FFFFFF',
                fontSize: 12,
                formatter: '{b}\n{d}%'
            },
            emphasis: {
                label: {
                    show: true,
                    fontSize: 14,
                    fontWeight: 'bold'
                }
            },
            labelLine: {
                lineStyle: { color: '#2A3A5E' }
            },
            data: pieData,
            animationDuration: 800,
            animationEasing: 'elasticOut'
        }],
        // 图例在底部
        legend: {
            bottom: 0,
            textStyle: { color: '#A0B0C8', fontSize: 12 },
            type: 'scroll'
        },
        color: ['#2B579A', '#00BFA5', '#FF9800', '#5B9BD5', '#26C6DA', '#AB47BC', '#EF5350', '#66BB6A']
    };

    chartInstances.product.setOption(option, true);
}

/**
 * 折线图：每日生成量趋势
 */
function initTrendChart(dailyTrend) {
    var dom = document.getElementById('chartTrend');
    if (!dom) return;

    if (!chartInstances.trend) {
        chartInstances.trend = echarts.init(dom);
        new ResizeObserver(function() {
            chartInstances.trend.resize();
        }).observe(dom.parentElement);
    }

    var dates = Object.keys(dailyTrend);
    var counts = Object.values(dailyTrend);

    var option = {
        backgroundColor: 'transparent',
        tooltip: {
            trigger: 'axis',
            backgroundColor: 'rgba(22, 33, 62, 0.9)',
            borderColor: '#2A3A5E',
            textStyle: { color: '#FFFFFF', fontSize: 12 }
        },
        grid: {
            left: '3%',
            right: '4%',
            bottom: '15%',
            containLabel: true
        },
        xAxis: {
            type: 'category',
            data: dates.length ? dates : ['暂无数据'],
            boundaryGap: false,
            axisLabel: {
                color: '#A0B0C8',
                fontSize: 12,
                rotate: dates.length > 5 ? 30 : 0
            },
            axisLine: { lineStyle: { color: '#2A3A5E' } },
            splitLine: { show: false }
        },
        yAxis: {
            type: 'value',
            minInterval: 1,
            axisLabel: { color: '#A0B0C8' },
            splitLine: { lineStyle: { color: '#1E2A4A', type: 'dashed' } },
            axisLine: { show: false }
        },
        series: [{
            type: 'line',
            smooth: true,
            data: counts.length ? counts : [0],
            symbol: 'circle',
            symbolSize: 8,
            lineStyle: {
                width: 3,
                color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                    { offset: 0, color: '#2B579A' },
                    { offset: 1, color: '#00BFA5' }
                ])
            },
            itemStyle: {
                color: '#00BFA5',
                borderColor: '#FFFFFF',
                borderWidth: 2
            },
            areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                    { offset: 0, color: 'rgba(0, 191, 165, 0.3)' },
                    { offset: 1, color: 'rgba(0, 191, 165, 0.02)' }
                ])
            },
            animationDuration: 1000,
            animationEasing: 'cubicOut'
        }],
        legend: {
            bottom: 0,
            textStyle: { color: '#A0B0C8', fontSize: 12 }
        }
    };

    chartInstances.trend.setOption(option, true);
}
