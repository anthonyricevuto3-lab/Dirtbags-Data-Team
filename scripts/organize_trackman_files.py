#!/usr/bin/env python3
"""
Organize and clean all Trackman CSV files from a source directory.

Processes all CSV files, cleans them, and organizes them into the canonical folder structure.

Usage:
    python scripts/organize_trackman_files.py --source "Trackman CSVs" --output "BaseballData"
"""

import sys
import argparse
import pandas as pd
from pathlib import Path
import re
from typing import Optional, Dict, Tuple
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import clean_trackman

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def parse_filename(filename: str) -> Dict[str, str]:
    """
    Parse Trackman filename to extract metadata.
    
    Expected formats:
    - 20251003-BlairField-Private-1_unverified.csv
    - 20251003-BlairField-Private-1_unverified_playerpositioning_NoFHC.csv
    
    Returns:
        Dictionary with date, session_number, and other metadata
    """
    # Remove extension
    name = Path(filename).stem
    
    # Pattern: YYYYMMDD-BlairField-Private-N_unverified...
    pattern = r'(\d{8})-BlairField-Private-(\d+)_unverified'
    match = re.match(pattern, name)
    
    if match:
        date_str = match.group(1)
        session_num = match.group(2)
        
        return {
            'date': date_str,
            'session_number': session_num,
            'opponent': 'Practice',
            'location': 'BlairField',
        }
    
    # Fallback: try to extract date from any format
    date_match = re.search(r'(\d{8})', name)
    if date_match:
        return {
            'date': date_match.group(1),
            'session_number': '1',
            'opponent': 'Practice',
            'location': 'Unknown',
        }
    
    return {
        'date': 'Unknown',
        'session_number': '1',
        'opponent': 'Practice',
        'location': 'Unknown',
    }


def extract_pitcher_name(df: pd.DataFrame) -> Optional[str]:
    """
    Extract pitcher name from DataFrame.
    
    Tries multiple column names and returns the first unique pitcher found.
    """
    # Try common pitcher column names
    pitcher_cols = ['Pitcher', 'PitcherId', 'Pitcher Id', 'pitcher_id', 'PitcherName', 'Pitcher Name']
    
    for col in pitcher_cols:
        if col in df.columns:
            pitchers = df[col].dropna().unique()
            if len(pitchers) > 0:
                # Return first pitcher (or most common if multiple)
                return str(pitchers[0])
    
    return None


def organize_file(
    source_path: Path,
    output_root: Path,
    metadata: Dict[str, str],
    pitcher_name: Optional[str] = None,
) -> Tuple[Path, bool]:
    """
    Clean and organize a single Trackman CSV file.
    
    Args:
        source_path: Path to source CSV file
        output_root: Root directory for organized files (BaseballData)
        metadata: Dictionary with date, session_number, opponent, etc.
        pitcher_name: Pitcher name (extracted from file if None)
        
    Returns:
        Tuple of (output_path, success)
    """
    try:
        # Read raw CSV
        logger.info(f"Processing: {source_path.name}")
        df_raw = pd.read_csv(source_path)
        
        # Extract pitcher name if not provided
        if pitcher_name is None:
            pitcher_name = extract_pitcher_name(df_raw)
            if pitcher_name is None:
                pitcher_name = "Unknown"
            else:
                # Clean pitcher name (remove common prefixes/suffixes)
                pitcher_name = pitcher_name.strip().replace(' ', '_')
        
        # Clean data
        df_clean = clean_trackman(df_raw, strict=False)
        
        # Build output path
        date = metadata['date']
        year = date[:4] if len(date) == 8 else '2025'
        opponent = metadata.get('opponent', 'Practice')
        session_num = metadata.get('session_number', '1')
        
        # Format: BaseballData/YYYY/Opponent/Series_YYYYMMDD/Session_N/Pitching/Trackman/
        output_dir = (
            output_root / year / opponent / f"Series_{date}" / f"Session_{session_num}" /
            "Pitching" / "Trackman"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build output filename: YYYYMMDD_Opponent_Session#_PitcherName_Trackman.csv
        output_filename = f"{date}_{opponent}_Session{session_num}_{pitcher_name}_Trackman.csv"
        output_path = output_dir / output_filename
        
        # Handle duplicates
        if output_path.exists():
            logger.warning(f"File already exists: {output_path}")
            # Add suffix
            counter = 1
            while output_path.exists():
                output_filename = f"{date}_{opponent}_Session{session_num}_{pitcher_name}_Trackman_{counter}.csv"
                output_path = output_dir / output_filename
                counter += 1
        
        # Save cleaned file
        df_clean.to_csv(output_path, index=False)
        logger.info(f"  [SUCCESS] Saved to: {output_path}")
        
        return output_path, True
        
    except Exception as e:
        logger.error(f"  ✗ Error processing {source_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return None, False


def main():
    """Main organization function."""
    parser = argparse.ArgumentParser(description='Organize and clean Trackman CSV files')
    parser.add_argument('--source', '-s', default='Trackman CSVs', help='Source directory with CSV files')
    parser.add_argument('--output', '-o', default='BaseballData', help='Output root directory')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    source_dir = Path(args.source)
    output_root = Path(args.output)
    
    if not source_dir.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        sys.exit(1)
    
    # Find all CSV files
    csv_files = list(source_dir.glob('*.csv'))
    
    if len(csv_files) == 0:
        logger.warning(f"No CSV files found in {source_dir}")
        sys.exit(0)
    
    logger.info(f"Found {len(csv_files)} CSV files to process")
    logger.info(f"Output directory: {output_root}")
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No files will be modified")
    
    # Process each file
    success_count = 0
    error_count = 0
    
    for csv_file in sorted(csv_files):
        # Parse metadata from filename
        metadata = parse_filename(csv_file.name)
        
        if args.dry_run:
            logger.info(f"[DRY RUN] Would process: {csv_file.name}")
            logger.info(f"  Metadata: {metadata}")
            continue
        
        output_path, success = organize_file(csv_file, output_root, metadata)
        
        if success:
            success_count += 1
        else:
            error_count += 1
    
    # Summary
    logger.info("-" * 60)
    logger.info(f"Processing complete:")
    logger.info(f"  Success: {success_count}")
    logger.info(f"  Errors: {error_count}")
    logger.info(f"  Total: {len(csv_files)}")


if __name__ == "__main__":
    main()

