"""
Leaguepedia Fetcher — with promotion/relegation detection
CS 163 Group 10 - Brandon Lee & Stephani Marie Soriano

Adds a MidSeasonMove column:
  "Promotion"  — moved from lower tier to higher tier within the season
  "Relegation" — moved from higher tier to lower tier within the season
  "Roster"     — changed teams within same tier
  ""           — played for one team only

Run:
    python fetch_final.py
"""

import pandas as pd
import time
import os
import json
from mwrogue.esports_client import EsportsClient

LEAGUES = [
    ("LoL Champions Korea",               "LCK",   "S"),
    ("Challengers Korea",                 "LCK",   "A"),
    ("Tencent LoL Pro League",            "LPL",   "S"),
    ("League Championship Series",        "LCS",   "S"),
    ("NA Academy League",                 "LCS",   "A"),
    ("Europe League Championship Series", "LEC",   "S"),
    ("LoL EMEA Championship",             "LEC",   "S"),
    ("European Challenger Series",        "LEC",   "A"),
    ("LoL Master Series",                 "LMS",   "S"),
    ("Pacific Championship Series",       "PCS",   "S"),
    ("Turkish Championship League",       "TCL",   "S"),
    ("Vietnam Championship Series",       "VCS",   "S"),
    ("CBLOL",                             "CBLOL", "S"),
    ("Liga Latinoamerica",                "LLA",   "S"),
    ("Oceanic Pro League",                "OCE",   "S"),
    ("KeSPA",                             "LCK",   "A"),
]

SEASON_YEAR_MAP = {
    6: 2016, 7: 2017, 8: 2018, 9: 2019, 10: 2020,
    11: 2021, 12: 2022, 13: 2023, 14: 2024, 15: 2025
}
SEASONS = {s: (f"{y}-01-01", f"{y}-12-31") for s, y in SEASON_YEAR_MAP.items()}

QUERY_DELAY  = 2
RETRY_WAIT   = 60
MAX_RETRIES  = 4
PROGRESS_FILE = "fetch_progress.json"

TIER_ORDER = ['S', 'A', 'B', 'C', 'D', '?']
TIER_MAP = {
    'S':'S','A':'A','B':'B','C':'C','D':'D',
    'Primary':'S','Secondary':'A','Tertiary':'B',
    'Showmatch':'D','Qualifier':'C'
}

def query_with_retry(site, **kwargs):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return list(site.cargo_client.query(**kwargs))
        except Exception as e:
            if 'ratelimited' in str(e):
                wait = RETRY_WAIT * attempt
                print(f"      Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"      Error: {e}")
                return None
    return None

def fetch_league_season(site, league_name, date_start, date_end):
    rows = query_with_retry(
        site,
        tables="TournamentPlayers,Tournaments",
        fields=(
            "TournamentPlayers.Player=Player,"
            "TournamentPlayers.Team=Team,"
            "TournamentPlayers.Role=Role,"
            "Tournaments.TournamentLevel=TournamentLevel,"
            "Tournaments.DateStart=DateStart"
        ),
        where=(
            f'Tournaments.League="{league_name}" AND '
            f'Tournaments.DateStart >= "{date_start}" AND '
            f'Tournaments.DateStart <= "{date_end}"'
        ),
        join_on="TournamentPlayers.OverviewPage=Tournaments.OverviewPage",
        order_by="Tournaments.DateStart ASC",
        limit=2000
    )
    return rows or []

def detect_move(appearances):
    """
    Given a list of (date, team, tier, league) tuples sorted by date,
    classify the mid-season movement:
      Promotion   — tier improved within same league (e.g. CK → LCK)
      Relegation  — tier dropped within same league
      Transfer    — moved to a different league (e.g. LEC → LCS, LPL → LCK)
      Roster      — same tier, same league, different team (org swap)
      ""          — only one team, no movement
    """
    if len(appearances) <= 1:
        return ""

    tiers   = [a[2] for a in appearances]
    leagues = [a[3] for a in appearances]
    teams   = [a[1] for a in appearances]

    if len(set(teams)) == 1:
        return ""  # same team throughout

    first_tier,   last_tier   = tiers[0],   tiers[-1]
    first_league, last_league = leagues[0], leagues[-1]

    # Cross-league move (e.g. LEC → LCS, LPL → LCK)
    if first_league != last_league and first_league != '?' and last_league != '?':
        return "Transfer"

    # Same league — check tier change
    real_tiers = [t for t in tiers if t != '?']
    if len(set(real_tiers)) <= 1:
        return "Roster"  # same tier, same league, different team

    fi = TIER_ORDER.index(first_tier) if first_tier != '?' else 99
    li = TIER_ORDER.index(last_tier)  if last_tier  != '?' else 99

    if li < fi:
        return "Promotion"
    elif li > fi:
        return "Relegation"
    else:
        return "Roster"

# ── Load CSVs ─────────────────────────────────────────────────────────────────

print("Loading season CSVs...")
season_dfs = {}
season_players = {}

for s, year in SEASON_YEAR_MAP.items():
    try:
        df = pd.read_csv(f'player_careers_S{s}.csv')
        drop = [c for c in ['Team','League','Role','Tier','Region','MidSeasonMove','AllTeams'] if c in df.columns]
        df = df.drop(columns=drop)
        season_dfs[s] = df
        season_players[s] = set(df['Player'].tolist())
        print(f"  S{s} ({year}): {len(season_players[s])} players")
    except FileNotFoundError:
        print(f"  WARNING: player_careers_S{s}.csv not found")

# ── Load progress ─────────────────────────────────────────────────────────────

# all_data[season][player] = {Team, League, Role, Tier, AllTeams, appearances[]}
all_data = {s: {} for s in SEASON_YEAR_MAP}
completed = set()

if os.path.exists(PROGRESS_FILE):
    print(f"\nResuming from progress file...")
    with open(PROGRESS_FILE, 'r') as f:
        progress = json.load(f)
    completed = set(tuple(x) for x in progress.get("completed", []))
    if os.path.exists("player_team_history.csv"):
        try:
            existing = pd.read_csv("player_team_history.csv")
            if 'Season' in existing.columns and len(existing) > 0:
                for _, row in existing.iterrows():
                    s = int(row['Season'])
                    if s in all_data:
                        all_data[s][row['Player']] = row.to_dict()
                print(f"  Loaded {sum(len(v) for v in all_data.values())} existing records")
        except Exception as e:
            print(f"  Could not load existing records: {e}")
    print(f"  Completed: {len(completed)} league-seasons")
else:
    print(f"\nStarting fresh...")

# ── Connect ───────────────────────────────────────────────────────────────────

print("\nConnecting to Leaguepedia...")
site = EsportsClient("lol")
print("Connected!\n")

# ── Main loop ─────────────────────────────────────────────────────────────────

total_queries = len(SEASON_YEAR_MAP) * len(LEAGUES)
done = 0

# Track raw appearances per player per season for move detection
# appearances[season][player] = [(date, team, tier), ...]
appearances = {s: {} for s in SEASON_YEAR_MAP}

# Pre-populate from existing records
for s, players in all_data.items():
    for player, rec in players.items():
        all_teams = rec.get("AllTeams", rec.get("Team", ""))
        if isinstance(all_teams, str) and "→" in all_teams:
                teams = [t.strip() for t in all_teams.split("→")]
                appearances[s][player] = [(f"{SEASON_YEAR_MAP[s]}-01-01", t, rec.get("Tier","?"), rec.get("League","?")) for t in teams]

for season, (date_start, date_end) in SEASONS.items():
    if season not in season_players:
        continue

    csv_players = season_players[season]
    year_str = str(SEASON_YEAR_MAP[season])
    print(f"[Season {season} / {year_str}]")

    for league_name, league_abbr, default_tier in LEAGUES:
        done += 1
        key = (season, league_name)

        if key in completed:
            print(f"  ✓ {league_name} — already done")
            continue

        print(f"  [{done}/{total_queries}] {league_name}...", end=" ", flush=True)
        rows = fetch_league_season(site, league_name, date_start, date_end)

        new_matches = 0
        for row in rows:
            player = (row.get("Player") or "").strip()
            team   = (row.get("Team") or "").strip()
            if not player or not team or player not in csv_players:
                continue
            date = str(row.get("DateStart") or "")
            if date and not date.startswith(year_str):
                continue

            tier = TIER_MAP.get(str(row.get("TournamentLevel") or "").strip(), default_tier)
            role = (row.get("Role") or "").strip()

            # Track appearances for move detection (date, team, tier, league)
            if player not in appearances[season]:
                appearances[season][player] = []
            app_list = appearances[season][player]
            if not any(a[1] == team for a in app_list):
                app_list.append((date, team, tier, league_abbr))

            if player not in all_data[season]:
                all_data[season][player] = {
                    "Player": player, "Season": season,
                    "Team": team, "League": league_abbr,
                    "Role": role, "Tier": tier,
                    "AllTeams": [team]
                }
                new_matches += 1
            else:
                rec = all_data[season][player]
                all_teams = rec.get("AllTeams", [rec["Team"]])
                if isinstance(all_teams, str):
                    all_teams = [t.strip() for t in all_teams.split("→")]
                if team not in all_teams:
                    all_teams.append(team)
                rec["AllTeams"] = all_teams
                if TIER_ORDER.index(tier) < TIER_ORDER.index(rec["Tier"]):
                    rec.update({"Team": team, "League": league_abbr,
                                "Role": role, "Tier": tier})

        print(f"{len(rows)} rows → {new_matches} new players")

        completed.add(key)
        with open(PROGRESS_FILE, 'w') as f:
            json.dump({"completed": [list(x) for x in completed]}, f)

        time.sleep(QUERY_DELAY)

    # After all leagues for this season, detect moves
    for player, rec in all_data[season].items():
        app_list = sorted(appearances[season].get(player, []), key=lambda x: x[0])
        rec["MidSeasonMove"] = detect_move(app_list)
        all_teams = rec.get("AllTeams", [rec["Team"]])
        if isinstance(all_teams, list):
            rec["AllTeams"] = " → ".join(all_teams)

    promotions  = sum(1 for r in all_data[season].values() if r.get("MidSeasonMove") == "Promotion")
    relegations = sum(1 for r in all_data[season].values() if r.get("MidSeasonMove") == "Relegation")
    transfers   = sum(1 for r in all_data[season].values() if r.get("MidSeasonMove") == "Transfer")
    print(f"  Season {season} total: {season_total}/{len(csv_players)} ({pct:.1f}%) | "
          f"Promotions: {promotions} | Relegations: {relegations} | Transfers: {transfers}\n")

    # Save after each season
    all_records = []
    for s, players in all_data.items():
        for rec in players.values():
            all_records.append(dict(rec))
    if all_records:
        pd.DataFrame(all_records).to_csv("player_team_history.csv", index=False)

# ── Final merge ───────────────────────────────────────────────────────────────

print("=== Merging into season CSVs ===\n")

all_records = [dict(rec) for s, players in all_data.items() for rec in players.values()]

if not all_records:
    print("No records to merge.")
else:
    df_teams = pd.DataFrame(all_records)
    df_teams.to_csv("player_team_history.csv", index=False)
    print(f"✓ Saved player_team_history.csv ({len(df_teams)} rows)")

    for season, df in season_dfs.items():
        merge_cols = (
            df_teams[df_teams['Season'] == season]
            [['Player', 'Team', 'League', 'Role', 'Tier', 'MidSeasonMove', 'AllTeams']]
            .drop_duplicates('Player')
        )
        merged = df.merge(merge_cols, on='Player', how='left')
        front = ['Player', 'Team', 'League', 'Role', 'Tier', 'MidSeasonMove', 'AllTeams']
        if 'Country' in merged.columns:
            front.insert(front.index('MidSeasonMove'), 'Country')
        rest = [c for c in merged.columns if c not in front]
        merged = merged[front + rest]
        merged.to_csv(f'player_careers_S{season}.csv', index=False)

        filled   = merged['Team'].notna().sum()
        total    = len(merged)
        promoted = merged[merged['MidSeasonMove'] == 'Promotion'].shape[0]
        print(f"  S{season}: {filled}/{total} ({filled/total*100:.1f}%) | {promoted} promotions flagged")

    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    print("\n✓ All done!")
    print("\nMidSeasonMove breakdown across all seasons:")
    print(df_teams['MidSeasonMove'].value_counts().to_string())