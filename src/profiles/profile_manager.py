"""
Manages player profiles and processes new CSV files.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
import re
from datetime import datetime

from ..schemas import clean_trackman
from .paths import ensure_player_dir, split_player_dir_name
from .player_profile import PlayerProfile, load_player_profile, save_player_profile
from .roster import get_roster_entry
from .team_config import get_allowed_players, get_skip_players


class ProfileManager:
    """Manages player profiles and processes CSV files."""

    @staticmethod
    def _normalize_name(first: str, last: str) -> tuple:
        def _clean(s: str) -> str:
            return ''.join(ch for ch in s.lower() if ch.isalnum())
        return (_clean(first or ""), _clean(last or ""))

    @classmethod
    def _allowed_normalized(cls) -> set:
        allowed = set()
        for first, last in get_allowed_players():
            allowed.add(cls._normalize_name(first, last))
            allowed.add(cls._normalize_name(last, first))
        return allowed

    @classmethod
    def skip_players(cls) -> set:
        skip = set()
        for first, last in get_skip_players():
            skip.add((first, last))
        return skip

    @classmethod
    def is_allowed_player(cls, first: str, last: str) -> bool:
        key = cls._normalize_name(first, last)
        rev = cls._normalize_name(last, first)
        allowed = cls._allowed_normalized()
        return key in allowed or rev in allowed
    
    def __init__(self, profiles_dir: Path, raw_csv_dir: Path):
        self.profiles_dir = Path(profiles_dir)
        self.raw_csv_dir = Path(raw_csv_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_player_name(self, df: pd.DataFrame, filename: str) -> Optional[tuple]:
        """
        Extract player name from DataFrame or filename.
        
        Returns: (first_name, last_name) or None
        """
        def _parse_name(raw: str) -> Optional[tuple]:
            """Parse a raw string into (first, last)."""
            if not raw:
                return None
            name = str(raw).strip()
            if ',' in name:
                parts = [p.strip() for p in name.split(',')]
                if len(parts) == 2:
                    return (parts[1], parts[0])
            else:
                parts = name.split()
                if len(parts) >= 2:
                    return (parts[0], parts[-1])
            return None
        # Try to get from DataFrame columns
        # Note: clean_trackman renames the Trackman "Pitcher" column to
        # "pitcher_id" (which often still contains the human-readable name),
        # so include it when attempting to extract names.
        name_columns = [
            'pitcher_id',
            'pitcher',
            'pitcher_name',
            'player',
            'player_name',
            'name',
        ]
        for col in name_columns:
            if col in df.columns:
                names = df[col].dropna().unique()
                if len(names) > 0:
                    parsed = _parse_name(names[0])
                    if parsed:
                        return parsed
                    # Single-token name; fall through to filename logic
        
        # Try to extract from filename
        # Patterns: "FirstName_LastName", "LastName_FirstName", "FirstName LastName"
        filename_base = Path(filename).stem
        
        # Remove common prefixes/suffixes
        filename_base = re.sub(r'_\d{8}', '', filename_base)  # Remove dates
        filename_base = re.sub(r'_\d{6}', '', filename_base)  # Remove times
        filename_base = re.sub(r'_Trackman', '', filename_base, flags=re.IGNORECASE)
        filename_base = re.sub(r'_Practice', '', filename_base, flags=re.IGNORECASE)
        filename_base = re.sub(r'_Game', '', filename_base, flags=re.IGNORECASE)
        
        # Try patterns
        # "FirstName_LastName" or "LastName_FirstName"
        if '_' in filename_base:
            parts = filename_base.split('_')
            if len(parts) >= 2:
                # Check if last part looks like a last name (capitalized, no numbers)
                last_part = parts[-1]
                if last_part and last_part[0].isupper() and not any(c.isdigit() for c in last_part):
                    return (parts[0], last_part)
                elif len(parts) >= 2:
                    return (parts[0], parts[1])
        
        # "FirstName LastName" (space separated)
        if ' ' in filename_base:
            parts = filename_base.split()
            if len(parts) >= 2:
                return (parts[0], parts[-1])
        
        return None
    
    def process_csv_file(self, csv_path: Path) -> Dict:
        """
        Process a single CSV file and add to appropriate player profile(s).
        If multiple pitchers appear in the same file, split by pitcher and
        create/update separate profiles.
        
        Returns: Dict with processing results
        """
        try:
            # Load and clean data
            df_raw = pd.read_csv(csv_path, low_memory=False)
            df = clean_trackman(df_raw, strict=False)
            
            if len(df) == 0:
                return {
                    'success': False,
                    'error': 'No valid data in CSV file',
                    'file': str(csv_path),
                }
            
            # Identify pitcher column to split on
            pitcher_col = None
            for candidate in ['pitcher_id', 'pitcher', 'Pitcher']:
                if candidate in df.columns:
                    pitcher_col = candidate
                    break
            
            # If no pitcher column, fall back to single extraction
            if not pitcher_col:
                player_name = self.extract_player_name(df, csv_path.name)
                if not player_name:
                    return {
                        'success': False,
                        'error': 'Could not extract player name from file',
                        'file': str(csv_path),
                    }
                first_name, last_name = player_name
                if not self.is_allowed_player(first_name, last_name):
                    return {
                        'success': False,
                        'error': 'Player not in allowed list',
                        'file': str(csv_path),
                    }
                if (first_name, last_name) in self.skip_players():
                    return {
                        'success': False,
                        'error': 'Skipped filler player',
                        'file': str(csv_path),
                    }
                return self._process_single_player(df, csv_path, first_name, last_name)
            
            # Split by unique pitchers in the file
            pitcher_values = df[pitcher_col].dropna().unique()
            results = []
            for pitcher_value in pitcher_values:
                df_p = df[df[pitcher_col] == pitcher_value].copy()
                if len(df_p) == 0:
                    continue
                name_tuple = self.extract_player_name(df_p, csv_path.name)
                if not name_tuple:
                    continue
                first_name, last_name = name_tuple
                if not self.is_allowed_player(first_name, last_name):
                    continue
                if (first_name, last_name) in self.skip_players():
                    continue
                res = self._process_single_player(df_p, csv_path, first_name, last_name, raw_player_id=pitcher_value)
                results.append(res)
            
            if not results:
                return {
                    'success': False,
                    'error': 'No valid pitcher entries found in file',
                    'file': str(csv_path),
                }
            
            successful = [r for r in results if r.get('success')]
            failed = [r for r in results if not r.get('success')]
            return {
                'success': len(failed) == 0,
                'file': str(csv_path),
                'details': results,
                'successful': len(successful),
                'failed': len(failed),
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'file': str(csv_path),
            }

    def _process_single_player(self, df: pd.DataFrame, csv_path: Path, first_name: str, last_name: str, raw_player_id=None) -> Dict:
        """Process and append outing for a single player subset."""
        if not self.is_allowed_player(first_name, last_name):
            return {
                'success': False,
                'error': 'Player not in allowed list',
                'file': str(csv_path),
            }
        if (first_name, last_name) in self.skip_players():
            return {
                'success': False,
                'error': 'Skipped filler player',
                'file': str(csv_path),
            }
        roster_info = get_roster_entry(first_name, last_name)

        player_id = None
        if raw_player_id:
            player_id = str(raw_player_id).strip()
        elif 'pitcher_id' in df.columns:
            ids = df['pitcher_id'].dropna()
            if len(ids) > 0:
                player_id = str(ids.iloc[0]).strip()
        
        profile = load_player_profile(first_name, last_name, self.profiles_dir)
        if profile is None:
            profile = PlayerProfile(first_name, last_name)
        if not profile.player_id and player_id:
            profile.player_id = player_id
        if roster_info:
            if not profile.position and roster_info.get('position'):
                profile.position = roster_info['position']
            if not profile.bats and roster_info.get('bats'):
                profile.bats = roster_info['bats']
            if not profile.throws and roster_info.get('throws'):
                profile.throws = roster_info['throws']

        # Derive outing date: prefer CSV 'date' column, else filename, else today
        outing_date = datetime.now().strftime('%Y-%m-%d')
        if 'date' in df.columns:
            dates = pd.to_datetime(df['date'], errors='coerce').dropna()
            if len(dates) > 0:
                outing_date = dates.iloc[0].strftime('%Y-%m-%d')

        # Derive game_id if present
        game_id = None
        if 'game_id' in df.columns:
            vals = df['game_id'].dropna()
            if len(vals) > 0:
                game_id = str(vals.iloc[0])

        metadata = {
            'source_file': csv_path.name,
            'source_path': str(csv_path),
            'date': outing_date,
            'pitches': len(df),
            'added_at': datetime.now().isoformat(),
            'player_id': player_id,
        }
        if game_id:
            metadata['game_id'] = game_id
        if roster_info:
            metadata.update({
                'position': roster_info.get('position'),
                'bats': roster_info.get('bats'),
                'throws': roster_info.get('throws'),
            })

        # De-duplicate outings by source path before adding this outing
        profile.outings = [
            o for o in profile.outings
            if o.get('metadata', {}).get('source_path') != metadata.get('source_path')
        ]

        # Try to extract date from filename if not set from CSV
        if outing_date == datetime.now().strftime('%Y-%m-%d'):
            date_match = re.search(r'(\d{8})', csv_path.name)
            if date_match:
                date_str = date_match.group(1)
                try:
                    metadata['date'] = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                except Exception:
                    pass

        profile.add_outing(df, metadata)
        save_player_profile(profile, self.profiles_dir)

        return {
            'success': True,
            'player': profile.full_name,
            'file': str(csv_path),
            'pitches': len(df),
            'total_outings': profile.total_outings,
            'total_pitches': profile.total_pitches,
        }
    
    def process_all_csvs(self) -> Dict:
        """Process all CSV files in raw_csv_dir."""
        csv_files = [f for f in self.raw_csv_dir.glob('*.csv') if 'NoFHC' not in f.name]
        
        results = {
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'details': [],
        }
        
        for csv_file in csv_files:
            result = self.process_csv_file(csv_file)
            results['details'].append(result)
            
            if result['success']:
                results['successful'] += 1
            else:
                results['failed'] += 1
            results['processed'] += 1
        
        return results
    
    def get_all_profiles(self) -> List[PlayerProfile]:
        """Get all player profiles."""
        profiles = []

        for entry in self.profiles_dir.iterdir():
            if not entry.is_dir():
                continue

            # Canonical structure: Last_First
            split = split_player_dir_name(entry.name)
            if split:
                first_name, last_name = split
                if not self.is_allowed_player(first_name, last_name):
                    continue
                profile = load_player_profile(first_name, last_name, self.profiles_dir)
                if profile:
                    profiles.append(profile)
                continue

            # Legacy structure: Last/First
            for first_name_dir in entry.iterdir():
                if not first_name_dir.is_dir():
                    continue
                first_name = first_name_dir.name
                last_name = entry.name
                if not self.is_allowed_player(first_name, last_name):
                    continue
                ensure_player_dir(self.profiles_dir, first_name, last_name)
                profile = load_player_profile(first_name, last_name, self.profiles_dir)
                if profile:
                    profiles.append(profile)

        return profiles

