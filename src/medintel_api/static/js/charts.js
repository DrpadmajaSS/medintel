/**
 * MedIntel Charting Module using Chart.js.
 * Renders 365-day historical dispensing curves, sparkline trends, and network health donut charts.
 */

let modalUtilChartInstance = null;
let donutChartInstance = null;

function renderSparkline(canvasId, color, dataPoints) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  const existingChart = Chart.getChart(ctx);
  if (existingChart) existingChart.destroy();

  const labels = dataPoints.map((_, i) => i);

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        data: dataPoints,
        borderColor: color,
        borderWidth: 2,
        pointRadius: 0,
        fill: false,
        tension: 0.4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false }
      },
      scales: {
        x: { display: false },
        y: { display: false }
      }
    }
  });
}

function renderDonutChart(canvasId, healthy = 3, monitor = 2, atRisk = 2) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  if (donutChartInstance) {
    donutChartInstance.destroy();
  }

  donutChartInstance = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Healthy', 'Monitor', 'At Risk'],
      datasets: [{
        data: [healthy, monitor, atRisk],
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
        borderWidth: 0,
        hoverOffset: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleFont: { family: "'Inter', sans-serif", size: 11, weight: '700' },
          bodyFont: { family: "'Inter', sans-serif", size: 11 },
          padding: 8,
          cornerRadius: 6
        }
      }
    }
  });
}

function renderUtilizationChart(canvasId, timeSeries, daysToStockout, predictedDate) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  if (modalUtilChartInstance) {
    modalUtilChartInstance.destroy();
  }

  // Filter to last 60 days of historical data for clean visualization
  const recentPoints = timeSeries.slice(-60);
  const labels = recentPoints.map(p => p.date.substring(5)); // MM-DD
  const dataValues = recentPoints.map(p => p.quantity_used);

  // Compute 7-day rolling average
  const ma7Values = [];
  for (let i = 0; i < dataValues.length; i++) {
    const start = Math.max(0, i - 6);
    const subset = dataValues.slice(start, i + 1);
    const avg = subset.reduce((a, b) => a + b, 0) / subset.length;
    ma7Values.push(round(avg, 1));
  }

  modalUtilChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Daily Dispensed Units',
          data: dataValues,
          backgroundColor: 'rgba(26, 115, 232, 0.12)',
          borderColor: 'rgba(26, 115, 232, 0.85)',
          borderWidth: 1.5,
          pointRadius: 2,
          pointHoverRadius: 5,
          fill: true,
          tension: 0.2
        },
        {
          label: '7-Day Moving Avg (Burn Rate)',
          data: ma7Values,
          borderColor: '#ea8600',
          borderWidth: 2.5,
          borderDash: [4, 4],
          pointRadius: 0,
          fill: false,
          tension: 0.3
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          position: 'top',
          labels: {
            font: { family: "'Inter', sans-serif", size: 11, weight: '600' },
            boxWidth: 12,
            boxHeight: 12
          }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          titleFont: { family: "'Inter', sans-serif", size: 12, weight: '700' },
          bodyFont: { family: "'Inter', sans-serif", size: 11 },
          padding: 10,
          cornerRadius: 6
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { size: 10, family: "'Inter', sans-serif" }, maxTicksLimit: 12 }
        },
        y: {
          grid: { color: '#f1f5f9' },
          ticks: { font: { size: 10, family: "'Inter', sans-serif" }, precision: 0 },
          title: { display: true, text: 'Units Dispensed', font: { size: 10, weight: '600' } }
        }
      }
    }
  });
}

function round(val, decimals) {
  return Number(Math.round(val + 'e' + decimals) + 'e-' + decimals);
}
