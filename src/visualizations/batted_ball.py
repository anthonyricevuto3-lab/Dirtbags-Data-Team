"""
Batted ball visualization functions.
"""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Optional
import matplotlib.patches as patches


def plot_spray_chart(df: pd.DataFrame, pitch_type: Optional[str] = None, ax=None) -> plt.Figure:
    """
    Plot spray chart (field plot) for batted balls.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Filter by pitch type (None = all)
        ax: Matplotlib axis (creates new if None)
        
    Returns:
        Matplotlib figure
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Filter to batted balls in play
    df = df[df['pitch_call'] == 'InPlay']
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 10))
    else:
        fig = ax.figure
    
    # Draw baseball field outline (simplified)
    # Home plate
    home_plate = patches.Polygon(
        [[0, 0], [-0.7, -0.7], [0, -1.4], [0.7, -0.7]],
        fill=True,
        color='brown',
        alpha=0.5,
    )
    ax.add_patch(home_plate)
    
    # Draw field lines (simplified)
    # Foul lines
    ax.plot([0, 325], [0, 325], 'k-', linewidth=2, alpha=0.5)
    ax.plot([0, -325], [0, 325], 'k-', linewidth=2, alpha=0.5)
    
    # Outfield arc (simplified)
    theta = np.linspace(0, np.pi, 100)
    radius = 400
    x_arc = radius * np.cos(theta)
    y_arc = radius * np.sin(theta)
    ax.plot(x_arc, y_arc, 'k-', linewidth=2, alpha=0.5)
    
    # Plot batted balls
    valid = df.dropna(subset=['spray_angle', 'distance'])
    
    if len(valid) > 0:
        # Convert spray angle and distance to x, y coordinates
        # Spray angle: negative = pull side (left), positive = oppo side (right)
        # Distance is in feet
        angles_rad = np.deg2rad(valid['spray_angle'])
        distances = valid['distance']
        
        x = distances * np.sin(angles_rad)
        y = distances * np.cos(angles_rad)
        
        # Color by hit type if available
        if 'hit_type' in valid.columns:
            hit_types = valid['hit_type'].dropna().unique()
            colors_map = {
                'GroundBall': 'brown',
                'LineDrive': 'green',
                'FlyBall': 'blue',
                'PopUp': 'gray',
            }
            
            for hit_type in hit_types:
                mask = valid['hit_type'] == hit_type
                color = colors_map.get(hit_type, 'black')
                ax.scatter(
                    x[mask],
                    y[mask],
                    label=hit_type,
                    alpha=0.6,
                    s=80,
                    c=color,
                    edgecolors='black',
                    linewidth=0.5,
                )
        else:
            ax.scatter(x, y, alpha=0.6, s=80, c='blue', edgecolors='black', linewidth=0.5)
    
    ax.set_xlabel('Horizontal Distance (feet)', fontsize=10)
    ax.set_ylabel('Vertical Distance (feet)', fontsize=10)
    ax.set_title('Spray Chart' + (f' - {pitch_type}' if pitch_type else ''), fontsize=12, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=9)
    ax.set_xlim(-450, 450)
    ax.set_ylim(0, 450)
    
    return fig


def plot_whiff_zone_heatmap(df: pd.DataFrame, pitch_type: Optional[str] = None, ax=None) -> plt.Figure:
    """
    Plot whiff zone heatmap/density view.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Filter by pitch type (None = all)
        ax: Matplotlib axis (creates new if None)
        
    Returns:
        Matplotlib figure
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Filter to whiffs
    df = df[df['whiff'] == True]
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.figure
    
    valid = df.dropna(subset=['plate_x', 'plate_z'])
    
    if len(valid) > 0:
        # Create 2D histogram
        H, xedges, yedges = np.histogram2d(
            valid['plate_x'],
            valid['plate_z'],
            bins=20,
            range=[[-24, 24], [-6, 6]],
        )
        
        # Plot heatmap
        im = ax.imshow(
            H.T,
            origin='lower',
            extent=[-24, 24, -6, 6],
            cmap='YlOrRd',
            alpha=0.7,
            aspect='auto',
        )
        
        # Add colorbar
        plt.colorbar(im, ax=ax, label='Whiff Count')
        
        # Overlay scatter for individual points
        ax.scatter(valid['plate_x'], valid['plate_z'], alpha=0.3, s=20, c='black', edgecolors='none')
    
    # Draw strike zone
    from .pitch_location import _draw_strike_zone
    _draw_strike_zone(ax)
    
    ax.set_xlabel('Horizontal Location (inches)', fontsize=10)
    ax.set_ylabel('Vertical Location (inches)', fontsize=10)
    ax.set_title('Whiff Zone Heatmap' + (f' - {pitch_type}' if pitch_type else ''), fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-24, 24)
    ax.set_ylim(-6, 6)
    ax.set_aspect('equal')
    
    return fig

