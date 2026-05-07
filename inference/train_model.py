"""
train_model.py — Train and Save Inference Models
CS 163 Group 10 - Brandon Lee & Stephani Marie Soriano

Reads the season CSVs, builds the feature dataset, trains two models,
evaluates them on a held-out test set, and saves the trained models
as .pkl files for the inference service (inference/app.py) to load.

Models trained:
  1. Random Forest Regressor  → predicts career length (seasons)
  2. Cox Proportional Hazards → predicts survival curve per season

Run:
    python train_model.py

    # Or with custom paths:
    DATA_DIR=./data OUTPUT_DIR=./inference/models python train_model.py

Outputs (saved to OUTPUT_DIR, default = inference/models/):
    rf_model.pkl       — trained Random Forest + feature list + imputer
    cox_model.pkl      — trained Cox PH model
    metadata.pkl       — shared feature/league/role metadata
    training_report.txt — metrics, feature importances, model summary
"""

import os
import pickle
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────

DATA_DIR   = os.environ.get("DATA_DIR",   ".")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "inference/models")
SEASONS    = list(range(6, 16))
MAX_SEASON = 15
TEST_SIZE  = 0.2
RANDOM_STATE = 42

VALID_LEAGUES = ["LCK", "LPL", "LEC", "LCS"]
VALID_ROLES   = ["Top", "Jungle", "Mid", "Bot", "Support"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Step 1: Load season CSVs ──────────────────────────────────────────────────

print("=" * 60)
print("STEP 1: Loading season CSVs")
print("=" * 60)

dfs = {}
for s in SEASONS:
    path = f"{DATA_DIR}/player_careers_S{s}.csv"
    try:
        dfs[s] = pd.read_csv(path)
        print(f"  S{s}: {len(dfs[s])} players loaded")
    except FileNotFoundError:
        print(f"  WARNING: {path} not found — skipping")

if not dfs:
    raise FileNotFoundError(f"No CSV files found in {DATA_DIR}. "
                            "Place player_careers_S6.csv through S15.csv there.")

# ── Step 2: Build player career records ───────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 2: Building player career records")
print("=" * 60)

player_seasons = {}
player_league  = {}
player_role    = {}
player_stats   = {}

for s, df in dfs.items():
    for _, row in df.iterrows():
        p = row["Player"]
        player_seasons.setdefault(p, []).append(s)

        # First known league / role (use as primary)
        for col, store in [("League", player_league), ("Role", player_role)]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() and p not in store:
                store[p] = str(val).strip()

        # Collect per-season stats for feature engineering
        player_stats.setdefault(p, []).append({
            "kda":     pd.to_numeric(row.get("KDA"), errors="coerce"),
            "gpm":     pd.to_numeric(row.get("GPM"), errors="coerce"),
            "csm":     pd.to_numeric(row.get("CSM"), errors="coerce"),
            "dpm":     pd.to_numeric(row.get("DPM"), errors="coerce"),
            "winrate": pd.to_numeric(
                str(row.get("Win rate", "")).replace("%", ""), errors="coerce"),
            "kp":      pd.to_numeric(
                str(row.get("KP%", "")).replace("%", ""), errors="coerce"),
            "games":   pd.to_numeric(row.get("Games"), errors="coerce"),
        })

def safe_mean(vals):
    clean = [v for v in vals if pd.notna(v)]
    return round(float(np.mean(clean)), 3) if clean else np.nan

records = []
for p, seasons in player_seasons.items():
    career_len = len(set(seasons))
    last_s     = max(seasons)
    observed   = int(last_s != MAX_SEASON)   # 1 = career ended, 0 = still active (censored)
    debut      = min(seasons)

    league   = player_league.get(p)
    role_raw = str(player_role.get(p, ""))
    role     = role_raw.split(",")[0].strip()

    # Only keep players with known major league + role
    if league not in VALID_LEAGUES:
        continue
    if role not in VALID_ROLES:
        continue

    stats = player_stats.get(p, [])
    records.append({
        "Player":       p,
        "Career_Seasons": career_len,
        "Observed":     observed,
        "League":       league,
        "Role":         role,
        "Debut":        debut,
        # Early era = debuted S6-S9 (more seasons available → longer careers)
        "Early_Era":    int(debut <= 9),
        # Career-average performance stats
        "Avg_KDA":      safe_mean([s["kda"]     for s in stats]),
        "Avg_GPM":      safe_mean([s["gpm"]     for s in stats]),
        "Avg_CSM":      safe_mean([s["csm"]     for s in stats]),
        "Avg_DPM":      safe_mean([s["dpm"]     for s in stats]),
        "Avg_WR":       safe_mean([s["winrate"] for s in stats]),
        "Avg_KP":       safe_mean([s["kp"]      for s in stats]),
        "Total_Games":  int(sum(
            s["games"] for s in stats if pd.notna(s["games"]))),
    })

df_full = pd.DataFrame(records)
print(f"  Players with major league + known role: {len(df_full)}")
print(f"  Career length distribution:")
print(df_full["Career_Seasons"].value_counts().sort_index().to_string())

# ── Step 3: Feature engineering ───────────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 3: Feature engineering")
print("=" * 60)

# Impute missing performance stats with median
NUMERIC_FEATS = ["Avg_KDA", "Avg_GPM", "Avg_CSM", "Avg_DPM",
                 "Avg_WR", "Avg_KP", "Total_Games"]
imputer = SimpleImputer(strategy="median")
df_full[NUMERIC_FEATS] = imputer.fit_transform(df_full[NUMERIC_FEATS])

# Save median values as fallback for inference (when user doesn't provide stats)
MEDIANS = {col: float(np.median(df_full[col])) for col in NUMERIC_FEATS}
print(f"  Median fallback values for inference:")
for k, v in MEDIANS.items():
    print(f"    {k:<15}: {v:.2f}")

# One-hot encode League and Role
df_enc = pd.get_dummies(df_full, columns=["League", "Role"], drop_first=False)

# Convert bool columns (pandas >= 2.0 returns bool from get_dummies)
bool_cols = df_enc.select_dtypes(include="bool").columns
df_enc[bool_cols] = df_enc[bool_cols].astype(int)

# Drop reference categories (LCS = reference league, Top = reference role)
for drop_col in ["League_LCS", "Role_Top"]:
    if drop_col in df_enc.columns:
        df_enc = df_enc.drop(columns=[drop_col])

# Final feature list (everything except target, player name, survival columns)
FEATURE_COLS = [c for c in df_enc.columns
                if c not in ["Player", "Career_Seasons", "Observed"]]

print(f"\n  Feature columns ({len(FEATURE_COLS)}):")
for f in FEATURE_COLS:
    print(f"    {f}")

# ── Step 4: Train / test split ─────────────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 4: Train / test split (80/20, stratified)")
print("=" * 60)

# Stratify by career length bucket so both sets have similar distributions
df_enc["_bucket"] = pd.cut(
    df_enc["Career_Seasons"],
    bins=[0, 1, 2, 3, 5, 100],
    labels=["1", "2", "3", "4-5", "6+"]
)
train_df, test_df = train_test_split(
    df_enc,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=df_enc["_bucket"]
)
train_df = train_df.drop(columns=["_bucket"])
test_df  = test_df.drop(columns=["_bucket"])

X_train = train_df[FEATURE_COLS]
y_train = train_df["Career_Seasons"]
X_test  = test_df[FEATURE_COLS]
y_test  = test_df["Career_Seasons"]

print(f"  Train: {len(train_df)} players  (mean career = {y_train.mean():.2f})")
print(f"  Test:  {len(test_df)} players  (mean career = {y_test.mean():.2f})")

# Save for reference
train_df.to_csv(f"{OUTPUT_DIR}/../train_set.csv", index=False)
test_df.to_csv(f"{OUTPUT_DIR}/../test_set.csv",   index=False)
print(f"  Saved: train_set.csv, test_set.csv")

# ── Step 5: Train Random Forest ───────────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 5: Training Random Forest Regressor")
print("=" * 60)
print("  Hyperparameters:")
print("    n_estimators = 200")
print("    max_depth    = 8")
print("    min_samples_leaf = 5")

rf_model = RandomForestRegressor(
    n_estimators=200,
    max_depth=8,
    min_samples_leaf=5,
    random_state=RANDOM_STATE,
    n_jobs=-1,
)
rf_model.fit(X_train, y_train)

rf_pred_train = rf_model.predict(X_train)
rf_pred_test  = rf_model.predict(X_test)

mae_train = mean_absolute_error(y_train, rf_pred_train)
mae_test  = mean_absolute_error(y_test,  rf_pred_test)
rmse_test = float(np.sqrt(mean_squared_error(y_test, rf_pred_test)))
r2_test   = r2_score(y_test, rf_pred_test)

print(f"\n  Train MAE : {mae_train:.3f} seasons")
print(f"  Test  MAE : {mae_test:.3f}  seasons   ← main metric")
print(f"  Test  RMSE: {rmse_test:.3f} seasons")
print(f"  Test  R²  : {r2_test:.3f}             ← variance explained")

# Feature importances
feat_imp = (
    pd.Series(rf_model.feature_importances_, index=FEATURE_COLS)
    .sort_values(ascending=False)
)
print(f"\n  Feature importances (top 10):")
for feat, imp in feat_imp.head(10).items():
    bar = "█" * int(imp * 100)
    print(f"    {feat:<25} {imp:.4f}  {bar}")

# ── Step 6: Train Cox Proportional Hazards ────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 6: Training Cox Proportional Hazards Model")
print("=" * 60)
print("  Target : hazard of career ending per season")
print("  Features: League (vs LCS), Role (vs Top), Early_Era")

COX_FEATURES = [
    "League_LCK", "League_LPL", "League_LEC",
    "Role_Jungle", "Role_Mid", "Role_Bot", "Role_Support",
    "Early_Era",
]
# Only keep features that exist after encoding
COX_FEATURES = [f for f in COX_FEATURES if f in df_enc.columns]

cox_train = train_df[COX_FEATURES + ["Career_Seasons", "Observed"]].copy()
cox_test  = test_df[COX_FEATURES  + ["Career_Seasons", "Observed"]].copy()

cph = CoxPHFitter(penalizer=0.1)
cph.fit(cox_train, duration_col="Career_Seasons", event_col="Observed")

c_train = concordance_index(
    cox_train["Career_Seasons"],
    -cph.predict_partial_hazard(cox_train[COX_FEATURES]),
    cox_train["Observed"]
)
c_test = concordance_index(
    cox_test["Career_Seasons"],
    -cph.predict_partial_hazard(cox_test[COX_FEATURES]),
    cox_test["Observed"]
)

print(f"\n  C-index (train): {c_train:.3f}")
print(f"  C-index (test) : {c_test:.3f}  ← 0.5=random, 1.0=perfect")
print(f"  Interpretation : model correctly ranks {c_test*100:.1f}% of player pairs")

print(f"\n  Hazard Ratios (HR < 1 = lower risk of career ending = longer career):")
hr_df = np.exp(cph.params_).rename("HR").to_frame()
hr_df["p-value"] = cph.summary["p"]
hr_df["significant"] = hr_df["p-value"] < 0.05
print(hr_df.round(4).to_string())

# ── Step 7: Save models ───────────────────────────────────────────────────────

print("\n" + "=" * 60)
print("STEP 7: Saving models")
print("=" * 60)

# Random Forest bundle — everything inference/app.py needs
rf_bundle = {
    "model":        rf_model,
    "feature_cols": FEATURE_COLS,
    "imputer":      imputer,
    "medians":      MEDIANS,       # fallback when user omits optional stats
    "mae":          mae_test,
    "rmse":         rmse_test,
    "r2":           r2_test,
    "train_size":   len(train_df),
    "test_size":    len(test_df),
}
rf_path = f"{OUTPUT_DIR}/rf_model.pkl"
with open(rf_path, "wb") as f:
    pickle.dump(rf_bundle, f)
print(f"  ✓ rf_model.pkl  (MAE={mae_test:.3f}, R²={r2_test:.3f})")

# Cox model
cox_path = f"{OUTPUT_DIR}/cox_model.pkl"
with open(cox_path, "wb") as f:
    pickle.dump(cph, f)
print(f"  ✓ cox_model.pkl (C-index={c_test:.3f})")

# Shared metadata
meta = {
    "valid_leagues":  VALID_LEAGUES,
    "valid_roles":    VALID_ROLES,
    "cox_features":   COX_FEATURES,
    "feature_cols":   FEATURE_COLS,
    "n_train":        len(train_df),
    "n_test":         len(test_df),
    "seasons":        "S6-S15 (2016-2025)",
    "source":         "gol.gg + Leaguepedia",
}
meta_path = f"{OUTPUT_DIR}/metadata.pkl"
with open(meta_path, "wb") as f:
    pickle.dump(meta, f)
print(f"  ✓ metadata.pkl")

# ── Step 8: Training report ───────────────────────────────────────────────────

report_lines = [
    "=" * 60,
    "TRAINING REPORT — Esports Career Longevity Models",
    "CS 163 Group 10 — Brandon Lee & Stephani Marie Soriano",
    "=" * 60,
    f"",
    f"Dataset: {len(df_full)} players (major leagues + known role)",
    f"Seasons: S6-S15 (2016-2025)",
    f"Source:  gol.gg + Leaguepedia",
    f"",
    f"Train/Test Split",
    f"  Strategy:   stratified 80/20 by career length bucket",
    f"  Train size: {len(train_df)} players",
    f"  Test  size: {len(test_df)} players",
    f"  Random seed: {RANDOM_STATE}",
    f"",
    f"Random Forest Regressor",
    f"  n_estimators:    200",
    f"  max_depth:       8",
    f"  min_samples_leaf: 5",
    f"  Train MAE:  {mae_train:.3f} seasons",
    f"  Test  MAE:  {mae_test:.3f} seasons",
    f"  Test  RMSE: {rmse_test:.3f} seasons",
    f"  Test  R²:   {r2_test:.3f}",
    f"",
    f"  Feature importances:",
]
for feat, imp in feat_imp.items():
    report_lines.append(f"    {feat:<25} {imp:.4f}")

report_lines += [
    f"",
    f"Cox Proportional Hazards",
    f"  penalizer:      0.1",
    f"  Train C-index:  {c_train:.3f}",
    f"  Test  C-index:  {c_test:.3f}",
    f"",
    f"  Hazard Ratios:",
]
for var in COX_FEATURES:
    hr  = float(np.exp(cph.params_[var]))
    p   = float(cph.summary.loc[var, "p"])
    sig = " *" if p < 0.05 else ""
    report_lines.append(f"    {var:<25} HR={hr:.3f}  p={p:.4f}{sig}")

report_lines += [
    f"",
    f"Saved files:",
    f"  {rf_path}",
    f"  {cox_path}",
    f"  {meta_path}",
    f"",
    f"* p < 0.05",
]

report_path = f"{OUTPUT_DIR}/training_report.txt"
with open(report_path, "w") as f:
    f.write("\n".join(report_lines))
print(f"  ✓ training_report.txt")

print("\n" + "=" * 60)
print("DONE. All models saved to:", OUTPUT_DIR)
print("Next step: run inference/app.py or deploy with:")
print("  cd inference && gcloud run deploy esports-inference --source .")
print("=" * 60)
