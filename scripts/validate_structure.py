#!/usr/bin/env python3
"""
Validate folder structure and file naming conventions.

Usage:
    python scripts/validate_structure.py <path>
    python scripts/validate_structure.py BaseballData/
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Tuple


# Expected folder structure pattern
FOLDER_PATTERN = re.compile(
    r'^BaseballData/(\d{4})/([^/]+)/Series_(\d{8})/Game_(\d+)/'
)

# File naming pattern: YYYYMMDD_Opponent_Game#_PitcherName_DataType.csv
FILE_PATTERN = re.compile(
    r'^(\d{8})_([^_]+)_Game(\d+)_([^_]+)_([^.]+)\.(csv|pdf)$'
)


def validate_folder_structure(root_path: Path) -> Tuple[List[str], List[str]]:
    """
    Validate folder structure matches canonical hierarchy.
    
    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []
    
    root_path = Path(root_path).resolve()
    
    # Check if BaseballData exists
    baseball_data = root_path / "BaseballData"
    if not baseball_data.exists():
        warnings.append(f"BaseballData/ directory not found at {root_path}")
        return errors, warnings
    
    # Walk through structure
    for year_dir in baseball_data.iterdir():
        if not year_dir.is_dir():
            continue
            
        # Validate year format
        if not year_dir.name.isdigit() or len(year_dir.name) != 4:
            errors.append(f"Invalid year directory: {year_dir.name} (must be YYYY)")
            continue
        
        # Check opponent directories
        for opponent_dir in year_dir.iterdir():
            if not opponent_dir.is_dir():
                continue
            
            # Check series directories
            for series_dir in opponent_dir.iterdir():
                if not series_dir.is_dir():
                    continue
                
                # Validate series format: Series_YYYYMMDD
                if not series_dir.name.startswith("Series_"):
                    errors.append(f"Invalid series directory: {series_dir.name} (must start with 'Series_')")
                    continue
                
                series_date = series_dir.name.replace("Series_", "")
                if not re.match(r'^\d{8}$', series_date):
                    errors.append(f"Invalid series date format: {series_date} (must be YYYYMMDD)")
                
                # Check game directories
                for game_dir in series_dir.iterdir():
                    if not game_dir.is_dir():
                        continue
                    
                    # Validate game format: Game_#
                    if not game_dir.name.startswith("Game_"):
                        errors.append(f"Invalid game directory: {game_dir.name} (must start with 'Game_')")
                        continue
                    
                    game_num = game_dir.name.replace("Game_", "")
                    if not game_num.isdigit():
                        errors.append(f"Invalid game number: {game_num} (must be numeric)")
    
    return errors, warnings


def validate_file_naming(root_path: Path) -> Tuple[List[str], List[str]]:
    """
    Validate file names match convention.
    
    Returns:
        Tuple of (errors, warnings)
    """
    errors = []
    warnings = []
    
    root_path = Path(root_path).resolve()
    baseball_data = root_path / "BaseballData"
    
    if not baseball_data.exists():
        return errors, warnings
    
    # Find all CSV and PDF files
    for file_path in baseball_data.rglob("*.csv"):
        validate_single_file(file_path, errors, warnings)
    
    for file_path in baseball_data.rglob("*.pdf"):
        validate_single_file(file_path, errors, warnings)
    
    return errors, warnings


def validate_single_file(file_path: Path, errors: List[str], warnings: List[str]):
    """Validate a single file name."""
    filename = file_path.name
    
    match = FILE_PATTERN.match(filename)
    if not match:
        errors.append(f"Invalid file name: {file_path} (does not match YYYYMMDD_Opponent_Game#_PitcherName_DataType.ext)")
        return
    
    date, opponent, game_num, pitcher, data_type, ext = match.groups()
    
    # Validate date format
    if not re.match(r'^\d{8}$', date):
        errors.append(f"Invalid date in filename: {file_path} (date must be YYYYMMDD)")
    
    # Validate game number
    if not game_num.isdigit():
        errors.append(f"Invalid game number in filename: {file_path}")


def main():
    """Main validation function."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_structure.py <path>")
        sys.exit(1)
    
    root_path = Path(sys.argv[1])
    
    if not root_path.exists():
        print(f"Error: Path does not exist: {root_path}")
        sys.exit(1)
    
    print(f"Validating structure at: {root_path}")
    print("-" * 60)
    
    # Validate folder structure
    folder_errors, folder_warnings = validate_folder_structure(root_path)
    
    # Validate file naming
    file_errors, file_warnings = validate_file_naming(root_path)
    
    # Combine results
    all_errors = folder_errors + file_errors
    all_warnings = folder_warnings + file_warnings
    
    # Report results
    if all_warnings:
        print("\nWarnings:")
        for warning in all_warnings:
            print(f"  ⚠ {warning}")
    
    if all_errors:
        print("\nErrors:")
        for error in all_errors:
            print(f"  ✗ {error}")
        print(f"\nFound {len(all_errors)} error(s)")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Structure validation passed!")
        if all_warnings:
            print(f"  ({len(all_warnings)} warning(s) found)")
        sys.exit(0)


if __name__ == "__main__":
    main()

