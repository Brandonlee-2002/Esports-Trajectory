/**
 * Main JavaScript for Esports Trajectory Dashboard
 * Handles homepage initialization and common functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Theme colors
    const theme = {
        blue: '#5b8bd4',
        blueDark: '#3d6cb3',
        blueLight: '#a8c5e8',
        gold: '#d4a74a',
        goldDark: '#c9a227',
        goldLight: '#e8d4a0'
    };

    // Update homepage metrics (placeholder values - replace with real data)
    const metrics = {
        total: '--',
        avgCareer: '--',
        medianCareer: '--',
        promotion: '--'
    };

    // Update metric elements if they exist
    if (document.getElementById('metric-total')) {
        document.getElementById('metric-total').textContent = metrics.total;
    }
    if (document.getElementById('metric-avg-career')) {
        document.getElementById('metric-avg-career').textContent = metrics.avgCareer;
    }
    if (document.getElementById('metric-median-career')) {
        document.getElementById('metric-median-career').textContent = metrics.medianCareer;
    }
    if (document.getElementById('metric-promotion')) {
        document.getElementById('metric-promotion').textContent = metrics.promotion;
    }

    // Initialize region chart on homepage if element exists
    const regionChartEl = document.getElementById('region-chart');
    if (regionChartEl && typeof Plotly !== 'undefined') {
        initRegionChart(regionChartEl, theme);
    }
});

/**
 * Initialize the region distribution chart on the homepage
 */
function initRegionChart(element, theme) {
    const data = [{
        labels: ['LPL', 'LCK', 'LEC', 'LCS', 'VCS', 'PCS', 'CBLOL', 'LJL', 'LLA'],
        values: [125, 100, 75, 60, 40, 35, 30, 20, 15],
        type: 'pie',
        hole: 0.4,
        marker: {
            colors: [
                theme.gold,      // LPL
                theme.goldDark,  // LCK
                theme.blue,      // LEC
                theme.blueDark,  // LCS
                theme.blueLight, // VCS
                theme.goldLight, // PCS
                theme.blueLight, // CBLOL
                theme.goldLight, // LJL
                theme.blueLight  // LLA
            ]
        },
        textinfo: 'label+percent',
        textposition: 'outside'
    }];

    const layout = {
        margin: { t: 20, b: 20, l: 20, r: 20 },
        showlegend: false,
        height: 350
    };

    Plotly.newPlot(element, data, layout, { responsive: true });
}

/**
 * Utility function to format numbers
 */
function formatNumber(num, decimals = 1) {
    if (typeof num !== 'number' || isNaN(num)) return '--';
    return num.toFixed(decimals);
}

/**
 * Utility function to format percentages
 */
function formatPercent(num, decimals = 1) {
    if (typeof num !== 'number' || isNaN(num)) return '--';
    return num.toFixed(decimals) + '%';
}
