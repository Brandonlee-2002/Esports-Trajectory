"""
Build h2_longitudinal.csv from h2_roster_panel.csv + h2_league_tier_map.csv.

Player-level definitions (match standard H2 panel logic):

  - debut_season — min calendar year the player appears (groupby transform min).
  - debut_tier — tier on roster rows in that debut year only, first row after
    sorting by split/league (not mode across career).
  - first_tier1_season — min year where mapped tier == 1 (NaN if never).
  - seasons_to_promotion — first_tier1_season - debut_season (NaN if no first T1 year).
  - censored — still without Tier 1 and last observed year recent enough to be “at risk”:
      first_tier1_season.isna() & (last_season >= current_season - 1)

Also writes LoL season labels (S6–S15) derived from 2016–2025.

Usage (from repo root):
  python src/analysis/build_h2_panel.py
  python src/analysis/build_h2_panel.py --current-season 2025 \\
      --roster data/h2/h2_roster_panel.csv --map data/h2/h2_league_tier_map.csv \\
      --out data/h2/h2_longitudinal.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROSTER = REPO_ROOT / "data" / "h2" / "h2_roster_panel.csv"
DEFAULT_MAP = REPO_ROOT / "data" / "h2" / "h2_league_tier_map.csv"
DEFAULT_OUT = REPO_ROOT / "data" / "h2" / "h2_longitudinal.csv"

# Calendar year -> competitive season index (S6 = 2016, …, S15 = 2025)
YEAR_TO_SNUM = {y: i for i, y in enumerate(range(2016, 2026), start=6)}


def year_to_lol_season(y: int) -> str:
    n = YEAR_TO_SNUM.get(int(y))
    return f"S{n}" if n is not None else ""


SPLIT_ORDER = (
    ("Play-In", 5),
    ("Spring", 10),
    ("Summer", 20),
    ("Split 1", 15),
    ("Split 2", 25),
    ("Winter", 8),
    ("Fall", 30),
    ("Playoffs", 40),
    ("Showmatch", 50),
    ("Qualifier", 3),
)


def split_sort_key(split_val: object) -> int:
    if split_val is None or (isinstance(split_val, float) and pd.isna(split_val)):
        return 100
    s = str(split_val).lower()
    for key, rank in SPLIT_ORDER:
        if key.lower() in s:
            return rank
    return 35


def load_league_rules(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df["tier"] = pd.to_numeric(df["tier"], errors="coerce").fillna(2).astype(int)
    df["match_mode"] = df["match_mode"].fillna("contains").str.strip().str.lower()
    return df


def lookup_league_tier_region(league: str, rules: pd.DataFrame) -> Tuple[int, str]:
    """Return (tier, region). Longer patterns first for contains; __DEFAULT__ last."""
    l = (league or "").strip()
    non_default = rules[rules["match_mode"] != "default"].copy()
    if not non_default.empty:
        non_default["_plen"] = non_default["league_pattern"].str.len()
        non_default = non_default.sort_values("_plen", ascending=False)
        for _, row in non_default.iterrows():
            pat = str(row["league_pattern"]).strip()
            mode = row["match_mode"]
            if mode == "exact" and l == pat:
                return int(row["tier"]), str(row["region"])
            if mode == "contains" and pat.lower() in l.lower():
                return int(row["tier"]), str(row["region"])
    default_rows = rules[rules["match_mode"] == "default"]
    if not default_rows.empty:
        r = default_rows.iloc[0]
        return int(r["tier"]), str(r["region"])
    return 2, "Unknown"


def build_longitudinal(
    roster: pd.DataFrame,
    rules: pd.DataFrame,
    current_season: int = 2025,
) -> pd.DataFrame:
    """
    One row per player. ``current_season`` is the latest calendar year in the panel
    (used for censoring: last_season >= current_season - 1).
    """
    df = roster.copy()
    df["tier"] = df["league"].apply(lambda x: lookup_league_tier_region(x, rules)[0])
    df["region_m"] = df["league"].apply(lambda x: lookup_league_tier_region(x, rules)[1])
    df["_sk"] = df["split"].apply(split_sort_key)

    df["debut_season"] = df.groupby("player")["year"].transform("min")

    # Rows in debut year only — first row after split/league order = debut tier (not career mode)
    in_debut = df[df["year"] == df["debut_season"]].sort_values(
        ["player", "_sk", "league"]
    )
    # Drop transform column so .first() does not duplicate "debut_season" after we rename "year"
    in_debut = in_debut.drop(columns=["debut_season"], errors="ignore")
    debut_snap = in_debut.groupby("player", as_index=False).first()
    debut_snap = debut_snap.rename(
        columns={
            "year": "debut_season",
            "tier": "debut_tier",
            "league": "debut_league",
            "region_m": "debut_region",
        }
    )[["player", "debut_season", "debut_tier", "debut_league", "debut_region"]]

    first_tier1 = (
        df[df["tier"] == 1]
        .groupby("player")["year"]
        .min()
        .rename("first_tier1_season")
    )
    last_season = df.groupby("player")["year"].max().rename("last_season")

    out = debut_snap.merge(first_tier1.reset_index(), on="player", how="left")
    out = out.merge(last_season.reset_index(), on="player", how="left")

    out["debut_season"] = out["debut_season"].astype(int)

    out["ever_reached_tier1"] = out["first_tier1_season"].notna()

    out["seasons_to_promotion"] = out["first_tier1_season"] - out["debut_season"]
    out.loc[out["first_tier1_season"].isna(), "seasons_to_promotion"] = np.nan

    out["censored"] = out["first_tier1_season"].isna() & (
        out["last_season"] >= (current_season - 1)
    )

    out["promoted_from_tier2"] = (out["debut_tier"] == 2) & out["ever_reached_tier1"]

    # LoL season labels (S6–S15) for years in range
    out["debut_lol_season"] = out["debut_season"].apply(
        lambda x: year_to_lol_season(int(x)) if pd.notna(x) else ""
    )
    out["first_tier1_lol_season"] = out["first_tier1_season"].apply(
        lambda x: year_to_lol_season(int(x)) if pd.notna(x) else ""
    )

    # Stable column order + backward-compatible aliases
    out["debut_year"] = out["debut_season"]
    out["first_tier1_year"] = out["first_tier1_season"]
    out["seasons_debut_to_first_tier1"] = out["seasons_to_promotion"]
    out["right_censored_no_tier1"] = out["censored"].astype(int)
    out["last_year_observed"] = out["last_season"]

    cols = [
        "player",
        "debut_season",
        "debut_lol_season",
        "debut_league",
        "debut_tier",
        "debut_region",
        "first_tier1_season",
        "first_tier1_lol_season",
        "ever_reached_tier1",
        "promoted_from_tier2",
        "seasons_to_promotion",
        "last_season",
        "censored",
        "debut_year",
        "first_tier1_year",
        "seasons_debut_to_first_tier1",
        "right_censored_no_tier1",
        "last_year_observed",
    ]
    return out[cols]


def main() -> int:
    ap = argparse.ArgumentParser(description="Build h2_longitudinal.csv for Hypothesis 2")
    ap.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    ap.add_argument("--map", type=Path, default=DEFAULT_MAP)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--current-season",
        type=int,
        default=2025,
        help="Latest calendar year in panel; censoring uses last_season >= this minus 1",
    )
    args = ap.parse_args()

    if not args.roster.is_file():
        print(f"error: roster file not found: {args.roster}")
        print("Run: python scrapers/pull_h2_roster_panel.py")
        return 1
    if not args.map.is_file():
        print(f"error: league map not found: {args.map}")
        return 1

    roster = pd.read_csv(args.roster, dtype={"year": int})
    rules = load_league_rules(args.map)
    long_df = build_longitudinal(roster, rules, current_season=args.current_season)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    long_df.to_csv(args.out, index=False)
    print(f"Wrote {len(long_df)} players to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
