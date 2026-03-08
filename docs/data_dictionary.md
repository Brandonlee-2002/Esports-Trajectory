# Data Dictionary

This document describes the structure and meaning of all data fields in the project.

---

## Raw Data Tables

### players_raw

Source: Leaguepedia Players table

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `player_id` | string | Unique identifier from Leaguepedia | "Faker" |
| `in_game_name` | string | Current in-game name | "Faker" |
| `real_name` | string | Player's real name | "Lee Sang-hyeok" |
| `country` | string | Nationality | "South Korea" |
| `role` | string | Primary competitive role | "Mid" |
| `current_team` | string | Current team (if active) | "T1" |
| `is_retired` | boolean | Retirement status | False |

### tenures_raw

Source: Leaguepedia Tenures table

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `player_id` | string | Reference to player | "Faker" |
| `team_name` | string | Team played for | "T1" |
| `team_region` | string | Team's primary region | "Korea" |
| `date_join` | date | Date joined team | 2013-02-01 |
| `date_leave` | date | Date left team (null if current) | null |
| `role` | string | Role on team | "Mid" |
| `role_modifier` | string | Additional role info | "Starter" |

### tournaments_raw

Source: Leaguepedia Tournaments table

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `tournament_id` | string | Tournament identifier | "LCK/2024 Season/Spring Season" |
| `name` | string | Tournament name | "LCK Spring 2024" |
| `region` | string | Primary region | "Korea" |
| `league` | string | Associated league | "LCK" |
| `date_start` | date | Start date | 2024-01-17 |
| `date_end` | date | End date | 2024-03-31 |
| `prizepool` | float | Prize pool (if available) | 300000.00 |

---

## Processed Data Tables

### players_processed

Cleaned and enriched player data

| Field | Type | Description | Derivation |
|-------|------|-------------|------------|
| `player_id` | string | Unique identifier | From raw |
| `in_game_name` | string | Standardized IGN | Cleaned |
| `real_name` | string | Real name | From raw |
| `nationality` | string | ISO country code | Standardized |
| `primary_role` | string | Main role | Standardized to: Top, Jungle, Mid, ADC, Support |
| `birth_date` | date | Date of birth | From raw (where available) |
| `career_start_date` | date | First professional appearance | MIN(date_join) from tenures |
| `career_end_date` | date | Last professional appearance | MAX(date_leave) or current date if active |
| `current_status` | string | Active/Retired/Inactive | Derived |
| `peak_tier` | int | Highest tier reached | 1, 2, or 3 |

### career_metrics

Derived career statistics per player

| Field | Type | Description | Derivation |
|-------|------|-------------|------------|
| `player_id` | string | Reference to player | FK |
| `career_length_months` | int | Total career duration | (end_date - start_date) in months |
| `career_length_years` | float | Career in years | months / 12 |
| `time_to_tier1_months` | int | Time to reach Tier 1 | First Tier 1 date - start_date |
| `num_teams` | int | Teams played for | COUNT(DISTINCT team) |
| `num_regions` | int | Regions played in | COUNT(DISTINCT region) |
| `promoted_tier2_to_tier1` | boolean | Made the jump | Check tenure history |
| `primary_region` | string | Region with most time | MODE(region) weighted by time |

---

## Categorical Variable Standards

### Roles
- `Top` - Top lane
- `Jungle` - Jungle position
- `Mid` - Mid lane
- `ADC` - Bot lane carry (also called Bot, Marksman)
- `Support` - Support position

### Regions (Tier 1)
| Code | Full Name | Country/Area |
|------|-----------|--------------|
| LCK | LoL Champions Korea | South Korea |
| LPL | LoL Pro League | China |
| LEC | LoL European Championship | Europe |
| LCS | LoL Championship Series | North America |
| PCS | Pacific Championship Series | Taiwan/SE Asia |
| VCS | Vietnam Championship Series | Vietnam |
| CBLOL | Campeonato Brasileiro | Brazil |
| LJL | LoL Japan League | Japan |
| LLA | Liga Latinoamérica | Latin America |

### Competitive Tiers
- **Tier 1**: Top regional league (LCK, LPL, LEC, LCS, etc.)
- **Tier 2**: Development leagues (LCK CL, LDL, EMEA Masters, etc.)
- **Tier 3**: Amateur/semi-pro leagues

### Career Status
- `Active`: Played within last 6 months
- `Inactive`: No activity 6-18 months
- `Retired`: Announced retirement OR no activity >18 months

---

## Data Quality Notes

### Known Issues
1. Historical data before 2013 may be incomplete
2. Some Asian region data has inconsistent date formats
3. Name variations exist (e.g., "Sneaky" vs "C9 Sneaky")
4. Team name changes over time need mapping

### Handling Missing Data
- Missing birth dates: Excluded from age-related analysis
- Missing leave dates (current players): Use current date
- Missing role info: Impute from most common role in tenures

---

*Last Updated: February 2026*
