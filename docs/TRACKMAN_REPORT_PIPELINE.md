# Trackman Postgame Report Pipeline

## Overview

This pipeline replaces the outsourced 6-4-3 post-performance reports with an in-house, automated system.

## Definition of Done ✓

- ✅ **Drop Trackman CSV into folder → PDF is produced automatically**
- ✅ **Same format every time** - Consistent layout, visuals, and tables
- ✅ **Works for any pitcher or outing with minimal manual input**
- ✅ **Post-outing report produced same night (or early next morning)**

## Two Methods of Operation

### Method 1: Automatic File Watcher (Recommended)

**Setup once, then automatic:**

1. Start the file watcher:
   ```powershell
   python scripts\watch_trackman.py "BaseballData\2025\Practice\Series_20251003\Session_4\Pitching\Trackman" --output "BaseballData\2025\Practice\Series_20251003\Session_4\Pitching\Reports"
   ```

2. Drop Trackman CSV files into the watched directory

3. Reports are automatically generated in the output directory

**Features:**
- Extracts pitcher name from CSV data
- Extracts game metadata from filename/path
- No manual input required after initial setup
- Runs continuously until stopped (Ctrl+C)

### Method 2: Manual Generation

**For one-off reports:**

```powershell
python scripts\generate_report.py "path\to\trackman.csv" --pitcher "PitcherName" --opponent "Opponent" --game "Game1"
```

**Minimal input required:**
- CSV file path (required)
- Pitcher name (can be extracted from CSV if not provided)
- Opponent and game info (optional, can be extracted from path)

## Report Contents

Every report includes (same format every time):

### Visualizations
1. **Pitch Location Plots** (4 panels)
   - All pitches
   - 2-strike pitches
   - Whiffs
   - Batted balls in play

2. **Pitch Movement**
   - HB vs IVB scatter plot (color-coded by pitch type)
   - Spin axis/tilt polar plot (if data available)

3. **Batted Ball Visuals**
   - Spray chart (field plot)
   - Whiff zone heatmap

### Tables
1. **Arsenal Summary** (by pitch type)
   - Pitches, Usage%, Strike%
   - Velocity AVG + MAX
   - Spin Rate AVG
   - IVB AVG + HB AVG
   - Extension AVG
   - Release Height & Side AVG

2. **Contact Outcomes** (by pitch type)
   - BIP count
   - GB% / FB% / LD% / PU%
   - Launch Angle AVG
   - Exit Velocity AVG + MAX
   - Hard Hit %
   - Pull% / Middle% / Oppo%

3. **Plate Discipline** (by pitch type)
   - Zone% / Heart% / Shadow%
   - Chase% / Swing%
   - Whiff% / Z-Whiff% / O-Whiff%
   - Put-Away Proxy

## Workflow for Post-Outing Reports

### Same Night / Early Morning Process

1. **Export Trackman CSV** from Trackman system
2. **Drop file** into the appropriate Trackman folder:
   ```
   BaseballData/YYYY/Opponent/Series_YYYYMMDD/Game_#/Pitching/Trackman/
   ```
3. **File watcher automatically generates report** in:
   ```
   BaseballData/YYYY/Opponent/Series_YYYYMMDD/Game_#/Pitching/Reports/
   ```
4. **Report is ready** - Same format, no manual formatting needed

## File Naming Convention

Reports follow the naming convention:
```
YYYYMMDD_Opponent_Game#_PitcherName_Trackman_report.pdf
```

Example:
```
20251003_Practice_Session4_Grindlinger_Trackman_report.pdf
```

## Consistency Guarantees

- **Same layout** - Every report uses identical page structure
- **Same visuals** - Consistent plot styles and colors
- **Same metrics** - All calculations use the shared metrics library
- **Same format** - PDF layout is standardized

## Minimal Manual Input

The system requires minimal input because:

1. **Pitcher name** - Extracted from CSV data (Pitcher column)
2. **Game metadata** - Extracted from folder structure and filename
3. **Date** - Extracted from filename (YYYYMMDD format)
4. **Opponent** - Extracted from folder path

Only required if not in standard structure:
- Pitcher name (if CSV doesn't have Pitcher column)
- Opponent name (if not in folder path)
- Game identifier (if not in folder path)

## Comparison to 6-4-3 Reports

**Advantages:**
- ✅ In-house control
- ✅ No outsourcing delays
- ✅ Consistent format
- ✅ Automated pipeline
- ✅ No additional cost per report
- ✅ Customizable (can modify templates as needed)

**Same Quality:**
- All required visuals included
- All required metrics calculated
- Professional PDF format
- Ready for coaching staff use

## Troubleshooting

### Report not generating automatically
- Check file watcher is running
- Verify CSV file is in watched directory
- Check logs for errors

### Missing pitcher name
- Ensure CSV has "Pitcher" or "PitcherId" column
- Or provide manually with `--pitcher` flag

### Report format issues
- All reports use the same template
- If format differs, check for data quality issues
- Verify CSV has required columns

## Next Steps

1. Set up file watcher for each game/series
2. Train staff on drop-file process
3. Verify reports match coaching needs
4. Adjust templates if needed (but maintain consistency)

