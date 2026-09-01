let chartInstances = [];
let timeframe = "day";
let rawDataMap = undefined;

function formatTimestamp(value) {
    if (!value) return "Never";
    const date = new Date(value);
    if (isNaN(date)) return "Never";
    return date.toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}

function formatChartLabel(value, currentTimeframe) {
    if (!value) return null;
    const date = new Date(value);
    if (isNaN(date)) return null;
    if (currentTimeframe === "day") {
        return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
    }
    if (currentTimeframe === "month") {
        return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    }
    return date.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function initCharts() {
    const dataset = rawDataMap[timeframe];
    document.getElementById("ath").innerHTML = `
        <div class="ath-stat"><span class="ath-stat-label">Player Count</span><span class="ath-stat-value">${ath_data["playerCount"]}</span><span class="ath-stat-time">${formatTimestamp(ath_data["playerCountAt"])}</span></div>
        <div class="ath-stat"><span class="ath-stat-label">Plays (24h)</span><span class="ath-stat-value">${ath_data["plays24h"]}</span><span class="ath-stat-time">${formatTimestamp(ath_data["plays24hAt"])}</span></div>
        <div class="ath-stat"><span class="ath-stat-label">Unique Plays (24h)</span><span class="ath-stat-value">${ath_data["uniquePlays24h"]}</span><span class="ath-stat-time">${formatTimestamp(ath_data["uniquePlays24hAt"])}</span></div>
    `;

    for (let i = 0; i < 4; i++) {
        const graphInfo = dataset.graphs[i];

        const filteredLabels = [];
        const filteredValues = [];

        graphInfo.values.forEach((val, idx) => {
            if (val !== -1) {
                const label = formatChartLabel(dataset.labels[idx], timeframe);
                filteredLabels.push(label || `Point ${idx + 1}`);
                filteredValues.push(val);
            }
        });

        document.getElementById(`title-${i}`).textContent = graphInfo.title;

        const ctx = document.getElementById(`canvas-${i}`).getContext('2d');

        if (chartInstances[i]) {
            chartInstances[i].destroy();
        }

        chartInstances[i] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: filteredLabels,
                datasets: [{
                    label: graphInfo.title,
                    data: filteredValues,
                    borderColor: '#5bc0de',
                    backgroundColor: 'rgba(91, 192, 222, 0.05)',
                    borderWidth: 2,
                    tension: 0.2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const value = context.parsed.y;
                                return ` ${value}${graphInfo.unit}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: '#2d2d2d' },
                        ticks: { color: '#aaaaaa' }
                    },
                    y: {
                        min: 0,
                        beginAtZero: true,
                        grid: {
                            color: '#2d2d2d'
                        },
                        ticks: {
                            color: '#aaaaaa',
                            stepSize: 1,
                            precision: 0,
                            callback: function (value) {
                                if (Number.isInteger(value)) {
                                    return value;
                                } else {
                                    return Math.round(value)
                                }
                            }
                        }
                    }
                }
            }
        });
    }
}

function switchTimeframe(new_timeframe, element) {
    timeframe = new_timeframe;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    element.classList.add('active');
    initCharts();
}
function doTick() {
    fetch(chart_url).then((raw) => raw.json().then((value) => { rawDataMap = value; initCharts(); }));
    setTimeout(() => doTick(), 60000);
}

doTick();

