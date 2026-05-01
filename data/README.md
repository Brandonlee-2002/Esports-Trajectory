# Data Directory

This directory contains all data for the Esports Career Trajectory project.

## Required External Data Download

The raw data file is too large for GitHub and must be downloaded separately:

**File:** `League of Legends Player Statistics by Year.xlsx`

**Download:** [Request access from project maintainers]

**Setup:**
1. Download the Excel file
2. Place it in a known location (e.g., `Downloads/` folder)
3. Run the processing script:
   ```bash
   python src/cleaning/process_excel_data.py
   ```
4. This generates `data/processed/players_processed.csv` and `data/processed/career_metrics.csv`

## Structure

```
data/
├── raw/          # Original, immutable data (external download)
├── interim/      # Intermediate data transformations
└── processed/    # Final, analysis-ready datasets
```

## Data Flow

```
[Excel File - External Download] 
        ↓ 
  process_excel_data.py
        ↓ 
 processed/*.csv
        ↓
      eda.py
        ↓
   reports/*.png (canonical) + website/js/eda_data.json
        ↓
   website/reports/figures/*.png (copied for App Engine static hosting)
```

## Files

### Raw Data (External - Not in Git)
- `League of Legends Player Statistics by Year.xlsx` - Player statistics by season (S6-S15)
  - Contains: Player, Country, Games, Win rate, KDA, and 20+ performance metrics
  - Sheets: S6 through S15 (Season 6 = 2016, Season 15 = 2025)
  - Enriched sheet with Team, League, Role, Tier info

### Processed Data
- `players_processed.csv` - Cleaned player data with role, nationality, status
- `career_metrics.csv` - Derived career statistics (length, region, tier transitions)

## Notes

- Raw data files (*.xlsx, *.csv) are excluded from Git (see `.gitignore`)
- Processed datasets are regenerated from the Excel file
- See `docs/data_dictionary.md` for field descriptions

## Data Collection Date

- Source: Leaguepedia / Oracle's Elixir
- Coverage: Seasons 6-15 (2016-2025)
- Players: ~1,570 unique professional players
- Last processed: March 2026
