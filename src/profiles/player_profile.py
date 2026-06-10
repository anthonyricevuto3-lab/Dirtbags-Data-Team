"""
Player profile data structure.

Stores and accumulates player statistics across multiple outings.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from .paths import ensure_player_dir, get_legacy_player_dir, get_player_dir


class PlayerProfile:
    """Stores cumulative player statistics."""
    
    def __init__(self, first_name: str, last_name: str):
        self.first_name = first_name.strip()
        self.last_name = last_name.strip()
        self.full_name = f"{self.first_name} {self.last_name}"
        self.player_id: Optional[str] = None
        self.position: Optional[str] = None
        self.bats: Optional[str] = None
        self.throws: Optional[str] = None
        
        # Track all outings
        self.outings: List[Dict] = []
        
        # Cumulative statistics (will be calculated)
        self.cumulative_stats: Optional[pd.DataFrame] = None
        
        # Metadata
        self.created_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()
        self.total_outings = 0
        self.total_pitches = 0

    def _recompute_totals(self):
        self.total_outings = len(self.outings)
        self.total_pitches = sum(len(o['data']) for o in self.outings)
        # Set last_updated to latest outing date if available, else keep existing
        latest_dt = None
        for o in self.outings:
            meta = o.get('metadata', {})
            dstr = meta.get('date')
            if not dstr:
                continue
            try:
                dt = datetime.fromisoformat(str(dstr))
            except Exception:
                try:
                    dt = datetime.strptime(str(dstr), "%Y-%m-%d")
                except Exception:
                    dt = None
            if dt and (latest_dt is None or dt > latest_dt):
                latest_dt = dt
        if latest_dt:
            self.last_updated = latest_dt.isoformat()
    
    def add_outing(self, df: pd.DataFrame, metadata: Dict):
        """
        Add a new outing to the profile.
        Skips adding if an outing with the same source_path, or same game/date already exists.
        """
        src = metadata.get('source_path')
        new_date = metadata.get('date')
        new_game = metadata.get('game_id')
        for existing in self.outings:
            em = existing.get('metadata', {})
            if src and em.get('source_path') == src:
                return  # duplicate source
            if new_game and em.get('game_id') == new_game:
                return  # duplicate game id
            if new_date and em.get('date') == new_date and not (new_game or em.get('game_id')):
                return  # duplicate date when no game id provided
        outing = {
            'data': df,
            'metadata': metadata,
            'added_at': datetime.now().isoformat(),
        }
        self.outings.append(outing)
        self._recompute_totals()
        # Persist player_id if present in metadata and not already stored
        if not self.player_id and metadata.get('player_id'):
            self.player_id = str(metadata['player_id'])
        # Persist roster info if provided
        if not self.position and metadata.get('position'):
            self.position = metadata['position']
        if not self.bats and metadata.get('bats'):
            self.bats = metadata['bats']
        if not self.throws and metadata.get('throws'):
            self.throws = metadata['throws']
    
    def get_cumulative_data(self) -> pd.DataFrame:
        """Get combined DataFrame of all outings."""
        if not self.outings:
            return pd.DataFrame()
        
        all_data = []
        for outing in self.outings:
            all_data.append(outing['data'])
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame()
    
    def to_dict(self) -> Dict:
        """Convert profile to dictionary for JSON serialization."""
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'player_id': self.player_id,
            'position': self.position,
            'bats': self.bats,
            'throws': self.throws,
            'created_at': self.created_at,
            'last_updated': self.last_updated,
            'total_outings': self.total_outings,
            'total_pitches': self.total_pitches,
            'outings_metadata': [o['metadata'] for o in self.outings],
        }
    
    @classmethod
    def from_dict(cls, data: Dict, outings_data: List[pd.DataFrame]) -> 'PlayerProfile':
        """Reconstruct profile from dictionary."""
        profile = cls(data['first_name'], data['last_name'])
        profile.created_at = data.get('created_at', datetime.now().isoformat())
        profile.last_updated = data.get('last_updated', datetime.now().isoformat())
        profile.total_outings = data.get('total_outings', 0)
        profile.total_pitches = data.get('total_pitches', 0)
        profile.player_id = data.get('player_id')
        profile.position = data.get('position')
        profile.bats = data.get('bats')
        profile.throws = data.get('throws')
        
        # Reconstruct outings
        for i, (metadata, df) in enumerate(zip(data.get('outings_metadata', []), outings_data)):
            profile.outings.append({
                'data': df,
                'metadata': metadata,
                'added_at': metadata.get('added_at', datetime.now().isoformat()),
            })
        profile._recompute_totals()
        
        return profile


def save_player_profile(profile: PlayerProfile, profiles_dir: Path):
    """Save player profile to disk."""
    player_dir = ensure_player_dir(profiles_dir, profile.first_name, profile.last_name)

    # Ensure totals are accurate before saving
    profile._recompute_totals()
    
    # Remove existing outing CSVs to avoid duplicates before writing fresh
    for existing in player_dir.glob("outing_*.csv"):
        try:
            existing.unlink()
        except FileNotFoundError:
            pass

    # Save metadata
    metadata_file = player_dir / 'profile.json'
    with open(metadata_file, 'w') as f:
        json.dump(profile.to_dict(), f, indent=2)
    
    # Save each outing's data
    for i, outing in enumerate(profile.outings):
        outing_file = player_dir / f"outing_{i+1:03d}.csv"
        outing['data'].to_csv(outing_file, index=False)
    
    return player_dir


def load_player_profile(first_name: str, last_name: str, profiles_dir: Path) -> Optional[PlayerProfile]:
    """Load player profile from disk."""
    player_dir = get_player_dir(profiles_dir, first_name, last_name)
    legacy_dir = get_legacy_player_dir(profiles_dir, first_name, last_name)

    if not player_dir.exists() and legacy_dir.exists():
        # Migrate legacy structure on read
        try:
            legacy_dir.rename(player_dir)
        except Exception:
            player_dir = legacy_dir

    if not player_dir.exists():
        return None

    metadata_file = player_dir / 'profile.json'
    if not metadata_file.exists():
        return None

    # Load metadata
    with open(metadata_file, 'r') as f:
        data = json.load(f)
    
    # Load all outing CSVs
    outings_data = []
    outing_files = sorted(player_dir.glob('outing_*.csv'))
    for outing_file in outing_files:
        df = pd.read_csv(outing_file)
        outings_data.append(df)
    
    return PlayerProfile.from_dict(data, outings_data)

