# Setup Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

1. **Clone or navigate to the project directory**

```bash
cd "Dirtbags Data Team"
```

2. **Create a virtual environment (recommended)**

```bash
python -m venv venv
```

3. **Activate virtual environment**

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

4. **Install dependencies**

```bash
pip install -r requirements.txt
```

## Verify Installation

Run the validation script to verify everything is set up correctly:

```bash
python scripts/validate_structure.py .
```

## Quick Start

### 1. Clean Trackman Data

```bash
python scripts/clean_trackman.py raw_data.csv clean_data.csv
```

### 2. Generate Postgame Report

```bash
python scripts/generate_report.py clean_data.csv --pitcher "Smith" --opponent "UCLA" --game "Game1"
```

### 3. Set Up File Watcher (Optional)

```bash
python scripts/watch_trackman.py BaseballData/2026/UCLA/Series_20260315/Game_1/Pitching/Trackman/ --output Reports/
```

## Project Structure

```
.
├── BaseballData/          # Main data directory (create as needed)
├── src/
│   ├── schemas/           # Data schema definitions
│   ├── metrics/           # Shared metrics library
│   ├── parsers/           # Data parsers
│   ├── visualizations/   # Plotting functions
│   └── reports/           # Report generators
├── scripts/               # CLI tools
├── tests/                 # Unit tests
├── config/                # Configuration files
└── docs/                  # Documentation
```

## Configuration

Edit `config/config.yaml` to customize paths and settings.

## Troubleshooting

### Import Errors

If you get import errors, make sure:
1. Virtual environment is activated
2. Dependencies are installed: `pip install -r requirements.txt`
3. You're running scripts from the project root

### File Not Found Errors

Make sure:
1. File paths are correct (use forward slashes or raw strings on Windows)
2. Directories exist (create them if needed)
3. File names match expected conventions

### Permission Errors

On Windows, you may need to run PowerShell as Administrator for file watching.

## Next Steps

- Read [README.md](../README.md) for overview
- Read [FOLDER_STRUCTURE.md](FOLDER_STRUCTURE.md) for data organization
- Read [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) for quality standards

