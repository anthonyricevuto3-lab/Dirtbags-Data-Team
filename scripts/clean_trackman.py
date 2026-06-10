#!/usr/bin/env python3
"""
Clean Trackman CSV file to canonical schema.

Usage:
    python scripts/clean_trackman.py <input.csv> <output.csv>
    python scripts/clean_trackman.py raw_data.csv clean_data.csv
"""

import sys
import pandas as pd
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import clean_trackman, validate_trackman


def main():
    """Main cleaning function."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/clean_trackman.py <input.csv> <output.csv>")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}")
        sys.exit(1)
    
    print(f"Reading: {input_path}")
    
    # Read raw CSV
    try:
        df = pd.read_csv(input_path)
        print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        sys.exit(1)
    
    # Clean data
    print("Cleaning data...")
    try:
        df_clean = clean_trackman(df, strict=False)
        print(f"  Cleaned to {len(df_clean)} rows, {len(df_clean.columns)} columns")
    except Exception as e:
        print(f"Error cleaning data: {e}")
        sys.exit(1)
    
    # Validate
    print("Validating...")
    is_valid, errors = validate_trackman(df_clean)
    if not is_valid:
        print("  Validation warnings:")
        for error in errors:
            print(f"    - {error}")
    else:
        print("  [SUCCESS] Validation passed")
    
    # Save
    print(f"Writing: {output_path}")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_clean.to_csv(output_path, index=False)
        print("  [SUCCESS] Done")
    except Exception as e:
        print(f"Error writing CSV: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

