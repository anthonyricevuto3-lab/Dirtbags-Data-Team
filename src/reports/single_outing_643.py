"""
Single-outing report generator (643Charts-inspired) for Dirtbags.

Layout:
- Fan/spray charts vs LHH and vs RHH (batted-ball distribution)
- Spin-axis polar scatter by pitch type
- Pitch-type outcome table (PA/AB/H/1B/2B/3B/HR/K/BB/BA/SLG/OPS/WOBA/BABIP)
- Pitch-type arsenal table (Pitches, Pitch%, Velo, Spin, Spin Axis, IVB, HB, Vert Appr, Horz Appr, Extension, Release)
"""

import math
from pathlib import Path
from typing import Dict, Optional, Union, List

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Wedge, Rectangle
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

from ..metrics import (
    calculate_usage_rate,
    calculate_velocity_avg,
    calculate_spin_avg,
    calculate_ivb_avg,
    calculate_hb_avg,
    calculate_extension_avg,
    calculate_release_height_avg,
    calculate_release_side_avg,
    generate_arsenal_summary,
    generate_plate_discipline_summary,
    generate_contact_summary,
)
from .example_style import EXAMPLE_COLORS
from ..pitch_colors import get_pitch_color, get_pitch_color_map, DEFAULT_PITCH_COLOR


def _abbrev_pitch(pt: str) -> str:
    if not pt:
        return pt
    key = pt.lower().replace("-", "").replace(" ", "")
    if key == "2seamfastball":
        return "2 seam"
    if key in ("4seamfastball", "fourseamfastball", "fourseam"):
        return "4 seam"
    return pt


def _pitch_label(pt: str) -> str:
    return _abbrev_pitch(pt)


# In single-outing reports, combine OneSeamFastball (and variants) with Fastball
_ONE_SEAM_FASTBALL_KEYS = {"oneseamfastball", "oneseamfast ball", "oneseam", "1seamfastball", "1seam"}


def _normalize_pitch_type_single_outing(df: pd.DataFrame) -> pd.DataFrame:
    """Map OneSeamFastball and variants to Fastball so they are combined in single-outing reports."""
    if df is None or df.empty or "pitch_type" not in df.columns:
        return df
    df = df.copy()
    pt = df["pitch_type"].astype(str)
    key = pt.str.lower().str.strip().str.replace(" ", "").str.replace("-", "")
    is_one_seam = key.isin(_ONE_SEAM_FASTBALL_KEYS)
    if is_one_seam.any():
        df.loc[is_one_seam, "pitch_type"] = "Fastball"
    return df


def _ensure_plate_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure plate_x / plate_z exist by deriving from common alternates."""
    df = df.copy()
    if "plate_x" not in df.columns:
        for cand in ["plate_loc_side", "px", "PlateLocSide"]:
            if cand in df.columns:
                df["plate_x"] = df[cand]
                break
    if "plate_z" not in df.columns:
        for cand in ["plate_loc_height", "pz", "PlateLocHeight"]:
            if cand in df.columns:
                df["plate_z"] = df[cand]
                break
    if "plate_x" in df.columns:
        df["plate_x"] = pd.to_numeric(df["plate_x"], errors="coerce")
    if "plate_z" in df.columns:
        df["plate_z"] = pd.to_numeric(df["plate_z"], errors="coerce")
    return df


def _fan_chart(ax, df_hits: pd.DataFrame, title: str):
    # bins of spray angles (degrees)
    bins = [-90, -60, -30, -10, 10, 30, 60, 90]
    bin_labels = ["7%", "16%", "39%", "28%", "11%", "17%", "??"]
    counts, _ = np.histogram(df_hits["spray_angle"].dropna(), bins=bins)
    total = counts.sum()
    if total == 0:
        total = 1
    percents = counts / total
    angles = list(zip(bins[:-1], bins[1:]))
    cmap = [
        "#dcead2",
        "#b0d18c",
        "#87b86e",
        "#5d9c52",
        "#91c07c",
        "#6da45f",
        "#5f8f55",
    ]
    for i, (start, end) in enumerate(angles):
        theta1 = 90 - end
        theta2 = 90 - start
        color = cmap[i % len(cmap)]
        w = Wedge(center=(0, 0), r=1.0, theta1=theta1, theta2=theta2, facecolor=color, edgecolor="white")
        ax.add_patch(w)
        ang = math.radians((theta1 + theta2) / 2)
        ax.text(0.6 * math.cos(ang), 0.6 * math.sin(ang), f"{int(percents[i]*100)}%", ha="center", va="center", fontsize=10, color="#1f1f1f")
    ax.set_xlim(-1, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(title, fontsize=12, fontweight="bold", color=EXAMPLE_COLORS["primary"])


def _spin_axis_polar(ax, df: pd.DataFrame):
    if "spin_axis" not in df.columns:
        ax.set_axis_off()
        return
    pitch_types = df["pitch_type"].dropna().unique()
    color_map = get_pitch_color_map(pitch_types)
    for pt in pitch_types:
        c = color_map.get(pt, DEFAULT_PITCH_COLOR)
        sub = df[df["pitch_type"] == pt]
        theta = np.deg2rad(sub["spin_axis"].dropna())
        r = sub["spin_rate"].fillna(2000)
        ax.scatter(theta, r, s=15, alpha=0.7, color=c, label=_pitch_label(pt))
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_title("Spin Axis", fontsize=12, fontweight="bold", color=EXAMPLE_COLORS["primary"])
    if len(pitch_types) > 0:
        ax.legend(loc="upper right", fontsize=8)


def _pitch_outcome_table(df: pd.DataFrame) -> pd.DataFrame:
    # Approximate outcome table by pitch_type
    grouped = df.groupby("pitch_type")
    rows = []
    for pt, g in grouped:
        pa = len(g)
        ab = len(g[g["pitch_call"].isin(["StrikeCalled", "StrikeSwinging", "FoulBallNotFieldable", "InPlay"])])
        singles = int((g["hit_type"] == "Single").sum()) if "hit_type" in g.columns else 0
        doubles = int((g["hit_type"] == "Double").sum()) if "hit_type" in g.columns else 0
        triples = int((g["hit_type"] == "Triple").sum()) if "hit_type" in g.columns else 0
        hr = int((g["hit_type"] == "HomeRun").sum()) if "hit_type" in g.columns else 0
        hits = singles + doubles + triples + hr
        k = len(g[g["pitch_call"] == "StrikeSwinging"])
        bb = len(g[g["pitch_call"] == "BallCalled"])
        ba = hits / ab if ab else 0
        slg = (singles + 2 * doubles + 3 * triples + 4 * hr) / ab if ab else 0
        ops = 0  # placeholder; data limited
        rows.append([_abbrev_pitch(pt), pa, ab, hits, singles, doubles, triples, hr, k, bb, round(ba, 3), round(slg, 3), ops, np.nan, np.nan])
    cols = ["Pitch Type", "PA", "AB", "H", "1B", "2B", "3B", "HR", "K", "BB", "BA", "SLG", "OPS", "WOBA", "BABIP"]
    return pd.DataFrame(rows, columns=cols)


def _arsenal_table(df: pd.DataFrame) -> pd.DataFrame:
    pitch_types = df["pitch_type"].dropna().unique()
    rows = []
    total = len(df)
    for pt in pitch_types:
        rows.append([
            _abbrev_pitch(pt),
            len(df[df["pitch_type"] == pt]),
            round(calculate_usage_rate(df, pt), 1),
            round(calculate_velocity_avg(df, pt), 1),
            round(calculate_spin_avg(df, pt), 0),
            round(df[df["pitch_type"] == pt]["spin_axis"].mean() if "spin_axis" in df else np.nan, 1),
            round(calculate_ivb_avg(df, pt), 1),
            round(calculate_hb_avg(df, pt), 1),
            round(df[df["pitch_type"] == pt]["vert_appr_angle"].mean() if "vert_appr_angle" in df else np.nan, 1),
            round(df[df["pitch_type"] == pt]["horz_appr_angle"].mean() if "horz_appr_angle" in df else np.nan, 1),
            round(calculate_extension_avg(df, pt), 2),
            round(calculate_release_height_avg(df, pt), 2),
            round(calculate_release_side_avg(df, pt), 2),
        ])
    cols = ["Pitch Type", "Pitches", "Pitch%", "Velo", "SR AVG", "Spin Axis", "IVB", "HB", "Vert Appr", "Horz Appr", "Extension", "Release H", "Release S"]
    return pd.DataFrame(rows, columns=cols)


def _pitch_location_page(pdf, df: pd.DataFrame, title: str):
    """Profile-style pitch location page: all, two-strike, whiff, BIP with legend outside."""
    fig, axes = plt.subplots(2, 2, figsize=(11, 8.5), dpi=120)
    fig.subplots_adjust(right=0.78, top=0.9)
    fig.suptitle("Pitch Location - Single Outing", fontsize=16, fontweight="bold", color=COLORS["text"])

    def _panel(ax, data: pd.DataFrame, panel_title: str):
        if data.empty or not {"plate_x", "plate_z"}.issubset(data.columns):
            ax.axis("off")
            ax.text(0.5, 0.5, "No data", ha="center", va="center", fontsize=10, color=COLORS["text"])
            return []
        # Strike zone (feet)
        sz_w = 19.94 / 12
        sz_h = 25.79 / 12
        sz_bot = 1.5
        rect = Rectangle((-sz_w / 2, sz_bot), sz_w, sz_h, edgecolor="black", facecolor="none", linewidth=1.2, linestyle="--", zorder=1)
        ax.add_patch(rect)
        handles = []
        pts = data["pitch_type"].dropna().unique()
        color_map = get_pitch_color_map(pts)
        for pt in pts:
            sub = data[data["pitch_type"] == pt]
            lbl = _pitch_label(pt)
            x_ft = sub["plate_x"] / 12.0
            z_ft = sub["plate_z"] / 12.0
            color = color_map.get(pt, DEFAULT_PITCH_COLOR)
            ax.scatter(x_ft, z_ft, s=32, alpha=0.7, c=[color], edgecolors="white", linewidths=0.35, label=lbl, zorder=2)
            handles.append(Line2D([0], [0], marker='o', color='white', markerfacecolor=color, markeredgecolor='white', markersize=6, label=lbl))
        ax.set_xlim(-2.5, 2.5)
        ax.set_ylim(0, 5)
        ax.set_aspect("equal", adjustable="box")
        ax.set_title(panel_title, fontsize=12, fontweight="bold")
        ax.set_xlabel("Pitch Length (ft)")
        ax.set_ylabel("Pitch Height (ft)")
        ax.grid(True, linestyle="--", alpha=0.5)
        return handles

    handles_all = []
    df_all = df.dropna(subset=["plate_x", "plate_z"]) if {"plate_x", "plate_z"}.issubset(df.columns) else pd.DataFrame()
    df_two = df[df["strikes"] == 2] if "strikes" in df.columns else pd.DataFrame()
    df_whiff = df[df["whiff"] == True] if "whiff" in df.columns else pd.DataFrame()
    df_bip = df[df["pitch_call"] == "InPlay"] if "pitch_call" in df.columns else pd.DataFrame()

    handles_all += _panel(axes[0, 0], df_all, "All Pitches")
    handles_all += _panel(axes[0, 1], df_two.dropna(subset=["plate_x", "plate_z"]) if not df_two.empty else df_two, "Two-Strike Pitches")
    handles_all += _panel(axes[1, 0], df_whiff.dropna(subset=["plate_x", "plate_z"]) if not df_whiff.empty else df_whiff, "Whiff Pitches")
    handles_all += _panel(axes[1, 1], df_bip.dropna(subset=["plate_x", "plate_z"]) if not df_bip.empty else df_bip, "BIP Pitches")

    if handles_all:
        seen = set()
        uniq = []
        for h in handles_all:
            lbl = h.get_label()
            if lbl not in seen:
                seen.add(lbl)
                uniq.append(h)
        fig.legend(uniq, [h.get_label() for h in uniq],
                   title="Pitch Type", fontsize=8, title_fontsize=9,
                   frameon=False, loc="center left", bbox_to_anchor=(0.80, 0.5))

    pdf.savefig(fig, bbox_inches="tight", dpi=120)
    plt.close(fig)


def _pitch_result_summary(df: pd.DataFrame) -> str:
    total = len(df)
    strikes = df["strike"].sum() if "strike" in df.columns else 0
    whiffs = df["whiff"].sum() if "whiff" in df.columns else 0
    bip = len(df[df["pitch_call"] == "InPlay"]) if "pitch_call" in df.columns else 0
    balls = len(df[df["pitch_call"] == "BallCalled"]) if "pitch_call" in df.columns else 0
    return f"Pitches: {total}\nStrikes: {int(strikes)}\nWhiffs: {int(whiffs)}\nIn Play: {bip}\nBalls: {balls}"


def _extract_outing_date(df: pd.DataFrame) -> str:
    if "date" in df.columns:
        dt = pd.to_datetime(df["date"], errors="coerce").dropna()
        if len(dt) > 0:
            return dt.iloc[0].strftime("%m/%d/%Y")
    return "N/A"


def _format_outing_title(header: Union[str, Dict], outing_date: str) -> str:
    """Return title like 'F. Lastname - Outing from MM/DD/YYYY'."""
    name = None
    if isinstance(header, dict):
        name = header.get("name")
    elif isinstance(header, str):
        name = header
    name = (name or "").strip()
    if name:
        parts = name.split()
        if len(parts) >= 2:
            first_initial = parts[0][0] + "."
            last = " ".join(parts[1:])
            return f"{first_initial} {last} - Outing from {outing_date}"
    return f"Outing from {outing_date}"


def generate_single_outing_643(
    df: pd.DataFrame,
    output_path: str,
    title: str = "Single Outing",
    game_info: Optional[Dict[str, str]] = None,
    header: Optional[Dict[str, str]] = None,
):
    """
    Generate a single-outing PDF in 643Charts-inspired layout.
    """
    # Clean and normalize Trackman columns so plate_x/plate_z etc. exist
    df = clean_trackman(df, strict=False)
    df = _ensure_plate_columns(df)
    # Combine OneSeamFastball with Fastball in single-outing reports
    df = _normalize_pitch_type_single_outing(df)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Derive hitter handedness masks safely
    has_batter_side = "batter_side" in df.columns
    batter_side = df["batter_side"].astype(str) if has_batter_side else pd.Series("", index=df.index)
    mask_l_full = batter_side.str.upper().str.startswith("L") if has_batter_side else pd.Series(False, index=df.index)
    mask_r_full = batter_side.str.upper().str.startswith("R") if has_batter_side else pd.Series(False, index=df.index)
    bip = df[df["pitch_call"] == "InPlay"] if "pitch_call" in df.columns else pd.DataFrame()
    bip_l = bip.loc[mask_l_full.reindex(bip.index, fill_value=False)]
    bip_r = bip.loc[mask_r_full.reindex(bip.index, fill_value=False)]

    outing_date = _extract_outing_date(df)
    outing_title = _format_outing_title(header, outing_date)

    with PdfPages(out_path) as pdf:
        # Page 1: fan charts + spin axis (match profile layout)
        fig = plt.figure(figsize=(11, 8.5), dpi=170)
        gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[2.0, 1.0])
        ax1 = fig.add_subplot(gs[0, 0])
        _fan_chart(ax1, bip_l if len(bip_l) else bip, "Hits vs LHH")
        ax2 = fig.add_subplot(gs[1, 0])
        _fan_chart(ax2, bip_r if len(bip_r) else bip, "Hits vs RHH")
        ax3 = fig.add_subplot(gs[:, 1], projection="polar")
        _spin_axis(ax3, df)
        header_text = title
        if header:
            ht_parts = []
            if header.get("name"):
                ht_parts.append(header["name"])
            if header.get("position"):
                ht_parts.append(f"{header['position']}")
            bt_parts = []
            if header.get("bats"):
                bt_parts.append(f"Bats: {header['bats']}")
            if header.get("throws"):
                bt_parts.append(f"Throws: {header['throws']}")
            if bt_parts:
                ht_parts.append(" | ".join(bt_parts))
            if ht_parts:
                header_text = " • ".join(ht_parts)
        fig.suptitle(f"{header_text}  •  Outing Date: {outing_date}", fontsize=16, fontweight="bold", color=EXAMPLE_COLORS["primary"])
        # pitch result summary
        summary = _pitch_result_summary(df)
        fig.text(0.05, 0.08, summary, fontsize=9, color=EXAMPLE_COLORS["text"], bbox=dict(facecolor="white", alpha=0.7, edgecolor="none"))
        pdf.savefig(fig, bbox_inches="tight", dpi=150)
        plt.close(fig)

        # Page 2: Pitch Location (profile-style)
        _pitch_location_page(pdf, df, outing_title)

        # Page 3: Summary tables (match profile format minus trends)
        arsenal_summary = generate_arsenal_summary(df)
        contact_summary = generate_contact_summary(df)
        plate_discipline = generate_plate_discipline_summary(df)

        def _display_df(table_df: pd.DataFrame) -> pd.DataFrame:
            """Return a copy with NaNs replaced by 0 for numeric columns to avoid 'nan' in tables."""
            tbl = table_df.copy()
            num_cols = tbl.select_dtypes(include=[np.number]).columns
            tbl[num_cols] = tbl[num_cols].fillna(0)
            return tbl

        # Arsenal Summary
        fig_as, ax_as = plt.subplots(figsize=(11, 8.5), dpi=100)
        ax_as.axis('off')
        ax_as.set_title('Arsenal Summary - Single Outing', fontsize=16, fontweight='bold', pad=20)
        table = ax_as.table(
            cellText=arsenal_summary.values,
            colLabels=arsenal_summary.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        for i in range(len(arsenal_summary.columns)):
            table[(0, i)].set_facecolor('#4CAF50')
            table[(0, i)].set_text_props(weight='bold', color='white')
        pdf.savefig(fig_as, bbox_inches='tight', dpi=100)
        plt.close(fig_as)

        # Contact Outcomes
        fig_co, ax_co = plt.subplots(figsize=(11, 8.5), dpi=100)
        ax_co.axis('off')
        ax_co.set_title('Contact Outcomes - Single Outing', fontsize=16, fontweight='bold', pad=20)
        contact_display = _display_df(contact_summary)
        table = ax_co.table(
            cellText=contact_display.values,
            colLabels=contact_display.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        for i in range(len(contact_summary.columns)):
            table[(0, i)].set_facecolor('#2196F3')
            table[(0, i)].set_text_props(weight='bold', color='white')
        pdf.savefig(fig_co, bbox_inches='tight', dpi=100)
        plt.close(fig_co)

        # Plate Discipline
        fig_pd, ax_pd = plt.subplots(figsize=(11, 8.5), dpi=100)
        ax_pd.axis('off')
        ax_pd.set_title('Plate Discipline - Single Outing', fontsize=16, fontweight='bold', pad=20)
        plate_display = _display_df(plate_discipline)
        table = ax_pd.table(
            cellText=plate_display.values,
            colLabels=plate_display.columns,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1],
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 2)
        for i in range(len(plate_discipline.columns)):
            table[(0, i)].set_facecolor('#FF9800')
            table[(0, i)].set_text_props(weight='bold', color='white')
        pdf.savefig(fig_pd, bbox_inches='tight', dpi=100)
        plt.close(fig_pd)
"""
Single-outing report in a 643Charts-inspired layout.

Generates:
- Fan/spray distribution vs LHH/RHH (BIP% by sector)
- Spin axis polar scatter by pitch type
- Outcome table by pitch type (PA, AB, H, 1B/2B/3B/HR, K, BB, BA, SLG, OPS, wOBA, BABIP)
- Arsenal table by pitch type (Pitches, Usage%, Velo, Spin, Spin Axis, IVB, HB, Vert Appr, Horz Appr, Extension, Release Side/Height)
"""

import math
from pathlib import Path
from typing import Dict, List, Tuple, Union

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Wedge
import numpy as np
import pandas as pd

from ..schemas import clean_trackman

# Color palette (higher contrast)
COLORS = {
    "bg": "#f8f8f2",
    "table_header": "#4f7f3b",
    "table_header_text": "#ffffff",
    "table_band": "#e6eddc",
    "text": "#111111",
    "fastball": get_pitch_color("fastball"),
    "slider": get_pitch_color("slider"),
    "changeup": get_pitch_color("changeup"),
    "curve": get_pitch_color("curveball"),
}

# Spray result color key
PLAY_RESULT_COLORS = {
    "Out": "#37474f",
    "Single": "#2e7d32",
    "Double": "#1565c0",
    "Triple": "#6a1b9a",
    "HomeRun": "#c62828",
    "Other": "#616161",
}

# Fair territory bounds (foul lines ~±45° around CF = 0)
FAIR_ANGLE_MIN, FAIR_ANGLE_MAX = -45, 45
# Split fair territory into 5 equal slices for 10 total wedges (5 infield, 5 outfield)
FAIR_SECTOR_BOUNDS = list(np.linspace(FAIR_ANGLE_MIN, FAIR_ANGLE_MAX, num=6))


def _fan_chart(ax, bip_df: pd.DataFrame, title: str):
    """Draw spray fan chart split into 4 infield + 4 outfield sectors (fair only)."""
    ax.set_facecolor(COLORS["bg"])
    ax.axis("off")

    # Normalize angles/distances and keep only fair territory
    bip = bip_df.copy()
    # Derive horizontal angle: priority Bearing -> Direction -> SprayAngle -> atan2(PositionAt110X, PositionAt110Y)
    bearing = pd.to_numeric(bip["bearing"], errors="coerce") if "bearing" in bip else pd.Series(np.nan, index=bip.index)
    direction = pd.to_numeric(bip["direction"], errors="coerce") if "direction" in bip else pd.Series(np.nan, index=bip.index)
    spray_angle = pd.to_numeric(bip["spray_angle"], errors="coerce") if "spray_angle" in bip else pd.Series(np.nan, index=bip.index)
    pos110x = pd.to_numeric(bip["positionat110x"], errors="coerce") if "positionat110x" in bip else pd.Series(np.nan, index=bip.index)
    pos110y = pd.to_numeric(bip["positionat110y"], errors="coerce") if "positionat110y" in bip else pd.Series(np.nan, index=bip.index)
    derived = pd.Series(np.degrees(np.arctan2(pos110x, pos110y)), index=bip.index)
    plot_angle = bearing.where(~bearing.isna(), direction)
    plot_angle = plot_angle.where(~plot_angle.isna(), spray_angle)
    plot_angle = plot_angle.where(~plot_angle.isna(), derived)
    plot_angle = plot_angle.fillna(0)  # final fallback straightaway
    # Constrain to fair territory (foul lines)
    plot_angle = plot_angle.clip(lower=FAIR_ANGLE_MIN, upper=FAIR_ANGLE_MAX)
    bip["plot_angle"] = plot_angle
    bip["distance"] = pd.to_numeric(bip.get("distance"), errors="coerce")
    bip = bip.dropna(subset=["plot_angle", "distance"])

    total = len(bip)
    total_for_pct = max(total, 1)  # keep wedges visible even with 0 fair balls

    # Distance threshold for infield vs outfield (feet)
    dist = bip["distance"]
    infield_mask = dist <= 150
    outfield_mask = dist > 150
    # If distance missing, treat all as outfield to avoid overcrowding inner wedge
    if infield_mask.isna().all():
        infield_mask = pd.Series([False] * len(bip), index=bip.index)
        outfield_mask = pd.Series([True] * len(bip), index=bip.index)

    # Draw field background (grass/dirt + fence) using a diamond infield
    fence_points = []
    fence_specs = [(-90, 335), (-40, 380), (0, 390), (40, 380), (90, 330)]
    max_fence = 400
    for ang, dist_ft in fence_specs:
        r = dist_ft / max_fence
        fence_points.append((r * math.sin(math.radians(ang)), r * math.cos(math.radians(ang))))
    fence_polygon = plt.Polygon(fence_points, closed=False, fill=None, edgecolor="#2e7d32", linewidth=2.0, alpha=0.8, zorder=1)
    ax.add_patch(fence_polygon)
    # Outfield grass (half-field)
    grass = Wedge((0, 0), 1.0, 90 - FAIR_ANGLE_MAX, 90 - FAIR_ANGLE_MIN, facecolor="#7fbf7f", edgecolor="none", alpha=0.25, zorder=0)
    ax.add_patch(grass)
    # Warning track (outer band)
    warning_track = Wedge((0, 0), 1.0, 90 - FAIR_ANGLE_MAX, 90 - FAIR_ANGLE_MIN, width=0.05, facecolor="#c28f5a", edgecolor="none", alpha=0.5, zorder=2)
    ax.add_patch(warning_track)
    # Infield dirt fill (everything inside the dashed boundary)
    infield_fill = Wedge((0, 0), 0.5, 90 - FAIR_ANGLE_MAX, 90 - FAIR_ANGLE_MIN, facecolor="#d2b48c", edgecolor="none", alpha=0.9, zorder=2.6)
    ax.add_patch(infield_fill)
    spray = bip["plot_angle"]
    sectors = list(zip(FAIR_SECTOR_BOUNDS[:-1], FAIR_SECTOR_BOUNDS[1:]))
    for (start, end) in sectors:
        # infield wedge (inner ring)
        sector_in = bip[(spray >= start) & (spray < end) & infield_mask]
        pct_in = int(round(len(sector_in) / total_for_pct * 100))
        theta1 = 90 - end
        theta2 = 90 - start
        # Keep infield clean (no sector coloring); only draw thin borders for readability
        wedge_in = Wedge(center=(0, 0), r=0.5, theta1=theta1, theta2=theta2, facecolor="none", edgecolor="#ffffff", linewidth=0.6)
        ax.add_patch(wedge_in)
        mid = (theta1 + theta2) / 2
        r_text = 0.42  # raise label further to fit multi-digit values comfortably
        ax.text(r_text * math.cos(math.radians(mid)), r_text * math.sin(math.radians(mid)), f"{pct_in}%", ha="center", va="center", fontsize=9, color=COLORS["text"])

        # outfield wedge (outer ring)
        sector_out = bip[(spray >= start) & (spray < end) & outfield_mask]
        pct_out = int(round(len(sector_out) / total_for_pct * 100))
        wedge_out = Wedge(center=(0, 0), r=1.0, theta1=theta1, theta2=theta2, facecolor=COLORS["table_header"], edgecolor="#ffffff")
        ax.add_patch(wedge_out)
        r_text_out = 0.75
        ax.text(r_text_out * math.cos(math.radians(mid)), r_text_out * math.sin(math.radians(mid)), f"{pct_out}%", ha="center", va="center", fontsize=9, color="white")

    # Scatter actual BIP locations using direction/spray and distance; color by result
    pts = bip[["plot_angle", "distance", "hit_type", "pitch_call"]].dropna(subset=["plot_angle", "distance"])
    if len(pts) > 0:
        def _result_label(row):
            ht = str(row.get("hit_type") or "").strip()
            pc = str(row.get("pitch_call") or "").strip()
            if ht.lower().startswith("single"):
                return "Single"
            if ht.lower().startswith("double"):
                return "Double"
            if ht.lower().startswith("triple"):
                return "Triple"
            if ht.lower().startswith("home"):
                return "HomeRun"
            # anything in play without a hit_type -> out
            if pc == "InPlay":
                return "Out"
            return "Other"

        # Prefer landing bearing for plotting; fallback to computed plot_angle
        scatter_angle = pd.to_numeric(pts.get("bearing"), errors="coerce") if "bearing" in pts else pd.Series(np.nan, index=pts.index)
        scatter_angle = scatter_angle.where(~scatter_angle.isna(), pts["plot_angle"])
        scatter_angle = scatter_angle.clip(lower=FAIR_ANGLE_MIN, upper=FAIR_ANGLE_MAX)

        results = pts.apply(_result_label, axis=1)
        colors = results.map(lambda r: PLAY_RESULT_COLORS.get(r, PLAY_RESULT_COLORS["Other"]))
        angles_rad = np.deg2rad(scatter_angle)
        distances = pts["distance"]
        # Normalize distances to chart radius (1.0 = outfield fence cap)
        max_plot_dist = max(330, np.nanmax(distances)) if len(distances) else 400
        scaled_r = np.clip(distances / max_plot_dist, 0, 1.0)
        x = scaled_r * np.sin(angles_rad)
        y = scaled_r * np.cos(angles_rad)
        ax.scatter(x, y, s=26, c=colors, alpha=0.9, edgecolors="white", linewidths=0.35, zorder=6)

        # Legend for outcomes
        uniq = results.unique()
        handles = [
            Line2D([0], [0], marker="o", color="white", markerfacecolor=PLAY_RESULT_COLORS.get(lbl, "#666"),
                   markeredgecolor="white", markersize=7, label=lbl)
            for lbl in uniq
        ]
        ax.legend(handles=handles, title="Result", loc="upper left", fontsize=7, title_fontsize=8, frameon=False)

    # Visual separator between infield and outfield rings; draw on top of wedges and points
    boundary = plt.Circle((0, 0), 0.5, edgecolor="#2d2d2d", facecolor="none", linewidth=1.5, linestyle="--", alpha=0.9, zorder=7)
    ax.add_patch(boundary)

    if total == 0:
        ax.text(0, -0.05, "No fair batted balls", ha="center", va="center", fontsize=9, color=COLORS["text"])

    ax.set_title(title, fontsize=12, fontweight="bold", color=COLORS["text"])
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(0, 1.05)
    ax.set_aspect("equal")


def _spin_axis(ax, df: pd.DataFrame):
    ax.set_facecolor("white")
    pitch_types = df["pitch_type"].dropna().unique()
    color_map = get_pitch_color_map(pitch_types)
    for pt in pitch_types:
        sub = df[df["pitch_type"] == pt]
        if "spin_axis" not in sub.columns:
            continue
        theta = np.deg2rad(pd.to_numeric(sub["spin_axis"], errors="coerce"))
        r = pd.to_numeric(sub["spin_rate"], errors="coerce")
        color = color_map.get(pt, DEFAULT_PITCH_COLOR)
        ax.scatter(theta, r, s=12, alpha=0.7, c=color, label=_pitch_label(pt), edgecolors="none")
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(1)  # counter-clockwise; 90° left, 270° right
    ax.set_thetagrids([0, 90, 180, 270], labels=["0", "90", "180", "270"])
    ax.set_title("Spin Axis / Tilt", fontsize=12, fontweight="bold", color=COLORS["text"], pad=40)
    max_spin = pd.to_numeric(df["spin_rate"], errors="coerce").max() if "spin_rate" in df.columns else 3000
    ax.set_rlim(0, max(3000, max_spin if not pd.isna(max_spin) else 3000))
    ax.grid(True, alpha=0.3)
    if len(pitch_types) > 0:
        ax.legend(
            fontsize=8,
            loc="upper center",
            bbox_to_anchor=(0.5, 1.22),  # raise above plot to avoid overlap
            ncol=2,
            frameon=False,
        )


def _location_movement_page(pdf, df: pd.DataFrame, title: str):
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.5), dpi=150)
    fig.suptitle(f"{title} - Pitch Location & Movement", fontsize=14, fontweight="bold", color=COLORS["text"])

    # Pitch location scatter
    ax_loc = axes[0]
    valid_loc = df.dropna(subset=["plate_x", "plate_z"]) if {"plate_x", "plate_z"}.issubset(df.columns) else pd.DataFrame()
    if len(valid_loc) > 0:
        # Color by pitch type
        pitch_types = valid_loc["pitch_type"].dropna().unique()
        color_map = get_pitch_color_map(pitch_types)
        for pt in pitch_types:
            sub = valid_loc[valid_loc["pitch_type"] == pt]
            color = color_map.get(pt, DEFAULT_PITCH_COLOR)
            ax_loc.scatter(
                sub["plate_x"],
                sub["plate_z"],
                alpha=0.7,
                s=32,
                c=[color],
                edgecolors="white",
                linewidths=0.35,
                label=pt,
            )
        rect = Rectangle((-9.97, 18.29), 19.94, 25.79, linewidth=1.5, edgecolor="black", facecolor="none", alpha=0.35)
        ax_loc.add_patch(rect)
        ax_loc.set_xlim(-24, 24)
        ax_loc.set_ylim(0, 60)
        ax_loc.set_aspect("equal")
        ax_loc.set_xlabel("Horizontal Location (in)")
        ax_loc.set_ylabel("Vertical Location (in)")
        ax_loc.set_title("Pitch Location", fontsize=12, fontweight="bold")
        ax_loc.grid(True, alpha=0.25)
        if len(pitch_types) > 0:
            ax_loc.legend(
                title="Pitch Type",
                fontsize=8,
                title_fontsize=9,
                frameon=False,
                loc="upper left",
                bbox_to_anchor=(1.02, 1.0),
            )
    else:
        ax_loc.axis("off")
        ax_loc.text(0.5, 0.5, "No pitch location data", ha="center", va="center", fontsize=10, color=COLORS["text"])

    # Movement scatter (HB vs IVB)
    ax_mov = axes[1]
    if {"hb", "ivb"}.issubset(df.columns):
        hb = pd.to_numeric(df["hb"], errors="coerce")
        ivb = pd.to_numeric(df["ivb"], errors="coerce")
        mask = hb.notna() & ivb.notna()
        if mask.sum() > 0:
            # Color by pitch type
            pitch_types = df.loc[mask, "pitch_type"].dropna().unique()
            color_map = get_pitch_color_map(pitch_types)
            for pt in pitch_types:
                sub_mask = mask & (df["pitch_type"] == pt)
                color = color_map.get(pt, DEFAULT_PITCH_COLOR)
                ax_mov.scatter(
                    hb[sub_mask],
                    ivb[sub_mask],
                    alpha=0.75,
                    color=color,
                    edgecolors="white",
                    linewidths=0.35,
                    s=36,
                    label=pt,
                )
            ax_mov.axhline(0, color="gray", linestyle="--", linewidth=0.7, alpha=0.5)
            ax_mov.axvline(0, color="gray", linestyle="--", linewidth=0.7, alpha=0.5)
            ax_mov.set_xlabel("Horizontal Break (in)")
            ax_mov.set_ylabel("Induced Vertical Break (in)")
            ax_mov.set_title("Pitch Movement (HB vs IVB)", fontsize=12, fontweight="bold")
            ax_mov.grid(True, alpha=0.25)
            if len(pitch_types) > 0:
                ax_mov.legend(
                    title="Pitch Type",
                    fontsize=8,
                    title_fontsize=9,
                    frameon=False,
                    loc="upper left",
                    bbox_to_anchor=(1.02, 1.0),
                )
        else:
            ax_mov.axis("off")
            ax_mov.text(0.5, 0.5, "No movement data", ha="center", va="center", fontsize=10, color=COLORS["text"])
    else:
        ax_mov.axis("off")
        ax_mov.text(0.5, 0.5, "No movement data", ha="center", va="center", fontsize=10, color=COLORS["text"])

    fig.tight_layout(rect=[0, 0, 1, 0.92])
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)
