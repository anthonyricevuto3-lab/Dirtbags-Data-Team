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

### 🌐 Web Interface (Recommended - Easiest to Use)

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Start web server**: 
   - **Windows**: Double-click `START_WEB_APP.bat` or run `python web_app\app.py`
   - **Mac/Linux**: Run `python web_app/app.py`
3. **Open browser**: Go to `http://localhost:5000`
4. **Upload CSV file**: Drag and drop your Trackman CSV, click "Generate Report"

**No technical knowledge required!** Just drag, drop, and click.

### 💻 Command Line Interface

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Validate your folder structure**: Run `python scripts/validate_structure.py <path>`
3. **Clean Trackman data**: Use `python scripts/clean_trackman.py <input.csv> <output.csv>`
4. **Generate postgame report**: 
   - **Automatic**: Set up file watcher - `python scripts/watch_trackman.py <watch_dir> --output <output_dir>`
   - **Manual**: `python scripts/generate_report.py <trackman.csv> --pitcher "Name" --game "Game1" --opponent "UCLA"`

See [docs/QUICK_START.md](docs/QUICK_START.md) for more examples.
See [docs/TRACKMAN_REPORT_PIPELINE.md](docs/TRACKMAN_REPORT_PIPELINE.md) for the complete automated pipeline guide.
See [web_app/README.md](web_app/README.md) for web interface details.

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

