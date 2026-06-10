# Player Profile System

## Overview

The Player Profile System automatically processes raw Trackman CSV files and creates cumulative player profiles. Simply drop CSV files into a folder, and the system will:

1. **Extract player names** from CSV files
2. **Organize by player** (Last Name / First Name)
3. **Accumulate statistics** across all outings
4. **Generate user-friendly PDF reports** for each player

## Quick Start

### 1. Create the RawCSVs Folder

Create a folder called `RawCSVs` in your project directory (if it doesn't exist).

### 2. Add CSV Files

Simply copy or move your Trackman CSV files into the `RawCSVs` folder.

### 3. Run the System

**Windows:**
```batch
START_PLAYER_PROFILES.bat
```

**Or manually:**
```bash
python scripts/process_player_profiles.py
```

### 4. View Reports

Player profiles and PDF reports are automatically generated in:
```
PlayerProfiles/
  LastName_FirstName/
    profile.json
    outing_001.csv
    outing_002.csv
    ...
    FirstName_LastName_Profile.pdf
```

## How It Works

### Player Name Extraction

The system tries multiple methods to extract player names:

1. **From CSV columns**: Looks for `pitcher`, `pitcher_name`, `player`, `player_name`, or `name`
2. **From filename**: Parses patterns like:
   - `FirstName_LastName_Trackman.csv`
   - `LastName_FirstName_Trackman.csv`
   - `FirstName LastName.csv`

### Profile Organization

Profiles are organized by:
- **Last Name** (folder)
  - **First Name** (subfolder)
    - Individual outing CSV files
    - Profile metadata (JSON)
    - Cumulative PDF report

### Cumulative Statistics

Each player profile accumulates:
- **All pitches** across all outings
- **Total outings** count
- **Total pitches** count
- **Cumulative metrics** (usage rates, strike rates, etc.)
- **Cumulative visualizations** (location plots, movement charts)

## PDF Report Contents

Each player's PDF report includes:

1. **Title Page**
   - Player name
   - Total outings
   - Total pitches
   - Last updated date

2. **Pitch Location Plots** (Cumulative)
   - All pitches
   - 2-strike pitches
   - Whiffs
   - Batted balls in play

3. **Movement Charts** (Cumulative)
   - Horizontal Break vs Induced Vertical Break
   - Color-coded by pitch type

4. **Summary Tables** (Cumulative)
   - Arsenal Summary (by pitch type)
   - Contact Outcomes (by pitch type)
   - Plate Discipline (by pitch type)

## File Structure

```
Project Root/
  RawCSVs/                    # Drop CSV files here
    file1.csv
    file2.csv
    ...
  
  PlayerProfiles/             # Generated automatically
    LastName_FirstName/
      profile.json            # Profile metadata
      outing_001.csv          # Individual outing data
      outing_002.csv
      ...
      FirstName_LastName_Profile.pdf  # Cumulative report
```

## Automatic Processing

The system runs in two modes:

### 1. Initial Processing
When you first run the script, it processes all existing CSV files in `RawCSVs/`.

### 2. File Watching
After initial processing, the system watches the `RawCSVs/` folder for new files and automatically:
- Processes new CSV files
- Updates player profiles
- Regenerates PDF reports

## Manual Processing

To process all files without watching:

```bash
python scripts/process_player_profiles.py --process-all
```

## Troubleshooting

### Player Name Not Detected

If a player name can't be extracted:
1. Check the CSV file has a `pitcher` or `pitcher_name` column
2. Rename the file to include the player name: `FirstName_LastName_Trackman.csv`
3. The system will try to extract from the filename

### Reports Not Generating

- Check that CSV files have valid Trackman data
- Ensure the `PlayerProfiles/` folder is writable
- Check the console output for error messages

### Multiple Players in One CSV

Currently, the system assumes one player per CSV file. If you have multiple players:
- Split the CSV into separate files (one per player)
- Or manually organize by player before processing

## Features

✅ **Automatic processing** - Just drop files in a folder
✅ **Cumulative statistics** - All outings combined
✅ **User-friendly PDFs** - Easy to read and share
✅ **Organized by player** - Last Name / First Name structure
✅ **Automatic updates** - Reports regenerate when new data is added
✅ **No manual input required** - Fully automated

## Example Workflow

1. **After a practice/game:**
   - Export Trackman CSV
   - Copy to `RawCSVs/` folder

2. **System automatically:**
   - Detects new file
   - Extracts player name
   - Adds to player profile
   - Updates cumulative statistics
   - Regenerates PDF report

3. **View report:**
   - Open `PlayerProfiles/LastName/FirstName/FirstName_LastName_Profile.pdf`
   - See cumulative stats across all outings

