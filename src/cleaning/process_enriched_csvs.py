"""
Process Enriched CSV Data
=========================
Transforms the enriched player_careers CSV files (S6-S15) into processed data.
These CSVs contain Team, League, Role, and Tier info for all seasons.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Season to Year mapping
SEASON_TO_YEAR = {
    'S6': 2016, 'S7': 2017, 'S8': 2018, 'S9': 2019, 'S10': 2020,
    'S11': 2021, 'S12': 2022, 'S13': 2023, 'S14': 2024, 'S15': 2025
}

# League to Region mapping
LEAGUE_TO_REGION = {
    'LCK': 'LCK', 'LPL': 'LPL', 'LEC': 'LEC', 'LCS': 'LCS',
    'PCS': 'PCS', 'VCS': 'VCS', 'CBLOL': 'CBLOL', 'LJL': 'LJL', 
    'LLA': 'LLA', 'TCL': 'TCL', 'LCO': 'LCO',
    # Older league names
    'NA LCS': 'LCS', 'EU LCS': 'LEC', 'OGN': 'LCK', 'GPL': 'PCS',
    'LMS': 'PCS', 'CBLoL': 'CBLOL', 'NALCS': 'LCS', 'EULCS': 'LEC',
    # Regional naming variations in data
    'Brazil': 'CBLOL', 'Vietnam': 'VCS', 
    'Latin America': 'LLA', 'LAN': 'LLA', 'LAS': 'LLA',
    # Tier 2 leagues
    'LCK CL': 'LCK', 'LDL': 'LPL', 'EUM': 'LEC', 'LTAN': 'LCS',
    'NLC': 'LEC', 'LFL': 'LEC', 'PRM': 'LEC', 'SL': 'LEC',
}

# Tier mapping
TIER_MAP = {'S': 1, 'A': 2, 'B': 2, 's': 1, 'a': 2, 'b': 2}


def load_enriched_csvs(csv_dir):
    """Load all enriched CSV files from directory."""
    all_data = {}
    
    for season in ['S6', 'S7', 'S8', 'S9', 'S10', 'S11', 'S12', 'S13', 'S14', 'S15']:
        csv_path = csv_dir / f'player_careers_{season}.csv'
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            all_data[season] = df
            print(f"  Loaded {season}: {len(df)} players")
        else:
            print(f"  Missing: {csv_path}")
    
    return all_data


def process_player_careers(all_data):
    """Process all season data to derive career metrics with enriched info."""
    
    # Track player data across seasons
    player_seasons = {}
    player_info = {}
    
    for season, df in all_data.items():
        year = SEASON_TO_YEAR.get(season, 2020)
        
        for _, row in df.iterrows():
            player = row.get('Player')
            if pd.isna(player):
                continue
            player = str(player).strip()
            
            if player not in player_seasons:
                player_seasons[player] = []
                player_info[player] = {
                    'teams': [],
                    'leagues': [],
                    'roles': [],
                    'tiers': [],
                    'countries': [],
                    'total_games': 0,
                    'win_rates': [],
                    'kdas': []
                }
            
            player_seasons[player].append(season)
            info = player_info[player]
            
            # Collect enriched data
            if not pd.isna(row.get('Team')):
                info['teams'].append(str(row['Team']))
            if not pd.isna(row.get('League')):
                info['leagues'].append(str(row['League']))
            if not pd.isna(row.get('Role')):
                info['roles'].append(str(row['Role']))
            if not pd.isna(row.get('Tier')):
                info['tiers'].append(str(row['Tier']))
            if not pd.isna(row.get('Country')):
                info['countries'].append(str(row['Country']))
            
            # Performance stats
            try:
                games = row.get('Games')
                if not pd.isna(games):
                    info['total_games'] += int(games)
            except (ValueError, TypeError):
                pass
            
            try:
                wr = row.get('Win rate')
                if not pd.isna(wr):
                    if isinstance(wr, str):
                        wr = float(wr.replace('%', '')) / 100
                    info['win_rates'].append(float(wr))
            except (ValueError, TypeError):
                pass
            
            try:
                kda = row.get('KDA')
                if not pd.isna(kda):
                    info['kdas'].append(float(kda))
            except (ValueError, TypeError):
                pass
    
    # Build processed dataframes
    players_data = []
    careers_data = []
    
    for player, seasons in player_seasons.items():
        info = player_info[player]
        
        # Career duration
        season_nums = [int(s[1:]) for s in seasons]
        first_season = min(season_nums)
        last_season = max(season_nums)
        career_length_years = last_season - first_season + 1
        num_seasons = len(set(seasons))
        
        # Primary role (most common)
        role = get_most_common(info['roles'])
        role = standardize_role(role)
        
        # Primary region (from league)
        league = get_most_common(info['leagues'])
        region = LEAGUE_TO_REGION.get(league, 'Unknown') if league else 'Unknown'
        
        # Country
        country = get_most_common(info['countries'])
        country = standardize_country(country)
        
        # Tier info
        tier_raw = get_most_common(info['tiers'])
        starting_tier = TIER_MAP.get(tier_raw, 2) if tier_raw else 2
        
        # Check if ever had Tier 1
        ever_tier1 = any(TIER_MAP.get(t, 2) == 1 for t in info['tiers'])
        
        # Status
        if 'S15' in seasons:
            status = 'Active'
        elif 'S14' in seasons:
            status = 'Inactive'
        else:
            status = 'Retired'
        
        # Number of unique teams/regions
        num_teams = len(set(info['teams'])) if info['teams'] else 1
        unique_regions = set(LEAGUE_TO_REGION.get(l, 'Unknown') for l in info['leagues'] if l)
        num_regions = len(unique_regions) if unique_regions else 1
        
        # Players data
        players_data.append({
            'player_id': player,
            'primary_role': role,
            'nationality': country,
            'current_status': status,
            'peak_tier': 1 if ever_tier1 else 2
        })
        
        # Career metrics
        careers_data.append({
            'player_id': player,
            'primary_region': region,
            'primary_league': league if league else 'Unknown',
            'career_length_months': career_length_years * 12,
            'career_length_years': float(career_length_years),
            'num_seasons_active': num_seasons,
            'time_to_tier1_months': np.nan if starting_tier == 1 else (12 if ever_tier1 else np.nan),
            'num_teams': num_teams,
            'num_regions': num_regions,
            'promoted_tier2_to_tier1': starting_tier == 2 and ever_tier1,
            'starting_tier': starting_tier,
            'career_start_year': 2010 + first_season,
            'career_end_year': 2010 + last_season,
            'total_games': info['total_games'],
            'avg_winrate': np.mean(info['win_rates']) if info['win_rates'] else np.nan,
            'avg_kda': np.mean(info['kdas']) if info['kdas'] else np.nan
        })
    
    players_df = pd.DataFrame(players_data)
    careers_df = pd.DataFrame(careers_data)
    
    return players_df, careers_df


def get_most_common(lst):
    """Get most common non-null value from list."""
    filtered = [x for x in lst if x and not pd.isna(x)]
    if not filtered:
        return None
    from collections import Counter
    return Counter(filtered).most_common(1)[0][0]


def standardize_role(role):
    """Standardize role names."""
    if not role or pd.isna(role):
        return 'Unknown'
    role = str(role).strip().lower()
    mapping = {
        'top': 'Top', 'toplane': 'Top',
        'jungle': 'Jungle', 'jng': 'Jungle', 'jungler': 'Jungle', 'jg': 'Jungle',
        'mid': 'Mid', 'middle': 'Mid', 'midlane': 'Mid',
        'adc': 'ADC', 'bot': 'ADC', 'ad carry': 'ADC', 'marksman': 'ADC', 'bottom': 'ADC',
        'support': 'Support', 'sup': 'Support', 'supp': 'Support'
    }
    return mapping.get(role, 'Unknown')


def standardize_country(country):
    """Convert country names to codes."""
    if not country or pd.isna(country):
        return 'Unknown'
    country = str(country).strip()
    mapping = {
        'South Korea': 'KR', 'Korea': 'KR', 'Republic of Korea': 'KR',
        'China': 'CN', "People's Republic of China": 'CN',
        'United States': 'US', 'USA': 'US', 'United States of America': 'US',
        'Denmark': 'DK', 'Sweden': 'SE', 'Germany': 'DE', 'France': 'FR',
        'Poland': 'PL', 'Spain': 'ES', 'Belgium': 'BE', 'Slovenia': 'SI',
        'Taiwan': 'TW', 'Vietnam': 'VN', 'Japan': 'JP', 'Philippines': 'PH',
        'Brazil': 'BR', 'Argentina': 'AR', 'Mexico': 'MX', 'Chile': 'CL',
        'Canada': 'CA', 'Australia': 'AU', 'New Zealand': 'NZ',
        'United Kingdom': 'GB', 'Russia': 'RU', 'Turkey': 'TR',
        'Netherlands': 'NL', 'Czech Republic': 'CZ', 'Czechia': 'CZ',
        'Croatia': 'HR', 'Bulgaria': 'BG', 'Romania': 'RO', 'Hungary': 'HU',
        'Norway': 'NO', 'Finland': 'FI', 'Greece': 'GR', 'Portugal': 'PT',
        'Hong Kong': 'HK', 'Singapore': 'SG', 'Malaysia': 'MY',
        'Thailand': 'TH', 'Indonesia': 'ID'
    }
    return mapping.get(country, country[:2].upper() if len(country) >= 2 else 'XX')


def main(csv_dir=None):
    """Main processing function."""
    import sys
    
    # Default CSV directory
    DEFAULT_PATHS = [
        Path(r"c:\Users\pixls\Downloads\school\SP26\CS163\updated csvs"),
        Path(__file__).parent.parent.parent / 'data' / 'raw' / 'enriched',
    ]
    
    if csv_dir is None and len(sys.argv) > 1:
        csv_dir = Path(sys.argv[1])
    
    if csv_dir is None:
        for path in DEFAULT_PATHS:
            if path.exists():
                csv_dir = path
                break
    
    if csv_dir is None or not Path(csv_dir).exists():
        print("ERROR: CSV directory not found!")
        print("\nUsage: python process_enriched_csvs.py [path_to_csv_directory]")
        print("\nExpected files: player_careers_S6.csv through player_careers_S15.csv")
        return
    
    OUTPUT_PATH = Path(__file__).parent.parent.parent / 'data' / 'processed'
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading enriched CSVs from: {csv_dir}")
    all_data = load_enriched_csvs(Path(csv_dir))
    
    print(f"\nProcessing {len(all_data)} seasons...")
    players_df, careers_df = process_player_careers(all_data)
    
    # Save
    players_df.to_csv(OUTPUT_PATH / 'players_processed.csv', index=False)
    careers_df.to_csv(OUTPUT_PATH / 'career_metrics.csv', index=False)
    
    print(f"\nSaved to: {OUTPUT_PATH}")
    
    # Stats
    print("\n" + "="*50)
    print("PROCESSING COMPLETE")
    print("="*50)
    print(f"Total players: {len(players_df)}")
    print(f"Mean career (seasons): {careers_df['career_length_years'].mean():.2f}")
    print(f"Median career (seasons): {careers_df['career_length_years'].median():.2f}")
    
    print(f"\nRole breakdown:")
    print(players_df['primary_role'].value_counts().to_string())
    
    print(f"\nRegion breakdown:")
    print(careers_df['primary_region'].value_counts().to_string())
    
    print(f"\nStatus breakdown:")
    print(players_df['current_status'].value_counts().to_string())
    
    # Data completeness
    unknown_role = (players_df['primary_role'] == 'Unknown').sum()
    unknown_region = (careers_df['primary_region'] == 'Unknown').sum()
    print(f"\nData completeness:")
    print(f"  Known roles: {len(players_df) - unknown_role}/{len(players_df)} ({100*(1-unknown_role/len(players_df)):.1f}%)")
    print(f"  Known regions: {len(careers_df) - unknown_region}/{len(careers_df)} ({100*(1-unknown_region/len(careers_df)):.1f}%)")


if __name__ == '__main__':
    main()
