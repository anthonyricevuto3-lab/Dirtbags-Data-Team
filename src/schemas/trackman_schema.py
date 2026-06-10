"""
Trackman data schema definition and cleaning functions.

Canonical schema for Trackman CSV exports.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TrackmanSchema:
    """Canonical Trackman data schema."""
    
    # Required columns with standardized names
    REQUIRED_COLUMNS = {
        'pitch_type': str,           # Pitch type (e.g., "Fastball", "Slider")
        'pitch_number': int,         # Sequential pitch number
        'batter_id': str,            # Batter identifier
        'pitcher_id': str,           # Pitcher identifier
        'inning': int,               # Inning number
        'balls': int,                # Ball count
        'strikes': int,              # Strike count
        'outs': int,                 # Outs in inning
        'pitch_call': str,           # Call (e.g., "BallCalled", "StrikeCalled", "InPlay")
        'strike': bool,              # Whether pitch was a strike
        'swing': bool,               # Whether batter swung
        'whiff': bool,               # Whether batter whiffed
        'velocity': float,           # Pitch velocity (mph)
        'spin_rate': float,          # Spin rate (rpm)
        'ivb': float,                # Induced vertical break (inches)
        'hb': float,                 # Horizontal break (inches)
        'extension': float,          # Extension (feet)
        'release_height': float,     # Release height (feet)
        'release_side': float,       # Release side (feet)
        'plate_x': float,            # Horizontal location at plate (inches)
        'plate_z': float,            # Vertical location at plate (inches)
        'zone': int,                 # Strike zone number (1-9, 0 if out of zone)
        'launch_angle': float,       # Launch angle (degrees, NaN if no contact)
        'exit_velocity': float,      # Exit velocity (mph, NaN if no contact)
        'hit_type': str,             # Hit type (e.g., "GroundBall", "LineDrive", "FlyBall", "PopUp")
        'spray_angle': float,        # Spray angle (degrees, NaN if no contact)
        'distance': float,           # Hit distance (feet, NaN if no contact)
    }
    
    # Optional columns (may not always be present)
    OPTIONAL_COLUMNS = {
        'spin_axis': float,          # Spin axis (degrees)
        'tilt': float,               # Tilt (degrees)
        'vaa': float,                # Vertical approach angle (degrees)
        'haa': float,                # Horizontal approach angle (degrees)
        'release_speed': float,      # Release speed (mph, alternative to velocity)
        'pfx_x': float,              # Horizontal movement (inches, alternative to hb)
        'pfx_z': float,              # Vertical movement (inches, alternative to ivb)
        'batter_side': str,          # Batter handedness
        'direction': float,          # Horizontal batted-ball angle from y-axis (degrees)
        'bearing': float,            # Landing horizontal angle (deg)
        'positionat110x': float,     # X at 110ft
        'positionat110y': float,     # Y at 110ft
        'date': str,                 # Game date if provided
        'game_id': str,              # Game identifier if provided
        'KorBB': str,                # Trackman strikeout/walk indicator (for K/BB)
        'tagged_hit_type': str,      # TaggedHitType raw label
        'pa_of_inning': int,         # PA number within inning (PAofInning)
        'top_bottom': str,           # Top or Bottom of inning (Top/Bottom)
        'outs_on_play': int,         # Outs recorded on the play (OutsOnPlay)
        'play_result': str,          # At-bat outcome (PlayResult: Out, Single, etc.)
        'runs_scored': int,           # Runs scored on the play (RunsScored)
    }
    
    # Column mapping from common Trackman export names to canonical names
    COLUMN_MAPPING = {
        # Pitch identification
        'Pitcher': 'pitcher_id',
        'Batter': 'batter_id',
        'PitcherId': 'pitcher_id',
        'BatterId': 'batter_id',
        'PitchNo': 'pitch_number',
        'Pitch Number': 'pitch_number',
        
        # Pitch type
        'TaggedPitchType': 'pitch_type',
        'Pitch Type': 'pitch_type',
        'AutoPitchType': 'pitch_type',
        'PlayResult': 'play_result',
        'Play Result': 'play_result',
        'HitResult': 'play_result',
        'Hit Result': 'play_result',
        'Result': 'play_result',
        'TaggedHitType': 'tagged_hit_type',
        'BatterSide': 'batter_side',
        'Batter Side': 'batter_side',
        'Stand': 'batter_side',
        
        # Count
        'Balls': 'balls',
        'Strikes': 'strikes',
        'Outs': 'outs',
        'Inning': 'inning',
        'PAofInning': 'pa_of_inning',
        'Top/Bottom': 'top_bottom',
        'OutsOnPlay': 'outs_on_play',
        'RunsScored': 'runs_scored',

        # Outcomes
        'PitchCall': 'pitch_call',
        'Pitch Call': 'pitch_call',
        'Strike': 'strike',
        'Swing': 'swing',
        'Whiff': 'whiff',
        
        # Velocity and spin
        'RelSpeed': 'velocity',
        'Rel Speed': 'velocity',
        'Velocity': 'velocity',
        'SpinRate': 'spin_rate',
        'Spin Rate': 'spin_rate',
        'Spin': 'spin_rate',
        
        # Movement
        'InducedVertBreak': 'ivb',
        'IVB': 'ivb',
        'VertBreak': 'ivb',
        'HorzBreak': 'hb',
        'HB': 'hb',
        'HorizontalBreak': 'hb',
        'PfxX': 'hb',
        'PfxZ': 'ivb',
        
        # Release
        'Extension': 'extension',
        'RelHeight': 'release_height',
        'Release Height': 'release_height',
        'RelSide': 'release_side',
        'Release Side': 'release_side',
        
        # Location
        'PlateLocSide': 'plate_x',
        'PlateLocHeight': 'plate_z',
        'Plate X': 'plate_x',
        'Plate Z': 'plate_z',
        'Zone': 'zone',
        
        # Batted ball
        'LaunchAngle': 'launch_angle',
        'Launch Angle': 'launch_angle',
        'Angle': 'launch_angle',
        'ExitSpeed': 'exit_velocity',
        'Exit Velocity': 'exit_velocity',
        'HitType': 'hit_type',
        'Hit Type': 'hit_type',
        'SprayAngle': 'spray_angle',
        'Distance': 'distance',
        'Direction': 'direction',
        'Bearing': 'bearing',
        'PositionAt110X': 'positionat110x',
        'PositionAt110Y': 'positionat110y',
        'Date': 'date',
        'GameID': 'game_id',
        'GameId': 'game_id',
        'Game ID': 'game_id',
        
        # Advanced
        'SpinAxis': 'spin_axis',
        'Tilt': 'tilt',
        'VAA': 'vaa',
        'HAA': 'haa',
        'KorBB': 'KorBB',
    }
    
    # Units (for documentation)
    UNITS = {
        'velocity': 'mph',
        'spin_rate': 'rpm',
        'ivb': 'inches',
        'hb': 'inches',
        'extension': 'feet',
        'release_height': 'feet',
        'release_side': 'feet',
        'plate_x': 'inches',
        'plate_z': 'inches',
        'launch_angle': 'degrees',
        'exit_velocity': 'mph',
        'spray_angle': 'degrees',
        'distance': 'feet',
    }


def clean_trackman(df: pd.DataFrame, strict: bool = False) -> pd.DataFrame:
    """
    Clean and normalize Trackman CSV data to canonical schema.
    
    Args:
        df: Raw Trackman DataFrame
        strict: If True, raise error on missing required columns
        
    Returns:
        Cleaned DataFrame with canonical column names and types
    """
    df = df.copy()
    
    # Track whether raw PlateLocSide/Height (feet) are present so we can convert to inches
    raw_plate_side_in_feet = 'PlateLocSide' in df.columns
    raw_plate_height_in_feet = 'PlateLocHeight' in df.columns

    # Map column names to canonical names
    rename_map = {}
    for old_name, new_name in TrackmanSchema.COLUMN_MAPPING.items():
        if old_name in df.columns:
            rename_map[old_name] = new_name
    
    df = df.rename(columns=rename_map)
    
    # Remove duplicate columns if any (keep first occurrence)
    df = df.loc[:, ~df.columns.duplicated()]

    # hit_type: prefer tagged_hit_type (GroundBall, etc.), fallback to play_result (Single, Out, etc.) for backward compatibility
    if 'hit_type' not in df.columns or df['hit_type'].isna().all():
        if 'tagged_hit_type' in df.columns:
            df['hit_type'] = df['tagged_hit_type']
        elif 'play_result' in df.columns:
            df['hit_type'] = df['play_result']
    
    # Derive strike, swing, whiff from PitchCall if columns don't exist
    if 'pitch_call' in df.columns:
        pitch_call_col = df['pitch_call']
        if isinstance(pitch_call_col, pd.Series):
            if 'strike' not in df.columns:
                df['strike'] = pitch_call_col.astype(str).str.contains('Strike', case=False, na=False)
            if 'swing' not in df.columns:
                df['swing'] = pitch_call_col.astype(str).str.contains('Swinging|Foul|InPlay', case=False, na=False, regex=True)
            if 'whiff' not in df.columns:
                df['whiff'] = pitch_call_col.astype(str).str.contains('StrikeSwinging', case=False, na=False)
    
    # Derive zone from PlateLocHeight/PlateLocSide if Zone column doesn't exist
    # (This is a simplified zone calculation - actual zone requires batter height)
    if 'zone' not in df.columns and 'plate_z' in df.columns and 'plate_x' in df.columns:
        # Placeholder - would need actual zone calculation
        df['zone'] = 0  # Default to out of zone
    
    # Handle missing columns
    missing_required = []
    for col, dtype in TrackmanSchema.REQUIRED_COLUMNS.items():
        if col not in df.columns:
            missing_required.append(col)
    
    if missing_required and strict:
        raise ValueError(f"Missing required columns: {missing_required}")
    elif missing_required:
        logger.warning(f"Missing optional columns (will be filled with NaN): {missing_required}")
        for col in missing_required:
            df[col] = None
    
    # Ensure required columns exist (create with NaN if missing and not strict)
    for col, dtype in TrackmanSchema.REQUIRED_COLUMNS.items():
        if col not in df.columns:
            df[col] = None
    
    # Type conversions
    for col, dtype in TrackmanSchema.REQUIRED_COLUMNS.items():
        if col in df.columns:
            try:
                if dtype == bool:
                    # Handle boolean columns (may come as strings or 0/1)
                    df[col] = df[col].astype(str).str.lower().isin(['true', '1', 'yes', 't'])
                elif dtype == int:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                elif dtype == float:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif dtype == str:
                    df[col] = df[col].astype(str)
            except Exception as e:
                logger.warning(f"Could not convert {col} to {dtype}: {e}")
    
    # Handle optional columns
    for col, dtype in TrackmanSchema.OPTIONAL_COLUMNS.items():
        if col in df.columns:
            try:
                if dtype == float:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif dtype == int:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                elif dtype == str:
                    df[col] = df[col].astype(str).replace('nan', pd.NA)
            except Exception as e:
                logger.warning(f"Could not convert optional {col} to {dtype}: {e}")
    
    # Remove duplicate columns if any (keep first occurrence)
    df = df.loc[:, ~df.columns.duplicated()]

    # Convert plate_x / plate_z from feet to inches when sourced from PlateLocSide/Height
    try:
        if raw_plate_side_in_feet and 'plate_x' in df.columns:
            df['plate_x'] = pd.to_numeric(df['plate_x'], errors='coerce') * 12.0
        if raw_plate_height_in_feet and 'plate_z' in df.columns:
            df['plate_z'] = pd.to_numeric(df['plate_z'], errors='coerce') * 12.0
    except Exception as e:
        logger.warning(f"Could not convert plate loc from feet to inches: {e}")
    
    # Standardize pitch type names
    if 'pitch_type' in df.columns:
        try:
            col = df['pitch_type']
            if isinstance(col, pd.Series):
                if pd.api.types.is_string_dtype(col) or col.dtype == 'object':
                    standardized = col.astype(str).str.strip().str.title()
                    # Normalize common variants to a concise label
                    pitch_map = {
                        '2 Seam Fastball': '2-Seam Fastball',
                        'Two Seam Fastball': '2-Seam Fastball',
                        'Two-Seam Fastball': '2-Seam Fastball',
                        '2 Seam': '2-Seam Fastball',
                        'Two Seam': '2-Seam Fastball',
                        'Twoseamfastball': '2-Seam Fastball',
                        'Twoseam': '2-Seam Fastball',
                        'Two-Seamfastball': '2-Seam Fastball',
                        'Two-Seam': '2-Seam Fastball',
                    }
                    df['pitch_type'] = standardized.replace(pitch_map)
                    df['pitch_type'] = df['pitch_type'].replace(['Undefined', 'None', '', 'Nan', 'Na'], pd.NA)
        except Exception as e:
            logger.warning(f"Could not standardize pitch_type: {e}")
    
    # Standardize pitch call names and force batted-ball events to "InPlay"
    if 'pitch_call' in df.columns:
        try:
            col = df['pitch_call']
            if isinstance(col, pd.Series):
                if pd.api.types.is_string_dtype(col) or col.dtype == 'object':
                    pc = col.astype(str).str.strip()
                    low = pc.str.lower()
                    replacements = {
                        'inplay': 'InPlay',
                        'in play': 'InPlay',
                        'in play, out(s)': 'InPlay',
                        'in play, out': 'InPlay',
                        'in play, runs': 'InPlay',
                        'in play, no out': 'InPlay',
                        'in play (runner out)': 'InPlay',
                        'in play (out)': 'InPlay',
                        'ballinplay': 'InPlay',
                        'ball in play': 'InPlay',
                        'ball in play (fielded)': 'InPlay',
                        'hit': 'InPlay',
                    }
                    mapped = low.map(replacements).fillna(pc)
                    # If pitch_call is empty/NaN but we have contact metrics, treat as InPlay
                    contact_mask = (
                        mapped.isna()
                        | (mapped.str.len() == 0)
                        | (mapped.str.lower() == 'nan')
                    ) & (
                        df.get('hit_type').notna()
                        | df.get('launch_angle').notna()
                        | df.get('exit_velocity').notna()
                        | df.get('spray_angle').notna()
                    )
                    mapped.loc[contact_mask] = 'InPlay'
                    df['pitch_call'] = mapped
        except Exception as e:
            logger.warning(f"Could not standardize pitch_call: {e}")
    
    # Standardize hit type names
    if 'hit_type' in df.columns:
        try:
            col = df['hit_type']
            if isinstance(col, pd.Series):
                if pd.api.types.is_string_dtype(col) or col.dtype == 'object':
                    df['hit_type'] = col.astype(str).str.strip()
                    df['hit_type'] = df['hit_type'].replace(['Undefined', 'None', '', 'Nan', 'Na'], pd.NA)
        except Exception as e:
            logger.warning(f"Could not standardize hit_type: {e}")
    
    # Select only canonical columns (required + optional that exist)
    canonical_cols = list(TrackmanSchema.REQUIRED_COLUMNS.keys())
    for col in TrackmanSchema.OPTIONAL_COLUMNS.keys():
        if col in df.columns:
            canonical_cols.append(col)
    
    df = df[canonical_cols]
    
    return df


def validate_trackman(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate Trackman DataFrame against canonical schema.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required columns
    for col in TrackmanSchema.REQUIRED_COLUMNS.keys():
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")
    
    # Check data types
    for col, expected_dtype in TrackmanSchema.REQUIRED_COLUMNS.items():
        if col in df.columns:
            if expected_dtype == bool:
                if not df[col].dtype == bool:
                    errors.append(f"Column {col} should be bool, got {df[col].dtype}")
            elif expected_dtype == int:
                if not pd.api.types.is_integer_dtype(df[col]):
                    errors.append(f"Column {col} should be int, got {df[col].dtype}")
            elif expected_dtype == float:
                if not pd.api.types.is_float_dtype(df[col]):
                    errors.append(f"Column {col} should be float, got {df[col].dtype}")
    
    return len(errors) == 0, errors

