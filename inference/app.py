"""
app.py — Career Longevity Inference Service
CS 163 Group 10 - Brandon Lee & Stephani Marie Soriano

A Flask REST API serving career length predictions for LoL esports players.
Runs as a Docker container on Google Cloud Run.

Endpoints:
    GET  /health           — health check
    GET  /info             — model metadata
    POST /predict          — predict career length for one player
    POST /predict/batch    — predict for multiple players
    POST /survival         — return full survival curve (probability per season)

Input (POST /predict):
    {
        "league":    "LCK",          # LCK | LPL | LEC | LCS
        "role":      "Mid",          # Top | Jungle | Mid | Bot | Support
        "debut":     7,              # season number (6-15)
        "kda":       4.2             # optional, for context only
    }

Output:
    {
        "predicted_seasons":  3.4,
        "survival_50pct":     3,
        "survival_probs":     {"1": 0.82, "2": 0.65, ...},
        "confidence":         "medium",
        "interpretation":     "..."
    }
"""

import os
import pickle
import numpy as np
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS

# ── Load models ───────────────────────────────────────────────────────────────

MODEL_DIR = os.environ.get('MODEL_DIR', '/app/models')

def load_models():
    with open(f'{MODEL_DIR}/cox_model.pkl', 'rb') as f:
        cox = pickle.load(f)
    with open(f'{MODEL_DIR}/nb_model.pkl', 'rb') as f:
        nb = pickle.load(f)
    with open(f'{MODEL_DIR}/metadata.pkl', 'rb') as f:
        meta = pickle.load(f)
    return cox, nb, meta

try:
    cox_model, nb_model, metadata = load_models()
    models_loaded = True
    print("Models loaded successfully")
except Exception as e:
    models_loaded = False
    print(f"WARNING: Could not load models: {e}")

# ── App ───────────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)  # allow requests from the website

VALID_LEAGUES = ['LCK', 'LPL', 'LEC', 'LCS']
VALID_ROLES   = ['Top', 'Jungle', 'Mid', 'Bot', 'Support']

# ── Helpers ───────────────────────────────────────────────────────────────────

def encode_input(league, role, debut):
    """Convert league/role/debut into model feature vector."""
    early_era = int(debut <= 9)
    return {
        # Cox features
        'cox': pd.DataFrame([{
            'LCK':       int(league == 'LCK'),
            'LPL':       int(league == 'LPL'),
            'LEC':       int(league == 'LEC'),
            'Jungle':    int(role == 'Jungle'),
            'Mid':       int(role == 'Mid'),
            'Bot':       int(role == 'Bot'),
            'Support':   int(role == 'Support'),
            'Early_Era': early_era,
        }]),
        # NB features (with const)
        'nb': pd.DataFrame([{
            'const':         1.0,
            'League_LCK':    int(league == 'LCK'),
            'League_LPL':    int(league == 'LPL'),
            'League_LEC':    int(league == 'LEC'),
            'Role_Jungle':   int(role == 'Jungle'),
            'Role_Mid':      int(role == 'Mid'),
            'Role_Bot':      int(role == 'Bot'),
            'Role_Support':  int(role == 'Support'),
            'Early_Era':     early_era,
        }]),
    }

def survival_to_median(sv_series):
    """Find the season at which survival probability first drops below 0.5."""
    for t, p in sv_series.items():
        if p <= 0.5:
            return int(t)
    return int(sv_series.index[-1])

def confidence_label(league, role):
    """Rough confidence based on sample size."""
    counts = {'LCK': 200, 'LEC': 190, 'LPL': 330, 'LCS': 83}
    n = counts.get(league, 50)
    if n >= 150: return 'high'
    if n >= 80:  return 'medium'
    return 'low'

def interpret(predicted, league, role, debut):
    era   = "early era" if debut <= 9 else "recent era"
    lines = []
    if predicted >= 4.0:
        lines.append(f"This player profile has above-average career longevity expectations.")
    elif predicted >= 2.5:
        lines.append(f"This player profile has an average career length expectation.")
    else:
        lines.append(f"This player profile has a below-average career length expectation.")
    lines.append(f"Players in {league} average "
                 f"{'longer' if league == 'LCK' else 'shorter'} careers than most leagues.")
    lines.append(f"Debuting in {era} {'increases' if debut <= 9 else 'slightly reduces'} "
                 f"expected career length due to more seasons available.")
    return " ".join(lines)

def validate(data):
    errors = []
    league = data.get('league', '').upper()
    role   = data.get('role', '').capitalize()
    debut  = data.get('debut')
    if league not in VALID_LEAGUES:
        errors.append(f"'league' must be one of {VALID_LEAGUES}")
    if role not in VALID_ROLES:
        errors.append(f"'role' must be one of {VALID_ROLES}")
    if debut is None:
        errors.append("'debut' (season number 6-15) is required")
    elif not isinstance(debut, int) or not (6 <= debut <= 15):
        errors.append("'debut' must be an integer between 6 and 15")
    return errors, league, role, debut

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status':        'ok',
        'models_loaded': models_loaded,
        'service':       'esports-career-inference',
        'version':       '1.0.0',
    })

@app.route('/info', methods=['GET'])
def info():
    return jsonify({
        'service':      'LoL Esports Career Longevity Predictor',
        'description':  'Predicts professional player career length using survival analysis',
        'models': {
            'cox':  'Cox Proportional Hazards — survival probability per season',
            'nb':   'Negative Binomial Regression — expected career length (seasons)',
        },
        'training': {
            'n_players':  metadata.get('n_train', 'unknown'),
            'seasons':    'S6–S15 (2016–2025)',
            'source':     'gol.gg + Leaguepedia',
        },
        'inputs': {
            'league': VALID_LEAGUES,
            'role':   VALID_ROLES,
            'debut':  'integer 6–15 (season number)',
        },
        'endpoints': {
            'GET  /health':          'Health check',
            'GET  /info':            'Model metadata',
            'POST /predict':         'Single prediction',
            'POST /predict/batch':   'Batch predictions',
            'POST /survival':        'Full survival curve',
        },
    })

@app.route('/predict', methods=['POST'])
def predict():
    if not models_loaded:
        return jsonify({'error': 'Models not loaded'}), 503

    data   = request.get_json(force=True)
    errors, league, role, debut = validate(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        features = encode_input(league, role, debut)

        # NB prediction — expected career length
        nb_pred = float(nb_model.predict(features['nb']).values[0])

        # Cox prediction — survival probabilities
        sv = cox_model.predict_survival_function(features['cox'])
        sv_dict = {int(t): round(float(sv.loc[t].values[0]), 3)
                   for t in sv.index if 1 <= t <= 10}
        median_sv = survival_to_median(
            {t: sv.loc[t].values[0] for t in sv.index})

        return jsonify({
            'input': {'league': league, 'role': role, 'debut': debut},
            'predicted_seasons': round(nb_pred, 2),
            'survival_50pct':    median_sv,
            'survival_probs':    sv_dict,
            'confidence':        confidence_label(league, role),
            'interpretation':    interpret(nb_pred, league, role, debut),
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/predict/batch', methods=['POST'])
def predict_batch():
    if not models_loaded:
        return jsonify({'error': 'Models not loaded'}), 503

    data    = request.get_json(force=True)
    players = data if isinstance(data, list) else data.get('players', [])
    if not players:
        return jsonify({'error': 'Provide a list of player objects'}), 400
    if len(players) > 50:
        return jsonify({'error': 'Batch limit is 50 players'}), 400

    results = []
    for p in players:
        errors, league, role, debut = validate(p)
        if errors:
            results.append({'input': p, 'errors': errors})
            continue
        try:
            features = encode_input(league, role, debut)
            nb_pred  = float(nb_model.predict(features['nb']).values[0])
            sv = cox_model.predict_survival_function(features['cox'])
            median_sv = survival_to_median(
                {t: sv.loc[t].values[0] for t in sv.index})
            results.append({
                'input':             {'league': league, 'role': role, 'debut': debut},
                'name':              p.get('name', ''),
                'predicted_seasons': round(nb_pred, 2),
                'survival_50pct':    median_sv,
                'confidence':        confidence_label(league, role),
            })
        except Exception as e:
            results.append({'input': p, 'error': str(e)})

    return jsonify({'results': results, 'count': len(results)})

@app.route('/survival', methods=['POST'])
def survival():
    """Return full survival curve data for charting on the website."""
    if not models_loaded:
        return jsonify({'error': 'Models not loaded'}), 503

    data   = request.get_json(force=True)
    errors, league, role, debut = validate(data)
    if errors:
        return jsonify({'errors': errors}), 400

    try:
        features = encode_input(league, role, debut)
        sv = cox_model.predict_survival_function(features['cox'])

        curve = [{'season': int(t), 'probability': round(float(sv.loc[t].values[0]), 4)}
                 for t in sv.index if 1 <= t <= 10]

        return jsonify({
            'input':          {'league': league, 'role': role, 'debut': debut},
            'survival_curve': curve,
            'median_season':  survival_to_median(
                {t: sv.loc[t].values[0] for t in sv.index}),
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)