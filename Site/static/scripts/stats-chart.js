let chartInstances = [];

function initCharts(timeframe) {
    const dataset = rawDataMap[timeframe];

    document.getElementById("ath").innerText = `Player Count: ${ath_data["playerCount"]}
    Plays 24h: ${ath_data["plays24h"]}
    Unique Plays 24h: ${ath_data["uniquePlays24h"]}`;

    for (let i = 0; i < 4; i++) {
        const graphInfo = dataset.graphs[i];

        const filteredLabels = [];
        const filteredValues = [];

        graphInfo.values.forEach((val, idx) => {
            if (val !== -1) {
                filteredLabels.push(dataset.labels[idx] || `Point ${idx + 1}`);
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

function switchTimeframe(timeframe, element) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    element.classList.add('active');
    initCharts(timeframe);
}

document.addEventListener("DOMContentLoaded", () => {
    initCharts('day');
});