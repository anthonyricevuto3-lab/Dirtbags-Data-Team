"""
Process raw CSV files and generate cumulative player profile reports.

Usage:
    python scripts/process_player_profiles.py
    
This script:
1. Monitors the 'RawCSVs' folder for new CSV files
2. Processes them and adds to player profiles
3. Generates/updates PDF reports for each player
"""

import sys
import subprocess
from pathlib import Path
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.profiles import ProfileManager
from src.profiles.paths import ensure_player_dir


class CSVHandler(FileSystemEventHandler):
    """Handle new CSV files."""
    
    def __init__(self, profile_manager: ProfileManager):
        self.profile_manager = profile_manager
        self.processed_files = set()
        self.base_dir = Path(__file__).parent.parent
    
    def on_created(self, event):
        """Called when a file is created."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if file_path.suffix.lower() == '.csv' and file_path not in self.processed_files:
            # Wait a moment for file to be fully written
            time.sleep(1)
            
            print(f"\n[NEW FILE] Processing: {file_path.name}")
            result = self.profile_manager.process_csv_file(file_path)
            
            if result['success']:
                print(f"[SUCCESS] Added to {result['player']} profile")
                print(f"  - Pitches: {result['pitches']}")
                print(f"  - Total outings: {result['total_outings']}")
                print(f"  - Total pitches: {result['total_pitches']}")
                
                # Generate/update PDF report
                from src.profiles import load_player_profile
                name_parts = result['player'].split()
                if len(name_parts) >= 2:
                    first_name = name_parts[0]
                    last_name = name_parts[-1]
                    player_profile = load_player_profile(
                        first_name,
                        last_name,
                        self.profile_manager.profiles_dir
                    )
                    if player_profile:
                        ensure_player_dir(self.profile_manager.profiles_dir, first_name, last_name)
                try:
                    reports = self.base_dir / "scripts" / "generate_preview_reports.py"
                    subprocess.run([sys.executable, str(reports)], check=True)
                except Exception as e:
                    print(f"[WARN] Report generation failed: {e}")
            else:
                print(f"[ERROR] Failed to process: {result.get('error', 'Unknown error')}")
            
            self.processed_files.add(file_path)


def process_all_existing():
    """Process all existing CSV files."""
    base_dir = Path(__file__).parent.parent
    raw_csv_dir = base_dir / 'Trackman CSVs'
    profiles_dir = base_dir / 'PlayerProfiles'
    
    profile_manager = ProfileManager(profiles_dir, raw_csv_dir)
    
    print("=" * 60)
    print("Processing all existing CSV files...")
    print("=" * 60)
    
    results = profile_manager.process_all_csvs()
    
    print(f"\n[SUMMARY]")
    print(f"  Processed: {results['processed']}")
    print(f"  Successful: {results['successful']}")
    print(f"  Failed: {results['failed']}")
    
    # Generate reports for all players
    print("\n[GENERATING REPORTS]")
    profiles = [
        p for p in profile_manager.get_all_profiles()
        if (p.first_name, p.last_name) not in profile_manager.skip_players()
    ]
    
    for profile in profiles:
        ensure_player_dir(profiles_dir, profile.first_name, profile.last_name)

    try:
        reports = base_dir / "scripts" / "generate_preview_reports.py"
        print("\n[GENERATING GAME, BULLPEN, AND PROFILE REPORTS]")
        subprocess.run([sys.executable, str(reports)], check=True)
    except Exception as e:
        print(f"[WARN] Report generation failed: {e}")

    print("\n[COMPLETE] All profiles processed and reports generated!")


def watch_folder():
    """Watch folder for new CSV files."""
    base_dir = Path(__file__).parent.parent
    raw_csv_dir = base_dir / 'Trackman CSVs'
    profiles_dir = base_dir / 'PlayerProfiles'
    
    # Do not create Trackman CSVs folder; expect it to exist
    profiles_dir.mkdir(parents=True, exist_ok=True)
    
    profile_manager = ProfileManager(profiles_dir, raw_csv_dir)
    event_handler = CSVHandler(profile_manager)
    observer = Observer()
    observer.schedule(event_handler, str(raw_csv_dir), recursive=False)
    observer.start()
    
    print("=" * 60)
    print("Player Profile System - File Watcher")
    print("=" * 60)
    print(f"Watching folder: {raw_csv_dir}")
    print(f"Profiles stored in: {profiles_dir}")
    print("\nDrop CSV files into the 'RawCSVs' folder to process them.")
    print("Press Ctrl+C to stop.\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[STOPPED] File watcher stopped.")
    
    observer.join()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Process player profile CSVs')
    parser.add_argument('--process-all', action='store_true',
                       help='Process all existing CSV files and generate reports')
    parser.add_argument('--watch', action='store_true', default=True,
                       help='Watch folder for new CSV files (default)')
    
    args = parser.parse_args()
    
    if args.process_all:
        process_all_existing()
    else:
        # First process all existing, then watch
        process_all_existing()
        print("\n" + "=" * 60)
        print("Starting file watcher...")
        print("=" * 60 + "\n")
        watch_folder()

