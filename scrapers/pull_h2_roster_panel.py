"""
Pull h2_roster_panel.csv from Leaguepedia Cargo via mwrogue (one calendar year per batch).

Output columns (source of truth for Hypothesis 2 roster rows):
  player, team, role, league, year, split, is_starter

Run ``src/analysis/build_h2_panel.py`` on this CSV + ``data/h2/h2_league_tier_map.csv`` to get
player-level: debut_season, debut_tier (from debut year only), first_tier1_season,
seasons_to_promotion, censored (see that script).

Leaguepedia ``TournamentPlayers`` does not expose IsStarter/IsSubstitute in Cargo; ``is_starter``
is left blank (unknown). Extend this script if a field is added upstream.

Install:
  pip install mwrogue mwparserfromhell pandas

Usage (from repo root):
  python scrapers/pull_h2_roster_panel.py
  python scrapers/pull_h2_roster_panel.py --out data/h2/h2_roster_panel.csv --start-year 2018 --end-year 2020

Requires network access to lol.fandom.com.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

try:
    from mwrogue.esports_client import EsportsClient
except ImportError as e:
    EsportsClient = None  # type: ignore
    _IMPORT_ERR = e
else:
    _IMPORT_ERR = None

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "data" / "h2" / "h2_roster_panel.csv"

PAGE_SIZE = 500
PAGE_DELAY = 2.0
YEAR_DELAY = 5.0
RETRY_WAIT = 90
MAX_RETRIES = 6


def query_with_retry(site: Any, **kwargs: Any) -> Optional[List[Dict[str, Any]]]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return list(site.cargo_client.query(**kwargs))
        except Exception as e:
            err = str(e).lower()
            if "ratelimit" in err:
                wait = RETRY_WAIT * attempt
                print(f"    Rate limited. Waiting {wait}s... ({attempt}/{MAX_RETRIES})")
                time.sleep(wait)
            else:
                print(f"    Error: {e}")
                return None
    return None


def fetch_year_all_pages(site: Any, year: int) -> Optional[List[Dict[str, Any]]]:
    """TournamentPlayers × Tournaments for tournaments starting in ``year``."""
    date_start = f"{year}-01-01"
    date_end = f"{year}-12-31"
    all_rows: List[Dict[str, Any]] = []
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
                "Tournaments.League=League,"
                "Tournaments.Split=Split,"
                "Tournaments.DateStart=DateStart"
            ),
            where=(
                f'Tournaments.DateStart >= "{date_start}" AND '
                f'Tournaments.DateStart <= "{date_end}"'
            ),
            join_on="TournamentPlayers.OverviewPage=Tournaments.OverviewPage",
            order_by="Tournaments.DateStart ASC, TournamentPlayers.Player ASC",
            limit=PAGE_SIZE,
            offset=offset,
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


def rows_to_records(rows: List[Dict[str, Any]], year: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        player = (row.get("Player") or "").strip()
        team = (row.get("Team") or "").strip()
        role = (row.get("Role") or "").strip()
        league = (row.get("League") or "").strip()
        split = row.get("Split")
        split_s = "" if split is None or (isinstance(split, float) and pd.isna(split)) else str(split).strip()
        ds = row.get("DateStart") or ""
        ds = str(ds).strip()
        y = year
        if ds and len(ds) >= 4 and ds[:4].isdigit():
            y = int(ds[:4])
        # is_starter: not available in Cargo — leave blank
        out.append(
            {
                "player": player,
                "team": team,
                "role": role,
                "league": league,
                "year": y,
                "split": split_s,
                "is_starter": "",
            }
        )
    return out


def pull_roster_panel(
    out_path: Path,
    start_year: int = 2016,
    end_year: int = 2025,
) -> int:
    if EsportsClient is None:
        print("error: mwrogue is required: pip install mwrogue mwparserfromhell", file=sys.stderr)
        print(_IMPORT_ERR, file=sys.stderr)
        return 1

    print("Connecting to Leaguepedia (mwrogue)...")
    site = EsportsClient("lol")
    print("Connected.\n")

    all_records: List[Dict[str, Any]] = []
    for year in range(start_year, end_year + 1):
        print(f"[{year}] Fetching TournamentPlayers…")
        rows = fetch_year_all_pages(site, year)
        if rows is None:
            print(f"Aborting on year {year}.")
            return 1
        recs = rows_to_records(rows, year)
        all_records.extend(recs)
        print(f"  Year {year}: {len(recs)} roster rows (running total {len(all_records)})\n")
        time.sleep(YEAR_DELAY)

    df = pd.DataFrame(all_records)
    df = df[df["player"] != ""]
    df = df.drop_duplicates(
        subset=["player", "team", "role", "league", "year", "split", "is_starter"],
        keep="first",
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows to {out_path}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Pull h2_roster_panel.csv from Leaguepedia Cargo")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output CSV path")
    p.add_argument("--start-year", type=int, default=2016)
    p.add_argument("--end-year", type=int, default=2025)
    args = p.parse_args()
    return pull_roster_panel(args.out, args.start_year, args.end_year)


if __name__ == "__main__":
    raise SystemExit(main())
