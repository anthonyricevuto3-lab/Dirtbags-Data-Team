"""
Movement and physical metrics calculations.
"""

import pandas as pd
import numpy as np
from typing import Optional


def calculate_ivb_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average induced vertical break.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average IVB in inches, or NaN if no data
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    ivb_values = df['ivb'].dropna()
    if len(ivb_values) == 0:
        return np.nan
    
    return ivb_values.mean()


def calculate_hb_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average horizontal break.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average HB in inches, or NaN if no data
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    hb_values = df['hb'].dropna()
    if len(hb_values) == 0:
        return np.nan
    
    return hb_values.mean()


def calculate_spin_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average spin rate.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average spin rate in rpm, or NaN if no data
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    spin_values = df['spin_rate'].dropna()
    if len(spin_values) == 0:
        return np.nan
    
    return spin_values.mean()


def calculate_extension_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average extension.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average extension in feet, or NaN if no data
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    ext_values = df['extension'].dropna()
    if len(ext_values) == 0:
        return np.nan
    
    return ext_values.mean()


def calculate_velocity_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average velocity.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average velocity in mph, or NaN if no data
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    vel_values = df['velocity'].dropna()
    if len(vel_values) == 0:
        return np.nan
    
    return vel_values.mean()


def calculate_velocity_max(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate maximum velocity.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Maximum velocity in mph, or NaN if no data
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    vel_values = df['velocity'].dropna()
    if len(vel_values) == 0:
        return np.nan
    
    return vel_values.max()


def calculate_release_height_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average release height.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average release height in feet, or NaN if no data
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    rh_values = df['release_height'].dropna()
    if len(rh_values) == 0:
        return np.nan
    
    return rh_values.mean()


def calculate_release_side_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average release side.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average release side in feet, or NaN if no data
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if len(df) == 0:
        return np.nan
    
    rs_values = df['release_side'].dropna()
    if len(rs_values) == 0:
        return np.nan
    
    return rs_values.mean()

