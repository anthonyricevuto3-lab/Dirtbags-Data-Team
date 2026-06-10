#!/usr/bin/env python3
"""
File watcher for automatic Trackman report generation.

Watches a directory for new Trackman CSV files and automatically generates reports.

Usage:
    python scripts/watch_trackman.py <watch_directory> --output <output_directory>
    python scripts/watch_trackman.py BaseballData/2026/UCLA/Series_20260315/Game_1/Pitching/Trackman/ --output Reports/
"""

import sys
import argparse
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reports import generate_trackman_report
from src.schemas import clean_trackman
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


class TrackmanFileHandler(FileSystemEventHandler):
    """Handler for Trackman CSV file events."""
    
    def __init__(self, output_dir: Path, pitcher_name: str = None, game_info: dict = None):
        """
        Initialize handler.
        
        Args:
            output_dir: Directory to save generated reports
            pitcher_name: Default pitcher name (can be extracted from filename)
            game_info: Default game info (can be extracted from path)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pitcher_name = pitcher_name
        self.game_info = game_info or {}
        self.processed_files = set()
    
    def on_created(self, event):
        """Handle file creation event."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Only process CSV files
        if file_path.suffix.lower() != '.csv':
            return
        
        # Avoid processing the same file multiple times
        if file_path in self.processed_files:
            return
        
        # Wait a moment for file to be fully written
        time.sleep(1)
        
        logger.info(f"New CSV file detected: {file_path}")
        
        try:
            self.process_file(file_path)
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    def extract_metadata_from_path(self, file_path: Path) -> tuple:
        """
        Extract pitcher name and game info from file path.
        
        Expected path structure:
        BaseballData/YYYY/Opponent/Series_YYYYMMDD/Game_#/Pitching/Trackman/filename.csv
        
        Expected filename:
        YYYYMMDD_Opponent_Game#_PitcherName_Trackman.csv
        """
        pitcher_name = self.pitcher_name
        game_info = self.game_info.copy()
        
        # Try to extract from filename
        filename = file_path.stem
        parts = filename.split('_')
        
        if len(parts) >= 4:
            # Format: YYYYMMDD_Opponent_Game#_PitcherName_DataType
            if not pitcher_name and len(parts) >= 4:
                pitcher_name = parts[3]  # Pitcher name is typically 4th part
            
            if 'opponent' not in game_info and len(parts) >= 2:
                game_info['opponent'] = parts[1]
            
            if 'game' not in game_info and len(parts) >= 3:
                game_info['game'] = parts[2]
            
            if 'date' not in game_info and len(parts) >= 1:
                date_str = parts[0]
                if len(date_str) == 8 and date_str.isdigit():
                    # Format: YYYYMMDD -> YYYY-MM-DD
                    game_info['date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        
        # Try to extract from path
        path_parts = file_path.parts
        for i, part in enumerate(path_parts):
            if part.startswith('Series_'):
                series_date = part.replace('Series_', '')
                if len(series_date) == 8 and series_date.isdigit():
                    game_info['date'] = f"{series_date[:4]}-{series_date[4:6]}-{series_date[6:8]}"
            
            if part.startswith('Game_'):
                if 'game' not in game_info:
                    game_info['game'] = part
            
            # Opponent is typically before Series
            if i > 0 and path_parts[i-1].isdigit() and len(path_parts[i-1]) == 4:
                if 'opponent' not in game_info:
                    game_info['opponent'] = part
        
        return pitcher_name, game_info
    
    def extract_pitcher_from_csv(self, file_path: Path) -> Optional[str]:
        """Extract pitcher name from CSV data."""
        try:
            df = pd.read_csv(file_path, nrows=10)  # Read first few rows to get pitcher name
            # Try common pitcher column names
            pitcher_cols = ['Pitcher', 'PitcherId', 'Pitcher Id', 'pitcher_id', 'PitcherName']
            for col in pitcher_cols:
                if col in df.columns:
                    pitchers = df[col].dropna().unique()
                    if len(pitchers) > 0:
                        pitcher = str(pitchers[0])
                        # Clean pitcher name (remove commas, spaces -> underscores)
                        pitcher = pitcher.replace(', ', '_').replace(',', '_').replace(' ', '_')
                        return pitcher
        except Exception as e:
            logger.debug(f"Could not extract pitcher from CSV: {e}")
        return None
    
    def process_file(self, file_path: Path):
        """Process a Trackman CSV file and generate report."""
        # Extract metadata from path/filename
        pitcher_name, game_info = self.extract_metadata_from_path(file_path)
        
        # If pitcher name not in filename, try to extract from CSV
        if not pitcher_name or pitcher_name == 'Unknown':
            pitcher_name = self.extract_pitcher_from_csv(file_path)
        
        # Use default if provided
        if not pitcher_name:
            pitcher_name = self.pitcher_name
        
        if not pitcher_name:
            logger.warning(f"Could not determine pitcher name for {file_path}. Skipping.")
            return
        
        # Generate output filename
        output_filename = f"{file_path.stem}_report.pdf"
        output_path = self.output_dir / output_filename
        
        logger.info(f"Generating report: {output_path}")
        logger.info(f"  Pitcher: {pitcher_name}")
        if game_info:
            logger.info(f"  Game Info: {game_info}")
        
        # Generate report
        generate_trackman_report(
            csv_path=str(file_path),
            output_path=str(output_path),
            pitcher_name=pitcher_name,
            game_info=game_info if game_info else None,
        )
        
        logger.info(f"  [SUCCESS] Report generated: {output_path}")
        self.processed_files.add(file_path)


def main():
    """Main watcher function."""
    parser = argparse.ArgumentParser(description='Watch directory for Trackman CSV files and auto-generate reports')
    parser.add_argument('watch_dir', help='Directory to watch for CSV files')
    parser.add_argument('--output', '-o', required=True, help='Output directory for generated reports')
    parser.add_argument('--pitcher', help='Default pitcher name (if not in filename)')
    parser.add_argument('--opponent', help='Default opponent name')
    parser.add_argument('--game', help='Default game identifier')
    parser.add_argument('--date', help='Default game date')
    
    args = parser.parse_args()
    
    watch_dir = Path(args.watch_dir)
    if not watch_dir.exists():
        print(f"Error: Watch directory does not exist: {watch_dir}")
        sys.exit(1)
    
    if not watch_dir.is_dir():
        print(f"Error: Watch path is not a directory: {watch_dir}")
        sys.exit(1)
    
    # Build default game info
    game_info = {}
    if args.opponent:
        game_info['opponent'] = args.opponent
    if args.game:
        game_info['game'] = args.game
    if args.date:
        game_info['date'] = args.date
    
    # Create event handler
    event_handler = TrackmanFileHandler(
        output_dir=args.output,
        pitcher_name=args.pitcher,
        game_info=game_info,
    )
    
    # Create observer
    observer = Observer()
    observer.schedule(event_handler, str(watch_dir), recursive=False)
    
    logger.info(f"Watching directory: {watch_dir}")
    logger.info(f"Output directory: {args.output}")
    logger.info("Press Ctrl+C to stop")
    
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping watcher...")
        observer.stop()
    
    observer.join()
    logger.info("Watcher stopped")


if __name__ == "__main__":
    main()

