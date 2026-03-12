"""
Adds SeasonTierChange column to each season CSV.
Shows the tier change a player made FROM the previous season TO this season.

Values:
  "Promoted"   — moved to a higher tier league vs last season
  "Relegated"  — moved to a lower tier league vs last season
  "Stable"     — same tier as last season
  ""           — no data for previous season (can't compare)

Run AFTER fetch_final.py has completed:
    python add_tier_changes.py
"""

import pandas as pd

SEASONS = list(range(6, 16))
TIER_ORDER = ['S', 'A', 'B', 'C', 'D']

print("Loading season CSVs...")
dfs = {}
for s in SEASONS:
    try:
        dfs[s] = pd.read_csv(f'player_careers_S{s}.csv')
        print(f"  S{s}: {len(dfs[s])} players")
    except FileNotFoundError:
        print(f"  WARNING: player_careers_S{s}.csv not found")

# Build tier lookup: player -> {season: tier}
tier_lookup = {}
for s, df in dfs.items():
    if 'Tier' not in df.columns:
        continue
    for _, row in df.iterrows():
        p = row['Player']
        t = row.get('Tier')
        if pd.isna(t) or t not in TIER_ORDER:
            continue
        if p not in tier_lookup:
            tier_lookup[p] = {}
        tier_lookup[p][s] = t

print(f"\nBuilt tier history for {len(tier_lookup)} players")

# Add SeasonTierChange to each season CSV
print("\nAdding SeasonTierChange column...")
for s, df in dfs.items():
    # Drop existing column if present
    if 'SeasonTierChange' in df.columns:
        df = df.drop(columns=['SeasonTierChange'])

    changes = []
    for _, row in df.iterrows():
        p = row['Player']
        curr_tier = row.get('Tier')

        if pd.isna(curr_tier) or curr_tier not in TIER_ORDER or p not in tier_lookup:
            changes.append('')
            continue

        # Find the most recent previous season this player has data for
        prev_season = None
        for ps in range(s - 1, 4, -1):  # look back up to S5
            if ps in tier_lookup.get(p, {}):
                prev_season = ps
                break

        if prev_season is None:
            changes.append('')  # no prior data
            continue

        prev_tier = tier_lookup[p][prev_season]
        pi = TIER_ORDER.index(prev_tier)
        ci = TIER_ORDER.index(curr_tier)

        if ci < pi:
            changes.append('Promoted')
        elif ci > pi:
            changes.append('Relegated')
        else:
            changes.append('Stable')

    df['SeasonTierChange'] = changes

    # Place SeasonTierChange right after Tier
    front = ['Player', 'Team', 'League', 'Role', 'Tier', 'SeasonTierChange']
    if 'MidSeasonMove' in df.columns:
        front.append('MidSeasonMove')
    if 'AllTeams' in df.columns:
        front.append('AllTeams')
    if 'Country' in df.columns:
        front.append('Country')
    rest = [c for c in df.columns if c not in front]
    df = df[front + rest]

    df.to_csv(f'player_careers_S{s}.csv', index=False)

    promoted  = (df['SeasonTierChange'] == 'Promoted').sum()
    relegated = (df['SeasonTierChange'] == 'Relegated').sum()
    stable    = (df['SeasonTierChange'] == 'Stable').sum()
    print(f"  S{s}: {promoted} promoted, {relegated} relegated, {stable} stable")

print("\n✓ Done! SeasonTierChange column added to all season CSVs.")
print("\nExample — players who were Promoted entering S10:")
try:
    s10 = pd.read_csv('player_careers_S10.csv')
    promos = s10[s10['SeasonTierChange'] == 'Promoted'][['Player','Team','League','Tier','SeasonTierChange']]
    print(promos.to_string(index=False))
except:
    pass