"""
Generate Hypothesis 2 figures and ``website/js/h2_summary.json`` from the H2 panel.

Reads ``data/h2/h2_longitudinal.csv`` if present; otherwise builds it from
``h2_roster_panel.csv`` + ``h2_league_tier_map.csv`` (same as ``build_h2_panel.py``).

Outputs (default paths):
  - ``reports/h2_fig*.png`` — static figures for the paper/repo
  - ``website/assets/figures/h2_fig*.png`` — copies for the static site
  - ``website/js/h2_summary.json`` — metrics, tables, and chart data
  - ``website/js/h2_summary.js`` — same payload as ``window.H2_SUMMARY_DATA`` (loads synchronously on Hypothesis 2 for print/PDF)

Usage (repo root):
  python src/analysis/h2_figures.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from build_h2_panel import (
    DEFAULT_MAP,
    DEFAULT_OUT,
    DEFAULT_ROSTER,
    build_longitudinal,
    load_league_rules,
    split_sort_key,
    year_to_lol_season,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = REPO_ROOT / "reports"
ASSETS_FIG = REPO_ROOT / "website" / "assets" / "figures"
JS_DIR = REPO_ROOT / "website" / "js"

GOLD = "#d4a74a"
BLUE = "#5b8bd4"
MUTED = "#94a3b8"
TICK = "#64748b"


def _ensure_longitudinal(
    roster_path: Path,
    map_path: Path,
    long_path: Path,
    current_season: int,
) -> pd.DataFrame:
    if long_path.is_file():
        return pd.read_csv(long_path)
    if not roster_path.is_file():
        raise FileNotFoundError(
            f"Missing {long_path} and roster {roster_path}. "
            "Run: python scrapers/pull_h2_roster_panel.py then python src/analysis/build_h2_panel.py"
        )
    roster = pd.read_csv(roster_path, dtype={"year": int})
    rules = load_league_rules(map_path)
    return build_longitudinal(roster, rules, current_season=current_season)


def _debut_role(roster: pd.DataFrame, players_debut: pd.DataFrame) -> pd.DataFrame:
    """Map player -> role at debut year (first row by split/league order)."""
    df = roster.copy()
    df["_sk"] = df["split"].apply(split_sort_key)
    m = players_debut.merge(
        df,
        left_on=["player", "debut_season"],
        right_on=["player", "year"],
        how="left",
    )
    m = m.sort_values(["player", "_sk", "league"])
    snap = m.groupby("player", as_index=False).first()
    return snap[["player", "role"]].rename(columns={"role": "debut_role"})


def _short_league(name: str, max_len: int = 28) -> str:
    s = (name or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _cohort_stats(long_df: pd.DataFrame, roster: pd.DataFrame | None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    t2 = long_df[long_df["debut_tier"] == 2].copy()
    n_t2 = len(t2)
    promoted = t2["promoted_from_tier2"].fillna(False).astype(bool)
    n_prom = int(promoted.sum())
    rate = (100.0 * n_prom / n_t2) if n_t2 else 0.0

    seasons = t2.loc[promoted, "seasons_to_promotion"].dropna()
    med = float(seasons.median()) if len(seasons) else float("nan")
    within2 = seasons[seasons <= 2]
    pct_within_2 = (100.0 * len(within2) / len(seasons)) if len(seasons) else float("nan")

    # League breakdown (all debut leagues with n >= 1; page filters n>=2 for chart)
    league_rows = []
    for league, g in t2.groupby("debut_league", dropna=False):
        nn = len(g)
        pr = int(g["promoted_from_tier2"].fillna(False).sum())
        league_rows.append(
            {
                "league": str(league) if pd.notna(league) else "(unknown)",
                "league_short": _short_league(str(league) if pd.notna(league) else "(unknown)"),
                "n": nn,
                "promoted": pr,
                "rate_pct": (100.0 * pr / nn) if nn else 0.0,
            }
        )
    league_rows.sort(key=lambda r: (-r["n"], r["league"]))

    # Role breakdown
    role_rows: List[Dict[str, Any]] = []
    if roster is not None and not roster.empty:
        dr = _debut_role(roster, t2[["player", "debut_season"]])
        t2r = t2.merge(dr, on="player", how="left")
        t2r["debut_role"] = t2r["debut_role"].fillna("(unknown)")
        for role, g in t2r.groupby("debut_role", dropna=False):
            nn = len(g)
            pr = int(g["promoted_from_tier2"].fillna(False).sum())
            role_rows.append(
                {
                    "role": str(role),
                    "n": nn,
                    "promoted": pr,
                    "rate_pct": (100.0 * pr / nn) if nn else 0.0,
                }
            )
        role_order = ["Top", "Jungle", "Mid", "Bot", "ADC", "Support", "(unknown)"]
        role_rows.sort(
            key=lambda r: (role_order.index(r["role"]) if r["role"] in role_order else 99, -r["n"])
        )
    else:
        t2r = t2

    # Histogram: seasons until promotion (1 .. max), only promoted T2
    hist_counts: Dict[int, int] = {}
    if len(seasons):
        mx = int(max(1, seasons.max()))
        for i in range(1, mx + 1):
            hist_counts[i] = int((seasons == i).sum())

    # Promoted player detail rows
    prom_df = t2[promoted].sort_values(
        ["seasons_to_promotion", "player"], na_position="last"
    )
    player_detail = []
    for _, row in prom_df.iterrows():
        ds = int(row["debut_season"]) if pd.notna(row["debut_season"]) else None
        fs = row["first_tier1_season"]
        st = row["seasons_to_promotion"]
        player_detail.append(
            {
                "player": row["player"],
                "league": _short_league(str(row.get("debut_league", "")), 40),
                "debut_season_label": row.get("debut_lol_season") or (year_to_lol_season(ds) if ds else ""),
                "first_t1_label": row.get("first_tier1_lol_season")
                or (year_to_lol_season(int(fs)) if pd.notna(fs) else ""),
                "seasons_taken": int(st) if pd.notna(st) else None,
                "tier_path": "T2 → T1",
            }
        )

    summary: Dict[str, Any] = {
        "n_tier2_debut": n_t2,
        "n_promoted_to_tier1": n_prom,
        "promotion_rate_pct": round(rate, 2),
        "median_seasons_to_tier1": None if np.isnan(med) else round(med, 2),
        "pct_promoted_within_2_seasons": None if np.isnan(pct_within_2) else round(pct_within_2, 1),
        "n_never_t1": n_t2 - n_prom,
        "league_table": league_rows,
        "role_table": role_rows,
        "time_histogram": hist_counts,
        "promoted_players": player_detail,
    }
    return t2r, summary


def _plot_outcomes(n_never: int, n_prom: int, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    sizes = [n_never, n_prom]
    labels = [
        f"Never reached Tier 1 ({100 * n_never / max(1, sum(sizes)):.1f}%)",
        f"Promoted to Tier 1 ({100 * n_prom / max(1, sum(sizes)):.1f}%)",
    ]
    colors = [MUTED, GOLD]
    ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.5, edgecolor="white", linewidth=2),
        textprops={"color": TICK, "fontsize": 10},
    )
    ax.set_title("Tier 2 debut — career outcomes", color=TICK, fontsize=12, pad=12)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _plot_time_histogram(hist: Dict[int, int], n_promoted: int, path: Path) -> None:
    if not hist:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.text(0.5, 0.5, "No Tier 2 → Tier 1 promotions in cohort", ha="center", va="center")
        ax.axis("off")
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return
    keys = sorted(hist.keys())
    vals = [hist[k] for k in keys]
    labels = [f"{k} season{'s' if k != 1 else ''}" if k <= 3 else str(k) for k in keys]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(range(len(keys)), vals, color=GOLD, edgecolor="white", linewidth=0.8)
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=9, color=TICK)
    ax.set_ylabel("Players", color=TICK)
    ax.set_xlabel("Seasons from Tier 2 debut to first Tier 1 season", color=TICK)
    ymax = max(vals) if vals else 1
    ax.set_ylim(0, ymax + max(1, ymax * 0.15))
    ax.set_title(
        f"Time to first Tier 1 (n = {n_promoted} promoted)",
        color=TICK,
        fontsize=12,
    )
    ax.tick_params(colors=TICK)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _plot_league_rates(league_table: List[Dict[str, Any]], path: Path, min_n: int = 2) -> None:
    filt = [r for r in league_table if r["n"] >= min_n]
    filt.sort(key=lambda r: -r["n"])
    filt = filt[:20]
    if not filt:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, f"No leagues with ≥{min_n} Tier 2 debuts", ha="center", va="center")
        ax.axis("off")
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return
    filt.sort(key=lambda r: (-r["rate_pct"], -r["n"]))
    labels = [r["league_short"] for r in filt]
    rates = [r["rate_pct"] for r in filt]
    colors = [GOLD if r["promoted"] > 0 else BLUE for r in filt]
    fig, ax = plt.subplots(figsize=(8, max(4, 0.35 * len(filt))))
    y = np.arange(len(filt))
    ax.barh(y, rates, color=colors, edgecolor="white", height=0.65)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9, color=TICK)
    ax.invert_yaxis()
    ax.set_xlabel("Promotion rate (%)", color=TICK)
    ax.set_title(f"Tier 2 → Tier 1 by debut league (n ≥ {min_n} per league)", color=TICK, fontsize=11)
    ax.tick_params(colors=TICK)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _plot_role_rates(role_table: List[Dict[str, Any]], path: Path, min_n: int = 2) -> None:
    filt = [r for r in role_table if r["n"] >= min_n]
    if not filt:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.text(0.5, 0.5, f"No roles with ≥{min_n} Tier 2 debuts", ha="center", va="center")
        ax.axis("off")
        fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
        plt.close(fig)
        return
    filt.sort(key=lambda r: -r["rate_pct"])
    labels = [r["role"] for r in filt]
    rates = [r["rate_pct"] for r in filt]
    colors = [GOLD if r["rate_pct"] > 0 else MUTED for r in filt]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(filt))
    ax.bar(x, rates, color=colors, edgecolor="white", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right", fontsize=10, color=TICK)
    ax.set_ylabel("Promotion rate (%)", color=TICK)
    ax.set_title(f"By debut role (n ≥ {min_n})", color=TICK, fontsize=11)
    ax.tick_params(colors=TICK)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _copy_reports_to_assets(paths: List[Path]) -> None:
    ASSETS_FIG.mkdir(parents=True, exist_ok=True)
    for p in paths:
        if p.is_file():
            dest = ASSETS_FIG / p.name
            dest.write_bytes(p.read_bytes())


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate H2 figures and h2_summary.json")
    ap.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    ap.add_argument("--map", type=Path, default=DEFAULT_MAP)
    ap.add_argument("--longitudinal", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--current-season", type=int, default=2025)
    ap.add_argument("--reports", type=Path, default=REPORTS_DIR)
    args = ap.parse_args()

    plt.style.use("seaborn-v0_8-whitegrid")
    plt.rcParams["font.size"] = 10

    try:
        long_df = _ensure_longitudinal(
            args.roster, args.map, args.longitudinal, args.current_season
        )
    except FileNotFoundError as e:
        print(e)
        return 1

    roster_df: pd.DataFrame | None = None
    if args.roster.is_file():
        roster_df = pd.read_csv(args.roster, dtype={"year": int})

    _, summary = _cohort_stats(long_df, roster_df)

    n_t2 = summary["n_tier2_debut"]
    n_prom = summary["n_promoted_to_tier1"]
    n_never = summary["n_never_t1"]
    hist = summary["time_histogram"]

    args.reports.mkdir(parents=True, exist_ok=True)
    JS_DIR.mkdir(parents=True, exist_ok=True)

    p1 = args.reports / "h2_fig1_tier2_outcomes.png"
    p2 = args.reports / "h2_fig2_seasons_to_tier1.png"
    p3 = args.reports / "h2_fig3_promotion_by_league.png"
    p4 = args.reports / "h2_fig4_promotion_by_role.png"

    _plot_outcomes(n_never, n_prom, p1)
    _plot_time_histogram(hist, n_prom, p2)
    _plot_league_rates(summary["league_table"], p3, min_n=2)
    _plot_role_rates(summary["role_table"], p4, min_n=2)
    _copy_reports_to_assets([p1, p2, p3, p4])

    n_roster = len(roster_df) if roster_df is not None else 0
    league_all = list(summary["league_table"])
    league_top = sorted(league_all, key=lambda r: (-r["n"], r["league"]))[:40]
    for row in summary["role_table"]:
        row["rate_pct"] = round(float(row["rate_pct"]), 2)
    for row in league_top:
        row["rate_pct"] = round(float(row["rate_pct"]), 2)

    try:
        roster_rel = args.roster.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        roster_rel = args.roster.as_posix()

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "roster_source": roster_rel,
        "cohort": "Players whose first observed year is in a Tier 2 league (2016–2025 panel)",
        "n_roster_rows": n_roster,
        "n_unique_players_panel": int(len(long_df)),
        "n_debut_leagues_distinct": len(league_all),
        **{k: v for k, v in summary.items() if k != "league_table"},
        "league_table": league_top,
        "methodology_notes": [
            "Source: Leaguepedia Cargo (TournamentPlayers × Tournaments), scoped by tournament start date per calendar year.",
            "Tier 1 vs 2: string match against data/h2/h2_league_tier_map.csv (see match_mode: contains / exact / default).",
            "Debut tier: first roster row in the player's minimum calendar year after split ordering (same rule as build_h2_panel.py).",
            "First Tier 1 season: earliest year with any Tier-1-mapped league appearance; seasons_to_promotion is the calendar-year difference (0 = same year).",
            "Cargo does not expose starter/substitute flags; every roster row is treated equally.",
        ],
    }
    out_json = JS_DIR / "h2_summary.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # Load synchronously from /pages/hypothesis2.html so print/PDF and slow networks
    # still see metrics without waiting on fetch().
    out_js = JS_DIR / "h2_summary.js"
    js_body = json.dumps(payload, ensure_ascii=True)
    out_js.write_text(
        "/* Generated by h2_figures.py — do not edit by hand */\n"
        "window.H2_SUMMARY_DATA = "
        + js_body
        + ";\n",
        encoding="utf-8",
    )

    print(f"Wrote {p1.name}, {p2.name}, {p3.name}, {p4.name} under {args.reports}")
    print(f"Copied figures to {ASSETS_FIG}")
    print(f"Wrote {out_json} and {out_js.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
