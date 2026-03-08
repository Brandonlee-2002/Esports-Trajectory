"""
Visualization utilities for Esports Trajectory analysis.
Provides consistent styling and reusable plotting functions.
"""

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, List, Tuple

# Color palette for consistent styling
COLORS = {
    'primary': '#4CAF50',
    'secondary': '#2196F3',
    'accent': '#FF9800',
    'danger': '#f44336',
    'neutral': '#9E9E9E',
    'background': '#f8f9fa'
}

REGION_COLORS = {
    'LCK': '#E31937',
    'LPL': '#C8102E', 
    'LEC': '#0A74DA',
    'LCS': '#003366',
    'PCS': '#00A651',
    'VCS': '#DA251D',
    'CBLOL': '#009C3B',
    'LJL': '#BC002D',
    'LLA': '#006847'
}

ROLE_COLORS = {
    'Top': '#F44336',
    'Jungle': '#4CAF50',
    'Mid': '#2196F3',
    'ADC': '#FF9800',
    'Support': '#9C27B0'
}


def apply_default_layout(fig: go.Figure, title: str = None) -> go.Figure:
    """Apply consistent layout styling to a plotly figure."""
    fig.update_layout(
        title=title,
        font=dict(family="Inter, sans-serif", size=12),
        plot_bgcolor='white',
        paper_bgcolor='white',
        margin=dict(l=60, r=40, t=60, b=60),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#eee')
    return fig


def career_length_histogram(
    df: pd.DataFrame,
    column: str = 'career_length_years',
    title: str = 'Distribution of Career Lengths',
    show_stats: bool = True,
    nbins: int = 30
) -> go.Figure:
    """Create a histogram of career lengths with optional statistics overlay."""
    
    fig = px.histogram(
        df,
        x=column,
        nbins=nbins,
        color_discrete_sequence=[COLORS['primary']]
    )
    
    if show_stats:
        mean_val = df[column].mean()
        median_val = df[column].median()
        
        fig.add_vline(
            x=mean_val, 
            line_dash="dash", 
            line_color=COLORS['secondary'],
            annotation_text=f"Mean: {mean_val:.1f}",
            annotation_position="top right"
        )
        fig.add_vline(
            x=median_val, 
            line_dash="dot", 
            line_color=COLORS['accent'],
            annotation_text=f"Median: {median_val:.1f}",
            annotation_position="top left"
        )
    
    fig.update_layout(
        xaxis_title='Career Length (Years)',
        yaxis_title='Number of Players',
        bargap=0.1
    )
    
    return apply_default_layout(fig, title)


def career_boxplot_by_category(
    df: pd.DataFrame,
    category_col: str,
    value_col: str = 'career_length_years',
    title: str = None,
    color_map: dict = None
) -> go.Figure:
    """Create boxplots comparing career lengths across categories."""
    
    if color_map is None:
        color_map = REGION_COLORS if 'region' in category_col.lower() else ROLE_COLORS
    
    fig = px.box(
        df,
        x=category_col,
        y=value_col,
        color=category_col,
        color_discrete_map=color_map
    )
    
    fig.update_layout(
        xaxis_title=category_col.replace('_', ' ').title(),
        yaxis_title='Career Length (Years)',
        showlegend=False
    )
    
    return apply_default_layout(fig, title)


def regional_comparison_bar(
    df: pd.DataFrame,
    region_col: str = 'primary_region',
    value_col: str = 'career_length_years',
    agg_func: str = 'mean',
    title: str = 'Career Metrics by Region'
) -> go.Figure:
    """Create a bar chart comparing metrics across regions."""
    
    agg_data = df.groupby(region_col)[value_col].agg([agg_func, 'std', 'count'])
    agg_data = agg_data.sort_values(agg_func, ascending=False)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=agg_data.index,
        y=agg_data[agg_func],
        error_y=dict(type='data', array=agg_data['std']),
        marker_color=[REGION_COLORS.get(r, COLORS['neutral']) for r in agg_data.index],
        text=[f"n={int(c)}" for c in agg_data['count']],
        textposition='outside'
    ))
    
    fig.update_layout(
        xaxis_title='Region',
        yaxis_title=f'{agg_func.title()} {value_col.replace("_", " ").title()}'
    )
    
    return apply_default_layout(fig, title)


def promotion_funnel(
    df: pd.DataFrame,
    starting_tier_col: str = 'starting_tier',
    promoted_col: str = 'promoted_tier2_to_tier1',
    title: str = 'Tier 2 to Tier 1 Promotion Funnel'
) -> go.Figure:
    """Create a funnel chart showing tier transition rates."""
    
    tier2_players = df[df[starting_tier_col] == 2]
    total_tier2 = len(tier2_players)
    promoted = tier2_players[promoted_col].sum()
    not_promoted = total_tier2 - promoted
    
    fig = go.Figure(go.Funnel(
        y=['Started in Tier 2', 'Promoted to Tier 1'],
        x=[total_tier2, promoted],
        textposition="inside",
        textinfo="value+percent initial",
        marker=dict(color=[COLORS['secondary'], COLORS['primary']])
    ))
    
    return apply_default_layout(fig, title)


def promotion_pie_chart(
    df: pd.DataFrame,
    promoted_col: str = 'promoted_tier2_to_tier1',
    starting_tier_col: str = 'starting_tier',
    title: str = 'Tier 2 Player Outcomes'
) -> go.Figure:
    """Create a pie chart showing promotion outcomes."""
    
    tier2_players = df[df[starting_tier_col] == 2]
    promoted = tier2_players[promoted_col].sum()
    not_promoted = len(tier2_players) - promoted
    
    fig = go.Figure(data=[go.Pie(
        labels=['Did Not Promote', 'Promoted to Tier 1'],
        values=[not_promoted, promoted],
        marker=dict(colors=[COLORS['danger'], COLORS['primary']]),
        hole=0.4,
        textinfo='percent+label'
    )])
    
    return apply_default_layout(fig, title)


def time_to_promotion_histogram(
    df: pd.DataFrame,
    time_col: str = 'time_to_tier1_months',
    title: str = 'Time to Tier 1 Promotion'
) -> go.Figure:
    """Create a histogram of time to promotion."""
    
    promoted = df[df[time_col].notna()]
    
    fig = px.histogram(
        promoted,
        x=time_col,
        nbins=20,
        color_discrete_sequence=[COLORS['primary']]
    )
    
    mean_time = promoted[time_col].mean()
    fig.add_vline(
        x=mean_time,
        line_dash="dash",
        line_color=COLORS['accent'],
        annotation_text=f"Avg: {mean_time:.0f} months"
    )
    
    fig.update_layout(
        xaxis_title='Months to Promotion',
        yaxis_title='Number of Players'
    )
    
    return apply_default_layout(fig, title)


def survival_curve(
    df: pd.DataFrame,
    time_col: str = 'career_length_months',
    event_col: str = 'is_retired',
    group_col: Optional[str] = None,
    title: str = 'Career Survival Curve'
) -> go.Figure:
    """
    Create a Kaplan-Meier style survival curve.
    Note: For proper survival analysis, use the lifelines library.
    This is a simplified visualization.
    """
    
    fig = go.Figure()
    
    if group_col is None:
        sorted_times = df[time_col].sort_values()
        n = len(sorted_times)
        survival_prob = [(n - i) / n for i in range(n)]
        
        fig.add_trace(go.Scatter(
            x=sorted_times,
            y=survival_prob,
            mode='lines',
            name='All Players',
            line=dict(color=COLORS['primary'], width=2)
        ))
    else:
        color_map = REGION_COLORS if 'region' in group_col.lower() else ROLE_COLORS
        for group in df[group_col].unique():
            group_data = df[df[group_col] == group]
            sorted_times = group_data[time_col].sort_values()
            n = len(sorted_times)
            survival_prob = [(n - i) / n for i in range(n)]
            
            fig.add_trace(go.Scatter(
                x=sorted_times,
                y=survival_prob,
                mode='lines',
                name=group,
                line=dict(color=color_map.get(group, COLORS['neutral']), width=2)
            ))
    
    fig.update_layout(
        xaxis_title='Career Duration (Months)',
        yaxis_title='Proportion Still Active',
        yaxis=dict(range=[0, 1])
    )
    
    return apply_default_layout(fig, title)


def create_summary_metrics_figure(
    metrics: dict,
    title: str = 'Key Metrics'
) -> go.Figure:
    """Create a figure displaying key metrics as indicator cards."""
    
    n_metrics = len(metrics)
    fig = make_subplots(
        rows=1, cols=n_metrics,
        specs=[[{"type": "indicator"}] * n_metrics]
    )
    
    for i, (name, value) in enumerate(metrics.items()):
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=value,
                title={"text": name},
                number={"font": {"size": 40}}
            ),
            row=1, col=i+1
        )
    
    fig.update_layout(height=200)
    return apply_default_layout(fig, title)


def role_distribution_pie(
    df: pd.DataFrame,
    role_col: str = 'primary_role',
    title: str = 'Player Distribution by Role'
) -> go.Figure:
    """Create a pie chart showing role distribution."""
    
    role_counts = df[role_col].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=role_counts.index,
        values=role_counts.values,
        marker=dict(colors=[ROLE_COLORS.get(r, COLORS['neutral']) for r in role_counts.index]),
        hole=0.3
    )])
    
    return apply_default_layout(fig, title)


def regional_heatmap(
    df: pd.DataFrame,
    region_col: str = 'primary_region',
    metric_cols: List[str] = None,
    title: str = 'Regional Metrics Heatmap'
) -> go.Figure:
    """Create a heatmap comparing multiple metrics across regions."""
    
    if metric_cols is None:
        metric_cols = ['career_length_years', 'num_teams', 'num_regions']
    
    agg_data = df.groupby(region_col)[metric_cols].mean()
    
    # Normalize for heatmap
    normalized = (agg_data - agg_data.min()) / (agg_data.max() - agg_data.min())
    
    fig = go.Figure(data=go.Heatmap(
        z=normalized.values,
        x=metric_cols,
        y=agg_data.index,
        colorscale='Viridis',
        text=agg_data.values.round(2),
        texttemplate="%{text}",
        textfont={"size": 10}
    ))
    
    fig.update_layout(
        xaxis_title='Metric',
        yaxis_title='Region'
    )
    
    return apply_default_layout(fig, title)
