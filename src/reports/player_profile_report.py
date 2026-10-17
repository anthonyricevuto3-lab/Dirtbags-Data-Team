"""
Generate user-friendly cumulative player profile PDF reports.
"""

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
import numpy as np
from pathlib import Path
from typing import Optional, List, Callable
from datetime import datetime, date

from ..metrics import (
    generate_arsenal_summary,
    generate_plate_discipline_summary,
    generate_contact_summary,
    compute_inning_success_metrics,
)
from .single_outing_643 import _fan_chart, _spin_axis
from ..pitch_colors import get_pitch_color_map, DEFAULT_PITCH_COLOR

# In-season cutoff for 2026 reports
DATE_CUTOFF_2026 = date(2026, 2, 13)

# Fall 2026 window (inclusive)
FALL_2026_START = date(2026, 9, 1)
FALL_2026_END = date(2027, 2, 12)

# Logo path candidates (handle workspace path quirks and copied asset)
_LOGO_CANDIDATES = [
    Path(__file__).resolve().parent.parent / "images" / "Dirtbag Data Team baseball logo.png",
    Path("images") / "Dirtbag Data Team baseball logo.png",
]


def _find_logo_path() -> Optional[Path]:
    for p in _LOGO_CANDIDATES:
        if p.exists():
            return p
    return None

def _pitch_label(pt: str) -> str:
    """Normalize pitch type names for legends."""
    if not pt:
        return pt
    low = pt.strip().lower()
    if low in {"fourseamfastball", "four-seam fastball", "four seam fastball", "4seam", "4-seam", "4 seam"}:
        return "4 seam"
    if low in {"twoseamfastball", "two-seam fastball", "two seam fastball", "2seam", "2-seam", "2 seam"}:
        return "2 seam"
    return pt


from .pitch_grouping import get_pitch_grouping_fn

def _parse_outing_date(meta_date) -> Optional[datetime]:
    """Best-effort parse of outing date from metadata."""
    if not meta_date:
        return None
    s = str(meta_date)
    # Try ISO first
    try:
        return datetime.fromisoformat(s)
    except Exception:
        pass
    # Common explicit formats
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def generate_player_profile_report(
    profile,
    output_path: str,
    inning_success_df: Optional[pd.DataFrame] = None,
    title_label: str = "Player Profile",
    inning_success_title: str = "Inning Success — In-Season",
) -> None:
    """
    Generate cumulative player profile PDF report.
    
    Args:
        profile: PlayerProfile object
        output_path: Path for output PDF
        inning_success_df: Optional table of inning success metrics (for windowed reports).
        title_label: Heading shown on the title page.
        inning_success_title: Heading for the optional inning-success page.
    """
    # Get cumulative data and work on a copy so grouping never mutates shared data
    df = profile.get_cumulative_data().copy()
    
    if len(df) == 0:
        raise ValueError("No data available for profile")

    # Ensure pitch_type column exists (saved CSVs use "pitch_type"; fallback for alternatives)
    if "pitch_type" not in df.columns:
        for col in ("Pitch Type", "TaggedPitchType", "AutoPitchType"):
            if col in df.columns:
                df["pitch_type"] = df[col].astype(str)
                break

    # Apply pitcher-specific pitch grouping from team config
    grouping_fn = get_pitch_grouping_fn(profile)
    if grouping_fn is not None:
        df = grouping_fn(df)
    
    # Calculate summaries
    arsenal_summary = generate_arsenal_summary(df)
    plate_discipline = generate_plate_discipline_summary(df)
    contact_summary = generate_contact_summary(df)
    
    # Pre-compute filtered dataframes
    filtered = {}
    filtered['two_strike'] = df[df['strikes'] == 2].copy() if 'strikes' in df.columns else pd.DataFrame()
    filtered['whiffs'] = df[df['whiff'] == True].copy() if 'whiff' in df.columns else pd.DataFrame()
    filtered['bip'] = df[df['pitch_call'] == 'InPlay'].copy() if 'pitch_call' in df.columns else pd.DataFrame()
    filtered['valid_locations'] = df.dropna(subset=['plate_x', 'plate_z']).copy()
    filtered['valid_movement'] = df.dropna(subset=['hb', 'ivb']).copy()
    filtered['valid_batted'] = filtered['bip'].dropna(subset=['spray_angle', 'distance']).copy() if len(filtered['bip']) > 0 else pd.DataFrame()
    pitch_color_map = get_pitch_color_map(df['pitch_type'].dropna().unique()) if 'pitch_type' in df.columns else {}
    
    # Optimize matplotlib settings
    plt.rcParams['figure.max_open_warning'] = 0
    plt.rcParams['font.size'] = 10
    plt.rcParams['figure.titlesize'] = 14
    plt.rcParams['figure.titleweight'] = 'bold'
    plt.ioff()
    
    def _scatter_by_pitch_type(ax, df: pd.DataFrame, xcol: str, ycol: str, title: str, xlabel: str, ylabel: str, add_zone=False, colors_map=None):
        if df.empty:
            ax.axis('off')
            ax.text(0.5, 0.5, "No data", ha='center', va='center')
            return []
        pt_vals = df['pitch_type'].dropna().unique() if 'pitch_type' in df.columns else []
        colors_map = colors_map or get_pitch_color_map(pt_vals)
        has_points = False
        handles = []
        for pt in pt_vals:
            sub = df[df.get('pitch_type') == pt].dropna(subset=[xcol, ycol])
            if len(sub) == 0:
                continue
            c = colors_map.get(pt, DEFAULT_PITCH_COLOR)
            lbl = _pitch_label(pt)
            ax.scatter(sub[xcol], sub[ycol], alpha=0.6, s=28, c=[c], edgecolors='white', linewidths=0.35, label=lbl)
            has_points = True
            handles.append(plt.Line2D([0], [0], marker='o', color='white', markerfacecolor=c, markeredgecolor='white', markersize=6, label=lbl))
        if add_zone:
            rect = Rectangle((-9.97, 18.29), 19.94, 25.79, linewidth=1.5, edgecolor='black', facecolor='none', alpha=0.3)
            ax.add_patch(rect)
            ax.set_xlim(-24, 24)
            ax.set_ylim(0, 60)
            ax.set_aspect('equal')
        ax.set_xlabel(xlabel, fontsize=10)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.2)
        if not has_points:
            ax.axis('off')
            ax.text(0.5, 0.5, "No data", ha='center', va='center')
        return handles

    def _plot_all_pitch_zone_heatmap(ax, df_loc: pd.DataFrame):
        """
        Plot all-pitches zone as a 3x3 red heatmap plus out-of-zone percentages.
        """
        if df_loc.empty or not {"plate_x", "plate_z"}.issubset(df_loc.columns):
            ax.axis("off")
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        coords = df_loc.dropna(subset=["plate_x", "plate_z"])
        total = len(coords)
        if total == 0:
            ax.axis("off")
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
            return

        # Strike-zone geometry (inches).
        left, right = -9.97, 9.97
        bottom, top = 18.29, 44.08
        third_w = (right - left) / 3.0
        third_h = (top - bottom) / 3.0

        cell_pcts = []
        for row in range(3):
            for col in range(3):
                x0 = left + col * third_w
                x1 = x0 + third_w
                y0 = bottom + row * third_h
                y1 = y0 + third_h
                in_cell = ((coords["plate_x"] >= x0) & (coords["plate_x"] < x1) &
                           (coords["plate_z"] >= y0) & (coords["plate_z"] < y1)).sum()
                cell_pcts.append(in_cell / total * 100.0)
        max_pct = max(cell_pcts) if cell_pcts else 0.0

        # Draw 3x3 heatmap squares (light red for low%, dark red for high%).
        idx = 0
        for row in range(3):
            for col in range(3):
                x0 = left + col * third_w
                y0 = bottom + row * third_h
                pct = cell_pcts[idx]
                idx += 1
                intensity = (pct / max_pct) if max_pct > 0 else 0.0
                # Use red colormap where low intensity is near-white.
                fill = plt.cm.Reds(0.08 + 0.82 * intensity)
                ax.add_patch(Rectangle(
                    (x0, y0),
                    third_w,
                    third_h,
                    linewidth=1.0,
                    edgecolor="black",
                    facecolor=fill,
                    alpha=0.95,
                    zorder=1,
                ))
                ax.text(
                    x0 + third_w / 2.0,
                    y0 + third_h / 2.0,
                    f"{pct:.1f}%",
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    color="black",
                    zorder=2,
                )

        # Draw strike zone border and +3-inch boundary guide.
        ax.add_patch(Rectangle((left, bottom), right - left, top - bottom, linewidth=1.6, edgecolor="black", facecolor="none", zorder=3))
        outer_left, outer_right = left - 3.0, right + 3.0
        outer_bottom, outer_top = bottom - 3.0, top + 3.0
        ax.add_patch(Rectangle(
            (outer_left, outer_bottom),
            outer_right - outer_left,
            outer_top - outer_bottom,
            linewidth=1.0,
            edgecolor="black",
            facecolor="none",
            linestyle=":",
            alpha=0.35,
            zorder=3,
        ))

        # >3-inch side percentages and within-3-inch percentage.
        above3 = (coords["plate_z"] > (top + 3.0)).sum() / total * 100.0
        below3 = (coords["plate_z"] < (bottom - 3.0)).sum() / total * 100.0
        right3 = (coords["plate_x"] > (right + 3.0)).sum() / total * 100.0
        left3 = (coords["plate_x"] < (left - 3.0)).sum() / total * 100.0
        # Within-3-inch area split into 4 equal quadrants with heatmap shading.
        mid_x = (outer_left + outer_right) / 2.0
        mid_y = (outer_bottom + outer_top) / 2.0
        q_defs = [
            ("Top Left", outer_left, mid_x, mid_y, outer_top),
            ("Top Right", mid_x, outer_right, mid_y, outer_top),
            ("Bottom Left", outer_left, mid_x, outer_bottom, mid_y),
            ("Bottom Right", mid_x, outer_right, outer_bottom, mid_y),
        ]
        q_pcts = []
        for _, x0, x1, y0, y1 in q_defs:
            cnt = (
                (coords["plate_x"] >= x0)
                & (coords["plate_x"] <= x1)
                & (coords["plate_z"] >= y0)
                & (coords["plate_z"] <= y1)
            ).sum()
            q_pcts.append(cnt / total * 100.0)
        q_max = max(q_pcts) if q_pcts else 0.0

        # Draw quadrant heatmap under the 3x3 zone cells.
        for i, (_name, x0, x1, y0, y1) in enumerate(q_defs):
            pct = q_pcts[i]
            intensity = (pct / q_max) if q_max > 0 else 0.0
            q_fill = plt.cm.Reds(0.04 + 0.75 * intensity)
            ax.add_patch(Rectangle(
                (x0, y0),
                x1 - x0,
                y1 - y0,
                linewidth=0.8,
                edgecolor="black",
                facecolor=q_fill,
                alpha=0.22,
                zorder=0.5,
            ))

        # Show only percentages in the visible 3-inch ring corners (not over strike-zone cells).
        ring_labels = [
            ((outer_left + left) / 2.0, (top + outer_top) / 2.0, q_pcts[0]),   # top-left
            ((right + outer_right) / 2.0, (top + outer_top) / 2.0, q_pcts[1]), # top-right
            ((outer_left + left) / 2.0, (outer_bottom + bottom) / 2.0, q_pcts[2]), # bottom-left
            ((right + outer_right) / 2.0, (outer_bottom + bottom) / 2.0, q_pcts[3]), # bottom-right
        ]
        for x, y, pct in ring_labels:
            ax.text(
                x,
                y,
                f"{pct:.1f}%",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
                color="black",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.55, pad=0.2),
                zorder=4,
            )

        ax.text((left + right) / 2.0, outer_top + 1.1, f">3in Above: {above3:.1f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")
        ax.text((left + right) / 2.0, outer_bottom - 1.3, f">3in Below: {below3:.1f}%", ha="center", va="top", fontsize=8, fontweight="bold")
        ax.text(outer_left - 0.8, (bottom + top) / 2.0, f">3in Left: {left3:.1f}%", ha="right", va="center", fontsize=8, fontweight="bold", rotation=90)
        ax.text(outer_right + 0.8, (bottom + top) / 2.0, f">3in Right: {right3:.1f}%", ha="left", va="center", fontsize=8, fontweight="bold", rotation=270)

        ax.set_xlim(-24, 24)
        ax.set_ylim(0, 60)
        ax.set_aspect("equal")
        ax.set_xlabel("Horizontal Location (inches)", fontsize=10)
        ax.set_ylabel("Vertical Location (inches)", fontsize=10)
        ax.set_title("All Pitches", fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.2)

    def _abbrev_name(name: str) -> str:
        n = (name or "").strip()
        if len(n) <= 9:  # abbreviate when 10+ characters
            return n
        parts = n.split()
        if len(parts) >= 2:
            first, last = parts[0], " ".join(parts[1:])
            return f"{first[0]}. {last}"
        return n[:10]

    def _build_outing_trends(profile) -> pd.DataFrame:
        """Return per-outing, per-pitch summary for trend plotting."""
        grouping_fn = get_pitch_grouping_fn(profile)
        rows: List[dict] = []
        for outing in profile.outings:
            df_out = outing.get("data", pd.DataFrame())
            meta = outing.get("metadata", {})
            if df_out is None or len(df_out) == 0:
                continue
            # Work on a copy; apply pitcher-specific grouping so trends use combined types
            df_out = df_out.copy()
            if grouping_fn is not None:
                df_out = grouping_fn(df_out)
            total = len(df_out)
            # Resolve outing date/label
            date_val = meta.get("date")
            date_dt = pd.to_datetime(pd.Series([date_val]), errors="coerce").dropna()
            if len(date_dt) > 0:
                date_dt = date_dt.iloc[0]
            else:
                date_dt = pd.NaT
            outing_label = date_dt.strftime("%m/%d/%Y") if pd.notna(date_dt) else meta.get("source_file", "Outing")
            for pt, g in df_out.groupby("pitch_type"):
                cnt = len(g)
                usage = cnt / total * 100 if total else np.nan
                velo = g["velocity"].mean() if "velocity" in g else np.nan
                spin = g["spin_rate"].mean() if "spin_rate" in g else np.nan
                hb = g["hb"].mean() if "hb" in g else np.nan
                ivb = g["ivb"].mean() if "ivb" in g else np.nan
                whiff = g["whiff"].mean() * 100 if "whiff" in g else np.nan
                strike = g["strike"].mean() * 100 if "strike" in g else np.nan
                hb_avg = g["hb"].mean() if "hb" in g else np.nan
                rows.append({
                    "outing_dt": date_dt,
                    "outing_label": outing_label,
                    "pitch_type": pt,
                    "usage_pct": usage,
                    "velo": velo,
                    "spin": spin,
                    "whiff_pct": whiff,
                    "strike_pct": strike,
                    "ivb": ivb,
                    "hb": hb,
                    "hb_avg": hb_avg,
                })
        if not rows:
            return pd.DataFrame()
        trend_df = pd.DataFrame(rows)
        trend_df = trend_df.sort_values(["outing_dt", "outing_label"]).reset_index(drop=True)
        # Assign x index for plotting order
        unique_labels = trend_df["outing_label"].unique()
        label_to_x = {lbl: i for i, lbl in enumerate(unique_labels)}
        trend_df["x_idx"] = trend_df["outing_label"].map(label_to_x)
        return trend_df

    def _tagged_side_rates(df_side: pd.DataFrame) -> dict:
        """Compute GB/FB/LD/PU% from tagged_hit_type, excluding bunts/undefined."""
        if df_side is None or len(df_side) == 0 or "tagged_hit_type" not in df_side.columns:
            return {"gb": np.nan, "fb": np.nan, "ld": np.nan, "pu": np.nan, "total": 0}
        tags_raw = df_side["tagged_hit_type"].astype(str).str.strip().str.lower()
        valid = tags_raw.str.contains("ground|fly|line|pop", regex=True)
        tags = tags_raw[valid]
        tags = tags[~tags.isin(["", "nan", "none", "undefined", "bunt", "bunted ball", "bunted"])]
        total = len(tags)
        if total == 0:
            return {"gb": np.nan, "fb": np.nan, "ld": np.nan, "pu": np.nan, "total": 0}
        gb = tags.str.contains("ground").sum() / total * 100.0
        fb = tags.str.contains("fly").sum() / total * 100.0
        ld = tags.str.contains("line").sum() / total * 100.0
        pu = tags.str.contains("pop").sum() / total * 100.0
        return {"gb": gb, "fb": fb, "ld": ld, "pu": pu, "total": total}

    def _tagged_summary_table(df: pd.DataFrame) -> pd.DataFrame:
        if "tagged_hit_type" not in df.columns:
            return pd.DataFrame()
        if "batter_side" in df.columns:
            side_col = df["batter_side"].astype(str).str.upper()
            df_r = df[side_col.str.startswith("R")]
            df_l = df[side_col.str.startswith("L")]
        else:
            df_r = df_l = df.iloc[0:0]
        stats_r = _tagged_side_rates(df_r)
        stats_l = _tagged_side_rates(df_l)
        rows = [
            ["RHH", stats_r["gb"], stats_r["fb"], stats_r["ld"], stats_r["pu"], stats_r["total"]],
            ["LHH", stats_l["gb"], stats_l["fb"], stats_l["ld"], stats_l["pu"], stats_l["total"]],
        ]
        return pd.DataFrame(rows, columns=["Split", "GB%", "FB%", "LD%", "PU%", "Tagged Count"])

    def _plot_trend(ax, trend_df: pd.DataFrame, metric: str, ylabel: str, colors_map=None):
        if trend_df.empty or metric not in trend_df:
            ax.axis('off')
            return
        pitches = trend_df["pitch_type"].unique()
        colors_map = colors_map or get_pitch_color_map(pitches)
        for pt in pitches:
            sub = trend_df[trend_df["pitch_type"] == pt]
            c = colors_map.get(pt, DEFAULT_PITCH_COLOR)
            ax.plot(sub["x_idx"], sub[metric], marker="o", label=_pitch_label(pt), color=c, linewidth=1.8, markersize=4)
        ax.set_xticks(sorted(trend_df["x_idx"].unique()))
        labels = trend_df.sort_values("x_idx")[["x_idx", "outing_label"]].drop_duplicates()["outing_label"]
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, frameon=False, loc="best")

    def _tagged_rates(df_side: pd.DataFrame) -> dict:
        if df_side is None or len(df_side) == 0 or "tagged_hit_type" not in df_side.columns:
            return {"gb": np.nan, "fb": np.nan, "ld": np.nan, "total": 0}
        tags = df_side["tagged_hit_type"].astype(str).str.strip().str.lower()
        tags = tags[~tags.isin(["", "nan", "none", "undefined"])]
        total = len(tags)
        if total == 0:
            return {"gb": np.nan, "fb": np.nan, "ld": np.nan, "total": 0}
        gb = tags.str.contains("ground").sum() / total * 100.0
        fb = tags.str.contains("fly").sum() / total * 100.0
        ld = tags.str.contains("line").sum() / total * 100.0
        return {"gb": gb, "fb": fb, "ld": ld, "total": total}

    def _tagged_table(df: pd.DataFrame) -> pd.DataFrame:
        rows = []
        if "pitch_type" not in df.columns:
            return pd.DataFrame()
        if "batter_side" in df.columns:
            side_col = df["batter_side"].astype(str).str.upper()
            df_r = df[side_col.str.startswith("R")]
            df_l = df[side_col.str.startswith("L")]
        else:
            df_r = df_l = df.iloc[0:0]
        for pt in df["pitch_type"].dropna().unique():
            df_pt = df[df["pitch_type"] == pt]
            df_pt_r = df_r[df_r["pitch_type"] == pt]
            df_pt_l = df_l[df_l["pitch_type"] == pt]
            stats_r = _tagged_rates(df_pt_r)
            stats_l = _tagged_rates(df_pt_l)
            rows.append([_pitch_label(pt), "RHH", stats_r["gb"], stats_r["fb"], stats_r["ld"], stats_r["total"]])
            rows.append([_pitch_label(pt), "LHH", stats_l["gb"], stats_l["fb"], stats_l["ld"], stats_l["total"]])
        return pd.DataFrame(rows, columns=["Pitch Type", "Split", "GB% (Tagged)", "FB% (Tagged)", "LD% (Tagged)", "Tagged Count"])
    
    # Create PDF
    with PdfPages(output_path) as pdf:
        # Title page
        fig = plt.figure(figsize=(8.5, 11), dpi=100)
        ax = fig.add_subplot(111)
        ax.axis('off')

        # Add Dirtbags logo at the top if available
        logo_path = _find_logo_path()
        if logo_path:
            try:
                logo_img = plt.imread(logo_path)
                ax_logo = fig.add_axes([0.16, 0.78, 0.68, 0.68 * 8.5 / 3 / 11])
                ax_logo.imshow(logo_img)
                ax_logo.axis('off')
            except Exception:
                # Fail silently if the logo cannot be loaded; keep the rest of the page
                pass
        
        disp_name = _abbrev_name(profile.full_name)
        title_text = f"{title_label}\n{disp_name}\n\n"
        title_text += f"Total Outings: {profile.total_outings}\n"
        title_text += f"Total Pitches: {profile.total_pitches}\n\n"
        if getattr(profile, 'player_id', None):
            title_text += f"Player ID: {profile.player_id}\n\n"
        if getattr(profile, 'position', None):
            title_text += f"Position: {profile.position}\n"
        bats_throws = []
        if getattr(profile, 'bats', None):
            bats_throws.append(f"Bats: {profile.bats}")
        if getattr(profile, 'throws', None):
            bats_throws.append(f"Throws: {profile.throws}")
        if bats_throws:
            title_text += " | ".join(bats_throws) + "\n"
        title_text += f"Last Updated: {profile.last_updated[:10]}"
        
        ax.text(0.5, 0.5, title_text, ha='center', va='center', 
                fontsize=18, fontweight='bold', transform=ax.transAxes)
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)
        
        # Pitch Location Plots with pitch-type legend
        fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), dpi=100)
        fig.suptitle('Pitch Location - Cumulative', fontsize=16, fontweight='bold')
        # Leave room on the right for an external legend (avoids title overlap)
        fig.subplots_adjust(top=0.9, right=0.78)
        pitch_types_all = df['pitch_type'].dropna().unique() if 'pitch_type' in df.columns else []
        colors_map = get_pitch_color_map(pitch_types_all) if len(pitch_color_map) == 0 else pitch_color_map
        legend_handles = []
        
        _plot_all_pitch_zone_heatmap(axes[0, 0], filtered['valid_locations'])
        legend_handles += _scatter_by_pitch_type(
            axes[0, 1],
            filtered['two_strike'].dropna(subset=['plate_x', 'plate_z']) if not filtered['two_strike'].empty else filtered['two_strike'],
            "plate_x",
            "plate_z",
            "2-Strike Pitches",
            "Horizontal Location (inches)",
            "Vertical Location (inches)",
            add_zone=True,
            colors_map=colors_map,
        )
        legend_handles += _scatter_by_pitch_type(
            axes[1, 0],
            filtered['whiffs'].dropna(subset=['plate_x', 'plate_z']) if not filtered['whiffs'].empty else filtered['whiffs'],
            "plate_x",
            "plate_z",
            "Whiffs",
            "Horizontal Location (inches)",
            "Vertical Location (inches)",
            add_zone=True,
            colors_map=colors_map,
        )
        legend_handles += _scatter_by_pitch_type(
            axes[1, 1],
            filtered['bip'].dropna(subset=['plate_x', 'plate_z']) if not filtered['bip'].empty else filtered['bip'],
            "plate_x",
            "plate_z",
            "Batted Balls in Play",
            "Horizontal Location (inches)",
            "Vertical Location (inches)",
            add_zone=True,
            colors_map=colors_map,
        )
        # Figure-level legend (unique handles) centered above charts (same style as trends page)
        if legend_handles:
            seen = set()
            uniq_handles = []
            for h in legend_handles:
                lbl = h.get_label()
                if lbl not in seen:
                    seen.add(lbl)
                    uniq_handles.append(h)
            fig.legend(
                uniq_handles,
                [h.get_label() for h in uniq_handles],
                title="Pitch Type",
                fontsize=8,
                title_fontsize=9,
                frameon=False,
                loc="center left",
                bbox_to_anchor=(0.90, 0.5),
                ncol=1,
            )
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches="tight", dpi=100)
        plt.close(fig)
        
        # Movement Plot
        fig = plt.figure(figsize=(11, 8.5), dpi=100)
        fig.suptitle('Pitch Movement - Cumulative', fontsize=16, fontweight='bold')
        
        ax = plt.subplot(1, 1, 1)
        valid_mov = filtered['valid_movement']
        pitch_types = []
        if len(valid_mov) > 0:
            pitch_types = valid_mov['pitch_type'].dropna().unique()
            colors_map = get_pitch_color_map(pitch_types) if len(pitch_color_map) == 0 else pitch_color_map
            for pt in pitch_types:
                pt_data = valid_mov[valid_mov['pitch_type'] == pt]
                if len(pt_data) > 0:
                    color = colors_map.get(pt, DEFAULT_PITCH_COLOR)
                    ax.scatter(pt_data['hb'], pt_data['ivb'], label=_pitch_label(pt), 
                             alpha=0.5, s=20, c=[color], edgecolors='none')
        ax.axhline(y=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
        ax.set_xlabel('Horizontal Break (inches)', fontsize=11)
        ax.set_ylabel('Induced Vertical Break (inches)', fontsize=11)
        ax.set_title('Pitch Movement: HB vs IVB', fontsize=13, fontweight='bold')
        if len(pitch_types) <= 10:
            ax.legend(loc='best', fontsize=9, ncol=2)
        ax.grid(True, alpha=0.2)
        
        plt.tight_layout()
        pdf.savefig(fig, bbox_inches='tight', dpi=100)
        plt.close(fig)

        # Spray + Spin (cumulative)
        bip = df[df["pitch_call"] == "InPlay"].copy() if "pitch_call" in df.columns else pd.DataFrame()
        batter_side = bip["batter_side"] if "batter_side" in bip.columns else pd.Series([], dtype=str)
        batter_side = batter_side.astype(str).str.upper()
        mask_l = batter_side.str.contains("L", na=False)
        mask_r = batter_side.str.contains("R", na=False)
        bip_l = bip.loc[mask_l.reindex(bip.index, fill_value=False)]
        bip_r = bip.loc[mask_r.reindex(bip.index, fill_value=False)]

        fig = plt.figure(figsize=(11, 8.5), dpi=150)
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[2.0, 1.0])

        ax_s1 = fig.add_subplot(gs[0, 0])
        _fan_chart(ax_s1, bip_l, "Hits vs LHH")

        ax_s2 = fig.add_subplot(gs[1, 0])
        _fan_chart(ax_s2, bip_r, "Hits vs RHH")

        ax_spin = fig.add_subplot(gs[:, 1], projection="polar")
        spin_df = df.dropna(subset=["spin_axis", "spin_rate"]) if "spin_axis" in df and "spin_rate" in df else df.assign(spin_axis=np.nan, spin_rate=np.nan)
        _spin_axis(ax_spin, spin_df)

        fig.suptitle("Spray & Spin - Cumulative", fontsize=16, fontweight="bold")
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Pitch trends by outing (velo, spin, usage, whiff%, strike%, IVB, HB)
        trend_df_outing = _build_outing_trends(profile)
        if not trend_df_outing.empty:
            metrics = [
                ("velo", "Velo (avg mph)"),
                ("spin", "Spin Rate (rpm)"),
                ("usage_pct", "Usage %"),
                ("whiff_pct", "Whiff %"),
                ("strike_pct", "Strike %"),
                ("ivb", "IVB (in)"),
                ("hb", "HB (in)"),
            ]
            fig_tr = plt.figure(figsize=(11, 8.5), dpi=140)
            fig_tr.subplots_adjust(right=0.78, top=0.88)
            gs_tr = fig_tr.add_gridspec(3, 3)
            axes = []
            trend_color_map = get_pitch_color_map(trend_df_outing["pitch_type"].dropna().unique()) if len(pitch_color_map) == 0 else pitch_color_map
            for i, (col, label) in enumerate(metrics):
                row = i // 3
                col_idx = i % 3
                ax = fig_tr.add_subplot(gs_tr[row, col_idx])
                axes.append(ax)
                for pt in trend_df_outing["pitch_type"].dropna().unique():
                    sub = trend_df_outing[trend_df_outing["pitch_type"] == pt]
                    color = trend_color_map.get(pt, DEFAULT_PITCH_COLOR)
                    ax.plot(sub["x_idx"], sub[col], marker="o", linewidth=1.5, label=pt, color=color)
                ax.set_title(label, fontsize=11, fontweight="bold")
                ax.set_xticks(trend_df_outing["x_idx"].unique())
                ax.set_xticklabels(trend_df_outing["outing_label"].unique(), rotation=45, ha="right", fontsize=8)
                ax.grid(True, alpha=0.3)
            # Single legend across plots, placed outside right
            handles, labels = axes[0].get_legend_handles_labels()
            labels = [_pitch_label(lab) for lab in labels]
            fig_tr.legend(
                handles,
                labels,
                loc="center left",
                bbox_to_anchor=(1.02, 0.5),
                ncol=1,
                fontsize=8,
                frameon=False,
            )
            fig_tr.suptitle("Pitch Trends by Outing", fontsize=16, fontweight="bold")
            fig_tr.tight_layout(rect=[0, 0, 0.95, 0.94])
            pdf.savefig(fig_tr, bbox_inches="tight")
            plt.close(fig_tr)

        # Summary Tables
        def _save_summary_table(summary, title, header_color):
            fig, ax = plt.subplots(figsize=(11, 8.5), dpi=100)
            ax.axis('off')
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            if summary is None or len(summary) == 0:
                ax.text(0.5, 0.5, "No data", ha='center', va='center', fontsize=14)
                pdf.savefig(fig, bbox_inches='tight', dpi=100)
                plt.close(fig)
                return
            table = ax.table(
                cellText=summary.values,
                colLabels=summary.columns,
                cellLoc='center',
                loc='center',
                bbox=[0, 0, 1, 1],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 2)
            for i in range(len(summary.columns)):
                table[(0, i)].set_facecolor(header_color)
                table[(0, i)].set_text_props(weight='bold', color='white')
            pdf.savefig(fig, bbox_inches='tight', dpi=100)
            plt.close(fig)

        _save_summary_table(arsenal_summary, 'Arsenal Summary - Cumulative', '#4CAF50')
        _save_summary_table(contact_summary, 'Contact Outcomes - Cumulative', '#2196F3')
        _save_summary_table(plate_discipline, 'Plate Discipline - Cumulative', '#FF9800')

        # Inning Success table (e.g. for in-season report)
        if inning_success_df is not None and not inning_success_df.empty:
            fig, ax = plt.subplots(figsize=(11, 8.5), dpi=100)
            ax.axis('off')
            ax.set_title(inning_success_title, fontsize=16, fontweight='bold', pad=20)
            # Format percentages for display
            display_df = inning_success_df.copy()
            for col in ['PA Win %', 'Whiff %', 'Weak Contact %', 'Dominance %', 'Inning Success %']:
                if col in display_df.columns:
                    display_df[col] = display_df[col].apply(lambda x: f'{float(x):.1f}%' if pd.notna(x) else '—')
            cell_text = display_df.values.tolist()
            col_labels = list(display_df.columns)
            table = ax.table(
                cellText=cell_text,
                colLabels=col_labels,
                cellLoc='center',
                loc='center',
                bbox=[0, 0, 1, 1],
            )
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 2)
            for i in range(len(col_labels)):
                table[(0, i)].set_facecolor('#673AB7')
                table[(0, i)].set_text_props(weight='bold', color='white')
            pdf.savefig(fig, bbox_inches='tight', dpi=100)
            plt.close(fig)
        
        # Metadata
        d = pdf.infodict()
        d['Title'] = f'{title_label} - {profile.full_name}'
        d['Author'] = 'Dirtbags Data Team'
        d['Subject'] = f"Cumulative Statistics - {profile.total_outings} outings, {profile.total_pitches} pitches"


def _outings_in_window(profile, start: date, end: Optional[date] = None):
    """Return outings whose date falls in [start, end] (end optional)."""
    selected = []
    for outing in getattr(profile, "outings", []):
        meta = outing.get("metadata", {})
        dt = _parse_outing_date(meta.get("date"))
        if not dt:
            continue
        outing_date = dt.date()
        if outing_date < start:
            continue
        if end is not None and outing_date > end:
            continue
        selected.append(outing)
    return selected


def generate_windowed_player_profile_report(
    profile,
    output_path: str,
    start: date,
    end: Optional[date] = None,
    title_label: str = "Player Profile",
    inning_success_title: str = "Inning Success",
    empty_message: str = "No data available for profile in the selected date window",
) -> None:
    """Generate a profile PDF using only outings between start and end (inclusive)."""
    season_outings = _outings_in_window(profile, start, end)
    if not season_outings:
        raise ValueError(empty_message)

    # Build combined in-season DataFrame and compute inning success metrics for the table
    season_frames = [o.get("data") for o in season_outings if isinstance(o.get("data"), pd.DataFrame)]
    if season_frames:
        combined_season = pd.concat(season_frames, ignore_index=True)
        inning_success_df = compute_inning_success_metrics(combined_season)
    else:
        inning_success_df = None

    # Snapshot original state
    orig_outings = getattr(profile, "outings", None)
    orig_last_updated = getattr(profile, "last_updated", None)
    orig_total_outings = getattr(profile, "total_outings", None)
    orig_total_pitches = getattr(profile, "total_pitches", None)

    try:
        # Restrict profile to in-season outings and recompute totals
        profile.outings = season_outings
        if hasattr(profile, "_recompute_totals"):
            profile._recompute_totals()

        # Reuse the standard report generator with inning success table
        generate_player_profile_report(
            profile,
            output_path,
            inning_success_df=inning_success_df,
            title_label=title_label,
            inning_success_title=inning_success_title,
        )
    finally:
        # Restore original state so the in-memory profile remains cumulative
        if orig_outings is not None:
            profile.outings = orig_outings
        if orig_last_updated is not None:
            profile.last_updated = orig_last_updated
        if orig_total_outings is not None:
            profile.total_outings = orig_total_outings
        if orig_total_pitches is not None:
            profile.total_pitches = orig_total_pitches


def generate_inseason_player_profile_report(
    profile,
    output_path: str,
    cutoff: date = DATE_CUTOFF_2026,
) -> None:
    """
    Generate in-season player profile PDF report using only outings on/after cutoff.
    Layout/visuals are identical to the standard cumulative profile.
    """
    generate_windowed_player_profile_report(
        profile,
        output_path,
        start=cutoff,
        title_label="2026 In-Season Player Profile",
        inning_success_title="Inning Success — In-Season",
        empty_message="No in-season data available for profile",
    )


def generate_fall_2026_player_profile_report(
    profile,
    output_path: str,
    start: date = FALL_2026_START,
    end: date = FALL_2026_END,
) -> None:
    """Generate a Fall 2026 profile using outings from 2026-09-01 through 2027-02-12."""
    generate_windowed_player_profile_report(
        profile,
        output_path,
        start=start,
        end=end,
        title_label="Fall 2026 Player Profile",
        inning_success_title="Inning Success — Fall 2026",
        empty_message="No Fall 2026 data available for profile",
    )

