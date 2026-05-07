"""
train_test.py — Train/Test Split & Model Evaluation
CS 163 Group 10 - Brandon Lee & Stephani Marie Soriano

Builds a labeled dataset, splits into train/test sets, trains three models,
and evaluates them on held-out data.

Models:
  1. Negative Binomial Regression (career length prediction)
  2. Random Forest Regressor       (career length prediction)
  3. Cox Proportional Hazards      (survival analysis — evaluated by C-index)

Target variable: Career_Seasons (how many seasons a player competed)

Features:
  - League (LCK / LPL / LEC / LCS)
  - Role (Top / Jungle / Mid / Bot / Support)
  - Tier (S / A)
  - Debut season
  - Early_Era flag (debuted S6-S9 vs S10-S15)
  - Avg_KDA, Avg_GPM, Avg_CSM, Avg_DPM, Avg_WR, Avg_KP
  - Total_Games

Usage:
    python train_test.py

Outputs:
    train_set.csv
    test_set.csv
    model_evaluation.txt
    train_test_results.png
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (mean_absolute_error, mean_squared_error,
                              r2_score)
from sklearn.impute import SimpleImputer
from lifelines import CoxPHFitter
from lifelines.utils import concordance_index
import statsmodels.api as sm

DATA_DIR   = os.environ.get('DATA_DIR',   '.')
OUTPUT_DIR = os.environ.get('OUTPUT_DIR', '.')
os.makedirs(OUTPUT_DIR, exist_ok=True)

RANDOM_STATE = 42
TEST_SIZE    = 0.2   # 80/20 split
MAX_SEASON   = 15

GOLD  = '#d4a74a'
BLUE  = '#5b8bd4'
MUTED = '#94a3b8'
RED   = '#e05c5c'
GREEN = '#4caf7d'
DARK  = '#2c3e50'

# ── Load & build dataset ──────────────────────────────────────────────────────

print("Loading CSVs...")
dfs = {}
for s in range(6, 16):
    path = f'{DATA_DIR}/player_careers_S{s}.csv'
    try:
        dfs[s] = pd.read_csv(path)
    except FileNotFoundError:
        print(f"  WARNING: {path} not found")

player_seasons = {}
player_league  = {}
player_role    = {}
player_tier    = {}
player_stats   = {}

for s, df in dfs.items():
    for _, row in df.iterrows():
        p = row['Player']
        player_seasons.setdefault(p, []).append(s)
        for col, store in [('League', player_league), ('Role', player_role),
                           ('Tier', player_tier)]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() and p not in store:
                store[p] = str(val).strip()
        player_stats.setdefault(p, []).append({
            'kda':     pd.to_numeric(row.get('KDA'), errors='coerce'),
            'gpm':     pd.to_numeric(row.get('GPM'), errors='coerce'),
            'csm':     pd.to_numeric(row.get('CSM'), errors='coerce'),
            'dpm':     pd.to_numeric(row.get('DPM'), errors='coerce'),
            'winrate': pd.to_numeric(str(row.get('Win rate','')).replace('%',''), errors='coerce'),
            'games':   pd.to_numeric(row.get('Games'), errors='coerce'),
            'kp':      pd.to_numeric(str(row.get('KP%','')).replace('%',''), errors='coerce'),
        })

def safe_mean(vals):
    c = [x for x in vals if pd.notna(x)]
    return round(np.mean(c), 3) if c else np.nan

records = []
for p, seasons in player_seasons.items():
    career_len = len(set(seasons))
    league = player_league.get(p)
    role_raw = str(player_role.get(p, ''))
    role = role_raw.split(',')[0].strip()
    tier = player_tier.get(p, 'S')
    debut = min(seasons)
    last_s = max(seasons)

    if league not in ['LCK','LPL','LEC','LCS']:    continue
    if role not in ['Top','Jungle','Mid','Bot','Support']: continue

    stats = player_stats.get(p, [])
    records.append({
        'Player':       p,
        'Career_Seasons': career_len,
        'Observed':     int(last_s != MAX_SEASON),  # 1=ended, 0=censored
        'League':       league,
        'Role':         role,
        'Tier':         tier if tier in ['S','A'] else 'S',
        'Debut':        debut,
        'Early_Era':    int(debut <= 9),
        'Avg_KDA':      safe_mean([s['kda']     for s in stats]),
        'Avg_GPM':      safe_mean([s['gpm']     for s in stats]),
        'Avg_CSM':      safe_mean([s['csm']     for s in stats]),
        'Avg_DPM':      safe_mean([s['dpm']     for s in stats]),
        'Avg_WR':       safe_mean([s['winrate'] for s in stats]),
        'Avg_KP':       safe_mean([s['kp']      for s in stats]),
        'Total_Games':  int(sum(s['games'] for s in stats
                               if pd.notna(s['games']))),
    })

df_full = pd.DataFrame(records)
print(f"Full dataset: {len(df_full)} players")

# ── Impute missing values ─────────────────────────────────────────────────────

NUMERIC_FEATS = ['Avg_KDA','Avg_GPM','Avg_CSM','Avg_DPM','Avg_WR','Avg_KP','Total_Games']
imputer = SimpleImputer(strategy='median')
df_full[NUMERIC_FEATS] = imputer.fit_transform(df_full[NUMERIC_FEATS])

# ── Encode categoricals ───────────────────────────────────────────────────────

# One-hot encode League and Role (LCS / Top as reference)
df_enc = pd.get_dummies(df_full, columns=['League','Role','Tier'], drop_first=False)

# Convert bool columns to int (pd.get_dummies returns bool in newer pandas)
bool_cols = df_enc.select_dtypes(include='bool').columns
df_enc[bool_cols] = df_enc[bool_cols].astype(int)

# Drop reference categories manually for regression models
for drop_col in ['League_LCS', 'Role_Top', 'Tier_S']:
    if drop_col in df_enc.columns:
        df_enc = df_enc.drop(columns=[drop_col])

FEATURE_COLS = [c for c in df_enc.columns if c not in
                ['Player','Career_Seasons','Observed']]

# ── Train / test split ────────────────────────────────────────────────────────

# Stratify by career length bucket so both sets have similar distributions
df_enc['_bucket'] = pd.cut(df_enc['Career_Seasons'],
                            bins=[0,1,2,3,5,100],
                            labels=['1','2','3','4-5','6+'])

train_df, test_df = train_test_split(
    df_enc, test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=df_enc['_bucket']
)
train_df = train_df.drop(columns=['_bucket'])
test_df  = test_df.drop(columns=['_bucket'])

print(f"\nSplit: {len(train_df)} train / {len(test_df)} test")
print(f"Train career mean: {train_df['Career_Seasons'].mean():.2f}")
print(f"Test  career mean: {test_df['Career_Seasons'].mean():.2f}")

# Save train/test sets
train_df.to_csv(f'{OUTPUT_DIR}/train_set.csv', index=False)
test_df.to_csv(f'{OUTPUT_DIR}/test_set.csv',  index=False)
print(f"Saved: train_set.csv, test_set.csv")

# ── Helper ────────────────────────────────────────────────────────────────────

def evaluate(name, y_true, y_pred, lines):
    mae  = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2   = r2_score(y_true, y_pred)
    lines.append(f"\n{'─'*50}")
    lines.append(f"Model: {name}")
    lines.append(f"  MAE  (mean absolute error):  {mae:.3f} seasons")
    lines.append(f"  RMSE (root mean sq error):   {rmse:.3f} seasons")
    lines.append(f"  R²   (variance explained):   {r2:.3f}")
    lines.append(f"  Interpretation: predictions off by ~{mae:.1f} seasons on average")
    return mae, rmse, r2

output_lines = [
    "=" * 60,
    "TRAIN/TEST EVALUATION RESULTS",
    "CS 163 Group 10 — Esports Career Trajectory",
    "=" * 60,
    f"\nDataset: {len(df_full)} players (major leagues, known role)",
    f"Train:   {len(train_df)} players (80%)",
    f"Test:    {len(test_df)} players (20%)",
    f"Split strategy: stratified by career length bucket",
    f"Random seed: {RANDOM_STATE}",
]

X_train = train_df[FEATURE_COLS]
y_train = train_df['Career_Seasons']
X_test  = test_df[FEATURE_COLS]
y_test  = test_df['Career_Seasons']

results = {}

# ── Model 1: Negative Binomial Regression ────────────────────────────────────

print("\nTraining Negative Binomial Regression...")
X_train_nb = sm.add_constant(X_train)
X_test_nb  = sm.add_constant(X_test)

nb_model = sm.NegativeBinomial(y_train, X_train_nb).fit(disp=False)
nb_pred_train = nb_model.predict(X_train_nb)
nb_pred_test  = nb_model.predict(X_test_nb)

mae_nb, rmse_nb, r2_nb = evaluate('Negative Binomial Regression', y_test, nb_pred_test, output_lines)
results['Negative Binomial'] = {'pred': nb_pred_test, 'mae': mae_nb, 'rmse': rmse_nb, 'r2': r2_nb}

cv_nb_pred = nb_model.predict(X_train_nb)
output_lines.append(f"  Train MAE: {mean_absolute_error(y_train, cv_nb_pred):.3f}")

# ── Model 2: Random Forest Regressor ─────────────────────────────────────────

print("Training Random Forest Regressor...")
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

mae_rf, rmse_rf, r2_rf = evaluate('Random Forest Regressor', y_test, rf_pred_test, output_lines)
results['Random Forest'] = {'pred': rf_pred_test, 'mae': mae_rf, 'rmse': rmse_rf, 'r2': r2_rf}
output_lines.append(f"  Train MAE: {mean_absolute_error(y_train, rf_pred_train):.3f}")

# Feature importances
feat_imp = pd.Series(rf_model.feature_importances_, index=FEATURE_COLS)
feat_imp = feat_imp.sort_values(ascending=False).head(10)
output_lines.append(f"\n  Top 10 feature importances (Random Forest):")
for feat, imp in feat_imp.items():
    output_lines.append(f"    {feat:<25} {imp:.4f}")

# ── Model 3: Cox Proportional Hazards ─────────────────────────────────────────

print("Training Cox Proportional Hazards...")

# Cox needs Duration + Observed columns
cox_cols = [c for c in FEATURE_COLS if c in
            ['League_LCK','League_LPL','League_LEC',
             'Role_Jungle','Role_Mid','Role_Bot','Role_Support',
             'Tier_A','Early_Era','Avg_KDA','Avg_CSM','Avg_WR']]

cox_train = train_df[cox_cols + ['Career_Seasons','Observed']].copy()
cox_test  = test_df[cox_cols  + ['Career_Seasons','Observed']].copy()

cph = CoxPHFitter(penalizer=0.1)
cph.fit(cox_train, duration_col='Career_Seasons', event_col='Observed')

# C-index (concordance index) — main metric for survival models
c_index_train = concordance_index(
    cox_train['Career_Seasons'],
    -cph.predict_partial_hazard(cox_train[cox_cols]),
    cox_train['Observed']
)
c_index_test = concordance_index(
    cox_test['Career_Seasons'],
    -cph.predict_partial_hazard(cox_test[cox_cols]),
    cox_test['Observed']
)

output_lines.append(f"\n{'─'*50}")
output_lines.append(f"Model: Cox Proportional Hazards")
output_lines.append(f"  C-index (train): {c_index_train:.3f}")
output_lines.append(f"  C-index (test):  {c_index_test:.3f}")
output_lines.append(f"  Interpretation: C-index of {c_index_test:.3f} means the model correctly")
output_lines.append(f"  ranks {c_index_test*100:.1f}% of player pairs by career length.")
output_lines.append(f"  (0.5 = random, 1.0 = perfect, >0.6 = useful)")

# Cox hazard ratios
output_lines.append(f"\n  Hazard Ratios (exp(coef)), test set:")
cox_summary = cph.summary[['exp(coef)', 'exp(coef) lower 95%',
                             'exp(coef) upper 95%', 'p']].round(4)
output_lines.append(cox_summary.to_string())

# ── Summary comparison ────────────────────────────────────────────────────────

output_lines.append(f"\n{'='*60}")
output_lines.append("MODEL COMPARISON SUMMARY")
output_lines.append(f"{'='*60}")
output_lines.append(f"\n{'Model':<28} {'MAE':>8} {'RMSE':>8} {'R²':>8}")
output_lines.append(f"{'─'*54}")
output_lines.append(f"{'Negative Binomial Regression':<28} {mae_nb:>8.3f} {rmse_nb:>8.3f} {r2_nb:>8.3f}")
output_lines.append(f"{'Random Forest Regressor':<28} {mae_rf:>8.3f} {rmse_rf:>8.3f} {r2_rf:>8.3f}")
output_lines.append(f"{'Cox PH (C-index)':<28} {'—':>8} {'—':>8} {c_index_test:>8.3f}")
output_lines.append(f"\nBest MAE:  {'NB' if mae_nb < mae_rf else 'RF'}")
output_lines.append(f"Best RMSE: {'NB' if rmse_nb < rmse_rf else 'RF'}")
output_lines.append(f"Best R²:   {'NB' if r2_nb > r2_rf else 'RF'}")

# Save results text
txt_path = f'{OUTPUT_DIR}/model_evaluation.txt'
with open(txt_path, 'w') as f:
    f.write('\n'.join(output_lines))
print(f"Saved: model_evaluation.txt")
for line in output_lines:
    print(line)

# ── Plots ─────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(2, 2, figsize=(12, 9))
fig.suptitle('Train/Test Model Evaluation', fontsize=14, fontweight='bold', color=DARK)

# 1. Actual vs Predicted — NB
ax = axes[0, 0]
ax.scatter(y_test, nb_pred_test, alpha=0.5, color=BLUE, edgecolors='white',
           linewidth=0.3, s=40)
lim = max(y_test.max(), nb_pred_test.max()) + 0.5
ax.plot([0, lim], [0, lim], color=GOLD, linestyle='--', linewidth=1.5)
ax.set_xlabel('Actual Career Seasons', fontsize=10)
ax.set_ylabel('Predicted Career Seasons', fontsize=10)
ax.set_title(f'NB Regression\nMAE={mae_nb:.2f}, R²={r2_nb:.3f}', fontsize=11, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# 2. Actual vs Predicted — RF
ax = axes[0, 1]
ax.scatter(y_test, rf_pred_test, alpha=0.5, color=GOLD, edgecolors='white',
           linewidth=0.3, s=40)
ax.plot([0, lim], [0, lim], color=BLUE, linestyle='--', linewidth=1.5)
ax.set_xlabel('Actual Career Seasons', fontsize=10)
ax.set_ylabel('Predicted Career Seasons', fontsize=10)
ax.set_title(f'Random Forest\nMAE={mae_rf:.2f}, R²={r2_rf:.3f}', fontsize=11, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# 3. Residuals — both models
ax = axes[1, 0]
nb_resid = y_test - nb_pred_test
rf_resid = y_test - rf_pred_test
ax.hist(nb_resid, bins=20, alpha=0.6, color=BLUE,  label=f'NB (MAE={mae_nb:.2f})')
ax.hist(rf_resid, bins=20, alpha=0.6, color=GOLD, label=f'RF (MAE={mae_rf:.2f})')
ax.axvline(0, color=DARK, linestyle='--', linewidth=1)
ax.set_xlabel('Residual (Actual − Predicted)', fontsize=10)
ax.set_ylabel('Count', fontsize=10)
ax.set_title('Residual Distribution', fontsize=11, fontweight='bold')
ax.legend(fontsize=9)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# 4. Feature importance — RF
ax = axes[1, 1]
top_feats = feat_imp.head(8)
bars = ax.barh(range(len(top_feats)), top_feats.values[::-1],
               color=BLUE, edgecolor='white')
ax.set_yticks(range(len(top_feats)))
ax.set_yticklabels(top_feats.index[::-1], fontsize=9)
ax.set_xlabel('Feature Importance', fontsize=10)
ax.set_title('Top Features (Random Forest)', fontsize=11, fontweight='bold')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/train_test_results.png', dpi=150, bbox_inches='tight')
plt.close()
print(f"Saved: train_test_results.png")

print(f"\n✓ All outputs saved to: {OUTPUT_DIR}")
print(f"  train_set.csv         — {len(train_df)} players")
print(f"  test_set.csv          — {len(test_df)} players")
print(f"  model_evaluation.txt  — full metrics")
print(f"  train_test_results.png — evaluation plots")
