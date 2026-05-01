# Modeling Professional Player Career Trajectories in League of Legends Esports

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## About This Repository

This repository contains the full CS163 capstone pipeline for analyzing and modeling professional League of Legends career trajectories. It includes:

- data collection and cleaning code,
- hypothesis-specific analysis scripts,
- a deployed website on Google App Engine,
- and a Cloud Run Docker inference service used by the website.

## Live Demo

- Website (App Engine): [https://esport-trajectories.wl.r.appspot.com](https://esport-trajectories.wl.r.appspot.com)
- Local website deployment guide: [`website/README.md`](website/README.md)

## Table of Contents

- [Project Objectives](#project-objectives)
- [Research Questions](#research-questions)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Pipeline Walkthrough](#pipeline-walkthrough)
- [System Design and Scalability](#system-design-and-scalability)
- [Inference Service (Cloud Run)](#inference-service-cloud-run)
- [Cloud Data Storage](#cloud-data-storage)
- [Major Findings (Current)](#major-findings-current)
- [Team and License](#team-and-license)

## Project Objectives

1. Quantify the typical length of professional LoL careers.
2. Measure how often Tier 2 players transition to Tier 1.
3. Compare career longevity patterns across regions.
4. Provide interactive and model-backed insights through a live website.

## Research Questions

1. What is the typical length of a professional League of Legends career?
2. How often do players transition from Tier 2 leagues to Tier 1?
3. How do career lengths differ across regions?
4. Which structural factors are associated with longer careers?

## Repository Structure

```text
Esports-Trajectory/
├── data/                  # Raw, interim, and processed datasets
├── docs/                  # Supporting documentation
├── inference/             # Cloud Run inference service (Docker + Flask API + models)
├── notebooks/             # Exploratory notebooks
├── reports/               # Generated figures and analysis outputs
├── scrapers/              # Scraping / roster panel collection code
├── src/                   # Core processing and analysis scripts
├── tests/                 # Fixtures and tests
├── website/               # App Engine website (HTML/CSS/JS + lightweight backend)
├── run_etl.py             # ETL runner entry point
└── requirements.txt       # Root Python dependencies
```

### Key Directory Purpose (Top-Level)

- `data/`: source and derived datasets used across analyses.
- `src/analysis/`: EDA, hypothesis analysis, and figure generation scripts.
- `scrapers/`: data pull scripts (Leaguepedia/Cargo and related sources).
- `inference/`: trained model artifacts and prediction API for website integration.
- `website/`: user-facing dashboard, pages, and App Engine configuration.

## Getting Started

### Prerequisites

- Python 3.10+
- `pip`
- (Optional, for deployment) Google Cloud SDK (`gcloud`)

### Installation

```bash
git clone https://github.com/Brandonlee-2002/Esports-Trajectory.git
cd Esports-Trajectory
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Run Website Locally

```bash
cd website
python -m http.server 8000
```

Then open `http://localhost:8000`.

## Pipeline Walkthrough

The project flow from data collection to deployment:

1. **Collect data**
   - Player and roster/tournament records are gathered via scripts in `scrapers/`.
2. **Clean and transform**
   - Normalize identities, leagues, roles, and season ranges into processed tables.
3. **Analyze**
   - Run EDA and hypothesis scripts in `src/analysis/` to generate statistics and figures.
4. **Train/serve models**
   - Build model artifacts used by the inference API in `inference/`.
5. **Publish**
   - Website is deployed on App Engine and consumes both static assets and live APIs.

## System Design and Scalability

### High-Level Architecture

1. **Frontend website** (`website/`) is deployed to **Google App Engine**.
2. Website calls:
   - **Cloud Run inference API** (`inference/app.py`) for model predictions.
   - **App Engine API endpoint** (`/api/featured-finding`) for Firestore-backed featured insight.
3. App Engine endpoint reads from **Firestore** for dynamic dashboard content.

### Scalability Notes

- **App Engine**:
  - `automatic_scaling` is enabled (`website/app.yaml`) with `max_instances` configured.
  - Static assets are served with caching (short TTL for frequently updated figures).
- **Cloud Run inference**:
  - Containerized deployment with Gunicorn workers/threads for concurrent requests.
  - Stateless API design allows horizontal scaling.
- **Firestore-backed feature**:
  - Read-light dashboard payload (single document fetch) is cheap and scalable.
  - Endpoint returns cached/fallback response to avoid page failure when unavailable.

## Inference Service (Cloud Run)

Inference service code is located in:

- Docker config: `inference/Dockerfile`
- API server: `inference/app.py`
- Model artifacts: `inference/models/`

### Purpose

Provide real-time estimates of expected career length and survival probabilities for a player profile.

### Main Endpoints

- `GET /health` - health check
- `GET /info` - model metadata and supported inputs
- `POST /predict` - single-player career prediction
- `POST /predict/batch` - batch predictions
- `POST /survival` - survival curve by season

### Input/Output (example)

- **Input**: `league`, `role`, `debut`
- **Output**: `predicted_seasons`, `survival_probs`, `survival_50pct`, `confidence`, `interpretation`

## Cloud Data Storage

At least part of dashboard content is stored in **Google Firestore**:

- Collection/document (default): `dashboard/major_findings`
- Read by App Engine endpoint: `GET /api/featured-finding` in `website/main.py`
- Rendered on website page: `website/pages/findings.html` under "Cloud Database Featured Insight"

This feature includes a fallback payload when Firestore is not configured, so the page stays functional.

## Major Findings (Current)

- Career lengths are right-skewed: most careers are short, with a small long-career tail.
- Tier 2 to Tier 1 promotion is limited in the current panel and often time-sensitive.
- Regional career outcomes differ significantly, with LCK leading in observed longevity.
- A non-trivial predictive stack (Cox + Negative Binomial) is deployed and used live by the site.

## Team and License

- **Team**: CS163 Senior Capstone Project
- **License**: MIT ([`LICENSE`](LICENSE))

## Acknowledgments

- Leaguepedia and Liquipedia communities for open esports records
- Games of Legends for player-season performance data
- CS163 course staff for project guidance
