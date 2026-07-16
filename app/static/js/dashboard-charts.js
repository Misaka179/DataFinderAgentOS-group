var DashboardCharts = (function () {
    var donutChart = null, lineChart = null, barChart = null;
    var donutDom, lineDom, barDom;

    function init(donutId, lineId, barId) {
        donutDom = document.getElementById(donutId);
        lineDom = document.getElementById(lineId);
        barDom = document.getElementById(barId);
        if (donutDom) donutChart = echarts.init(donutDom);
        if (lineDom) lineChart = echarts.init(lineDom);
        if (barDom) barChart = echarts.init(barDom);
        window.addEventListener('resize', function () {
            if (donutChart) donutChart.resize();
            if (lineChart) lineChart.resize();
            if (barChart) barChart.resize();
        });
    }

    function renderDonut(data) {
        if (!donutChart) return;
        var total = data.reduce(function (s, d) { return s + d.value; }, 0);
        var ratio = total > 0 ? (data[0] ? (data[0].value / total * 100).toFixed(1) : 0) : 0;
        donutChart.setOption({
            tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
            graphic: [{
                type: 'text', left: 'center', top: '38%',
                style: { text: ratio + '%', fill: '#1e293b', fontSize: 26, fontWeight: 700, textAlign: 'center' }
            }, {
                type: 'text', left: 'center', top: '54%',
                style: { text: '深度采集率', fill: '#94a3b8', fontSize: 12, textAlign: 'center' }
            }],
            series: [{
                type: 'pie', radius: ['52%', '75%'], center: ['50%', '45%'],
                avoidLabelOverlap: true, label: { show: true, position: 'outside', formatter: '{b}\n{d}%', fontSize: 11, color: '#64748b', lineHeight: 16 },
                labelLine: { length: 8, length2: 6 },
                emphasis: { label: { show: true, fontSize: 13, fontWeight: 'bold' } },
                data: data,
                color: ['#22c55e', '#e2e8f0']
            }]
        });
    }

    function renderLine(data) {
        if (!lineChart) return;
        var dates = data.map(function (d) { return d.date; });
        var counts = data.map(function (d) { return d.count; });
        lineChart.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: 40, right: 20, bottom: 30, top: 20 },
            xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
            yAxis: { type: 'value', minInterval: 1 },
            series: [{
                type: 'line', smooth: true, data: counts,
                lineStyle: { width: 3, color: '#3b82f6' },
                itemStyle: { color: '#3b82f6' },
                areaStyle: { color: 'rgba(59,130,246,0.15)' }
            }]
        });
    }

    function renderBar(data) {
        if (!barChart) return;
        var names = data.map(function (d) { return d.name; });
        var values = data.map(function (d) { return d.value; });
        var colors = ['#22c55e', '#3b82f6', '#a855f7', '#f97316', '#ef4444', '#94a3b8'];
        barChart.setOption({
            tooltip: { trigger: 'axis' },
            grid: { left: 50, right: 20, bottom: 30, top: 20 },
            xAxis: { type: 'category', data: names, axisLabel: { fontSize: 11 } },
            yAxis: { type: 'value', minInterval: 1 },
            series: [{
                type: 'bar', data: values.map(function (v, i) {
                    return { value: v, itemStyle: { color: colors[i % colors.length] } };
                }),
                barWidth: 28, borderRadius: [4, 4, 0, 0]
            }]
        });
    }

    function updateAll(data) {
        if (data.deep_coverage) renderDonut(data.deep_coverage);
        if (data.daily_trend) renderLine(data.daily_trend);
        if (data.task_status_bar) renderBar(data.task_status_bar);
    }

    return { init: init, updateAll: updateAll, renderDonut: renderDonut, renderLine: renderLine, renderBar: renderBar };
})();
