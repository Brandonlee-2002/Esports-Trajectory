"""
Leaguepedia Country Fetcher — all players in one query
CS 163 Group 10 - Brandon Lee & Stephani Marie Soriano

Fetches country of origin for every player in your season CSVs
and adds a Country column to each CSV.

Install:
    pip install mwrogue mwparserfromhell pandas

Usage:
    1. Place in the same folder as your player_careers_S6.csv through S15.csv
    2. Run: python fetch_countries.py
"""

import pandas as pd
import time
from mwrogue.esports_client import EsportsClient

DELAY      = 8
RETRY_WAIT = 65
MAX_RETRIES = 5
BATCH_SIZE  = 500  # players per query (Leaguepedia limit)

# ── Load all unique player names ──────────────────────────────────────────────

print("Loading player names from season CSVs...")
all_players = set()
season_dfs = {}

for s in range(6, 16):
    try:
        df = pd.read_csv(f'player_careers_S{s}.csv')
        season_dfs[s] = df
        all_players.update(df['Player'].tolist())
    except FileNotFoundError:
        print(f"  WARNING: player_careers_S{s}.csv not found")

player_list = sorted(all_players)
print(f"Found {len(player_list)} unique players across all seasons\n")

# ── Connect ───────────────────────────────────────────────────────────────────

print("Connecting to Leaguepedia...")
site = EsportsClient("lol")
print("Connected!\n")

# ── Fetch countries in batches ────────────────────────────────────────────────

def fetch_batch(players):
    """Fetch country for a batch of players using an IN(...) query."""
    # Build SQL-style IN list
    names_sql = ", ".join(f'"{p}"' for p in players)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = site.cargo_client.query(
                tables="Players",
                fields="ID=Player, Country, Nationality, NationalityPrimary",
                where=f"ID IN ({names_sql})",
                limit=BATCH_SIZE
            )
            return list(response)
        except Exception as e:
            if "ratelimited" in str(e):
                if attempt < MAX_RETRIES:
                    print(f"  Rate limited. Waiting {RETRY_WAIT}s... (attempt {attempt}/{MAX_RETRIES})")
                    time.sleep(RETRY_WAIT)
                else:
                    print(f"  Gave up after {MAX_RETRIES} attempts.")
                    return []
            else:
                print(f"  Error: {e}")
                return []

# Split into batches of BATCH_SIZE
batches = [player_list[i:i+BATCH_SIZE] for i in range(0, len(player_list), BATCH_SIZE)]
print(f"Fetching countries in {len(batches)} batch(es) of up to {BATCH_SIZE} players...\n")

country_records = []
for i, batch in enumerate(batches):
    print(f"[Batch {i+1}/{len(batches)}] Fetching {len(batch)} players...")
    rows = fetch_batch(batch)
    if rows:
        country_records.extend(rows)
        print(f"  Got {len(rows)} results")
    else:
        print(f"  No results returned")
    if i < len(batches) - 1:
        print(f"  Waiting {DELAY}s...")
        time.sleep(DELAY)

# ── Build country lookup ──────────────────────────────────────────────────────

if not country_records:
    print("\nNo country data collected.")
else:
    country_df = pd.DataFrame(country_records)

    # Use NationalityPrimary first, fall back to Nationality, then Country
    def best_country(row):
        return (
            row.get("NationalityPrimary") or
            row.get("Nationality") or
            row.get("Country") or
            ""
        )

    country_df["Country"] = country_df.apply(best_country, axis=1)
    country_df = country_df[["Player", "Country"]].drop_duplicates("Player")

    matched   = (country_df["Country"] != "").sum()
    unmatched = len(country_df) - matched
    print(f"\n✓ Country found for {matched}/{len(country_df)} players")
    if unmatched:
        print(f"  {unmatched} players had no country data (likely non-standard names)")

    # Save standalone lookup
    country_df.to_csv("player_countries.csv", index=False)
    print(f"✓ Saved: player_countries.csv")

    # ── Merge into each season CSV ────────────────────────────────────────────

    print("\nMerging Country into season CSVs...")
    for s, df in season_dfs.items():
        # Drop existing Country column if present (avoid duplicates)
        if "Country" in df.columns:
            df = df.drop(columns=["Country"])

        merged = df.merge(country_df, on="Player", how="left")

        # Place Country right after Team/League/Role/Tier if they exist,
        # otherwise right after Player
        priority = ["Player", "Team", "League", "Role", "Tier", "Country"]
        front = [c for c in priority if c in merged.columns]
        rest  = [c for c in merged.columns if c not in front]
        merged = merged[front + rest]

        merged.to_csv(f'player_careers_S{s}.csv', index=False)

        filled = merged["Country"].notna().sum()
        total  = len(merged)
        print(f"  S{s}: {filled:>4}/{total} players have country ({filled/total*100:.1f}%)")

    # ── Country distribution ──────────────────────────────────────────────────

    print("\nTop 20 countries across all players:")
    top_countries = (
        country_df[country_df["Country"] != ""]["Country"]
        .value_counts()
        .head(20)
    )
    for country, count in top_countries.items():
        print(f"  {country:<25} {count}")

    print("\n✓ All done!")