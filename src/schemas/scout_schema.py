"""
Scouting data schema definition and cleaning functions.

Canonical schema for external scouting data (Trumedia, Sydex, etc.).
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ScoutSchema:
    """Canonical scouting data schema."""
    
    # Hitter profile schema
    HITTER_COLUMNS = {
        'player_id': str,            # Player identifier
        'player_name': str,          # Player name
        'handedness': str,           # Bats: L, R, S
        'approach': str,             # Approach description
        'chase_rate': float,         # Chase rate (%)
        'swing_rate': float,         # Swing rate (%)
        'zone_contact_rate': float,  # Zone contact rate (%)
        'pull_rate': float,          # Pull rate (%)
        'oppo_rate': float,          # Opposite field rate (%)
        'ground_ball_rate': float,   # Ground ball rate (%)
        'fly_ball_rate': float,      # Fly ball rate (%)
        'line_drive_rate': float,    # Line drive rate (%)
        'strength_zones': str,       # Strength zones (comma-separated)
        'weakness_zones': str,       # Weakness zones (comma-separated)
        'two_strike_approach': str,  # Two-strike approach notes
        'risp_tendencies': str,      # RISP tendencies
    }
    
    # Pitcher profile schema
    PITCHER_COLUMNS = {
        'player_id': str,            # Player identifier
        'player_name': str,          # Player name
        'handedness': str,           # Throws: L, R
        'arsenal': str,              # Arsenal description (comma-separated pitch types)
        'fastball_velocity': float,  # Fastball velocity (mph)
        'fastball_usage': float,     # Fastball usage (%)
        'breaking_ball_usage': float, # Breaking ball usage (%)
        'offspeed_usage': float,     # Offspeed usage (%)
        'putaway_pitch': str,        # Primary putaway pitch
        'first_inning_plan': str,    # First inning plan notes
        'strengths': str,            # Strengths description
        'weaknesses': str,           # Weaknesses description
    }
    
    # Usage pattern schema (by count, situation, etc.)
    USAGE_PATTERN_COLUMNS = {
        'player_id': str,            # Player identifier
        'count': str,                # Count (e.g., "0-0", "2-2")
        'situation': str,            # Situation (e.g., "RISP", "2-out")
        'pitch_type': str,           # Pitch type
        'usage_rate': float,         # Usage rate (%)
        'strike_rate': float,        # Strike rate (%)
        'whiff_rate': float,         # Whiff rate (%)
    }
    
    # Column mapping from common export names
    COLUMN_MAPPING = {
        'Player': 'player_name',
        'PlayerId': 'player_id',
        'Name': 'player_name',
        'Bats': 'handedness',
        'Throws': 'handedness',
        'Chase%': 'chase_rate',
        'Swing%': 'swing_rate',
        'ZoneContact%': 'zone_contact_rate',
        'Pull%': 'pull_rate',
        'Oppo%': 'oppo_rate',
        'GB%': 'ground_ball_rate',
        'FB%': 'fly_ball_rate',
        'LD%': 'line_drive_rate',
        'FB_Vel': 'fastball_velocity',
        'FB%': 'fastball_usage',
    }


def clean_scout(df: pd.DataFrame, data_type: str = 'hitter', strict: bool = False) -> pd.DataFrame:
    """
    Clean and normalize scouting CSV data to canonical schema.
    
    Args:
        df: Raw scouting DataFrame
        data_type: Type of data ('hitter', 'pitcher', 'usage_pattern')
        strict: If True, raise error on missing required columns
        
    Returns:
        Cleaned DataFrame with canonical column names and types
    """
    df = df.copy()
    
    # Map column names
    rename_map = {}
    for old_name, new_name in ScoutSchema.COLUMN_MAPPING.items():
        if old_name in df.columns:
            rename_map[old_name] = new_name
    
    df = df.rename(columns=rename_map)
    
    # Select appropriate schema based on data type
    if data_type == 'hitter':
        required_cols = ScoutSchema.HITTER_COLUMNS
    elif data_type == 'pitcher':
        required_cols = ScoutSchema.PITCHER_COLUMNS
    elif data_type == 'usage_pattern':
        required_cols = ScoutSchema.USAGE_PATTERN_COLUMNS
    else:
        raise ValueError(f"Unknown data_type: {data_type}. Must be 'hitter', 'pitcher', or 'usage_pattern'")
    
    # Handle missing columns
    missing_required = []
    for col, dtype in required_cols.items():
        if col not in df.columns:
            missing_required.append(col)
    
    if missing_required and strict:
        raise ValueError(f"Missing required columns: {missing_required}")
    elif missing_required:
        logger.warning(f"Missing optional columns (will be filled with NaN): {missing_required}")
        for col in missing_required:
            df[col] = None
    
    # Ensure required columns exist
    for col, dtype in required_cols.items():
        if col not in df.columns:
            df[col] = None
    
    # Type conversions
    for col, dtype in required_cols.items():
        if col in df.columns:
            try:
                if dtype == int:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                elif dtype == float:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif dtype == str:
                    df[col] = df[col].astype(str)
            except Exception as e:
                logger.warning(f"Could not convert {col} to {dtype}: {e}")
    
    # Select canonical columns
    canonical_cols = list(required_cols.keys())
    df = df[canonical_cols]
    
    return df


def validate_scout(df: pd.DataFrame, data_type: str = 'hitter') -> Tuple[bool, List[str]]:
    """
    Validate scouting DataFrame against canonical schema.
    
    Args:
        df: DataFrame to validate
        data_type: Type of data ('hitter', 'pitcher', 'usage_pattern')
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Select appropriate schema
    if data_type == 'hitter':
        required_cols = ScoutSchema.HITTER_COLUMNS
    elif data_type == 'pitcher':
        required_cols = ScoutSchema.PITCHER_COLUMNS
    elif data_type == 'usage_pattern':
        required_cols = ScoutSchema.USAGE_PATTERN_COLUMNS
    else:
        return False, [f"Unknown data_type: {data_type}"]
    
    # Check required columns
    for col in required_cols.keys():
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")
    
    # Check data types
    for col, expected_dtype in required_cols.items():
        if col in df.columns:
            if expected_dtype == float:
                if not pd.api.types.is_float_dtype(df[col]):
                    errors.append(f"Column {col} should be float, got {df[col].dtype}")
    
    return len(errors) == 0, errors

