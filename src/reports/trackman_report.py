"""
Trackman postgame report generator.

Generates a consistent PDF report from Trackman CSV data.
OPTIMIZED VERSION for faster generation.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend (faster)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Polygon
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Callable
import time

from ..schemas import clean_trackman
from ..metrics import (
    generate_arsenal_summary,
    generate_plate_discipline_summary,
    generate_contact_summary,
)
from ..pitch_colors import get_pitch_color_map, DEFAULT_PITCH_COLOR


def generate_trackman_report(
    csv_path: str,
    output_path: str,
    pitcher_name: str,
    game_info: Optional[Dict[str, str]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> None:
    """
    Generate Trackman postgame PDF report.
    
    Args:
        csv_path: Path to Trackman CSV file
        output_path: Path for output PDF
        pitcher_name: Pitcher name for report header
        game_info: Optional dict with 'opponent', 'game', 'date' keys
    """
    start_time = time.time()
    
    def update_progress(percent, message):
        """Helper to call progress callback if provided."""
        if progress_callback:
            progress_callback(percent, message)
    
    # Load and clean data (optimized CSV reading)
    # Progress: 30-40
    for p in range(30, 36):
        update_progress(p, 'Loading CSV file')
        time.sleep(0.05)
    df_raw = pd.read_csv(csv_path, low_memory=False)  # Faster for large files
    
    for p in range(36, 41):
        update_progress(p, 'Cleaning and validating data')
        time.sleep(0.05)
    df = clean_trackman(df_raw, strict=False)
    
    # Pre-compute filtered dataframes (major speedup - avoid repeated filtering)
    # Progress: 40-45
    for p in range(41, 46):
        update_progress(p, 'Pre-computing data filters')
        time.sleep(0.05)
    filtered = {}
    filtered['two_strike'] = df[df['strikes'] == 2].copy() if 'strikes' in df.columns else pd.DataFrame()
    filtered['whiffs'] = df[df['whiff'] == True].copy() if 'whiff' in df.columns else pd.DataFrame()
    filtered['bip'] = df[df['pitch_call'] == 'InPlay'].copy() if 'pitch_call' in df.columns else pd.DataFrame()
    filtered['valid_locations'] = df.dropna(subset=['plate_x', 'plate_z']).copy()
    filtered['valid_movement'] = df.dropna(subset=['hb', 'ivb']).copy()
    filtered['valid_batted'] = filtered['bip'].dropna(subset=['spray_angle', 'distance']).copy() if len(filtered['bip']) > 0 else pd.DataFrame()
    
    # Pre-compute all summaries (batch operation - calculate once)
    # Progress: 45-50
    for p in range(46, 51):
        update_progress(p, 'Calculating metrics')
        time.sleep(0.05)
    arsenal_summary = generate_arsenal_summary(df)
    plate_discipline = generate_plate_discipline_summary(df)
    contact_summary = generate_contact_summary(df)
    
    # Optimize matplotlib settings globally
    # Progress: 50-55
    for p in range(50, 56):
        update_progress(p, 'Initializing PDF')
        time.sleep(0.05)
    plt.rcParams['figure.max_open_warning'] = 0  # Suppress warnings
    plt.rcParams['font.size'] = 9
    plt.rcParams['figure.titlesize'] = 12
    plt.rcParams['figure.titleweight'] = 'bold'
    plt.ioff()  # Turn off interactive mode (faster)
    
    # Create PDF
    with PdfPages(output_path) as pdf:
        
        # Title page (optimized - lower DPI)
        # Progress: 55-60
        for p in range(55, 61):
            update_progress(p, 'Creating title page')
            time.sleep(0.05)
        fig = plt.figure(figsize=(8.5, 11), dpi=100)
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
        
        # Pitch Location Plots (optimized - use pre-filtered data, inline plotting)
        # Progress: 60-70
        for p in range(60, 71):
            update_progress(p, 'Generating pitch location plots')
            time.sleep(0.05)
        fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), dpi=100)
        fig.suptitle('Pitch Location', fontsize=14, fontweight='bold')
        
        # Inline optimized plotting (avoid function call overhead)
        
        # All pitches
        valid_all = filtered['valid_locations']
        if len(valid_all) > 0:
            axes[0, 0].scatter(valid_all['plate_x'], valid_all['plate_z'], alpha=0.6, s=30, c='blue', edgecolors='black', linewidth=0.3)
            rect = Rectangle((-9.97, 18.29), 19.94, 25.79, linewidth=1.5, edgecolor='black', facecolor='none', alpha=0.3)
        axes[0, 0].add_patch(rect)
        axes[0, 0].set_xlabel('Horizontal Location (inches)', fontsize=9)
        axes[0, 0].set_ylabel('Vertical Location (inches)', fontsize=9)
        axes[0, 0].set_title('All Pitches', fontsize=11, fontweight='bold')
        axes[0, 0].grid(True, alpha=0.2)
        axes[0, 0].set_xlim(-24, 24)
        axes[0, 0].set_ylim(0, 60)
        axes[0, 0].set_aspect('equal')
        
        # 2-strike
        valid_2s = filtered['two_strike'].dropna(subset=['plate_x', 'plate_z'])
        if len(valid_2s) > 0:
            axes[0, 1].scatter(valid_2s['plate_x'], valid_2s['plate_z'], alpha=0.6, s=30, c='red', edgecolors='black', linewidth=0.3)
            rect = Rectangle((-9.97, 18.29), 19.94, 25.79, linewidth=1.5, edgecolor='black', facecolor='none', alpha=0.3)
        axes[0, 1].add_patch(rect)
        axes[0, 1].set_xlabel('Horizontal Location (inches)', fontsize=9)
        axes[0, 1].set_ylabel('Vertical Location (inches)', fontsize=9)
        axes[0, 1].set_title('2-Strike Pitches', fontsize=11, fontweight='bold')
        axes[0, 1].grid(True, alpha=0.2)
        axes[0, 1].set_xlim(-24, 24)
        axes[0, 1].set_ylim(0, 60)
        axes[0, 1].set_aspect('equal')
        
        # Whiffs
        valid_whiff = filtered['whiffs'].dropna(subset=['plate_x', 'plate_z'])
        if len(valid_whiff) > 0:
            axes[1, 0].scatter(valid_whiff['plate_x'], valid_whiff['plate_z'], alpha=0.7, s=40, c='orange', edgecolors='black', linewidth=0.3)
            rect = Rectangle((-9.97, 18.29), 19.94, 25.79, linewidth=1.5, edgecolor='black', facecolor='none', alpha=0.3)
        axes[1, 0].add_patch(rect)
        axes[1, 0].set_xlabel('Horizontal Location (inches)', fontsize=9)
        axes[1, 0].set_ylabel('Vertical Location (inches)', fontsize=9)
        axes[1, 0].set_title('Whiffs', fontsize=11, fontweight='bold')
        axes[1, 0].grid(True, alpha=0.2)
        axes[1, 0].set_xlim(-24, 24)
        axes[1, 0].set_ylim(0, 60)
        axes[1, 0].set_aspect('equal')
        
        # BIP
        valid_bip = filtered['bip'].dropna(subset=['plate_x', 'plate_z'])
        if len(valid_bip) > 0:
            axes[1, 1].scatter(valid_bip['plate_x'], valid_bip['plate_z'], alpha=0.6, s=30, c='green', edgecolors='black', linewidth=0.3)
        rect = Rectangle((-8.5, -1.5), 17.0, 30.0, linewidth=1.5, edgecolor='black', facecolor='none', alpha=0.3)
        axes[1, 1].add_patch(rect)
        axes[1, 1].set_xlabel('Horizontal Location (inches)', fontsize=9)
        axes[1, 1].set_ylabel('Vertical Location (inches)', fontsize=9)
        axes[1, 1].set_title('Batted Balls in Play', fontsize=11, fontweight='bold')
        axes[1, 1].grid(True, alpha=0.2)
        axes[1, 1].set_xlim(-24, 24)
        axes[1, 1].set_ylim(0, 60)
        axes[1, 1].set_aspect('equal')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Movement Plots (optimized - inline plotting)
        # Progress: 70-75
        for p in range(70, 76):
            update_progress(p, 'Generating movement plots')
            time.sleep(0.05)
        fig = plt.figure(figsize=(11, 8.5), dpi=100)
        fig.suptitle('Pitch Movement', fontsize=14, fontweight='bold')
        
        ax1 = plt.subplot(1, 2, 1)
        valid_mov = filtered['valid_movement']
        pitch_types = []
        if len(valid_mov) > 0:
            pitch_types = valid_mov['pitch_type'].dropna().unique()
            color_map = get_pitch_color_map(pitch_types)
            for pt in pitch_types:
                pt_data = valid_mov[valid_mov['pitch_type'] == pt]
                if len(pt_data) > 0:
                    color = color_map.get(pt, DEFAULT_PITCH_COLOR)
                    ax1.scatter(pt_data['hb'], pt_data['ivb'], label=pt, alpha=0.5, s=20, c=[color], edgecolors='none')
        ax1.axhline(y=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        ax1.axvline(x=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        ax1.set_xlabel('Horizontal Break (inches)', fontsize=9)
        ax1.set_ylabel('Induced Vertical Break (inches)', fontsize=9)
        ax1.set_title('Pitch Movement: HB vs IVB', fontsize=11, fontweight='bold')
        if len(pitch_types) <= 10:
            ax1.legend(loc='best', fontsize=7, ncol=2)
        ax1.grid(True, alpha=0.2)
        
        # Spin axis plot (simplified)
        ax2 = plt.subplot(1, 2, 2)
        if 'spin_axis' in df.columns or 'tilt' in df.columns:
            try:
                ax2_polar = plt.subplot(1, 2, 2, projection='polar')
                spin_col = 'spin_axis' if 'spin_axis' in df.columns else 'tilt'
                spin_data = df[['pitch_type', spin_col]].dropna()
                if len(spin_data) > 0:
                    pitch_types = spin_data['pitch_type'].unique()
                    color_map = get_pitch_color_map(pitch_types)
                    for pt in pitch_types:
                        pt_data = spin_data[spin_data['pitch_type'] == pt]
                        theta = np.deg2rad(pt_data[spin_col])
                        r = np.ones(len(pt_data)) * 2
                        color = color_map.get(pt, DEFAULT_PITCH_COLOR)
                        ax2_polar.scatter(theta, r, label=pt, alpha=0.5, s=20, c=[color])
                    ax2_polar.set_theta_zero_location('N')
                    ax2_polar.set_theta_direction(-1)
                    ax2_polar.set_title('Spin Axis/Tilt', fontsize=11, fontweight='bold', pad=15)
                    if len(pitch_types) <= 5:
                        ax2_polar.legend(loc='upper right', fontsize=7)
            except:
                ax2.text(0.5, 0.5, 'Spin Axis Data\nNot Available', ha='center', va='center', fontsize=11, transform=ax2.transAxes)
                ax2.axis('off')
        else:
            ax2.text(0.5, 0.5, 'Spin Axis Data\nNot Available', ha='center', va='center', fontsize=11, transform=ax2.transAxes)
            ax2.axis('off')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Batted Ball Visuals (optimized - inline plotting)
        # Progress: 75-80
        for p in range(75, 81):
            update_progress(p, 'Generating batted ball visuals')
            time.sleep(0.05)
        fig = plt.figure(figsize=(11, 8.5), dpi=100)
        fig.suptitle('Batted Ball Visuals', fontsize=14, fontweight='bold')
        
        # Spray chart
        ax1 = plt.subplot(1, 2, 1)
        valid_batted = filtered['valid_batted']
        if len(valid_batted) > 0:
            from matplotlib.patches import Polygon
            home_plate = Polygon([[0, 0], [-0.7, -0.7], [0, -1.4], [0.7, -0.7]], fill=True, color='brown', alpha=0.5)
            ax1.add_patch(home_plate)
            ax1.plot([0, 325], [0, 325], 'k-', linewidth=1, alpha=0.3)
            ax1.plot([0, -325], [0, 325], 'k-', linewidth=1, alpha=0.3)
            angles_rad = np.deg2rad(valid_batted['spray_angle'])
            distances = valid_batted['distance']
            x = distances * np.sin(angles_rad)
            y = distances * np.cos(angles_rad)
            ax1.scatter(x, y, alpha=0.5, s=40, c='blue', edgecolors='none')
        ax1.set_xlabel('Horizontal Distance (feet)', fontsize=9)
        ax1.set_ylabel('Vertical Distance (feet)', fontsize=9)
        ax1.set_title('Spray Chart', fontsize=11, fontweight='bold')
        ax1.set_aspect('equal')
        ax1.grid(True, alpha=0.2)
        ax1.set_xlim(-450, 450)
        ax1.set_ylim(0, 450)
        
        # Whiff heatmap
        ax2 = plt.subplot(1, 2, 2)
        valid_whiff_loc = filtered['whiffs'].dropna(subset=['plate_x', 'plate_z'])
        if len(valid_whiff_loc) > 0:
            H, xedges, yedges = np.histogram2d(valid_whiff_loc['plate_x'], valid_whiff_loc['plate_z'], bins=15, range=[[-24, 24], [-6, 6]])
            im = ax2.imshow(H.T, origin='lower', extent=[-24, 24, -6, 6], cmap='YlOrRd', alpha=0.7, aspect='auto', interpolation='nearest')
            rect = Rectangle((-9.97, 18.29), 19.94, 25.79, linewidth=1.5, edgecolor='black', facecolor='none', alpha=0.5)
            ax2.add_patch(rect)
        ax2.set_xlabel('Horizontal Location (inches)', fontsize=9)
        ax2.set_ylabel('Vertical Location (inches)', fontsize=9)
        ax2.set_title('Whiff Zone Heatmap', fontsize=11, fontweight='bold')
        ax2.grid(True, alpha=0.2)
        ax2.set_xlim(-24, 24)
        ax2.set_ylim(-6, 6)
        ax2.set_aspect('equal')
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Tables (use pre-computed summaries - optimized)
        
        # Arsenal Summary Table
        # Progress: 80-83
        for p in range(80, 84):
            update_progress(p, 'Creating arsenal summary table')
            time.sleep(0.05)
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
        table.set_fontsize(7)
        table.scale(1, 1.8)
        
        for i in range(len(arsenal_summary.columns)):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Contact Outcomes Table (optimized)
        # Progress: 83-86
        for p in range(83, 87):
            update_progress(p, 'Creating contact outcomes table')
            time.sleep(0.05)
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
        
        # Plate Discipline Table
        # Progress: 86-89
        for p in range(86, 90):
            update_progress(p, 'Creating plate discipline table')
            time.sleep(0.05)
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
        # Progress: 90-95
        for p in range(90, 96):
            update_progress(p, 'Finalizing PDF')
            time.sleep(0.05)
        d = pdf.infodict()
        d['Title'] = f'Trackman Postgame Report - {pitcher_name}'
        d['Author'] = 'Dirtbags Data Team'
        if game_info and 'date' in game_info:
            d['Subject'] = f"Game Report - {game_info.get('date', '')}"
    
    elapsed = time.time() - start_time
    print(f"Report generated in {elapsed:.2f} seconds")

