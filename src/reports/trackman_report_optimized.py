"""
Optimized Trackman postgame report generator.

Performance optimizations:
- Pre-compute filtered dataframes
- Batch metric calculations
- Optimized matplotlib settings
- Reduced redundant operations
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend (faster)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Tuple
import time

from ..schemas import clean_trackman
from ..metrics import (
    generate_arsenal_summary,
    generate_plate_discipline_summary,
    generate_contact_summary,
)
from ..pitch_colors import get_pitch_color_map, DEFAULT_PITCH_COLOR


def _precompute_filtered_data(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Pre-compute commonly used filtered dataframes to avoid repeated filtering.
    
    Returns:
        Dictionary with pre-filtered dataframes
    """
    filtered = {}
    
    # Two-strike pitches
    filtered['two_strike'] = df[df['strikes'] == 2].copy() if 'strikes' in df.columns else pd.DataFrame()
    
    # Whiffs
    filtered['whiffs'] = df[df['whiff'] == True].copy() if 'whiff' in df.columns else pd.DataFrame()
    
    # Batted balls in play
    filtered['bip'] = df[df['pitch_call'] == 'InPlay'].copy() if 'pitch_call' in df.columns else pd.DataFrame()
    
    # Zone pitches
    if 'zone' in df.columns:
        filtered['zone'] = df[df['zone'].between(1, 9, inclusive='both')].copy()
    else:
        filtered['zone'] = pd.DataFrame()
    
    # Valid location data
    filtered['valid_locations'] = df.dropna(subset=['plate_x', 'plate_z']).copy()
    
    # Valid movement data
    filtered['valid_movement'] = df.dropna(subset=['hb', 'ivb']).copy()
    
    # Valid batted ball data
    filtered['valid_batted'] = filtered['bip'].dropna(subset=['spray_angle', 'distance']).copy()
    
    return filtered


def _fast_pitch_location_plot(
    df: pd.DataFrame,
    title: str,
    color: str,
    ax,
    valid_data: Optional[pd.DataFrame] = None
) -> None:
    """Optimized pitch location plot."""
    if valid_data is None:
        valid_data = df.dropna(subset=['plate_x', 'plate_z'])
    
    if len(valid_data) == 0:
        ax.text(0.5, 0.5, 'No data available', ha='center', va='center', transform=ax.transAxes)
        return
    
    # Use scatter with optimized parameters
    ax.scatter(
        valid_data['plate_x'],
        valid_data['plate_z'],
        alpha=0.6,
        s=30,  # Smaller markers = faster rendering
        c=color,
        edgecolors='black',
        linewidth=0.3,
    )
    
    # Draw strike zone (simplified)
    from matplotlib.patches import Rectangle
    rect = Rectangle(
        (-9.97, 18.29),
        19.94,
        25.79,
        linewidth=1.5,
        edgecolor='black',
        facecolor='none',
        alpha=0.3,
    )
    ax.add_patch(rect)
    
    ax.set_xlabel('Horizontal Location (inches)', fontsize=9)
    ax.set_ylabel('Vertical Location (inches)', fontsize=9)
    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-24, 24)
    ax.set_ylim(-6, 34)
    ax.set_aspect('equal')


def _fast_movement_scatter(df: pd.DataFrame, ax, valid_data: Optional[pd.DataFrame] = None) -> None:
    """Optimized movement scatter plot."""
    if valid_data is None:
        valid_data = df.dropna(subset=['hb', 'ivb', 'pitch_type'])
    
    if len(valid_data) == 0:
        ax.text(0.5, 0.5, 'No movement data', ha='center', va='center', transform=ax.transAxes)
        return
    
    # Get unique pitch types
    pitch_types = valid_data['pitch_type'].dropna().unique()
    color_map = get_pitch_color_map(pitch_types)

    for pitch_type in pitch_types:  # Preserve ordering from data
        pitch_data = valid_data[valid_data['pitch_type'] == pitch_type]
        if len(pitch_data) > 0:
            color = color_map.get(pitch_type, DEFAULT_PITCH_COLOR)
            ax.scatter(
                pitch_data['hb'],
                pitch_data['ivb'],
                label=pitch_type,
                alpha=0.5,
                s=20,  # Smaller markers
                c=[color],
                edgecolors='none',  # No edges = faster
            )
    
    ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    ax.set_xlabel('Horizontal Break (inches)', fontsize=9)
    ax.set_ylabel('Induced Vertical Break (inches)', fontsize=9)
    ax.set_title('Pitch Movement: HB vs IVB', fontsize=11, fontweight='bold')
    if len(pitch_types) <= 10:
        ax.legend(loc='best', fontsize=7, ncol=2)
    ax.grid(True, alpha=0.2)


def _fast_spray_chart(df: pd.DataFrame, ax, valid_data: Optional[pd.DataFrame] = None) -> None:
    """Optimized spray chart."""
    if valid_data is None:
        bip = df[df['pitch_call'] == 'InPlay'] if 'pitch_call' in df.columns else pd.DataFrame()
        valid_data = bip.dropna(subset=['spray_angle', 'distance'])
    
    if len(valid_data) == 0:
        ax.text(0.5, 0.5, 'No batted ball data', ha='center', va='center', transform=ax.transAxes)
        return
    
    # Simplified field drawing
    # Home plate
    from matplotlib.patches import Polygon
    home_plate = Polygon(
        [[0, 0], [-0.7, -0.7], [0, -1.4], [0.7, -0.7]],
        fill=True,
        color='brown',
        alpha=0.5,
    )
    ax.add_patch(home_plate)
    
    # Foul lines (simplified)
    ax.plot([0, 325], [0, 325], 'k-', linewidth=1, alpha=0.3)
    ax.plot([0, -325], [0, 325], 'k-', linewidth=1, alpha=0.3)
    
    # Convert to coordinates
    angles_rad = np.deg2rad(valid_data['spray_angle'])
    distances = valid_data['distance']
    x = distances * np.sin(angles_rad)
    y = distances * np.cos(angles_rad)
    
    # Simple scatter (no color coding for speed)
    ax.scatter(x, y, alpha=0.5, s=40, c='blue', edgecolors='none')
    
    ax.set_xlabel('Horizontal Distance (feet)', fontsize=9)
    ax.set_ylabel('Vertical Distance (feet)', fontsize=9)
    ax.set_title('Spray Chart', fontsize=11, fontweight='bold')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-450, 450)
    ax.set_ylim(0, 450)


def _fast_whiff_heatmap(df: pd.DataFrame, ax, valid_data: Optional[pd.DataFrame] = None) -> None:
    """Optimized whiff zone heatmap."""
    if valid_data is None:
        whiffs = df[df['whiff'] == True] if 'whiff' in df.columns else pd.DataFrame()
        valid_data = whiffs.dropna(subset=['plate_x', 'plate_z'])
    
    if len(valid_data) == 0:
        ax.text(0.5, 0.5, 'No whiff data', ha='center', va='center', transform=ax.transAxes)
        return
    
    # Use fewer bins for faster computation
    H, xedges, yedges = np.histogram2d(
        valid_data['plate_x'],
        valid_data['plate_z'],
        bins=15,  # Reduced from 20
        range=[[-24, 24], [0, 60]],
    )
    
    im = ax.imshow(
        H.T,
        origin='lower',
        extent=[-24, 24, 0, 60],
        cmap='YlOrRd',
        alpha=0.7,
        aspect='auto',
        interpolation='nearest',  # Faster than default
    )
    
    # Simplified strike zone
    from matplotlib.patches import Rectangle
    rect = Rectangle(
        (-8.5, -1.5),
        17.0,
        30.0,
        linewidth=1.5,
        edgecolor='black',
        facecolor='none',
        alpha=0.5,
    )
    ax.add_patch(rect)
    
    ax.set_xlabel('Horizontal Location (inches)', fontsize=9)
    ax.set_ylabel('Vertical Location (inches)', fontsize=9)
    ax.set_title('Whiff Zone Heatmap', fontsize=11, fontweight='bold')
    ax.grid(True, alpha=0.2)
    ax.set_xlim(-24, 24)
    ax.set_ylim(0, 60)
    ax.set_aspect('equal')


def generate_trackman_report(
    csv_path: str,
    output_path: str,
    pitcher_name: str,
    game_info: Optional[Dict[str, str]] = None,
) -> None:
    """
    Generate Trackman postgame PDF report (OPTIMIZED VERSION).
    
    Performance improvements:
    - Pre-computes filtered dataframes
    - Optimized matplotlib settings
    - Reduced plot complexity
    - Batch operations
    
    Args:
        csv_path: Path to Trackman CSV file
        output_path: Path for output PDF
        pitcher_name: Pitcher name for report header
        game_info: Optional dict with 'opponent', 'game', 'date' keys
    """
    start_time = time.time()
    
    # Load and clean data (optimize CSV reading)
    df_raw = pd.read_csv(csv_path, low_memory=False)  # Faster for large files
    df = clean_trackman(df_raw, strict=False)
    
    # Pre-compute all filtered dataframes (major speedup)
    filtered = _precompute_filtered_data(df)
    
    # Pre-compute all summaries (batch operation)
    arsenal_summary = generate_arsenal_summary(df)
    plate_discipline = generate_plate_discipline_summary(df)
    contact_summary = generate_contact_summary(df)
    
    # Optimize matplotlib settings globally
    plt.rcParams['figure.max_open_warning'] = 0  # Suppress warnings
    plt.rcParams['font.size'] = 9
    plt.rcParams['figure.titlesize'] = 12
    plt.rcParams['figure.titleweight'] = 'bold'
    plt.ioff()  # Turn off interactive mode (faster)
    
    # Create PDF
    with PdfPages(output_path) as pdf:
        # Title page (simplified)
        fig = plt.figure(figsize=(8.5, 11), dpi=100)  # Lower DPI = faster
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        title_text = f"Trackman Postgame Report\n{pitcher_name}"
        if game_info:
            if 'opponent' in game_info:
                title_text += f"\nvs. {game_info['opponent']}"
            if 'game' in game_info:
                title_text += f" - {game_info['game']}"
            if 'date' in game_info:
                title_text += f"\n{game_info['date']}"
        
        ax.text(0.5, 0.5, title_text, ha='center', va='center', fontsize=16, fontweight='bold')
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Pitch Location Plots (optimized - use pre-filtered data)
        fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), dpi=100)
        fig.suptitle('Pitch Location', fontsize=14, fontweight='bold')
        
        _fast_pitch_location_plot(df, 'All Pitches', 'blue', axes[0, 0], filtered['valid_locations'])
        _fast_pitch_location_plot(filtered['two_strike'], '2-Strike Pitches', 'red', axes[0, 1])
        _fast_pitch_location_plot(filtered['whiffs'], 'Whiffs', 'orange', axes[1, 0])
        _fast_pitch_location_plot(filtered['bip'], 'Batted Balls in Play', 'green', axes[1, 1])
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Movement Plots (optimized)
        fig = plt.figure(figsize=(11, 8.5), dpi=100)
        fig.suptitle('Pitch Movement', fontsize=14, fontweight='bold')
        
        ax1 = plt.subplot(1, 2, 1)
        _fast_movement_scatter(df, ax1, filtered['valid_movement'])
        
        # Spin axis plot (simplified - skip if no data)
        ax2 = plt.subplot(1, 2, 2)
        if 'spin_axis' in df.columns or 'tilt' in df.columns:
            # Simplified polar plot
            try:
                ax2_polar = plt.subplot(1, 2, 2, projection='polar')
                spin_data = df[['pitch_type', 'spin_axis']].dropna() if 'spin_axis' in df.columns else df[['pitch_type', 'tilt']].dropna()
                if len(spin_data) > 0:
                    pitch_types = spin_data['pitch_type'].unique()
                    color_map = get_pitch_color_map(pitch_types)
                    for pt in pitch_types:
                        pt_data = spin_data[spin_data['pitch_type'] == pt]
                        axis_col = 'spin_axis' if 'spin_axis' in pt_data.columns else 'tilt'
                        theta = np.deg2rad(pt_data[axis_col])
                        r = np.ones(len(pt_data)) * 2  # Simplified radius
                        color = color_map.get(pt, DEFAULT_PITCH_COLOR)
                        ax2_polar.scatter(theta, r, label=pt, alpha=0.5, s=20, c=[color])
                    ax2_polar.set_theta_zero_location('N')
                    ax2_polar.set_theta_direction(-1)
                    ax2_polar.set_title('Spin Axis/Tilt', fontsize=11, fontweight='bold', pad=15)
                    if len(pitch_types) <= 5:
                        ax2_polar.legend(loc='upper right', fontsize=7)
                else:
                    ax2_polar.text(0.5, 0.5, 'No spin axis data', ha='center', va='center', transform=ax2_polar.transAxes)
            except:
                ax2.text(0.5, 0.5, 'Spin Axis Data\nNot Available', ha='center', va='center', fontsize=11)
                ax2.axis('off')
        else:
            ax2.text(0.5, 0.5, 'Spin Axis Data\nNot Available', ha='center', va='center', fontsize=11)
            ax2.axis('off')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Batted Ball Visuals (optimized)
        fig = plt.figure(figsize=(11, 8.5), dpi=100)
        fig.suptitle('Batted Ball Visuals', fontsize=14, fontweight='bold')
        
        ax1 = plt.subplot(1, 2, 1)
        _fast_spray_chart(df, ax1, filtered['valid_batted'])
        
        ax2 = plt.subplot(1, 2, 2)
        _fast_whiff_heatmap(df, ax2, filtered['whiffs'].dropna(subset=['plate_x', 'plate_z']) if len(filtered['whiffs']) > 0 else pd.DataFrame())
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Tables (optimized - use pre-computed summaries)
        # Arsenal Summary
        fig, ax = plt.subplots(figsize=(11, 8.5), dpi=100)
        ax.axis('off')
        ax.set_title('Arsenal Summary (By Pitch Type)', fontsize=14, fontweight='bold', pad=20)
        
        table = ax.table(
            cellText=arsenal_summary.values,
            colLabels=arsenal_summary.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(7)  # Slightly smaller for speed
        table.scale(1, 1.8)
        
        for i in range(len(arsenal_summary.columns)):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Contact Outcomes
        fig, ax = plt.subplots(figsize=(11, 8.5), dpi=100)
        ax.axis('off')
        ax.set_title('Contact Outcomes (By Pitch Type)', fontsize=14, fontweight='bold', pad=20)
        
        table = ax.table(
            cellText=contact_summary.values,
            colLabels=contact_summary.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.8)
        
        for i in range(len(contact_summary.columns)):
            table[(0, i)].set_facecolor('#2196F3')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Plate Discipline
        fig, ax = plt.subplots(figsize=(11, 8.5), dpi=100)
        ax.axis('off')
        ax.set_title('Plate Discipline (By Pitch Type)', fontsize=14, fontweight='bold', pad=20)
        
        table = ax.table(
            cellText=plate_discipline.values,
            colLabels=plate_discipline.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.8)
        
        for i in range(len(plate_discipline.columns)):
            table[(0, i)].set_facecolor('#FF9800')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Metadata
        d = pdf.infodict()
        d['Title'] = f'Trackman Postgame Report - {pitcher_name}'
        d['Author'] = 'Dirtbags Data Team'
        if game_info and 'date' in game_info:
            d['Subject'] = f"Game Report - {game_info.get('date', '')}"
    
    elapsed = time.time() - start_time
    print(f"Report generated in {elapsed:.2f} seconds")

