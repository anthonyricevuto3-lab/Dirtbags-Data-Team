#!/usr/bin/env python3
"""
Organize and clean all Trackman CSV files from a source directory.

Processes all Trackman CSV files, cleans them, and organizes them into the
standard folder structure.

Usage:
    python scripts/organize_trackman_csvs.py --source "Trackman CSVs" --output "BaseballData"
"""

import sys
import argparse
import pandas as pd
from pathlib import Path
import re
from collections import defaultdict
import logging

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import clean_trackman

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


def parse_filename(filename: str) -> dict:
    """
    Parse Trackman filename to extract metadata.
    
    Expected format: YYYYMMDD-Location-Private-#_unverified.csv
    Example: 20251003-BlairField-Private-1_unverified.csv
    
    Returns:
        Dictionary with date, location, session_number
    """
    # Remove extension
    name = Path(filename).stem
    
    # Remove _unverified suffix if present
    name = name.replace('_unverified', '')
    
    # Pattern: YYYYMMDD-Location-Private-#
    pattern = r'(\d{8})-(.+?)-Private-(\d+)'
    match = re.match(pattern, name)
    
    if match:
        date_str, location, session = match.groups()
        return {
            'date': date_str,
            'location': location,
            'session_number': int(session),
        }
    
    # Fallback: try to extract date
    date_match = re.search(r'(\d{8})', name)
    if date_match:
        return {
            'date': date_match.group(1),
            'location': 'Unknown',
            'session_number': 1,
        }
    
    return {
        'date': 'Unknown',
        'location': 'Unknown',
        'session_number': 1,
    }


def extract_pitcher_info(df: pd.DataFrame) -> dict:
    """
    Extract pitcher information from Trackman DataFrame.
    
    Returns:
        Dictionary with pitcher names and IDs found in the data
    """
    pitchers = {}
    
    if 'Pitcher' in df.columns and 'PitcherId' in df.columns:
        pitcher_data = df[['Pitcher', 'PitcherId']].drop_duplicates()
        for _, row in pitcher_data.iterrows():
            pitcher_name = str(row['Pitcher']).strip()
            pitcher_id = str(row['PitcherId']).strip()
            if pitcher_name and pitcher_name != 'nan':
                # Extract last name from "Last, First" format
                if ',' in pitcher_name:
                    last_name = pitcher_name.split(',')[0].strip()
                else:
                    last_name = pitcher_name.split()[-1] if ' ' in pitcher_name else pitcher_name
                pitchers[pitcher_id] = {
                    'full_name': pitcher_name,
                    'last_name': last_name,
                }
    
    return pitchers


def organize_files(source_dir: Path, output_base: Path):
    """
    Process all Trackman CSV files and organize them.
    
    Args:
        source_dir: Directory containing source CSV files
        output_base: Base directory for organized output
    """
    # Find all CSV files (excluding playerpositioning files)
    csv_files = [
        f for f in source_dir.glob('*.csv')
        if '_playerpositioning_NoFHC' not in f.name
    ]
    
    logger.info(f"Found {len(csv_files)} Trackman CSV files to process")
    
    # Group files by date and session
    files_by_session = defaultdict(list)
    
    for csv_file in csv_files:
        metadata = parse_filename(csv_file.name)
        key = (metadata['date'], metadata['session_number'])
        files_by_session[key].append((csv_file, metadata))
    
    logger.info(f"Found {len(files_by_session)} unique sessions")
    
    # Process each session
    for (date, session_num), file_list in files_by_session.items():
        logger.info(f"\nProcessing session: {date} - Session {session_num}")
        
        # Get metadata from first file
        first_file, metadata = file_list[0]
        location = metadata['location']
        year = date[:4] if len(date) == 8 else '2025'
        
        # Determine if this is practice/scrimmage or game data
        # For now, treat all as practice data since filenames don't indicate games
        opponent = 'Practice'  # Default for practice/scrimmage data
        
        # Create output structure
        # For practice data: BaseballData/YYYY/Practice/Series_YYYYMMDD/Session_#/Pitching/Trackman/
        series_date = date
        output_dir = (
            output_base / year / opponent / f"Series_{series_date}" /
            f"Session_{session_num}" / "Pitching" / "Trackman"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"  Output directory: {output_dir}")
        
        # Process each file in the session
        for csv_file, file_metadata in file_list:
            logger.info(f"  Processing: {csv_file.name}")
            
            try:
                # Read raw CSV
                df_raw = pd.read_csv(csv_file)
                logger.info(f"    Loaded {len(df_raw)} rows")
                
                # Extract pitcher info from raw data (before cleaning)
                pitchers = extract_pitcher_info(df_raw)
                logger.info(f"    Found {len(pitchers)} pitcher(s)")
                
                # Clean data
                df_clean = clean_trackman(df_raw, strict=False)
                logger.info(f"    Cleaned to {len(df_clean)} rows")
                
                # If multiple pitchers, split by pitcher
                if len(pitchers) > 1:
                    for pitcher_id, pitcher_info in pitchers.items():
                        # Match by pitcher_id (convert both to string for comparison)
                        # Also try matching by original PitcherId if pitcher_id column exists
                        if 'pitcher_id' in df_clean.columns:
                            pitcher_df = df_clean[df_clean['pitcher_id'].astype(str) == str(pitcher_id)]
                        else:
                            # Fallback: use original PitcherId column if mapping didn't work
                            if 'PitcherId' in df_clean.columns:
                                pitcher_df = df_clean[df_clean['PitcherId'].astype(str) == str(pitcher_id)]
                            else:
                                logger.warning(f"    Could not find pitcher_id column for {pitcher_info['last_name']}")
                                continue
                        
                        if len(pitcher_df) > 0:
                            output_filename = (
                                f"{date}_{opponent}_Session{session_num}_"
                                f"{pitcher_info['last_name']}_Trackman.csv"
                            )
                            output_path = output_dir / output_filename
                            pitcher_df.to_csv(output_path, index=False)
                            logger.info(f"    Saved: {output_filename} ({len(pitcher_df)} pitches)")
                        else:
                            logger.warning(f"    No pitches found for pitcher {pitcher_info['last_name']} (ID: {pitcher_id})")
                else:
                    # Single pitcher or no pitcher info - save as single file
                    if pitchers:
                        pitcher_info = list(pitchers.values())[0]
                        pitcher_name = pitcher_info['last_name']
                    else:
                        pitcher_name = 'Unknown'
                    
                    output_filename = (
                        f"{date}_{opponent}_Session{session_num}_"
                        f"{pitcher_name}_Trackman.csv"
                    )
                    output_path = output_dir / output_filename
                    df_clean.to_csv(output_path, index=False)
                    logger.info(f"    Saved: {output_filename} ({len(df_clean)} pitches)")
                
            except Exception as e:
                logger.error(f"    Error processing {csv_file.name}: {e}")
                import traceback
                traceback.print_exc()
    
    logger.info(f"\n✓ Processing complete!")
    logger.info(f"  Organized files saved to: {output_base}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Organize and clean Trackman CSV files'
    )
    parser.add_argument(
        '--source', '-s',
        default='Trackman CSVs',
        help='Source directory containing CSV files (default: Trackman CSVs)'
    )
    parser.add_argument(
        '--output', '-o',
        default='BaseballData',
        help='Output base directory (default: BaseballData)'
    )
    
    args = parser.parse_args()
    
    source_dir = Path(args.source)
    if not source_dir.exists():
        logger.error(f"Source directory does not exist: {source_dir}")
        sys.exit(1)
    
    output_base = Path(args.output)
    output_base.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Source directory: {source_dir}")
    logger.info(f"Output directory: {output_base}")
    
    organize_files(source_dir, output_base)


if __name__ == "__main__":
    main()

