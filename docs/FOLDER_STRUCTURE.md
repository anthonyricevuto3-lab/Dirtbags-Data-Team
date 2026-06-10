# Folder Structure & Naming Conventions

## Quick Reference

### Folder Hierarchy

```
BaseballData/
└── YYYY/                    # Year (e.g., 2026)
    └── Opponent/            # Opponent name (e.g., "UCLA")
        └── Series_YYYYMMDD/ # Series date (e.g., "Series_20260315")
            └── Game_#/      # Game number (e.g., "Game_1")
                ├── Pitching/
                │   ├── Trackman/
                │   ├── ForcePlates/
                │   └── Reports/
                ├── Hitting/
                └── Video/
```

### File Naming

**Pattern**: `YYYYMMDD_Opponent_Game#_PitcherName_DataType.ext`

**Components**:
- `YYYYMMDD`: Date (e.g., 20260315)
- `Opponent`: Opponent name (e.g., UCLA)
- `Game#`: Game number (e.g., Game1)
- `PitcherName`: Pitcher last name (e.g., Smith)
- `DataType`: Data type (e.g., Trackman, ForcePlates, Report)
- `ext`: File extension (e.g., csv, pdf)

**Examples**:
- `20260315_UCLA_Game1_Smith_Trackman.csv`
- `20260315_UCLA_Game1_Smith_ForcePlates.csv`
- `20260315_UCLA_Game1_Smith_Report.pdf`

## Validation

Run the validation script to check your structure:

```bash
python scripts/validate_structure.py BaseballData/
```

## Rules

1. **Year directories**: Must be 4-digit year (e.g., 2026)
2. **Series directories**: Must start with "Series_" followed by YYYYMMDD
3. **Game directories**: Must start with "Game_" followed by number
4. **File names**: Must match exact pattern above
5. **No spaces**: Use underscores in file/directory names
6. **Consistency**: Same format every time

## Definition of Done

✓ Any staff member can find any report in <10 seconds
✓ No ambiguity about "latest" or "final" files
✓ Structure is self-documenting

