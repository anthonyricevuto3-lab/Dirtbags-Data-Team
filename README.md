# Dirtbags Data Team

**Mission**: Bridge the gap between coaching ideas and technical execution by turning messy data into clean, usable tools—without adding friction to coaching.

## Core Philosophy

- **No coaching decisions** - We build tools, coaches make decisions
- **No player-facing tools** - Internal use only
- **No opinions, only structured outputs** - Data-driven, not recommendation-driven
- **Consistency > novelty** - Same format every time
- **Speed + repeatability > perfection** - Works reliably beats perfect

## Data Organization System

### Folder Hierarchy

All data must follow this canonical structure:

```
/BaseballData
  /YYYY                    # Year (e.g., 2026)
    /Opponent              # Opponent name (e.g., "UCLA", "USC")
      /Series_YYYYMMDD     # Series date (e.g., "Series_20260315")
        /Game_1            # Game number in series
          /Pitching
            /Trackman      # Trackman CSV exports
            /ForcePlates   # Force plate CSVs
            /Reports       # Generated PDF reports
          /Hitting
          /Video
```

### File Naming Convention

All files must follow this pattern:

```
YYYYMMDD_Opponent_Game#_PitcherName_DataType.csv
```

**Examples:**
- `20260315_UCLA_Game1_Smith_Trackman.csv`
- `20260315_UCLA_Game1_Smith_ForcePlates.csv`
- `20260315_UCLA_Game1_Smith_Report.pdf`

**Definition of Done**: Any staff member can find any report in <10 seconds.

## Public repository note

This repo contains **code and documentation only**. Player names, Trackman CSVs, generated PDFs, and API credentials are excluded via `.gitignore`.

For local use:
1. Copy `config/team.example.yaml` → `config/team.local.yaml` and add your roster
2. Copy `.env.example` → `.env` for API credentials (if using bullpen import)
3. Place Trackman CSVs in `Trackman CSVs/` (gitignored)

## Quick Start

### Player Development Platform (new)

Run `docker compose up --build`, then open http://localhost:5000 to import a TrackMan CSV and review a pitcher's outing. Includes PostgreSQL, React/TypeScript, import validation, duplicate protection, arsenal summaries, and pitch-location charts.

Start with the invented sample at `tests/fixtures/synthetic_outing.csv`. See [the platform guide](docs/PLAYER_DEVELOPMENT_PLATFORM.md) for setup without Docker, the input contract, tests, and current limitations. This milestone is for local use; authentication and deployment are future work.

The older web-report interface referenced in historical documentation is not included in this checkout. Existing CLI report generation remains available below.

### 💻 Command Line Interface

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Validate your folder structure**: Run `python scripts/validate_structure.py <path>`
3. **Clean Trackman data**: Use `python scripts/clean_trackman.py <input.csv> <output.csv>`
4. **Generate postgame report**: 
   - **Automatic**: Set up file watcher - `python scripts/watch_trackman.py <watch_dir> --output <output_dir>`
   - **Manual**: `python scripts/generate_report.py <trackman.csv> --pitcher "Name" --game "Game1" --opponent "UCLA"`

See [docs/QUICK_START.md](docs/QUICK_START.md) for more examples.
See [docs/TRACKMAN_REPORT_PIPELINE.md](docs/TRACKMAN_REPORT_PIPELINE.md) for the complete automated pipeline guide.
See [the platform guide](docs/PLAYER_DEVELOPMENT_PLATFORM.md) for the new application.

## Project Structure

```
.
├── BaseballData/          # Main data directory (create as needed)
├── src/
│   ├── schemas/           # Data schema definitions
│   ├── metrics/           # Shared metrics library
│   ├── parsers/           # Data parsers (Trackman, Force Plates, etc.)
│   ├── visualizations/    # Plotting functions
│   └── reports/           # Report generators
├── scripts/               # CLI tools and utilities
├── tests/                 # Unit tests
└── config/                # Configuration files
```

## Team Workflow

- **Coaches coach** - They request outputs
- **Coding team builds tools** - We deliver repeatable artifacts
- **Reports delivered timely** - Post-outing reports same night/early morning
- **Consistency and communication always** - Same format, clear communication

## Confidentiality

All team data is confidential. Nothing is posted/shared externally without approval.

## Documentation

- [Quick Start Guide](docs/QUICK_START.md) - Get started in 5 minutes
- [Setup Guide](docs/SETUP.md) - Detailed installation instructions
- [Folder Structure](docs/FOLDER_STRUCTURE.md) - Data organization standards
- [Workflow Guide](docs/WORKFLOW.md) - Daily operations and best practices
- [Definition of Done](docs/DEFINITION_OF_DONE.md) - Quality standards checklist

## What's Included

### Core Infrastructure
- ✅ Folder structure and naming validation
- ✅ Data schema definitions (Trackman, Force Plates, Scouting)
- ✅ Shared metrics library (usage, whiff, contact, movement)
- ✅ Trackman postgame PDF report generator
- ✅ File-drop automation (auto-generate reports)
- ✅ Scouting report generator
- ✅ Internal dashboards (Streamlit)

### Scripts
- `validate_structure.py` - Validate folder/file naming
- `clean_trackman.py` - Clean Trackman CSV to canonical schema
- `generate_report.py` - Generate Trackman postgame PDF
- `watch_trackman.py` - Auto-generate reports on file drop
- `generate_scouting_report.py` - Generate opponent scouting PDF

