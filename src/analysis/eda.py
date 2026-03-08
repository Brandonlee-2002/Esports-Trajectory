"""
Exploratory Data Analysis (EDA) Script
=======================================
Generates EDA results and visualizations for the Esports Career Trajectory project.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Plot settings
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 11

# Color palette (League of Legends inspired - pastel blue & gold)
COLORS = {
    'blue': '#5b8bd4',
    'blue_dark': '#3d6cb3',
    'blue_light': '#a8c5e8',
    'gold': '#d4a74a',
    'gold_dark': '#c9a227',
    'gold_light': '#e8d4a0'
}


def generate_sample_data(n=500):
    """Generate realistic sample data based on expected distributions."""
    np.random.seed(42)
    
    regions = ['LCK', 'LPL', 'LEC', 'LCS', 'PCS', 'VCS', 'CBLOL', 'LJL', 'LLA']
    region_weights = [0.18, 0.22, 0.15, 0.12, 0.08, 0.09, 0.07, 0.05, 0.04]
    roles = ['Top', 'Jungle', 'Mid', 'ADC', 'Support']
    
    region_means = {'LCK': 32, 'LPL': 30, 'LEC': 26, 'LCS': 24, 'PCS': 22, 
                    'VCS': 20, 'CBLOL': 18, 'LJL': 16, 'LLA': 15}
    
    primary_regions = np.random.choice(regions, n, p=region_weights)
    
    career_months = []
    for region in primary_regions:
        mean = region_means[region]
        length = np.random.exponential(scale=mean * 0.8) + 6
        career_months.append(min(max(length, 3), 120))
    
    career_months = np.array(career_months)
    starting_tiers = np.random.choice([1, 2], n, p=[0.35, 0.65])
    
    promoted = []
    time_to_tier1 = []
    for i in range(n):
        if starting_tiers[i] == 1:
            promoted.append(False)
            time_to_tier1.append(0)
        else:
            prob = min(0.45, career_months[i] / 70)
            is_promoted = np.random.random() < prob
            promoted.append(is_promoted)
            time_to_tier1.append(np.random.uniform(6, min(36, career_months[i] * 0.5)) if is_promoted else np.nan)
    
    players = pd.DataFrame({
        'player_id': [f'player_{i:04d}' for i in range(n)],
        'primary_role': np.random.choice(roles, n),
        'nationality': np.random.choice(['KR', 'CN', 'US', 'DE', 'DK', 'BR', 'VN', 'JP', 'TW'], n),
        'current_status': np.random.choice(['Active', 'Retired', 'Inactive'], n, p=[0.25, 0.55, 0.20]),
        'peak_tier': np.where(np.array(promoted) | (starting_tiers == 1), 1, 2)
    })
    
    careers = pd.DataFrame({
        'player_id': players['player_id'],
        'primary_region': primary_regions,
        'career_length_months': career_months,
        'career_length_years': career_months / 12,
        'time_to_tier1_months': time_to_tier1,
        'num_teams': np.random.poisson(lam=2.5, size=n) + 1,
        'num_regions': np.random.choice([1, 2, 3], n, p=[0.72, 0.23, 0.05]),
        'promoted_tier2_to_tier1': promoted,
        'starting_tier': starting_tiers,
        'career_start_year': np.random.choice(range(2013, 2024), n)
    })
    
    return players, careers


def load_or_generate_data():
    """Load processed data or generate sample data."""
    DATA_PATH = Path(__file__).parent.parent.parent / 'data' / 'processed'
    
    players_file = DATA_PATH / 'players_processed.csv'
    careers_file = DATA_PATH / 'career_metrics.csv'
    
    if players_file.exists() and careers_file.exists():
        print("Loading real data...")
        players = pd.read_csv(players_file)
        careers = pd.read_csv(careers_file)
        is_sample = False
    else:
        print("Generating sample data for EDA demonstration...")
        players, careers = generate_sample_data(n=500)
        is_sample = True
    
    return players, careers, is_sample


def run_eda():
    """Run full EDA and generate visualizations."""
    
    # Setup output directory
    REPORTS_PATH = Path(__file__).parent.parent.parent / 'reports'
    REPORTS_PATH.mkdir(exist_ok=True)
    
    # Load data
    players, careers, is_sample = load_or_generate_data()
    df = careers.merge(players, on='player_id')
    
    print(f"\nDataset: {'SAMPLE DATA' if is_sample else 'REAL DATA'}")
    print(f"Total Players: {len(df)}")
    
    # =========================================================================
    # 1. Dataset Summary
    # =========================================================================
    print("\n" + "="*60)
    print("1. DATASET SUMMARY")
    print("="*60)
    
    print("\n** Target Variable **")
    print("- career_length_years: Duration of professional career (continuous)")
    
    print("\n** Features **")
    print(df.dtypes.to_string())
    
    print(f"\n** Shape **: Rows: {df.shape[0]}, Columns: {df.shape[1]}")
    
    # =========================================================================
    # 2. Data Quality
    # =========================================================================
    print("\n" + "="*60)
    print("2. DATA QUALITY ASSESSMENT")
    print("="*60)
    
    missing = df.isnull().sum()
    missing_pct = (missing / len(df) * 100).round(2)
    missing_df = pd.DataFrame({'Missing': missing, 'Percent': missing_pct})
    print("\n** Missing Values **")
    print(missing_df[missing_df['Missing'] > 0].to_string() if missing.sum() > 0 else "No missing values in core columns")
    
    duplicates = df.duplicated(subset=['player_id']).sum()
    print(f"\n** Duplicate player_ids **: {duplicates}")
    
    print(f"\n** Unique Values **")
    print(f"Regions: {df['primary_region'].nunique()} - {sorted(df['primary_region'].unique())}")
    print(f"Roles: {df['primary_role'].nunique()} - {sorted(df['primary_role'].unique())}")
    
    # =========================================================================
    # 3. Descriptive Statistics
    # =========================================================================
    print("\n" + "="*60)
    print("3. DESCRIPTIVE STATISTICS")
    print("="*60)
    
    print("\n** Career Length Statistics (Target Variable) **")
    career_stats = {
        'Mean': df['career_length_years'].mean(),
        'Median': df['career_length_years'].median(),
        'Std Dev': df['career_length_years'].std(),
        'Min': df['career_length_years'].min(),
        'Max': df['career_length_years'].max(),
        'Skewness': df['career_length_years'].skew()
    }
    for stat, value in career_stats.items():
        print(f"{stat}: {value:.3f}")
    
    print("\n** Career Length by Region **")
    region_stats = df.groupby('primary_region')['career_length_years'].agg(['mean', 'median', 'std', 'count'])
    region_stats = region_stats.sort_values('mean', ascending=False).round(2)
    region_stats.columns = ['Mean', 'Median', 'Std', 'Count']
    print(region_stats.to_string())
    
    print("\n** Correlation Matrix **")
    corr_cols = ['career_length_months', 'num_teams', 'num_regions', 'starting_tier', 'career_start_year']
    correlation_matrix = df[corr_cols].corr().round(3)
    print(correlation_matrix.to_string())
    
    # =========================================================================
    # 4. Visualizations
    # =========================================================================
    print("\n" + "="*60)
    print("4. GENERATING VISUALIZATIONS")
    print("="*60)
    
    # Check data completeness for regional/role analysis
    unknown_region_pct = (df['primary_region'] == 'Unknown').mean() * 100
    unknown_role_pct = (df['primary_role'] == 'Unknown').mean() * 100
    print(f"Note: {unknown_region_pct:.1f}% of players have unknown region")
    print(f"Note: {unknown_role_pct:.1f}% of players have unknown role")
    
    # Figure 1: Career Length Distribution (RELIABLE - derived from season appearances)
    fig, ax = plt.subplots(1, 1, figsize=(10, 6))
    
    ax.hist(df['career_length_years'], bins=range(1, 12), color=COLORS['blue'], edgecolor='white', alpha=0.8, align='left')
    ax.axvline(df['career_length_years'].mean(), color=COLORS['gold_dark'], linestyle='--', linewidth=2, 
               label=f"Mean: {df['career_length_years'].mean():.2f} seasons")
    ax.axvline(df['career_length_years'].median(), color=COLORS['gold'], linestyle=':', linewidth=2, 
               label=f"Median: {df['career_length_years'].median():.2f} seasons")
    ax.set_xlabel('Career Length (Seasons)')
    ax.set_ylabel('Number of Players')
    ax.set_title('Distribution of Professional Career Lengths (S6-S15)')
    ax.legend()
    ax.set_xticks(range(1, 11))
    
    plt.tight_layout()
    plt.savefig(REPORTS_PATH / 'eda_fig1_career_distribution.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: eda_fig1_career_distribution.png")
    
    # Skip tier/role/region visualizations if data is incomplete (>50% unknown)
    tier2_df = None
    promo_rate = None
    
    if unknown_region_pct > 50:
        print("Skipped: Regional analysis (insufficient region data - needs enriched data for all seasons)")
    if unknown_role_pct > 50:
        print("Skipped: Role analysis (insufficient role data - needs enriched data for all seasons)")
    print("Skipped: Tier transitions (tier data only available for S6 - not reliable for analysis)")
    
    # Figure 5: Temporal Trends
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    entry_counts = df['career_start_year'].value_counts().sort_index()
    entry_counts.plot(kind='bar', ax=axes[0], color=COLORS['blue'], edgecolor='white')
    axes[0].set_xlabel('Career Start Year')
    axes[0].set_ylabel('Number of New Players')
    axes[0].set_title('New Professional Players per Year')
    axes[0].tick_params(axis='x', rotation=45)
    
    retired_df = df[df['current_status'] == 'Retired']
    cohort_career = retired_df.groupby('career_start_year')['career_length_years'].mean()
    cohort_career.plot(kind='line', marker='o', ax=axes[1], color=COLORS['gold_dark'], linewidth=2, markersize=8)
    axes[1].fill_between(cohort_career.index, cohort_career.values, alpha=0.3, color=COLORS['gold_light'])
    axes[1].set_xlabel('Career Start Year')
    axes[1].set_ylabel('Mean Career Length (Years)')
    axes[1].set_title('Mean Career Length by Start Year (Retired Players)')
    axes[1].set_ylim(bottom=0)
    
    plt.tight_layout()
    plt.savefig(REPORTS_PATH / 'eda_fig5_temporal_trends.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("Saved: eda_fig5_temporal_trends.png")
    
    # =========================================================================
    # 5. Preliminary Insights
    # =========================================================================
    print("\n" + "="*60)
    print("5. PRELIMINARY INSIGHTS & HYPOTHESES")
    print("="*60)
    
    print(f"""
Key Observations (from reliable data):

1. CAREER LENGTH DISTRIBUTION
   - Right-skewed distribution (skewness: {df['career_length_years'].skew():.2f})
   - Median ({df['career_length_years'].median():.2f} seasons) < Mean ({df['career_length_years'].mean():.2f} seasons)
   - Most careers are 1-3 seasons

2. TEMPORAL TRENDS
   - Player entry rates vary by season
   - Career lengths may be affected by era of entry
   
3. DATA GAPS (pending enriched data for all seasons)
   - Regional breakdown: {unknown_region_pct:.1f}% unknown
   - Role breakdown: {unknown_role_pct:.1f}% unknown  
   - Tier transitions: Only S6 has tier data
""")
    
    # Summary for report
    print("\n" + "="*60)
    print("SUMMARY STATISTICS FOR PDF REPORT")
    print("="*60)
    
    summary = {
        'Total Players': len(df),
        'Mean Career (Seasons)': f"{df['career_length_years'].mean():.2f}",
        'Median Career (Seasons)': f"{df['career_length_years'].median():.2f}",
        'Std Dev (Seasons)': f"{df['career_length_years'].std():.2f}",
        'Max Career (Seasons)': f"{df['career_length_years'].max():.0f}",
        'Active Players': f"{(df['current_status']=='Active').sum()} ({(df['current_status']=='Active').mean()*100:.1f}%)"
    }
    
    for key, value in summary.items():
        print(f"{key}: {value}")
    
    print(f"\nFigures saved to: {REPORTS_PATH}")
    
    # =========================================================================
    # 6. Export to Dashboard
    # =========================================================================
    export_to_dashboard(df, region_stats, promo_rate, tier2_df, REPORTS_PATH)
    
    return df, region_stats, promo_rate


def export_to_dashboard(df, region_stats, promo_rate, tier2_df, reports_path):
    """Export EDA results to dashboard JSON and copy figures (only reliable data)."""
    import json
    import shutil
    
    print("\n" + "="*60)
    print("6. EXPORTING TO DASHBOARD")
    print("="*60)
    
    WEBSITE_PATH = Path(__file__).parent.parent.parent / 'website'
    ASSETS_PATH = WEBSITE_PATH / 'assets' / 'figures'
    ASSETS_PATH.mkdir(parents=True, exist_ok=True)
    
    # Only export reliable summary data (from season appearances)
    dashboard_data = {
        'summary': {
            'totalPlayers': int(len(df)),
            'avgCareerYears': round(df['career_length_years'].mean(), 2),
            'medianCareerYears': round(df['career_length_years'].median(), 2),
            'stdCareerYears': round(df['career_length_years'].std(), 2),
            'maxCareerYears': round(df['career_length_years'].max(), 2),
            'skewness': round(df['career_length_years'].skew(), 2),
            'activeRate': round((df['current_status'] == 'Active').mean() * 100, 1),
            'retiredRate': round((df['current_status'] == 'Retired').mean() * 100, 1)
        },
        'dataGaps': {
            'unknownRegionPct': round((df['primary_region'] == 'Unknown').mean() * 100, 1),
            'unknownRolePct': round((df['primary_role'] == 'Unknown').mean() * 100, 1),
            'note': 'Regional, role, and tier data only available for Season 6 players'
        }
    }
    
    # Save JSON data
    json_path = WEBSITE_PATH / 'js' / 'eda_data.json'
    with open(json_path, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    print(f"Saved: {json_path}")
    
    # Copy only reliable figures to website assets
    figure_files = [
        'eda_fig1_career_distribution.png',
        'eda_fig5_temporal_trends.png'
    ]
    
    for fig_file in figure_files:
        src = reports_path / fig_file
        if src.exists():
            dst = ASSETS_PATH / fig_file
            shutil.copy2(src, dst)
            print(f"Copied: {fig_file} -> website/assets/figures/")
    
    print("\nDashboard data updated (reliable data only)!")


if __name__ == "__main__":
    df, region_stats, promo_rate = run_eda()
