"""
Leaguepedia Team History Fetcher — with rate limit handling
CS 163 Group 10 - Brandon Lee & Stephani Marie Soriano

Install:
    pip install mwrogue mwparserfromhell pandas

Run:
    python fetch_team_history_v2.py
"""

import pandas as pd
import time
from mwrogue.esports_client import EsportsClient

PLAYERS = [
    "Faker", "xiaohu", "meiko", "Ruler", "Peanut", "Scout", "RooKie",
    "Deft", "Bdd", "JackeyLove", "Kiin", "Crisp", "Chovy", "Knight",
    "Keria", "Flandre", "Viper", "Canyon", "ShowMaker", "Caps"
]

SEASON_YEAR_MAP = {
    6: 2016, 7: 2017, 8: 2018, 9: 2019, 10: 2020,
    11: 2021, 12: 2022, 13: 2023, 14: 2024, 15: 2025
}
YEAR_TO_SEASON = {v: k for k, v in SEASON_YEAR_MAP.items()}

DELAY_BETWEEN_PLAYERS = 8   # seconds between each player
RETRY_WAIT = 65             # seconds to wait after a rate limit error
MAX_RETRIES = 5

print("Connecting to Leaguepedia...")
site = EsportsClient("lol")
print("Connected!\n")

def assign_season(date_str):
    if not date_str:
        return None
    try:
        year = int(str(date_str)[:4])
        return YEAR_TO_SEASON.get(year)
    except:
        return None

def fetch_with_retry(player):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = site.cargo_client.query(
                tables="TournamentPlayers,Tournaments",
                fields=(
                    "TournamentPlayers.Player=Player,"
                    "TournamentPlayers.Team=Team,"
                    "TournamentPlayers.Role=Role,"
                    "TournamentPlayers.OverviewPage=Tournament,"
                    "Tournaments.DateStart=DateStart,"
                    "Tournaments.League=League,"
                    "Tournaments.Region=Region"
                ),
                where=f'TournamentPlayers.Player="{player}"',
                join_on="TournamentPlayers.OverviewPage=Tournaments.OverviewPage",
                order_by="Tournaments.DateStart ASC",
                limit=500
            )
            return list(response)
        except Exception as e:
            if "ratelimited" in str(e):
                if attempt < MAX_RETRIES:
                    print(f"  Rate limited. Waiting {RETRY_WAIT}s... (attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(RETRY_WAIT)
                else:
                    print(f"  Gave up after {MAX_RETRIES} attempts.")
                    return None
            else:
                print(f"  Error: {e}")
                return None

all_records = []
failed = []

for i, player in enumerate(PLAYERS):
    print(f"[{i+1}/{len(PLAYERS)}] Fetching: {player}")
    rows = fetch_with_retry(player)

    if rows is None:
        failed.append(player)
    elif not rows:
        print(f"  WARNING: No results — check player name on lol.fandom.com")
    else:
        print(f"  Found {len(rows)} entries")
        seen = set()
        for row in rows:
            season = assign_season(row.get("DateStart", ""))
            team = (row.get("Team") or "").strip()
            if not team or not season:
                continue
            key = (player, team, season)
            if key not in seen:
                seen.add(key)
                all_records.append({
                    "Player":     player,
                    "Season":     season,
                    "Year":       SEASON_YEAR_MAP.get(season),
                    "Team":       team,
                    "League":     (row.get("League") or "").strip(),
                    "Region":     (row.get("Region") or "").strip(),
                    "Role":       (row.get("Role") or "").strip(),
                    "Tournament": (row.get("Tournament") or "").strip(),
                })

    print(f"  Waiting {DELAY_BETWEEN_PLAYERS}s...")
    time.sleep(DELAY_BETWEEN_PLAYERS)

if all_records:
    df = pd.DataFrame(all_records).sort_values(["Player", "Season", "Team"]).reset_index(drop=True)
    df.to_csv("player_team_history_full.csv", index=False)
    print(f"\n✓ Saved: player_team_history_full.csv ({len(df)} rows)")

    summary = (
        df.groupby(["Player", "Season", "Year"])
        .agg(
            Teams  =("Team",   lambda x: " → ".join(dict.fromkeys(x))),
            Leagues=("League", lambda x: ", ".join(sorted(set(x)))),
            Region =("Region", "first"),
            Role   =("Role",   "first"),
        )
        .reset_index()
        .sort_values(["Player", "Season"])
    )
    summary.to_csv("player_team_history.csv", index=False)
    print(f"✓ Saved: player_team_history.csv ({len(summary)} rows)")

    print("\nCoverage per player:")
    for p in PLAYERS:
        seasons = sorted(summary[summary["Player"] == p]["Season"].tolist())
        print(f"  {'✓' if seasons else '✗'} {p:15s}: {seasons}")
else:
    print("\nNo records collected.")

if failed:
    print(f"\nFailed (retry these manually): {failed}")