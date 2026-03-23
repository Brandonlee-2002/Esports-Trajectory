# Modeling Professional Player Career Trajectories in League of Legends Esports

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Project Overview

This project analyzes and models the career trajectories of professional League of Legends players across regions and competitive tiers. Using publicly available esports records, we study how long professional careers last, how players progress from lower-tier leagues to top-tier competition, and what factors are associated with career longevity.

## Live dashboard

**Production (Google App Engine):** [https://esport-trajectories.wl.r.appspot.com](https://esport-trajectories.wl.r.appspot.com)

For local development, see [`website/README.md`](website/README.md).

## Research Questions

1. What is the typical length of a professional League of Legends career?
2. How often do players transition from Tier 2 leagues to Tier 1?
3. How do career lengths differ across regions?
4. Are certain regions more effective at developing long-lasting professional players?

## Project Structure

```
Esports-Trajectory/
├── data/
│   ├── raw/              # Original scraped data
│   ├── interim/          # Intermediate processing
│   └── processed/        # Clean, analysis-ready data
├── notebooks/            # Jupyter notebooks for analysis
├── src/
│   ├── scraper/          # Data collection scripts
│   ├── cleaning/         # Data preprocessing
│   ├── analysis/         # Statistical analysis
│   └── visualization/    # Plotting functions
├── docs/                 # Documentation
├── website/              # Final presentation website
├── reports/              # Generated reports
├── presentations/        # Presentation materials
└── tests/                # Unit tests
```

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Esports-Trajectory.git
cd Esports-Trajectory

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Data Sources

- **Leaguepedia** (lol.fandom.com): Player profiles, career timelines, team history
- **Liquipedia**: Tournament participation, team rosters, competitive tier information

## Methodology

1. **Data Collection**: Web scraping of player career data from esports wikis
2. **Data Cleaning**: Standardization of names, dates, and categorical variables
3. **Exploratory Analysis**: Descriptive statistics and visualization
4. **Statistical Modeling**: Survival analysis, regression, and hypothesis testing
5. **Presentation**: Interactive website with findings

## Key Findings

*Coming soon...*

## Team

CS163 Senior Capstone Project

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Leaguepedia and Liquipedia communities for maintaining comprehensive esports data
- Course instructors and TAs for guidance
