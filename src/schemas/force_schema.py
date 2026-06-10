"""
Force plate data schema definition and cleaning functions.

Canonical schema for force plate CSV exports.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ForceSchema:
    """Canonical force plate data schema."""
    
    # Required columns
    REQUIRED_COLUMNS = {
        'pitch_number': int,         # Sequential pitch number
        'pitcher_id': str,           # Pitcher identifier
        'timestamp': float,          # Timestamp (seconds)
        'lead_leg_force': float,     # Lead leg force (N or lbs)
        'trail_leg_force': float,    # Trail leg force (N or lbs)
        'total_force': float,        # Total force (N or lbs)
        'force_peak': float,         # Peak force (N or lbs)
        'force_peak_time': float,    # Time to peak force (seconds)
    }
    
    # Optional columns
    OPTIONAL_COLUMNS = {
        'lead_leg_impulse': float,   # Lead leg impulse
        'trail_leg_impulse': float,  # Trail leg impulse
        'total_impulse': float,      # Total impulse
        'force_rate': float,          # Rate of force development
        'stance_width': float,       # Stance width (inches or cm)
        'knee_angle': float,         # Knee angle (degrees)
    }
    
    # Column mapping from common export names
    COLUMN_MAPPING = {
        'Pitcher': 'pitcher_id',
        'PitcherId': 'pitcher_id',
        'PitchNo': 'pitch_number',
        'Pitch Number': 'pitch_number',
        'Time': 'timestamp',
        'Timestamp': 'timestamp',
        'LeadLeg': 'lead_leg_force',
        'TrailLeg': 'trail_leg_force',
        'TotalForce': 'total_force',
        'PeakForce': 'force_peak',
        'PeakTime': 'force_peak_time',
    }
    
    UNITS = {
        'lead_leg_force': 'N or lbs',
        'trail_leg_force': 'N or lbs',
        'total_force': 'N or lbs',
        'force_peak': 'N or lbs',
        'force_peak_time': 'seconds',
        'timestamp': 'seconds',
    }


def clean_force(df: pd.DataFrame, strict: bool = False) -> pd.DataFrame:
    """
    Clean and normalize force plate CSV data to canonical schema.
    
    Args:
        df: Raw force plate DataFrame
        strict: If True, raise error on missing required columns
        
    Returns:
        Cleaned DataFrame with canonical column names and types
    """
    df = df.copy()
    
    # Map column names
    rename_map = {}
    for old_name, new_name in ForceSchema.COLUMN_MAPPING.items():
        if old_name in df.columns:
            rename_map[old_name] = new_name
    
    df = df.rename(columns=rename_map)
    
    # Handle missing columns
    missing_required = []
    for col, dtype in ForceSchema.REQUIRED_COLUMNS.items():
        if col not in df.columns:
            missing_required.append(col)
    
    if missing_required and strict:
        raise ValueError(f"Missing required columns: {missing_required}")
    elif missing_required:
        logger.warning(f"Missing optional columns (will be filled with NaN): {missing_required}")
        for col in missing_required:
            df[col] = None
    
    # Ensure required columns exist
    for col, dtype in ForceSchema.REQUIRED_COLUMNS.items():
        if col not in df.columns:
            df[col] = None
    
    # Type conversions
    for col, dtype in ForceSchema.REQUIRED_COLUMNS.items():
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
    
    # Handle optional columns
    for col, dtype in ForceSchema.OPTIONAL_COLUMNS.items():
        if col in df.columns:
            try:
                if dtype == float:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception as e:
                logger.warning(f"Could not convert optional {col} to {dtype}: {e}")
    
    # Select canonical columns
    canonical_cols = list(ForceSchema.REQUIRED_COLUMNS.keys())
    for col in ForceSchema.OPTIONAL_COLUMNS.keys():
        if col in df.columns:
            canonical_cols.append(col)
    
    df = df[canonical_cols]
    
    return df


def validate_force(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validate force plate DataFrame against canonical schema.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required columns
    for col in ForceSchema.REQUIRED_COLUMNS.keys():
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")
    
    # Check data types
    for col, expected_dtype in ForceSchema.REQUIRED_COLUMNS.items():
        if col in df.columns:
            if expected_dtype == int:
                if not pd.api.types.is_integer_dtype(df[col]):
                    errors.append(f"Column {col} should be int, got {df[col].dtype}")
            elif expected_dtype == float:
                if not pd.api.types.is_float_dtype(df[col]):
                    errors.append(f"Column {col} should be float, got {df[col].dtype}")
    
    return len(errors) == 0, errors

