# Quick Start Guide

## 5-Minute Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Validate your structure** (if you have data)
   ```bash
   python scripts/validate_structure.py BaseballData/
   ```

3. **Clean a Trackman CSV**
   ```bash
   python scripts/clean_trackman.py raw_data.csv clean_data.csv
   ```

4. **Generate a report**
   ```bash
   python scripts/generate_report.py clean_data.csv --pitcher "Smith" --opponent "UCLA" --game "Game1"
   ```

## Common Tasks

### Generate Postgame Report
```bash
python scripts/generate_report.py trackman.csv --pitcher "PitcherName" --opponent "Opponent" --game "Game1"
```

### Set Up Auto-Generation (File Watcher)
```bash
python scripts/watch_trackman.py BaseballData/2026/UCLA/Series_20260315/Game_1/Pitching/Trackman/ --output Reports/
```

### Generate Scouting Report
```bash
python scripts/generate_scouting_report.py --opponent "UCLA" --hitters hitters.csv --pitchers pitchers.csv
```

### Run Dashboard (if Streamlit installed)
```bash
streamlit run dashboards/arsenal_dashboard.py
```

## File Naming

Always follow the convention:
```
YYYYMMDD_Opponent_Game#_PitcherName_DataType.csv
```

Example: `20260315_UCLA_Game1_Smith_Trackman.csv`

## Folder Structure

```
BaseballData/
└── YYYY/
    └── Opponent/
        └── Series_YYYYMMDD/
            └── Game_#/
                ├── Pitching/
                │   ├── Trackman/
                │   ├── ForcePlates/
                │   └── Reports/
                ├── Hitting/
                └── Video/
```

## Need Help?

- Read [README.md](../README.md) for overview
- Read [SETUP.md](SETUP.md) for detailed setup
- Read [WORKFLOW.md](WORKFLOW.md) for daily operations
- Read [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) for quality standards

