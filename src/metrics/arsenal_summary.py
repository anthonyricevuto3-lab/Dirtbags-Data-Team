"""
Arsenal summary generators for reports.

These functions generate summary tables for arsenal, plate discipline, and contact outcomes.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional

from .pitch_metrics import (
    calculate_usage_rate,
    calculate_strike_rate,
    calculate_whiff_rate,
    calculate_zone_whiff_rate,
    calculate_out_of_zone_whiff_rate,
    calculate_zone_rate,
    calculate_heart_rate,
    calculate_shadow_rate,
    calculate_chase_rate,
    calculate_swing_rate,
    calculate_putaway_proxy,
)

from .movement_metrics import (
    calculate_velocity_avg,
    calculate_velocity_max,
    calculate_spin_avg,
    calculate_ivb_avg,
    calculate_hb_avg,
    calculate_extension_avg,
    calculate_release_height_avg,
    calculate_release_side_avg,
)

from .contact_metrics import (
    calculate_contact_outcomes,
    calculate_spray_distribution,
    calculate_launch_angle_avg,
    calculate_exit_velocity_avg,
    calculate_exit_velocity_max,
    calculate_hard_hit_rate,
)


def _display_pitch(pt: str) -> str:
    if not pt:
        return pt
    key = pt.lower().replace("-", "").replace(" ", "")
    if key == "2seamfastball":
        return "2 seam"
    if key in ("4seamfastball", "fourseamfastball", "fourseam"):
        return "4 seam"
    return pt


def generate_arsenal_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate arsenal summary table by pitch type.
    
    Columns:
    - Pitch Type
    - Pitches
    - Usage%
    - Strike%
    - Velo AVG
    - Velo MAX
    - SR AVG
    - IVB AVG
    - HB AVG
    - Exten AVG
    - Rel H AVG
    - Rel S AVG
    
    Args:
        df: Trackman DataFrame
        
    Returns:
        DataFrame with arsenal summary
    """
    pitch_types = df['pitch_type'].dropna().unique()
    
    rows = []
    for pitch_type in pitch_types:
        pitch_df = df[df['pitch_type'] == pitch_type]
        
        row = {
            'Pitch Type': _display_pitch(pitch_type),
            'Pitches': len(pitch_df),
            'Usage%': calculate_usage_rate(df, pitch_type),
            'Strike%': calculate_strike_rate(df, pitch_type),
            'Velo AVG': calculate_velocity_avg(df, pitch_type),
            'Velo MAX': calculate_velocity_max(df, pitch_type),
            'SR AVG': calculate_spin_avg(df, pitch_type),
            'IVB AVG': calculate_ivb_avg(df, pitch_type),
            'HB AVG': calculate_hb_avg(df, pitch_type),
            'Exten AVG': calculate_extension_avg(df, pitch_type),
            'Rel H AVG': calculate_release_height_avg(df, pitch_type),
            'Rel S AVG': calculate_release_side_avg(df, pitch_type),
            # Hidden column used only for sorting (dropped before returning)
            '_whiff_order': calculate_whiff_rate(df, pitch_type),
        }
        rows.append(row)
    
    summary_df = pd.DataFrame(rows)
    
    # Round numeric columns
    numeric_cols = summary_df.select_dtypes(include=[np.number]).columns
    summary_df[numeric_cols] = summary_df[numeric_cols].round(1)

    # Sort by whiff rate descending, then drop helper column
    if '_whiff_order' in summary_df.columns:
        summary_df = summary_df.sort_values(by='_whiff_order', ascending=False)
        summary_df = summary_df.drop(columns=['_whiff_order'])
        summary_df = summary_df.reset_index(drop=True)

    return summary_df


def generate_plate_discipline_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate plate discipline summary table by pitch type.
    
    Columns:
    - Pitch Type
    - Zone%
    - Heart%
    - Shadow%
    - Chase%
    - Swing%
    - Whiff%
    - Z-Whiff%
    - O-Whiff%
    - PA Prox
    
    Args:
        df: Trackman DataFrame
        
    Returns:
        DataFrame with plate discipline summary
    """
    pitch_types = df['pitch_type'].dropna().unique()
    
    rows = []
    for pitch_type in pitch_types:
        row = {
            'Pitch Type': _display_pitch(pitch_type),
            'Zone%': calculate_zone_rate(df, pitch_type),
            'Heart%': calculate_heart_rate(df, pitch_type),
            'Shadow%': calculate_shadow_rate(df, pitch_type),
            'Chase%': calculate_chase_rate(df, pitch_type),
            'Swing%': calculate_swing_rate(df, pitch_type),
            'Whiff%': calculate_whiff_rate(df, pitch_type),
            'Z-Whiff%': calculate_zone_whiff_rate(df, pitch_type),
            'O-Whiff%': calculate_out_of_zone_whiff_rate(df, pitch_type),
            'PA Prox': calculate_putaway_proxy(df, pitch_type),
        }
        rows.append(row)
    
    summary_df = pd.DataFrame(rows)
    
    # Round numeric columns
    numeric_cols = summary_df.select_dtypes(include=[np.number]).columns
    summary_df[numeric_cols] = summary_df[numeric_cols].round(1)
    
    # Sort by Whiff% descending
    if 'Whiff%' in summary_df.columns:
        summary_df = summary_df.sort_values(by='Whiff%', ascending=False)
        summary_df = summary_df.reset_index(drop=True)
    
    return summary_df


def generate_contact_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate contact outcomes summary table by pitch type.
    
    Columns:
    - Pitch Type
    - BIP
    - GB%
    - FB%
    - LD%
    - PU%
    - LA AVG
    - EV AVG
    - EV MAX
    - HH%
    - Pull%
    - Middle%
    - Oppo%
    
    Args:
        df: Trackman DataFrame
        
    Returns:
        DataFrame with contact summary
    """
    pitch_types = df['pitch_type'].dropna().unique()
    
    rows = []
    for pitch_type in pitch_types:
        pitch_df = df[df['pitch_type'] == pitch_type]
        bip_count = len(pitch_df[pitch_df['pitch_call'] == 'InPlay'])
        
        contact_outcomes = calculate_contact_outcomes(df, pitch_type)
        spray_dist = calculate_spray_distribution(df, pitch_type)
        
        row = {
            'Pitch Type': _display_pitch(pitch_type),
            'BIP': bip_count,
            'GB%': contact_outcomes['ground_ball_rate'],
            'FB%': contact_outcomes['fly_ball_rate'],
            'LD%': contact_outcomes['line_drive_rate'],
            'PU%': contact_outcomes['popup_rate'],
            'LA AVG': calculate_launch_angle_avg(df, pitch_type),
            'EV AVG': calculate_exit_velocity_avg(df, pitch_type),
            'EV MAX': calculate_exit_velocity_max(df, pitch_type),
            'HH%': calculate_hard_hit_rate(df, pitch_type),
            'Pull%': spray_dist['pull_rate'],
            'Middle%': spray_dist['middle_rate'],
            'Oppo%': spray_dist['oppo_rate'],
            # Hidden column for consistent sorting by whiff rate
            '_whiff_order': calculate_whiff_rate(df, pitch_type),
        }
        rows.append(row)
    
    summary_df = pd.DataFrame(rows)
    
    # Round numeric columns
    numeric_cols = summary_df.select_dtypes(include=[np.number]).columns
    summary_df[numeric_cols] = summary_df[numeric_cols].round(1)
    
    if '_whiff_order' in summary_df.columns:
        summary_df = summary_df.sort_values(by='_whiff_order', ascending=False)
        summary_df = summary_df.drop(columns=['_whiff_order'])
        summary_df = summary_df.reset_index(drop=True)
    
    return summary_df

