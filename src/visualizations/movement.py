"""
Movement visualization functions.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Optional
import matplotlib.patches as mpatches

from ..pitch_colors import get_pitch_color, get_pitch_color_map, DEFAULT_PITCH_COLOR


def plot_movement_scatter(df: pd.DataFrame, ax=None) -> plt.Figure:
    """
    Plot HB vs IVB scatter plot, color-coded by pitch type.
    
    Args:
        df: Trackman DataFrame
        ax: Matplotlib axis (creates new if None)
        
    Returns:
        Matplotlib figure
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure
    
    # Get unique pitch types
    pitch_types = df['pitch_type'].dropna().unique()

    # Universal color map for pitch types
    color_map = get_pitch_color_map(pitch_types)
    
    # Plot each pitch type
    for pitch_type in pitch_types:
        pitch_df = df[df['pitch_type'] == pitch_type]
        valid = pitch_df.dropna(subset=['hb', 'ivb'])
        
        if len(valid) > 0:
            ax.scatter(
                valid['hb'],
                valid['ivb'],
                label=pitch_type,
                alpha=0.6,
                s=60,
                c=[color_map.get(pitch_type, DEFAULT_PITCH_COLOR)],
                edgecolors='black',
                linewidth=0.5,
            )
    
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    ax.set_xlabel('Horizontal Break (inches)', fontsize=10)
    ax.set_ylabel('Induced Vertical Break (inches)', fontsize=10)
    ax.set_title('Pitch Movement: HB vs IVB', fontsize=12, fontweight='bold')
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)
    
    return fig


def plot_spin_axis_polar(df: pd.DataFrame, ax=None) -> plt.Figure:
    """
    Plot spin axis/tilt polar plot by pitch type.
    
    Args:
        df: Trackman DataFrame
        ax: Matplotlib axis (creates new if None)
        
    Returns:
        Matplotlib figure
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
    else:
        fig = ax.figure
        if not hasattr(ax, 'set_thetamin'):
            # Recreate as polar if not already
            fig.delaxes(ax)
            ax = fig.add_subplot(111, projection='polar')
    
    # Get unique pitch types
    pitch_types = df['pitch_type'].dropna().unique()
    
    # Universal color map
    color_map = get_pitch_color_map(pitch_types)
    
    # Plot each pitch type
    for pitch_type in pitch_types:
        pitch_df = df[df['pitch_type'] == pitch_type]
        
        # Use spin_axis if available, otherwise calculate from tilt
        if 'spin_axis' in pitch_df.columns:
            axis_data = pitch_df['spin_axis'].dropna()
        elif 'tilt' in pitch_df.columns:
            axis_data = pitch_df['tilt'].dropna()
        else:
            continue
        
        if len(axis_data) > 0:
            # Convert to radians for polar plot
            theta = np.deg2rad(axis_data)
            # Use spin rate as radius (normalized)
            if 'spin_rate' in pitch_df.columns:
                r = pitch_df.loc[axis_data.index, 'spin_rate'].fillna(2000) / 1000  # Normalize
            else:
                r = np.ones(len(axis_data))
            
            ax.scatter(
                theta,
                r,
                label=pitch_type,
                alpha=0.6,
                s=40,
                c=[color_map.get(pitch_type, DEFAULT_PITCH_COLOR)],
                edgecolors='black',
                linewidth=0.5,
            )
    
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_title('Spin Axis/Tilt by Pitch Type', fontsize=12, fontweight='bold', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=9)
    
    return fig

