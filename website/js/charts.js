/**
 * Chart utilities for Esports Trajectory Dashboard
 * Common chart configurations and helper functions
 */

const ChartTheme = {
    // Pastel blue and gold colors
    blue: '#5b8bd4',
    blueDark: '#3d6cb3',
    blueLight: '#a8c5e8',
    gold: '#d4a74a',
    goldDark: '#c9a227',
    goldLight: '#e8d4a0',
    
    // Neutral colors
    text: '#2c3e50',
    textLight: '#64748b',
    background: '#ffffff',
    grid: '#e2e8f0'
};

// Default Plotly layout settings
const defaultLayout = {
    font: {
        family: 'Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif',
        size: 12,
        color: ChartTheme.text
    },
    paper_bgcolor: ChartTheme.background,
    plot_bgcolor: ChartTheme.background,
    margin: { t: 30, b: 50, l: 60, r: 30 }
};

// Default Plotly config
const defaultConfig = {
    responsive: true,
    displayModeBar: false
};

/**
 * Create a histogram chart
 */
function createHistogram(element, data, options = {}) {
    const trace = {
        x: data.values,
        type: 'histogram',
        nbinsx: options.bins || 20,
        marker: {
            color: options.color || ChartTheme.blue
        }
    };

    const layout = {
        ...defaultLayout,
        xaxis: { title: options.xLabel || '' },
        yaxis: { title: options.yLabel || 'Count' },
        ...options.layout
    };

    Plotly.newPlot(element, [trace], layout, defaultConfig);
}

/**
 * Create a box plot
 */
function createBoxPlot(element, data, options = {}) {
    const traces = data.map((d, i) => ({
        y: d.values,
        type: 'box',
        name: d.name,
        marker: {
            color: options.colors ? options.colors[i % options.colors.length] : ChartTheme.blue
        },
        boxpoints: false
    }));

    const layout = {
        ...defaultLayout,
        yaxis: { title: options.yLabel || '' },
        showlegend: options.showLegend || false,
        ...options.layout
    };

    Plotly.newPlot(element, traces, layout, defaultConfig);
}

/**
 * Create a bar chart
 */
function createBarChart(element, data, options = {}) {
    const trace = {
        x: data.labels,
        y: data.values,
        type: 'bar',
        marker: {
            color: options.colors || ChartTheme.blue
        }
    };

    if (data.errors) {
        trace.error_y = {
            type: 'data',
            array: data.errors,
            visible: true,
            color: ChartTheme.textLight
        };
    }

    const layout = {
        ...defaultLayout,
        xaxis: { title: options.xLabel || '' },
        yaxis: { title: options.yLabel || '' },
        ...options.layout
    };

    Plotly.newPlot(element, [trace], layout, defaultConfig);
}

/**
 * Create a pie chart
 */
function createPieChart(element, data, options = {}) {
    const trace = {
        labels: data.labels,
        values: data.values,
        type: 'pie',
        hole: options.donut ? 0.4 : 0,
        marker: {
            colors: options.colors || [ChartTheme.blue, ChartTheme.gold]
        },
        textinfo: options.textInfo || 'percent+label'
    };

    const layout = {
        ...defaultLayout,
        showlegend: options.showLegend || false,
        ...options.layout
    };

    Plotly.newPlot(element, [trace], layout, defaultConfig);
}

/**
 * Add reference lines to a chart
 */
function addReferenceLines(element, lines) {
    const shapes = lines.map(line => ({
        type: 'line',
        x0: line.x,
        x1: line.x,
        y0: 0,
        y1: line.yMax || 1,
        line: {
            color: line.color || ChartTheme.goldDark,
            dash: line.dash || 'dash',
            width: 2
        }
    }));

    const annotations = lines.map(line => ({
        x: line.x,
        y: line.yMax || 1,
        text: line.label,
        showarrow: false,
        font: { color: line.color || ChartTheme.goldDark }
    }));

    Plotly.relayout(element, { shapes, annotations });
}
