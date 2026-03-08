"""
Process Excel Data
==================
Transforms the raw League of Legends Player Statistics Excel file
into the processed data format needed for EDA.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Season to Year mapping (Season 6 = 2016, etc.)
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
    'LMS': 'PCS', 'CBLoL': 'CBLOL'
}

# Tier mapping (S = Starter main roster = Tier 1)
TIER_MAP = {'S': 1, 'A': 2, 'B': 2, None: 2}


def load_excel_data(excel_path):
    """Load all sheets from the Excel file."""
    xl = pd.ExcelFile(excel_path)
    
    all_data = {}
    for sheet in xl.sheet_names:
        if sheet.startswith('S') and sheet[1:].isdigit():
            all_data[sheet] = pd.read_excel(xl, sheet)
    
    # Check for enriched sheet
    enriched_sheets = [s for s in xl.sheet_names if 'career' in s.lower()]
    if enriched_sheets:
        all_data['enriched'] = pd.read_excel(xl, enriched_sheets[0])
    
    return all_data


def process_player_careers(all_data):
    """Process all season data to derive career metrics."""
    
    # Track player appearances across seasons
    player_seasons = {}
    player_stats = {}
    
    for sheet_name, df in all_data.items():
        if sheet_name == 'enriched':
            continue
        if not sheet_name.startswith('S'):
            continue
            
        season = sheet_name
        year = SEASON_TO_YEAR.get(season, 2020)
        
        for _, row in df.iterrows():
            player = row['Player']
            if pd.isna(player):
                continue
                
            if player not in player_seasons:
                player_seasons[player] = []
                player_stats[player] = {
                    'total_games': 0,
                    'countries': [],
                    'leagues': [],
                    'roles': [],
                    'tiers': [],
                    'win_rates': [],
                    'kdas': []
                }
            
            player_seasons[player].append(season)
            
            # Accumulate stats
            stats = player_stats[player]
            try:
                games = row.get('Games')
                if not pd.isna(games):
                    stats['total_games'] += int(games)
            except (ValueError, TypeError):
                pass
            if not pd.isna(row.get('Country')):
                stats['countries'].append(row['Country'])
            try:
                winrate = row.get('Win rate')
                if not pd.isna(winrate):
                    stats['win_rates'].append(float(winrate))
            except (ValueError, TypeError):
                pass
            try:
                kda = row.get('KDA')
                if not pd.isna(kda):
                    stats['kdas'].append(float(kda))
            except (ValueError, TypeError):
                pass
    
    # Get enriched data if available
    enriched_lookup = {}
    if 'enriched' in all_data:
        edf = all_data['enriched']
        for _, row in edf.iterrows():
            player = row['Player']
            if pd.isna(player):
                continue
            enriched_lookup[player] = {
                'team': row.get('Team'),
                'league': row.get('League'),
                'role': row.get('Role'),
                'tier': row.get('Tier'),
                'country': row.get('Country')
            }
    
    # Build processed dataframes
    players_data = []
    careers_data = []
    
    for player, seasons in player_seasons.items():
        stats = player_stats[player]
        enriched = enriched_lookup.get(player, {})
        
        # Determine first/last season
        season_nums = [int(s[1:]) for s in seasons]
        first_season = min(season_nums)
        last_season = max(season_nums)
        
        # Career length in seasons (each season ≈ 1 year)
        career_length_seasons = len(set(seasons))
        career_length_years = last_season - first_season + 1
        
        # Determine country
        country = enriched.get('country')
        if pd.isna(country) and stats['countries']:
            country = stats['countries'][0]
        
        # Determine role (standardize)
        role = enriched.get('role')
        if pd.isna(role):
            role = 'Unknown'
        role = standardize_role(role)
        
        # Determine region from league
        league = enriched.get('league')
        region = LEAGUE_TO_REGION.get(league, 'Unknown')
        
        # Determine tier
        tier_raw = enriched.get('tier')
        starting_tier = TIER_MAP.get(tier_raw, 2)
        
        # Current status (if appeared in S15, likely active)
        if 'S15' in seasons:
            status = 'Active'
        elif 'S14' in seasons:
            status = 'Inactive'
        else:
            status = 'Retired'
        
        # Calculate averages
        avg_winrate = np.mean(stats['win_rates']) if stats['win_rates'] else 0.5
        avg_kda = np.mean(stats['kdas']) if stats['kdas'] else 2.0
        
        # Players data
        players_data.append({
            'player_id': player,
            'primary_role': role,
            'nationality': standardize_country(country),
            'current_status': status,
            'peak_tier': 1 if starting_tier == 1 else (1 if career_length_seasons >= 3 else 2)
        })
        
        # Career metrics
        careers_data.append({
            'player_id': player,
            'primary_region': region,
            'career_length_months': career_length_years * 12,
            'career_length_years': float(career_length_years),
            'time_to_tier1_months': np.nan if starting_tier == 1 else (12 if career_length_seasons >= 2 else np.nan),
            'num_teams': min(career_length_seasons, 5),  # Estimate
            'num_regions': 1,
            'promoted_tier2_to_tier1': starting_tier == 2 and career_length_seasons >= 3,
            'starting_tier': starting_tier,
            'career_start_year': 2016 + first_season - 6,
            'total_games': stats['total_games'],
            'avg_winrate': avg_winrate,
            'avg_kda': avg_kda
        })
    
    players_df = pd.DataFrame(players_data)
    careers_df = pd.DataFrame(careers_data)
    
    return players_df, careers_df


def standardize_role(role):
    """Standardize role names."""
    if pd.isna(role):
        return 'Unknown'
    role = str(role).strip().lower()
    mapping = {
        'top': 'Top', 'toplane': 'Top',
        'jungle': 'Jungle', 'jng': 'Jungle', 'jungler': 'Jungle',
        'mid': 'Mid', 'middle': 'Mid', 'midlane': 'Mid',
        'adc': 'ADC', 'bot': 'ADC', 'ad carry': 'ADC', 'marksman': 'ADC',
        'support': 'Support', 'sup': 'Support', 'supp': 'Support'
    }
    return mapping.get(role, 'Unknown')


def standardize_country(country):
    """Convert country names to codes."""
    if pd.isna(country):
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


def main(excel_path=None):
    """Main processing function.
    
    Args:
        excel_path: Path to the Excel file. If None, uses default location.
    """
    import sys
    
    # Check for command line argument
    if excel_path is None and len(sys.argv) > 1:
        excel_path = Path(sys.argv[1])
    
    # Default paths to check
    DEFAULT_PATHS = [
        Path(__file__).parent.parent.parent / 'data' / 'raw' / 'League of Legends Player Statistics by Year.xlsx',
        Path.home() / 'Downloads' / 'League of Legends Player Statistics by Year.xlsx',
        Path(r"c:\Users\pixls\Downloads\school\SP26\CS163\League of Legends Player Statistics by Year.xlsx"),
    ]
    
    if excel_path is None:
        for path in DEFAULT_PATHS:
            if path.exists():
                excel_path = path
                break
    
    if excel_path is None or not Path(excel_path).exists():
        print("ERROR: Excel file not found!")
        print("\nUsage: python process_excel_data.py [path_to_excel_file]")
        print("\nExpected file: 'League of Legends Player Statistics by Year.xlsx'")
        print("\nSearched locations:")
        for p in DEFAULT_PATHS:
            print(f"  - {p}")
        print("\nPlease download the file and either:")
        print("  1. Place it in data/raw/")
        print("  2. Place it in your Downloads folder")
        print("  3. Specify the path as a command line argument")
        return
    
    EXCEL_PATH = Path(excel_path)
    OUTPUT_PATH = Path(__file__).parent.parent.parent / 'data' / 'processed'
    RAW_PATH = Path(__file__).parent.parent.parent / 'data' / 'raw'
    
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading data from: {EXCEL_PATH}")
    all_data = load_excel_data(EXCEL_PATH)
    
    print(f"Found {len(all_data)} sheets")
    for name, df in all_data.items():
        print(f"  - {name}: {len(df)} rows")
    
    print("\nProcessing player careers...")
    players_df, careers_df = process_player_careers(all_data)
    
    print(f"\nProcessed data:")
    print(f"  - Players: {len(players_df)}")
    print(f"  - Unique regions: {careers_df['primary_region'].nunique()}")
    print(f"  - Unique roles: {players_df['primary_role'].nunique()}")
    
    # Save processed data
    players_df.to_csv(OUTPUT_PATH / 'players_processed.csv', index=False)
    careers_df.to_csv(OUTPUT_PATH / 'career_metrics.csv', index=False)
    
    print(f"\nSaved to:")
    print(f"  - {OUTPUT_PATH / 'players_processed.csv'}")
    print(f"  - {OUTPUT_PATH / 'career_metrics.csv'}")
    
    # Quick stats
    print("\n" + "="*50)
    print("QUICK STATS")
    print("="*50)
    print(f"Total players: {len(players_df)}")
    print(f"Mean career (years): {careers_df['career_length_years'].mean():.2f}")
    print(f"Median career (years): {careers_df['career_length_years'].median():.2f}")
    print(f"\nCareer length distribution:")
    print(careers_df['career_length_years'].describe())
    print(f"\nStatus breakdown:")
    print(players_df['current_status'].value_counts())
    print(f"\nRole breakdown:")
    print(players_df['primary_role'].value_counts())
    print(f"\nRegion breakdown:")
    print(careers_df['primary_region'].value_counts())


if __name__ == '__main__':
    main()
