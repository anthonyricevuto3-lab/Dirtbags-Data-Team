"""
Scouting report generator for opponent analysis.

Generates series-level scouting documents that update game-to-game.
"""

import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional, Dict, List
import json

from ..schemas import clean_scout


def generate_hitter_profile(hitter_data: pd.DataFrame) -> Dict:
    """
    Generate hitter profile summary from scouting data.
    
    Args:
        hitter_data: Cleaned scouting DataFrame for a single hitter
        
    Returns:
        Dictionary with profile summary
    """
    if len(hitter_data) == 0:
        return {}
    
    # Get first row (assuming single hitter per DataFrame)
    row = hitter_data.iloc[0]
    
    profile = {
        'player_name': row.get('player_name', 'Unknown'),
        'player_id': row.get('player_id', ''),
        'handedness': row.get('handedness', ''),
        'approach': row.get('approach', ''),
        'chase_rate': row.get('chase_rate', 0.0),
        'swing_rate': row.get('swing_rate', 0.0),
        'zone_contact_rate': row.get('zone_contact_rate', 0.0),
        'pull_rate': row.get('pull_rate', 0.0),
        'oppo_rate': row.get('oppo_rate', 0.0),
        'ground_ball_rate': row.get('ground_ball_rate', 0.0),
        'fly_ball_rate': row.get('fly_ball_rate', 0.0),
        'line_drive_rate': row.get('line_drive_rate', 0.0),
        'strength_zones': row.get('strength_zones', ''),
        'weakness_zones': row.get('weakness_zones', ''),
        'two_strike_approach': row.get('two_strike_approach', ''),
        'risp_tendencies': row.get('risp_tendencies', ''),
    }
    
    return profile


def generate_pitcher_profile(pitcher_data: pd.DataFrame) -> Dict:
    """
    Generate pitcher profile summary from scouting data.
    
    Args:
        pitcher_data: Cleaned scouting DataFrame for a single pitcher
        
    Returns:
        Dictionary with profile summary
    """
    if len(pitcher_data) == 0:
        return {}
    
    row = pitcher_data.iloc[0]
    
    profile = {
        'player_name': row.get('player_name', 'Unknown'),
        'player_id': row.get('player_id', ''),
        'handedness': row.get('handedness', ''),
        'arsenal': row.get('arsenal', ''),
        'fastball_velocity': row.get('fastball_velocity', 0.0),
        'fastball_usage': row.get('fastball_usage', 0.0),
        'breaking_ball_usage': row.get('breaking_ball_usage', 0.0),
        'offspeed_usage': row.get('offspeed_usage', 0.0),
        'putaway_pitch': row.get('putaway_pitch', ''),
        'first_inning_plan': row.get('first_inning_plan', ''),
        'strengths': row.get('strengths', ''),
        'weaknesses': row.get('weaknesses', ''),
    }
    
    return profile


def generate_scouting_report(
    hitter_data_path: Optional[str] = None,
    pitcher_data_path: Optional[str] = None,
    usage_pattern_path: Optional[str] = None,
    output_path: str = "scouting_report.pdf",
    opponent_name: str = "Opponent",
    series_info: Optional[Dict[str, str]] = None,
    internal_notes: Optional[Dict[str, str]] = None,
) -> None:
    """
    Generate series-level scouting report PDF.
    
    Args:
        hitter_data_path: Path to hitter scouting CSV
        pitcher_data_path: Path to pitcher scouting CSV
        usage_pattern_path: Path to usage pattern CSV
        output_path: Path for output PDF
        opponent_name: Opponent team name
        series_info: Dict with 'date', 'location', etc.
        internal_notes: Dict with additional notes (keyed by player_id or 'general')
    """
    series_info = series_info or {}
    internal_notes = internal_notes or {}
    
    # Load data
    hitters = []
    if hitter_data_path and Path(hitter_data_path).exists():
        df_hitters = pd.read_csv(hitter_data_path)
        df_hitters_clean = clean_scout(df_hitters, data_type='hitter', strict=False)
        for player_id in df_hitters_clean['player_id'].unique():
            hitter_df = df_hitters_clean[df_hitters_clean['player_id'] == player_id]
            hitters.append(generate_hitter_profile(hitter_df))
    
    pitchers = []
    if pitcher_data_path and Path(pitcher_data_path).exists():
        df_pitchers = pd.read_csv(pitcher_data_path)
        df_pitchers_clean = clean_scout(df_pitchers, data_type='pitcher', strict=False)
        for player_id in df_pitchers_clean['player_id'].unique():
            pitcher_df = df_pitchers_clean[df_pitchers_clean['player_id'] == player_id]
            pitchers.append(generate_pitcher_profile(pitcher_df))
    
    usage_patterns = None
    if usage_pattern_path and Path(usage_pattern_path).exists():
        df_usage = pd.read_csv(usage_pattern_path)
        usage_patterns = clean_scout(df_usage, data_type='usage_pattern', strict=False)
    
    # Create PDF
    with PdfPages(output_path) as pdf:
        plt.style.use('default')
        plt.rcParams['font.size'] = 9
        
        # Title page
        fig = plt.figure(figsize=(8.5, 11))
        ax = fig.add_subplot(111)
        ax.axis('off')
        
        title_text = f"Opponent Scouting Report\n{opponent_name}"
        if series_info.get('date'):
            title_text += f"\n{series_info['date']}"
        if series_info.get('location'):
            title_text += f" - {series_info['location']}"
        
        ax.text(0.5, 0.5, title_text, ha='center', va='center', fontsize=16, fontweight='bold')
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)
        
        # Opponent Hitters Section
        if hitters:
            for hitter in hitters:
                fig, ax = plt.subplots(figsize=(8.5, 11))
                ax.axis('off')
                
                y_pos = 0.95
                ax.text(0.1, y_pos, f"Hitter: {hitter['player_name']}", fontsize=14, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.05
                
                # Tendencies
                ax.text(0.1, y_pos, "Tendencies:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"Approach: {hitter.get('approach', 'N/A')}", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"Chase Rate: {hitter.get('chase_rate', 0):.1f}%", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"Swing Rate: {hitter.get('swing_rate', 0):.1f}%", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.05
                
                # Damage Profile
                ax.text(0.1, y_pos, "Damage Profile:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"Pull Rate: {hitter.get('pull_rate', 0):.1f}%", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"Oppo Rate: {hitter.get('oppo_rate', 0):.1f}%", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"GB%: {hitter.get('ground_ball_rate', 0):.1f}% | FB%: {hitter.get('fly_ball_rate', 0):.1f}% | LD%: {hitter.get('line_drive_rate', 0):.1f}%", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.05
                
                # Zones
                ax.text(0.1, y_pos, "Zones:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"Strength: {hitter.get('strength_zones', 'N/A')}", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"Weakness: {hitter.get('weakness_zones', 'N/A')}", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.05
                
                # Situations
                ax.text(0.1, y_pos, "Situations:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"2-Strike: {hitter.get('two_strike_approach', 'N/A')}", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"RISP: {hitter.get('risp_tendencies', 'N/A')}", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.05
                
                # Internal Notes
                player_id = hitter.get('player_id', '')
                if player_id in internal_notes:
                    ax.text(0.1, y_pos, "Notes:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                    y_pos -= 0.03
                    ax.text(0.15, y_pos, internal_notes[player_id], fontsize=10, transform=ax.transAxes, wrap=True)
                
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
        
        # Opponent Pitchers Section
        if pitchers:
            for pitcher in pitchers:
                fig, ax = plt.subplots(figsize=(8.5, 11))
                ax.axis('off')
                
                y_pos = 0.95
                ax.text(0.1, y_pos, f"Pitcher: {pitcher['player_name']}", fontsize=14, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.05
                
                # Arsenal
                ax.text(0.1, y_pos, "Arsenal:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"{pitcher.get('arsenal', 'N/A')}", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"FB Velocity: {pitcher.get('fastball_velocity', 0):.1f} mph", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.05
                
                # Usage Patterns
                ax.text(0.1, y_pos, "Usage Patterns:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"FB%: {pitcher.get('fastball_usage', 0):.1f}% | BB%: {pitcher.get('breaking_ball_usage', 0):.1f}% | OS%: {pitcher.get('offspeed_usage', 0):.1f}%", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.05
                
                # Strengths/Weaknesses
                ax.text(0.1, y_pos, "Strengths:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"{pitcher.get('strengths', 'N/A')}", fontsize=10, transform=ax.transAxes, wrap=True)
                y_pos -= 0.05
                
                ax.text(0.1, y_pos, "Weaknesses:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"{pitcher.get('weaknesses', 'N/A')}", fontsize=10, transform=ax.transAxes, wrap=True)
                y_pos -= 0.05
                
                # Game Patterns
                ax.text(0.1, y_pos, "Game Patterns:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"First Inning: {pitcher.get('first_inning_plan', 'N/A')}", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.03
                ax.text(0.15, y_pos, f"Putaway: {pitcher.get('putaway_pitch', 'N/A')}", fontsize=10, transform=ax.transAxes)
                y_pos -= 0.05
                
                # Internal Notes
                player_id = pitcher.get('player_id', '')
                if player_id in internal_notes:
                    ax.text(0.1, y_pos, "Notes:", fontsize=12, fontweight='bold', transform=ax.transAxes)
                    y_pos -= 0.03
                    ax.text(0.15, y_pos, internal_notes[player_id], fontsize=10, transform=ax.transAxes, wrap=True)
                
                pdf.savefig(fig, bbox_inches='tight')
                plt.close(fig)
        
        # Usage Pattern Table (if available)
        if usage_patterns is not None and len(usage_patterns) > 0:
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis('tight')
            ax.axis('off')
            ax.set_title('Usage Patterns by Count/Situation', fontsize=14, fontweight='bold', pad=20)
            
            # Create summary table
            table_data = usage_patterns[['player_id', 'count', 'situation', 'pitch_type', 'usage_rate', 'strike_rate', 'whiff_rate']].head(20)
            
            table = ax.table(
                cellText=table_data.values,
                colLabels=table_data.columns,
                cellLoc='center',
                loc='center',
                bbox=[0, 0, 1, 1],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.scale(1, 2)
            
            for i in range(len(table_data.columns)):
                table[(0, i)].set_facecolor('#9C27B0')
                table[(0, i)].set_text_props(weight='bold', color='white')
            
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
        
        # Metadata
        d = pdf.infodict()
        d['Title'] = f'Scouting Report - {opponent_name}'
        d['Author'] = 'Dirtbags Data Team'

