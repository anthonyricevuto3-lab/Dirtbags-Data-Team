"""
Pitch-level metrics calculations.

All metrics are transparent, reproducible, and explainable.
"""

import pandas as pd
import numpy as np
import pandas as pd
from typing import Optional, Tuple


def calculate_usage_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate usage rate for a pitch type.
    
    Formula: (Pitches of type) / (Total pitches) * 100
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Usage rate as percentage (0-100)
    """
    if pitch_type is None:
        return 100.0
    
    total_pitches = len(df)
    if total_pitches == 0:
        return 0.0
    
    pitch_count = len(df[df['pitch_type'] == pitch_type])
    return (pitch_count / total_pitches) * 100.0


def calculate_strike_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate strike rate for a pitch type.
    
    Formula: (Strikes) / (Total pitches) * 100
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Strike rate as percentage (0-100)
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return 0.0
    
    strikes = df['strike'].sum()
    total = len(df)
    return (strikes / total) * 100.0


def calculate_whiff_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate whiff rate for a pitch type.
    
    Formula: (Whiffs) / (Swings) * 100
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Whiff rate as percentage (0-100), or NaN if no swings
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    swings = df['swing'].sum()
    if swings == 0:
        return np.nan
    
    whiffs = df['whiff'].sum()
    return (whiffs / swings) * 100.0


def calculate_zone_whiff_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate zone whiff rate (whiffs on pitches in zone).
    
    Formula: (Whiffs in zone) / (Swings in zone) * 100
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Zone whiff rate as percentage (0-100), or NaN if no zone swings
    """
    if pitch_type:
        df = df[df["pitch_type"] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    # Use location masks (plate_x/plate_z) when available; fall back to zone numbers
    in_zone, _, _ = _location_masks(df)
    swings_in_zone = (df.get("swing", 0) & in_zone).sum()
    if swings_in_zone == 0:
        return np.nan
    
    whiffs_in_zone = (df.get("whiff", 0) & in_zone).sum()
    return (whiffs_in_zone / swings_in_zone) * 100.0


def calculate_out_of_zone_whiff_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate out-of-zone whiff rate (whiffs on pitches out of zone).
    
    Formula: (Whiffs out of zone) / (Swings out of zone) * 100
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Out-of-zone whiff rate as percentage (0-100), or NaN if no out-of-zone swings
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Out of zone pitches (zone 0 or NaN)
    ooz_df = df[(df['zone'] == 0) | (df['zone'].isna())]
    ooz_swings = ooz_df['swing'].sum()
    
    if ooz_swings == 0:
        return np.nan
    
    ooz_whiffs = ooz_df['whiff'].sum()
    return (ooz_whiffs / ooz_swings) * 100.0


def _location_masks(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Return boolean masks for in-zone, heart, and shadow using location if
    available; fall back to zone grid numbers otherwise.
    
    Heart is the core of the strike zone; shadow is the edge band inside the
    zone. These align with the definitions shared in the reports.
    """
    if "plate_x" in df.columns and "plate_z" in df.columns:
        px = pd.to_numeric(df["plate_x"], errors="coerce")
        pz = pd.to_numeric(df["plate_z"], errors="coerce")
        valid = px.notna() & pz.notna()
        # Strike zone extents (inches)
        strike_left, strike_right = -8.5, 8.5
        strike_bottom, strike_top = 18.0, 42.0
        # Heart (core) extents (tighter box)
        heart_left, heart_right = -6.0, 6.0
        heart_bottom, heart_top = 24.0, 36.0

        in_zone = valid & px.between(strike_left, strike_right) & pz.between(strike_bottom, strike_top)
        in_heart = valid & px.between(heart_left, heart_right) & pz.between(heart_bottom, heart_top)
        in_shadow = in_zone & ~in_heart
        return in_zone, in_heart, in_shadow

    # Fallback to zone grid numbers if plate location is missing
    zone = df.get("zone", pd.Series([], dtype="Int64"))
    in_zone = zone.between(1, 9, inclusive="both")
    # Heart = middle of the zone; Shadow = edges of the zone
    heart_zones = [5]
    shadow_zones = [1, 2, 3, 4, 6, 7, 8, 9]
    in_heart = zone.isin(heart_zones)
    in_shadow = zone.isin(shadow_zones)
    return in_zone, in_heart, in_shadow


def calculate_zone_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate zone rate (pitches in strike zone).
    
    Formula: (Pitches in zone) / (Total pitches) * 100
    """
    if pitch_type:
        df = df[df["pitch_type"] == pitch_type]
    
    total = len(df)
    if total == 0:
        return 0.0
    
    in_zone, _, _ = _location_masks(df)
    return (in_zone.sum() / total) * 100.0


def calculate_heart_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate heart rate (pitches in heart of zone).
    
    Heart = core of the strike zone (tight inner box).
    
    Formula: (Heart pitches) / (Total pitches) * 100
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    total = len(df)
    if total == 0:
        return 0.0
    
    _, in_heart, _ = _location_masks(df)
    return (in_heart.sum() / total) * 100.0


def calculate_shadow_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate shadow rate (pitches in shadow zone - edge of zone).
    
    Shadow = edge band of the strike zone (inside the zone, excluding heart).
    
    Formula: (Shadow pitches) / (Total pitches) * 100
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    total = len(df)
    if total == 0:
        return 0.0
    
    _, _, in_shadow = _location_masks(df)
    return (in_shadow.sum() / total) * 100.0


def calculate_chase_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate chase rate (swings on pitches out of zone).
    
    Formula: (Swings out of zone) / (Pitches out of zone) * 100
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Chase rate as percentage (0-100), or NaN if no out-of-zone pitches
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Out of zone pitches
    ooz_df = df[(df['zone'] == 0) | (df['zone'].isna())]
    
    if len(ooz_df) == 0:
        return np.nan
    
    ooz_swings = ooz_df['swing'].sum()
    return (ooz_swings / len(ooz_df)) * 100.0


def calculate_swing_rate(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate swing rate (swings on all pitches).
    
    Formula: (Swings) / (Total pitches) * 100
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Swing rate as percentage (0-100)
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return 0.0
    
    swings = df['swing'].sum()
    total = len(df)
    return (swings / total) * 100.0


def calculate_putaway_proxy(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate putaway proxy (strikeouts on 2-strike pitches).
    
    Simple proxy: (Strikeouts) / (2-strike pitches) * 100
    
    Note: This is a proxy metric. True putaway rate requires outcome data.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Putaway proxy as percentage (0-100), or NaN if no 2-strike pitches
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # 2-strike pitches
    two_strike_df = df[df['strikes'] == 2]
    
    if len(two_strike_df) == 0:
        return np.nan
    
    # This is a simplified proxy - actual putaway would need outcome data
    # For now, we'll use whiff rate on 2-strike pitches as proxy
    two_strike_swings = two_strike_df['swing'].sum()
    if two_strike_swings == 0:
        return np.nan
    
    two_strike_whiffs = two_strike_df['whiff'].sum()
    return (two_strike_whiffs / two_strike_swings) * 100.0

