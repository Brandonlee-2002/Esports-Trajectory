"""
Leaguepedia Bulk Team + Tier Fetcher v4 — saves progress as it goes
CS 163 Group 10 - Brandon Lee & Stephani Marie Soriano

Key improvements over v3:
  - Saves a progress file after every season so restarts pick up where left off
  - Much longer waits between requests to avoid rate limits
  - Merges into CSVs at the very end

Install:
    pip install mwrogue mwparserfromhell pandas

Run:
    python fetch_all_teams_v4.py

If interrupted, just run again — it will skip already-completed seasons.
"""

import pandas as pd
import time
import os
import json
from mwrogue.esports_client import EsportsClient

SEASONS = {
    6:  ("2016-01-01", "2016-12-31"),
    7:  ("2017-01-01", "2017-12-31"),
    8:  ("2018-01-01", "2018-12-31"),
    9:  ("2019-01-01", "2019-12-31"),
    10: ("2020-01-01", "2020-12-31"),
    11: ("2021-01-01", "2021-12-31"),
    12: ("2022-01-01", "2022-12-31"),
    13: ("2023-01-01", "2023-12-31"),
    14: ("2024-01-01", "2024-12-31"),
    15: ("2025-01-01", "2025-12-31"),
}

PAGE_SIZE    = 1000  # smaller pages = less likely to time out
PAGE_DELAY   = 8     # seconds between pages
SEASON_DELAY = 15    # seconds between seasons
RETRY_WAIT   = 90    # seconds to wait after rate limit
MAX_RETRIES  = 6
PROGRESS_FILE = "fetch_progress.json"  # saves completed seasons

LEAGUE_KEYWORDS = {
    'LoL Champions Korea':               'LCK',
    'Challengers Korea':                 'LCK',
    'KeSPA':                             'LCK',
    'Tencent LoL Pro League':            'LPL',
    'LPL':                               'LPL',
    'LoL EMEA Championship':             'LEC',
    'Europe League Championship Series': 'LEC',
    'LEC':                               'LEC',
    'League Championship Series':        'LCS',
    'LCS':                               'LCS',
    'North American':                    'LCS',
    'NA LCS':                            'LCS',
    'Pacific Championship Series':       'PCS',
    'LoL Master Series':                 'LMS',
    'LMS':                               'LMS',
    'Turkish Championship League':       'TCL',
    'TCL':                               'TCL',
    'Vietnam Championship Series':       'VCS',
    'CBLOL':                             'CBLOL',
    'Latin America':                     'LLA',
    'LLA':                               'LLA',
    'Oceanic':                           'OCE',
    'OPL':                               'OCE',
}
REGION_MAP = {
    'Korea': 'LCK', 'China': 'LPL', 'Europe': 'LEC', 'EMEA': 'LEC',
    'North America': 'LCS', 'NA': 'LCS', 'SEA': 'PCS', 'Asia': 'PCS',
    'Turkey': 'TCL', 'International': 'INT', 'Oceania': 'OCE',
    'Brazil': 'CBLOL', 'Vietnam': 'VCS', 'Latin America': 'LLA',
}
TIER_MAP = {
    'S': 'S', 'A': 'A', 'B': 'B', 'C': 'C', 'D': 'D',
    'Primary': 'S', 'Secondary': 'A', 'Tertiary': 'B',
    'Showmatch': 'D', 'Qualifier': 'C',
}
TIER_ORDER = ['S', 'A', 'B', 'C', 'D', '?']

def get_league(league_str, region_str):
    for kw, abbr in LEAGUE_KEYWORDS.items():
        if kw in str(league_str or ''):
            return abbr
    return REGION_MAP.get(str(region_str or '').strip(), str(region_str or '').strip() or '?')

def get_tier(level_str):
    return TIER_MAP.get(str(level_str or '').strip(), '?')

def query_with_retry(site, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return list(site.cargo_client.query(**kwargs))
        except Exception as e:
            if 'ratelimited' in str(e):
                wait = RETRY_WAIT * attempt  # back off longer each retry
                print(f"    Rate limited. Waiting {wait}s... ({attempt}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                print(f"    Error: {e}")
                return None
    print(f"    Gave up after {MAX_RETRIES} retries.")
    return None

def fetch_season_all_pages(site, date_start, date_end):
    all_rows = []
    offset = 0
    page = 1
    while True:
        print(f"    Page {page} (offset {offset})...", end=" ", flush=True)
        rows = query_with_retry(
            site,
            tables="TournamentPlayers,Tournaments",
            fields=(
                "TournamentPlayers.Player=Player,"
                "TournamentPlayers.Team=Team,"
                "TournamentPlayers.Role=Role,"
                "Tournaments.DateStart=DateStart,"
                "Tournaments.League=League,"
                "Tournaments.Region=Region,"
                "Tournaments.TournamentLevel=TournamentLevel"
            ),
            where=(
                f'Tournaments.DateStart >= "{date_start}" AND '
                f'Tournaments.DateStart <= "{date_end}"'
            ),
            join_on="TournamentPlayers.OverviewPage=Tournaments.OverviewPage",
            order_by="Tournaments.DateStart ASC, TournamentPlayers.Player ASC",
            limit=PAGE_SIZE,
            offset=offset
        )
        if rows is None:
            print("FAILED")
            return None
        print(f"{len(rows)} rows")
        all_rows.extend(rows)
        if len(rows) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
        page += 1
        time.sleep(PAGE_DELAY)
    return all_rows

def process_rows_for_season(rows, csv_players, season):
    year = 2015 + season
    player_best = {}
    for row in rows:
        player = (row.get("Player") or "").strip()
        team   = (row.get("Team") or "").strip()
        if not player or not team or player not in csv_players:
            continue
        date = str(row.get("DateStart") or "")
        if date and not date.startswith(str(year)):
            continue
        league = get_league(row.get("League", ""), row.get("Region", ""))
        tier   = get_tier(row.get("TournamentLevel", ""))
        role   = (row.get("Role") or "").strip()
        if player not in player_best:
            player_best[player] = {
                "Player": player, "Season": season,
                "Team": team, "League": league,
                "Role": role, "Tier": tier,
                "AllTeams": [team]
            }
        else:
            rec = player_best[player]
            if team not in rec["AllTeams"]:
                rec["AllTeams"].append(team)
            if TIER_ORDER.index(tier) < TIER_ORDER.index(rec["Tier"]):
                rec.update({"Team": team, "League": league, "Role": role, "Tier": tier})
    for rec in player_best.values():
        rec["AllTeams"] = " → ".join(rec["AllTeams"])
    return player_best

# ── Load CSVs ─────────────────────────────────────────────────────────────────

print("Loading season CSVs...")
season_dfs = {}
season_players = {}

for s in SEASONS:
    try:
        df = pd.read_csv(f'player_careers_S{s}.csv')
        drop = [c for c in ['Team','League','Role','Tier','Region'] if c in df.columns]
        df = df.drop(columns=drop)
        season_dfs[s] = df
        season_players[s] = set(df['Player'].tolist())
        print(f"  S{s}: {len(season_players[s])} players")
    except FileNotFoundError:
        print(f"  WARNING: player_careers_S{s}.csv not found")

# ── Load progress ─────────────────────────────────────────────────────────────

all_records = []
completed_seasons = set()

if os.path.exists(PROGRESS_FILE):
    print(f"\nFound progress file — loading completed seasons...")
    with open(PROGRESS_FILE, 'r') as f:
        progress = json.load(f)
    completed_seasons = set(progress.get("completed_seasons", []))
    # Load existing records
    if os.path.exists("player_team_history.csv"):
        existing = pd.read_csv("player_team_history.csv")
        all_records = existing.to_dict('records')
        print(f"  Loaded {len(all_records)} existing records from player_team_history.csv")
    print(f"  Already completed seasons: {sorted(completed_seasons)}")
else:
    print(f"\nNo progress file found — starting fresh")

# ── Connect ───────────────────────────────────────────────────────────────────

print("\nConnecting to Leaguepedia...")
site = EsportsClient("lol")
print("Connected!\n")

# ── Fetch each season ─────────────────────────────────────────────────────────

for season, (date_start, date_end) in SEASONS.items():
    if season not in season_players:
        continue
    if season in completed_seasons:
        print(f"[Season {season}] Already completed — skipping")
        continue

    print(f"[Season {season}] Fetching {date_start} → {date_end}")
    rows = fetch_season_all_pages(site, date_start, date_end)

    if rows is None:
        print(f"  FAILED — will retry next run\n")
        time.sleep(SEASON_DELAY)
        continue

    csv_players = season_players[season]
    player_best = process_rows_for_season(rows, csv_players, season)

    matched = len(player_best)
    total   = len(csv_players)
    print(f"  Matched {matched}/{total} players ({matched/total*100:.1f}%)")

    tier_dist = {t: sum(1 for r in player_best.values() if r['Tier']==t)
                 for t in TIER_ORDER if any(r['Tier']==t for r in player_best.values())}
    print(f"  Tiers: {tier_dist}")

    # Add to records
    all_records.extend(player_best.values())

    # Save progress
    df_so_far = pd.DataFrame(all_records)
    df_so_far.to_csv("player_team_history.csv", index=False)
    completed_seasons.add(season)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump({"completed_seasons": list(completed_seasons)}, f)

    print(f"  ✓ Progress saved ({len(all_records)} total records so far)\n")
    time.sleep(SEASON_DELAY)

# ── Final merge into CSVs ─────────────────────────────────────────────────────

print("=== Merging into season CSVs ===\n")

if not all_records:
    print("No records to merge.")
else:
    df_teams = pd.DataFrame(all_records)
    df_teams.to_csv("player_team_history.csv", index=False)
    print(f"✓ Final player_team_history.csv saved ({len(df_teams)} rows)\n")

    for season, df in season_dfs.items():
        merge_cols = (
            df_teams[df_teams['Season'] == season]
            [['Player', 'Team', 'League', 'Role', 'Tier']]
            .drop_duplicates('Player')
        )
        merged = df.merge(merge_cols, on='Player', how='left')
        front = ['Player', 'Team', 'League', 'Role', 'Tier']
        if 'Country' in merged.columns:
            front.append('Country')
        rest = [c for c in merged.columns if c not in front]
        merged = merged[front + rest]
        merged.to_csv(f'player_careers_S{season}.csv', index=False)

        filled = merged['Team'].notna().sum()
        total  = len(merged)
        print(f"  S{season}: {filled}/{total} players have team data ({filled/total*100:.1f}%)")

    # Clean up progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    print("\n✓ All done!")
    print("\nLeague distribution:")
    print(df_teams['League'].value_counts().to_string())
    print("\nTier distribution:")
    print(df_teams['Tier'].value_counts().to_string())