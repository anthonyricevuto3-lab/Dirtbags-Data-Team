"""
Contact and batted ball metrics calculations.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict


def calculate_contact_outcomes(df: pd.DataFrame, pitch_type: Optional[str] = None) -> Dict[str, float]:
    """
    Calculate contact outcome rates (GB%, FB%, LD%, PU%) for a pitch type.
    
    Uses the total batted balls in play (BIP) for the pitch type as the
    denominator and counts how many of those BIP are ground balls, fly balls,
    line drives, or popups. If ``tagged_hit_type`` is available it is preferred
    for classification; otherwise falls back to ``hit_type``. Returns NaN when
    no BIP are available.
    """
    if pitch_type:
        df = df[df["pitch_type"] == pitch_type]

    bip_df = df[df["pitch_call"] == "InPlay"].copy()
    total_bip = len(bip_df)

    if total_bip == 0:
        return {
            "ground_ball_rate": np.nan,
            "fly_ball_rate": np.nan,
            "line_drive_rate": np.nan,
            "popup_rate": np.nan,
        }

    if "tagged_hit_type" in bip_df.columns:
        hit_types = bip_df["tagged_hit_type"].astype(str)
    elif "hit_type" in bip_df.columns:
        hit_types = bip_df["hit_type"].astype(str)
    else:
        return {
            "ground_ball_rate": np.nan,
            "fly_ball_rate": np.nan,
            "line_drive_rate": np.nan,
            "popup_rate": np.nan,
        }

    hit_types = hit_types.str.lower()
    ground_balls = hit_types.str.contains("ground", na=False).sum()
    fly_balls = hit_types.str.contains("fly", na=False).sum()
    line_drives = hit_types.str.contains("line", na=False).sum()
    popups = hit_types.str.contains("pop", na=False).sum()

    return {
        "ground_ball_rate": (ground_balls / total_bip) * 100.0,
        "fly_ball_rate": (fly_balls / total_bip) * 100.0,
        "line_drive_rate": (line_drives / total_bip) * 100.0,
        "popup_rate": (popups / total_bip) * 100.0,
    }


def calculate_spray_distribution(df: pd.DataFrame, pitch_type: Optional[str] = None) -> Dict[str, float]:
    """
    Calculate spray distribution (Pull%, Middle%, Oppo%) using total BIP as denominator.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Dictionary with 'pull_rate', 'middle_rate', 'oppo_rate'
        All values are percentages (0-100), or NaN if no batted balls
    """
    if pitch_type:
        df = df[df["pitch_type"] == pitch_type]

    # Batted balls in play
    bip_df = df[df["pitch_call"] == "InPlay"].copy()
    total_bip = len(bip_df)

    if total_bip == 0:
        return {
            "pull_rate": np.nan,
            "middle_rate": np.nan,
            "oppo_rate": np.nan,
        }

    # Spray angle source: prefer spray_angle, fall back to direction, then bearing
    spray_series = bip_df["spray_angle"] if "spray_angle" in bip_df.columns else pd.Series([], dtype=float)
    if spray_series.dropna().empty and "direction" in bip_df.columns:
        spray_series = bip_df["direction"]
    if spray_series.dropna().empty and "bearing" in bip_df.columns:
        spray_series = bip_df["bearing"]

    spray_angles = spray_series.dropna()

    if len(spray_angles) == 0:
        return {
            "pull_rate": np.nan,
            "middle_rate": np.nan,
            "oppo_rate": np.nan,
        }

    # Spray angle: negative = pull side, positive = oppo side
    # Typical ranges: Pull < -15°, Middle -15° to 15°, Oppo > 15°
    pull = (spray_angles < -15).sum()
    middle = ((spray_angles >= -15) & (spray_angles <= 15)).sum()
    oppo = (spray_angles > 15).sum()

    return {
        "pull_rate": (pull / total_bip) * 100.0,
        "middle_rate": (middle / total_bip) * 100.0,
        "oppo_rate": (oppo / total_bip) * 100.0,
    }


def calculate_launch_angle_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average launch angle.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average launch angle in degrees, or NaN if no batted balls
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Batted balls in play
    bip_df = df[df['pitch_call'] == 'InPlay']
    la_values = bip_df['launch_angle'].dropna()
    
    if len(la_values) == 0:
        return np.nan
    
    return la_values.mean()


def calculate_exit_velocity_avg(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate average exit velocity.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Average exit velocity in mph, or NaN if no batted balls
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Batted balls in play
    bip_df = df[df['pitch_call'] == 'InPlay']
    ev_values = bip_df['exit_velocity'].dropna()
    
    if len(ev_values) == 0:
        return np.nan
    
    return ev_values.mean()


def calculate_exit_velocity_max(df: pd.DataFrame, pitch_type: Optional[str] = None) -> float:
    """
    Calculate maximum exit velocity.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        
    Returns:
        Maximum exit velocity in mph, or NaN if no batted balls
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Batted balls in play
    bip_df = df[df['pitch_call'] == 'InPlay']
    ev_values = bip_df['exit_velocity'].dropna()
    
    if len(ev_values) == 0:
        return np.nan
    
    return ev_values.max()


def calculate_hard_hit_rate(df: pd.DataFrame, pitch_type: Optional[str] = None, threshold: float = 95.0) -> float:
    """
    Calculate hard hit rate (exit velocity >= threshold).
    
    Args:
        df: Trackman DataFrame
        pitch_type: Pitch type to calculate for (None = all pitches)
        threshold: Exit velocity threshold in mph (default 95)
        
    Returns:
        Hard hit rate as percentage (0-100), or NaN if no batted balls
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Batted balls in play
    bip_df = df[df['pitch_call'] == 'InPlay']
    ev_values = bip_df['exit_velocity'].dropna()
    
    if len(ev_values) == 0:
        return np.nan
    
    hard_hits = (ev_values >= threshold).sum()
    return (hard_hits / len(ev_values)) * 100.0

