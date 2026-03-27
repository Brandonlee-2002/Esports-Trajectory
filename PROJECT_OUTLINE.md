# Modeling Professional Player Career Trajectories in League of Legends Esports
## Semester Project Outline

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Phase 1: Foundation & Literature Review](#phase-1-foundation--literature-review)
3. [Phase 2: Data Collection & Infrastructure](#phase-2-data-collection--infrastructure)
4. [Phase 3: Data Cleaning & Preprocessing](#phase-3-data-cleaning--preprocessing)
5. [Phase 4: Exploratory Data Analysis](#phase-4-exploratory-data-analysis)
6. [Phase 5: Statistical Modeling & Analysis](#phase-5-statistical-modeling--analysis)
7. [Phase 6: Visualization & Website Development](#phase-6-visualization--website-development)
8. [Phase 7: Final Deliverables](#phase-7-final-deliverables)
9. [Technology Stack](#technology-stack)
10. [Project Directory Structure](#project-directory-structure)
11. [Risk Management](#risk-management)
12. [References & Resources](#references--resources)

---

## Project Overview

### Objectives
- Analyze career trajectories of professional League of Legends players
- Model career length, promotion rates, and attrition across regions
- Identify factors associated with career longevity
- Present findings through an interactive website

### Key Deliverables
1. **Cleaned Dataset** - Structured data on player careers
2. **Literature Review** - Summary of related research
3. **Analysis Report** - Statistical findings and models
4. **Interactive Website** - Final presentation platform
5. **Technical Documentation** - Code and methodology documentation

---

## Phase 1: Foundation & Literature Review
**Duration: Weeks 1-3**

### 1.1 Project Setup
- [ ] Initialize Git repository with proper structure
- [ ] Set up development environment (Python, R)
- [ ] Create project documentation templates
- [ ] Establish team collaboration workflow

### 1.2 Literature Search
**Areas to Research:**

#### Academic Sources
- Sports economics and player career dynamics
- Labor market analysis in professional sports
- Survival analysis in career studies
- Esports industry research papers

#### Industry Sources
- Esports industry reports (Newzoo, SuperData)
- Professional gaming organization studies
- Player union and association data

#### Recommended Databases
- Google Scholar
- IEEE Xplore
- ACM Digital Library
- SSRN (Social Science Research Network)
- ResearchGate

### 1.3 Literature Review Deliverables
- [ ] Annotated bibliography (minimum 15-20 sources)
- [ ] Literature review document (5-7 pages)
- [ ] Identification of research gaps
- [ ] Methodology inspiration from related work

### 1.4 Key Search Terms
```
- "esports career longevity"
- "professional gaming labor markets"
- "sports career trajectory analysis"
- "survival analysis professional athletes"
- "player development pipeline sports"
- "career attrition rates competitive gaming"
- "League of Legends professional scene analysis"
```

---

## Phase 2: Data Collection & Infrastructure
**Duration: Weeks 3-6**

### 2.1 Data Source Analysis

#### Primary Source: Leaguepedia (lol.fandom.com)
**Data Available:**
- Player profiles (name, nationality, role, birthdate)
- Team history (join/leave dates, team names)
- Tournament participation
- Regional league information
- Career status (active/retired/inactive)

**Collection Method:** Web scraping with BeautifulSoup/Scrapy

#### Secondary Source: Liquipedia
**Data Available:**
- Tournament results
- Team rosters over time
- Prize money (limited)
- Regional competition structure

**Collection Method:** API calls where available, scraping otherwise

### 2.2 Data Schema Design

```
PLAYERS TABLE
├── player_id (unique identifier)
├── player_name (in-game name)
├── real_name
├── nationality
├── birth_date
├── primary_role
├── career_start_date
├── career_end_date (if applicable)
├── current_status (active/retired/inactive)
└── peak_tier_reached

TEAM_HISTORY TABLE
├── history_id
├── player_id (foreign key)
├── team_name
├── team_region
├── competitive_tier (1/2/3)
├── join_date
├── leave_date
└── role_on_team

TOURNAMENTS TABLE
├── tournament_id
├── tournament_name
├── region
├── tier
├── start_date
├── end_date
└── prize_pool

PLAYER_TOURNAMENTS TABLE
├── player_id (foreign key)
├── tournament_id (foreign key)
├── team_at_time
└── placement
```

### 2.3 Web Scraping Implementation

#### Tools
- **Python:** requests, BeautifulSoup4, Scrapy
- **Data Storage:** SQLite (development), PostgreSQL (production)
- **Rate Limiting:** respectful scraping with delays

#### Scraping Tasks
- [ ] Build player list scraper (all regions)
- [ ] Build player profile scraper
- [ ] Build team history scraper
- [ ] Build tournament data scraper
- [ ] Implement error handling and logging
- [ ] Create data validation checks

### 2.4 Regional Coverage

**Tier 1 Leagues (Priority):**
| Region Code | League Name | Priority |
|-------------|-------------|----------|
| LCK | League of Legends Champions Korea | High |
| LPL | League of Legends Pro League (China) | High |
| LEC | League of Legends European Championship | High |
| LCS | League of Legends Championship Series (NA) | High |
| PCS | Pacific Championship Series | Medium |
| VCS | Vietnam Championship Series | Medium |
| CBLOL | Campeonato Brasileiro de LoL | Medium |
| LJL | League of Legends Japan League | Medium |
| LLA | Liga Latinoamérica | Medium |

**Tier 2 Leagues (Secondary):**
- LCK Challengers League
- LDL (China Development League)
- EMEA Regional Leagues
- NACL / Proving Grounds

### 2.5 Data Collection Milestones
- [ ] Week 3: Scraper prototypes working
- [ ] Week 4: Player database populated (major regions)
- [ ] Week 5: Team history data collected
- [ ] Week 6: Data validation and quality checks complete

---

## Phase 3: Data Cleaning & Preprocessing
**Duration: Weeks 6-8**

### 3.1 Data Quality Issues to Address

#### Common Problems
- Inconsistent player name formats
- Missing dates (approximate to season/year)
- Duplicate player entries
- Team name variations over time
- Unclear career status
- Regional classification changes

### 3.2 Cleaning Pipeline

```python
# Pseudocode for cleaning pipeline
def cleaning_pipeline():
    1. Load raw data
    2. Standardize column names
    3. Handle missing values
       - Impute dates where possible
       - Flag incomplete records
    4. Resolve duplicates
       - Match on multiple identifiers
       - Manual review for edge cases
    5. Standardize categorical variables
       - Region codes
       - Competitive tiers
       - Player roles
    6. Validate date ranges
       - Career start < career end
       - Team join < team leave
    7. Create derived variables
       - Career length (months/years)
       - Peak tier achieved
       - Number of teams
       - Region changes
    8. Export cleaned dataset
```

### 3.3 Derived Variables to Create

| Variable | Description | Calculation |
|----------|-------------|-------------|
| `career_length_months` | Total professional career duration | end_date - start_date |
| `career_length_years` | Career in years | months / 12 |
| `peak_tier` | Highest competitive tier reached | MAX(tier) from team_history |
| `time_to_tier1` | Time from debut to Tier 1 | First Tier 1 date - start_date |
| `num_teams` | Total teams played for | COUNT(DISTINCT team_id) |
| `num_regions` | Regions played in | COUNT(DISTINCT region) |
| `tier2_to_tier1` | Boolean: promoted from T2 | Check history sequence |
| `still_active` | Current career status | Based on last activity |

### 3.4 Data Validation Checks
- [ ] No null values in required fields
- [ ] Dates are chronologically valid
- [ ] All players have at least one team entry
- [ ] Regional codes are standardized
- [ ] Tier classifications are consistent

### 3.5 Deliverables
- [ ] Cleaned CSV/Parquet datasets
- [ ] Data dictionary document
- [ ] Cleaning methodology documentation
- [ ] Data quality report

---

## Phase 4: Exploratory Data Analysis
**Duration: Weeks 8-10**

### 4.1 Descriptive Statistics

#### Player Demographics
- Total players in dataset (by region, by era)
- Role distribution across regions
- Nationality distribution
- Age at career start

#### Career Statistics
- Mean, median, std dev of career length
- Career length distribution (histogram)
- Career length by region
- Career length by role
- Career length by starting tier

### 4.2 Key Visualizations

#### Distribution Analysis
```
- Career length histogram (overall)
- Career length boxplots by region
- Career length over time (cohort analysis)
- Role distribution pie/bar charts
```

#### Trajectory Analysis
```
- Sankey diagram: Entry tier → Exit tier
- Career path flow visualization
- Promotion rate timelines
- Regional comparison radar charts
```

#### Time Series
```
- Active player counts over time
- New player entry rates by year
- Retirement rates by year
- Regional growth trends
```

### 4.3 Exploratory Questions

1. **Career Length Distribution**
   - Is the distribution normal, skewed, or multimodal?
   - Are there distinct career length clusters?

2. **Regional Comparisons**
   - Which regions have longest average careers?
   - Which regions have highest variance?

3. **Temporal Trends**
   - Are careers getting longer or shorter over time?
   - How has the professional scene grown?

4. **Promotion Patterns**
   - What percentage of Tier 2 players reach Tier 1?
   - How long does promotion typically take?

### 4.4 Tools for EDA
- **Python:** pandas, matplotlib, seaborn, plotly
- **R:** ggplot2, dplyr, tidyr
- **Notebooks:** Jupyter for iterative analysis

---

## Phase 5: Statistical Modeling & Analysis
**Duration: Weeks 10-13**

### 5.1 Research Questions → Analytical Methods

| Research Question | Analytical Method |
|-------------------|-------------------|
| Typical career length | Descriptive stats, survival analysis |
| Tier 2 → Tier 1 transition rates | Transition probability matrices |
| Regional career differences | ANOVA, Kruskal-Wallis tests |
| Factors affecting longevity | Cox proportional hazards, regression |

### 5.2 Survival Analysis

#### Kaplan-Meier Estimation
- Estimate survival curves for career duration
- Compare curves across regions
- Compare curves across roles
- Compare curves across entry cohorts

#### Cox Proportional Hazards Model
```
Hazard(exit) ~ β1(region) + β2(role) + β3(entry_tier) + 
               β4(entry_year) + β5(time_to_tier1) + ...
```

**Potential Covariates:**
- Starting region
- Player role
- Entry tier (1 vs 2)
- Year of career start
- Age at debut
- Number of team changes

### 5.3 Regression Analysis

#### Linear Regression
- Dependent: Career length (months)
- Independents: Region, role, entry tier, cohort

#### Logistic Regression
- Dependent: Reached Tier 1 (yes/no)
- Independents: Starting tier, region, role

### 5.4 Transition Analysis

#### Markov Chain Modeling
- States: Tier 2 → Tier 1 → Retired
- Calculate transition probabilities
- Compare across regions

### 5.5 Hypothesis Testing

| Hypothesis | Test |
|------------|------|
| Career lengths differ by region | ANOVA / Kruskal-Wallis |
| Earlier Tier 1 = longer career | Correlation / regression |
| Structured developmental leagues = higher promotion | Chi-square / proportion test |
| Attrition rates differ by region | Survival curve comparison (log-rank) |

### 5.6 Model Validation
- Cross-validation for predictive models
- Residual analysis
- Sensitivity analysis
- Bootstrap confidence intervals

### 5.7 Deliverables
- [ ] Statistical analysis report
- [ ] Model specification documents
- [ ] Significance test results
- [ ] Coefficient interpretation guide

---

## Phase 6: Visualization & Website Development
**Duration: Weeks 13-15**

### 6.1 Website Architecture

```
WEBSITE STRUCTURE
├── index.html (Landing page)
├── about.html (Project background)
├── methodology.html (Data & methods)
├── findings/
│   ├── overview.html (Key findings)
│   ├── career-length.html (Duration analysis)
│   ├── regional-comparison.html (Regional analysis)
│   ├── promotion-analysis.html (Tier transitions)
│   └── factors.html (Longevity factors)
├── visualizations/
│   └── interactive.html (Interactive dashboards)
├── data/
│   └── download.html (Dataset access)
├── team.html (About the team)
└── references.html (Bibliography)
```

### 6.2 Technology Options

#### Option A: Static Site Generator
- **Framework:** Jekyll, Hugo, or Eleventy
- **Hosting:** GitHub Pages
- **Pros:** Simple, free hosting, version control
- **Cons:** Limited interactivity

#### Option B: Python-Based Dashboard
- **Framework:** Streamlit or Dash
- **Hosting:** Streamlit Cloud, Heroku, or Render
- **Pros:** Highly interactive, Python integration
- **Cons:** Requires server, more complex deployment

#### Option C: JavaScript Framework
- **Framework:** React, Vue, or vanilla JS
- **Visualization:** D3.js, Chart.js, Plotly.js
- **Hosting:** Netlify, Vercel, GitHub Pages
- **Pros:** Full control, highly customizable
- **Cons:** Steeper learning curve

### 6.3 Recommended Approach
**Hybrid: Static site + Embedded interactive visualizations**

- Use a static site generator for content pages
- Embed Plotly/D3.js for interactive charts
- Host on GitHub Pages (free, simple)
- Export Jupyter notebooks to HTML for detailed analysis

### 6.4 Key Visualizations for Website

1. **Hero Visualization:** Interactive career timeline explorer
2. **Regional Dashboard:** Compare metrics across regions
3. **Survival Curves:** Interactive Kaplan-Meier plots
4. **Sankey Diagram:** Career path flows
5. **Data Explorer:** Filterable player database

### 6.5 Design Considerations
- Mobile-responsive design
- Accessible color schemes
- Clear navigation
- Fast loading times
- Professional, academic aesthetic

### 6.6 Website Development Tasks
- [ ] Choose technology stack
- [ ] Create wireframes/mockups
- [ ] Develop page templates
- [ ] Implement navigation
- [ ] Create visualization components
- [ ] Write content for each section
- [ ] Test across browsers/devices
- [ ] Deploy and test live site

---

## Phase 7: Final Deliverables
**Duration: Weeks 15-16**

### 7.1 Technical Report

**Structure:**
1. Executive Summary
2. Introduction & Background
3. Literature Review
4. Data & Methodology
5. Results
6. Discussion
7. Conclusions & Recommendations
8. References
9. Appendices

**Format:** PDF, 20-30 pages

### 7.2 Oral Presentation

**Structure:**
1. Introduction (2 min)
2. Background & Motivation (3 min)
3. Data & Methods (5 min)
4. Key Findings (8 min)
5. Demo of Website (3 min)
6. Conclusions (2 min)
7. Q&A (5 min)

**Total:** 25-30 minutes

**Materials:**
- [ ] Slide deck (PowerPoint/Google Slides)
- [ ] Speaker notes
- [ ] Demo script for website

### 7.3 Code Repository

**Repository Structure:**
```
Esports-Trajectory/
├── README.md
├── LICENSE
├── requirements.txt
├── setup.py
├── .gitignore
├── data/
│   ├── raw/
│   ├── processed/
│   └── README.md
├── notebooks/
│   ├── 01_data_collection.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_exploratory_analysis.ipynb
│   ├── 04_statistical_modeling.ipynb
│   └── 05_visualization.ipynb
├── src/
│   ├── __init__.py
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── leaguepedia.py
│   │   └── liquipedia.py
│   ├── cleaning/
│   │   ├── __init__.py
│   │   └── pipeline.py
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── descriptive.py
│   │   └── survival.py
│   └── visualization/
│       ├── __init__.py
│       └── plots.py
├── docs/
│   ├── literature_review.md
│   ├── data_dictionary.md
│   └── methodology.md
├── website/
│   ├── index.html
│   ├── css/
│   ├── js/
│   └── assets/
├── reports/
│   └── final_report.pdf
└── presentations/
    └── final_presentation.pptx
```

### 7.4 Dataset Release
- [ ] Cleaned dataset in CSV format
- [ ] Data dictionary
- [ ] Collection methodology documentation
- [ ] Usage license (consider CC-BY)

---

## Technology Stack

### Primary Language: Python

#### Data Collection
```
requests==2.31.0
beautifulsoup4==4.12.0
scrapy==2.11.0
selenium==4.15.0  # if needed for dynamic content
```

#### Data Processing
```
pandas==2.1.0
numpy==1.26.0
sqlalchemy==2.0.0  # database interface
```

#### Analysis
```
scipy==1.11.0
statsmodels==0.14.0
lifelines==0.27.0  # survival analysis
scikit-learn==1.3.0
```

#### Visualization
```
matplotlib==3.8.0
seaborn==0.13.0
plotly==5.18.0
altair==5.1.0
```

#### Development
```
jupyter==1.0.0
black==23.11.0  # code formatting
pytest==7.4.0  # testing
```

### Secondary Language: R (Optional)

```r
# Data manipulation
tidyverse
dplyr
tidyr

# Visualization
ggplot2
plotly

# Survival analysis
survival
survminer
```

### Website Development
```
# Static site
Jekyll or Hugo

# JavaScript libraries
plotly.js
d3.js
chart.js
```

---

## Project Directory Structure

Create this structure at project start:

```bash
mkdir -p data/{raw,processed,interim}
mkdir -p notebooks
mkdir -p src/{scraper,cleaning,analysis,visualization}
mkdir -p docs
mkdir -p website/{css,js,assets,pages}
mkdir -p reports
mkdir -p presentations
mkdir -p tests
```

---

## Risk Management

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Scraping blocked | Medium | High | Respectful rate limiting, caching, backup sources |
| Data quality issues | High | Medium | Robust validation, manual spot-checks |
| Missing historical data | Medium | Medium | Document limitations, focus on available periods |
| Scope creep | Medium | High | Strict scope boundaries, MVP approach |

### Schedule Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data collection takes longer | High | High | Start early, parallelize work |
| Analysis complexity | Medium | Medium | Prioritize core questions |
| Website development delays | Medium | Medium | Use templates, simplify if needed |

### Contingency Plans

1. **If scraping fails:** Use manually curated sample dataset
2. **If analysis is inconclusive:** Focus on descriptive findings
3. **If time runs short:** Prioritize core deliverables, simplify website

---

## References & Resources

### Leaguepedia Resources
- Main site: https://lol.fandom.com/wiki/League_of_Legends_Esports_Wiki
- API documentation: https://lol.fandom.com/wiki/Help:API
- Player categories: https://lol.fandom.com/wiki/Category:Players

### Liquipedia Resources
- Main site: https://liquipedia.net/leagueoflegends/
- API: https://liquipedia.net/api/

### Python Libraries Documentation
- lifelines (survival analysis): https://lifelines.readthedocs.io/
- plotly: https://plotly.com/python/
- beautifulsoup: https://beautiful-soup-4.readthedocs.io/

### Academic References (Starting Points)
- Esports economics literature
- Sports analytics methodology papers
- Survival analysis textbooks
- Labor economics research

### Similar Projects/Inspirations
- Baseball Reference career data analysis
- NBA player trajectory studies
- Soccer player market value analysis

---

## Weekly Milestone Checklist

### Weeks 1-3: Foundation
- [ ] Repository structure created
- [ ] Development environment set up
- [ ] Literature review completed
- [ ] Data sources identified and tested

### Weeks 3-6: Data Collection
- [ ] Scraping infrastructure built
- [ ] Player data collected (major regions)
- [ ] Team history data collected
- [ ] Raw data validated

### Weeks 6-8: Data Cleaning
- [ ] Cleaning pipeline implemented
- [ ] Derived variables created
- [ ] Data quality report completed
- [ ] Clean dataset exported

### Weeks 8-10: Exploratory Analysis
- [ ] Descriptive statistics generated
- [ ] Initial visualizations created
- [ ] Exploratory findings documented
- [ ] Analysis direction confirmed

### Weeks 10-13: Statistical Modeling
- [ ] Survival analysis completed
- [ ] Regression models fit
- [ ] Hypothesis tests conducted
- [ ] Results interpreted

### Weeks 13-15: Website Development
- [ ] Website structure created
- [ ] Content written
- [ ] Visualizations embedded
- [ ] Site deployed

### Weeks 15-16: Final Deliverables
- [ ] Technical report completed
- [ ] Presentation prepared
- [ ] Code repository documented
- [ ] Final presentation delivered

---

## Getting Started: First Actions

1. **Today:** Create the directory structure
2. **This week:** Set up Python environment with requirements
3. **This week:** Begin literature search
4. **This week:** Test scraping a single player page

---

*Last updated: February 2026*
*Project Duration: 16 weeks*
