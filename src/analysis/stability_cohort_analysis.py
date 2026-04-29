"""
Generate stability/cohort analysis outputs for final presentation.

Outputs:
  - website/js/stability_cohort_summary.json
  - website/js/stability_cohort_summary.js

Usage (repo root):
  python src/analysis/stability_cohort_analysis.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

import numpy as np
import pandas as pd

try:
    import statsmodels.api as sm
except ModuleNotFoundError:
    sm = None


REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed"
WEBSITE_JS_DIR = REPO_ROOT / "website" / "js"


def _load_data() -> tuple[pd.DataFrame, bool]:
    players_file = PROCESSED_DIR / "players_processed.csv"
    careers_file = PROCESSED_DIR / "career_metrics.csv"
    if players_file.is_file() and careers_file.is_file():
        players = pd.read_csv(players_file)
        careers = pd.read_csv(careers_file)
        df = careers.merge(players, on="player_id", how="left")
        return df, False

    # Keep this script runnable in fresh clones without local raw data.
    from eda import generate_sample_data  # local module under src/analysis

    players, careers = generate_sample_data(n=500)
    df = careers.merge(players, on="player_id", how="left")
    return df, True


def _bucket_volatility(num_teams: float) -> str:
    team_changes = max(0.0, float(num_teams) - 1.0)
    if team_changes <= 1:
        return "Stable (0-1 changes)"
    if team_changes <= 2:
        return "Moderate (2 changes)"
    return "High (3+ changes)"


def _fit_logit(y: pd.Series, x: pd.DataFrame) -> Dict[str, Any]:
    if sm is not None:
        x_const = sm.add_constant(x, has_constant="add")
        model = sm.Logit(y, x_const, missing="drop")
        res = model.fit(disp=False)

        out = {
            "method": "logit",
            "n_obs": int(res.nobs),
            "pseudo_r2": float(res.prsquared),
            "aic": float(res.aic),
            "coefficients": {},
        }
        for name in res.params.index:
            out["coefficients"][name] = {
                "coef": float(res.params[name]),
                "p_value": float(res.pvalues[name]),
                "odds_ratio": float(np.exp(res.params[name])),
            }
        return out

    # Fallback: linear probability model if statsmodels is unavailable.
    cols = ["const"] + list(x.columns)
    X = np.column_stack([np.ones(len(x)), x.to_numpy(dtype=float)])
    Y = y.to_numpy(dtype=float)
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    y_hat = X @ beta
    rss = float(((Y - y_hat) ** 2).sum())
    tss = float(((Y - Y.mean()) ** 2).sum())
    r2 = 0.0 if tss == 0 else 1.0 - (rss / tss)

    coeffs = {}
    for i, name in enumerate(cols):
        coeffs[name] = {
            "coef": float(beta[i]),
            "p_value": None,
            "odds_ratio": None,
        }
    return {
        "method": "linear_probability_fallback",
        "n_obs": int(len(y)),
        "pseudo_r2": None,
        "aic": None,
        "r2": float(r2),
        "coefficients": coeffs,
    }


def build_summary(df: pd.DataFrame, used_sample_data: bool) -> Dict[str, Any]:
    work = df.copy()
    work["career_length_years"] = pd.to_numeric(work["career_length_years"], errors="coerce")
    work["num_teams"] = pd.to_numeric(work["num_teams"], errors="coerce").fillna(1)
    work["starting_tier"] = pd.to_numeric(work.get("starting_tier"), errors="coerce").fillna(2)
    work["career_start_year"] = pd.to_numeric(work["career_start_year"], errors="coerce")
    work = work.dropna(subset=["career_length_years", "career_start_year"])

    work["team_changes_proxy"] = (work["num_teams"] - 1).clip(lower=0)
    work["volatility_bucket"] = work["num_teams"].apply(_bucket_volatility)
    work["survived_5y"] = (work["career_length_years"] >= 5).astype(int)
    work["early_exit_2y"] = (work["career_length_years"] <= 2).astype(int)

    by_bucket = (
        work.groupby("volatility_bucket", dropna=False)
        .agg(
            n_players=("player_id", "count"),
            avg_career_years=("career_length_years", "mean"),
            median_career_years=("career_length_years", "median"),
            pct_survived_5y=("survived_5y", "mean"),
            pct_early_exit_2y=("early_exit_2y", "mean"),
            avg_team_changes_proxy=("team_changes_proxy", "mean"),
        )
        .reset_index()
    )
    bucket_order = ["Stable (0-1 changes)", "Moderate (2 changes)", "High (3+ changes)"]
    by_bucket["volatility_bucket"] = pd.Categorical(by_bucket["volatility_bucket"], bucket_order, ordered=True)
    by_bucket = by_bucket.sort_values("volatility_bucket")

    cohort = (
        work.groupby("career_start_year")
        .agg(
            n_players=("player_id", "count"),
            avg_team_changes_proxy=("team_changes_proxy", "mean"),
            pct_early_exit_2y=("early_exit_2y", "mean"),
            avg_career_years=("career_length_years", "mean"),
        )
        .reset_index()
        .sort_values("career_start_year")
    )

    x_year = cohort["career_start_year"].to_numpy(dtype=float)
    y_changes = cohort["avg_team_changes_proxy"].to_numpy(dtype=float)
    y_exit = cohort["pct_early_exit_2y"].to_numpy(dtype=float)
    slope_changes = float(np.polyfit(x_year, y_changes, 1)[0]) if len(cohort) >= 2 else 0.0
    slope_exit = float(np.polyfit(x_year, y_exit, 1)[0]) if len(cohort) >= 2 else 0.0

    predictors = work[["team_changes_proxy", "starting_tier", "career_start_year"]].astype(float)
    logit_survival = _fit_logit(work["survived_5y"], predictors)
    logit_early_exit = _fit_logit(work["early_exit_2y"], predictors)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "used_sample_data": used_sample_data,
        "n_players": int(len(work)),
        "volatility_vs_survival": [
            {
                "bucket": str(r.volatility_bucket),
                "n_players": int(r.n_players),
                "avg_career_years": round(float(r.avg_career_years), 2),
                "median_career_years": round(float(r.median_career_years), 2),
                "pct_survived_5y": round(float(r.pct_survived_5y) * 100, 1),
                "pct_early_exit_2y": round(float(r.pct_early_exit_2y) * 100, 1),
                "avg_team_changes_proxy": round(float(r.avg_team_changes_proxy), 2),
            }
            for _, r in by_bucket.iterrows()
        ],
        "cohort_volatility": [
            {
                "career_start_year": int(r.career_start_year),
                "n_players": int(r.n_players),
                "avg_team_changes_proxy": round(float(r.avg_team_changes_proxy), 2),
                "pct_early_exit_2y": round(float(r.pct_early_exit_2y) * 100, 1),
                "avg_career_years": round(float(r.avg_career_years), 2),
            }
            for _, r in cohort.iterrows()
        ],
        "trend_summary": {
            "slope_team_changes_per_year": round(slope_changes, 4),
            "slope_early_exit_rate_per_year": round(slope_exit, 4),
            "interpretation": (
                "Positive slopes imply newer cohorts show more volatility/churn; "
                "negative slopes imply the opposite."
            ),
        },
        "logit_models": {
            "survived_5y": logit_survival,
            "early_exit_2y": logit_early_exit,
        },
        "notes": [
            "Team changes proxy uses num_teams - 1 from career-level aggregates.",
            "This is a structural proxy and not exact first-3-season transaction history.",
            "For stricter early-career stability, replace with season-level roster movement features.",
        ],
    }
    return summary


def main() -> int:
    df, used_sample_data = _load_data()
    summary = build_summary(df, used_sample_data)

    WEBSITE_JS_DIR.mkdir(parents=True, exist_ok=True)
    out_json = WEBSITE_JS_DIR / "stability_cohort_summary.json"
    out_js = WEBSITE_JS_DIR / "stability_cohort_summary.js"

    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    out_js.write_text(
        "/* Generated by stability_cohort_analysis.py */\n"
        "window.STABILITY_COHORT_SUMMARY = "
        + json.dumps(summary, ensure_ascii=True)
        + ";\n",
        encoding="utf-8",
    )

    print(f"Wrote {out_json}")
    print(f"Wrote {out_js}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

