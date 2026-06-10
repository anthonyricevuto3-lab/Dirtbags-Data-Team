"""
Pitch location visualization functions.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import pandas as pd
from typing import Optional


# Strike zone dimensions tuned to match ExampleReport proportions
STRIKE_ZONE_WIDTH = 17.0
STRIKE_ZONE_HEIGHT = 30.0  # inches
# Ground is 0; use a typical zone from ~18\" to ~48\"
STRIKE_ZONE_BOTTOM = 18.0
STRIKE_ZONE_TOP = STRIKE_ZONE_BOTTOM + STRIKE_ZONE_HEIGHT


def _draw_strike_zone(ax, color='black', linewidth=1.5, alpha=0.3):
    """Draw strike zone rectangle."""
    rect = patches.Rectangle(
        (-STRIKE_ZONE_WIDTH / 2, STRIKE_ZONE_BOTTOM),
        STRIKE_ZONE_WIDTH,
        STRIKE_ZONE_TOP - STRIKE_ZONE_BOTTOM,
        linewidth=linewidth,
        edgecolor=color,
        facecolor='none',
        alpha=alpha,
    )
    ax.add_patch(rect)
    return ax


def plot_pitch_location_all(df: pd.DataFrame, pitch_type: Optional[str] = None, ax=None) -> plt.Figure:
    """
    Plot all pitch locations.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Filter by pitch type (None = all)
        ax: Matplotlib axis (creates new if None)
        
    Returns:
        Matplotlib figure
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.figure
    
    # Filter valid locations
    valid = df.dropna(subset=['plate_x', 'plate_z'])
    
    if len(valid) > 0:
        ax.scatter(valid['plate_x'], valid['plate_z'], alpha=0.6, s=50, c='blue', edgecolors='black', linewidth=0.5)
    
    _draw_strike_zone(ax)
    
    ax.set_xlabel('Horizontal Location (inches)', fontsize=10)
    ax.set_ylabel('Vertical Location (inches)', fontsize=10)
    ax.set_title('All Pitches' + (f' - {pitch_type}' if pitch_type else ''), fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-24, 24)
    ax.set_ylim(-6, 6)
    ax.set_aspect('equal')
    
    return fig


def plot_pitch_location_two_strike(df: pd.DataFrame, pitch_type: Optional[str] = None, ax=None) -> plt.Figure:
    """
    Plot 2-strike pitch locations.
    
    Args:
        df: Trackman DataFrame
        pitch_type: Filter by pitch type (None = all)
        ax: Matplotlib axis (creates new if None)
        
    Returns:
        Matplotlib figure
    """
    if pitch_type:
        df = df[df['pitch_type'] == pitch_type]
    
    # Filter to 2-strike pitches
    df = df[df['strikes'] == 2]
    
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.figure
    
    valid = df.dropna(subset=['plate_x', 'plate_z'])
    
    if len(valid) > 0:
        ax.scatter(valid['plate_x'], valid['plate_z'], alpha=0.6, s=50, c='red', edgecolors='black', linewidth=0.5)
    
    _draw_strike_zone(ax)
    
    ax.set_xlabel('Horizontal Location (inches)', fontsize=10)
    ax.set_ylabel('Vertical Location (inches)', fontsize=10)
    ax.set_title('2-Strike Pitches' + (f' - {pitch_type}' if pitch_type else ''), fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-24, 24)
    ax.set_ylim(-6, 6)
    ax.set_aspect('equal')
    
    return fig


def plot_pitch_location_whiffs(df: pd.DataFrame, pitch_type: Optional[str] = None, ax=None) -> plt.Figure:
    """
    Plot whiff locations.
    
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
        ax.scatter(valid['plate_x'], valid['plate_z'], alpha=0.7, s=60, c='orange', edgecolors='black', linewidth=0.5)
    
    _draw_strike_zone(ax)
    
    ax.set_xlabel('Horizontal Location (inches)', fontsize=10)
    ax.set_ylabel('Vertical Location (inches)', fontsize=10)
    ax.set_title('Whiffs' + (f' - {pitch_type}' if pitch_type else ''), fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-24, 24)
    ax.set_ylim(-6, 6)
    ax.set_aspect('equal')
    
    return fig


def plot_pitch_location_bip(df: pd.DataFrame, pitch_type: Optional[str] = None, ax=None) -> plt.Figure:
    """
    Plot batted ball in play locations.
    
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
        fig, ax = plt.subplots(figsize=(8, 8))
    else:
        fig = ax.figure
    
    valid = df.dropna(subset=['plate_x', 'plate_z'])
    
    if len(valid) > 0:
        ax.scatter(valid['plate_x'], valid['plate_z'], alpha=0.6, s=50, c='green', edgecolors='black', linewidth=0.5)
    
    _draw_strike_zone(ax)
    
    ax.set_xlabel('Horizontal Location (inches)', fontsize=10)
    ax.set_ylabel('Vertical Location (inches)', fontsize=10)
    ax.set_title('Batted Balls in Play' + (f' - {pitch_type}' if pitch_type else ''), fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-24, 24)
    ax.set_ylim(-6, 6)
    ax.set_aspect('equal')
    
    return fig

