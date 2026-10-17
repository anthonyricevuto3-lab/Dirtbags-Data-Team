"""
One-page bullpen and game outing reports.

Landscape letter, black background, gold accents. The multi-page 643 outing
report is unchanged. These pages keep only the stats that fit on one sheet.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
import pandas as pd

from ..metrics.contact_metrics import calculate_contact_outcomes, calculate_hard_hit_rate
from ..metrics.inning_success_metrics import compute_inning_success_metrics
from ..metrics.movement_metrics import (
    calculate_extension_avg,
    calculate_hb_avg,
    calculate_ivb_avg,
    calculate_release_height_avg,
    calculate_release_side_avg,
    calculate_spin_avg,
    calculate_velocity_avg,
)
from ..metrics.pitch_metrics import (
    calculate_heart_rate,
    calculate_shadow_rate,
    calculate_whiff_rate,
    calculate_zone_rate,
)
from ..pitch_colors import get_pitch_color

BG = "#000000"
GOLD = "#F5C518"
WHITE = "#FFFFFF"
MUTED = "#B5B5B5"
CARD = "#141414"
LINE = "#333333"
ZONE_EDGE = "#F5C518"

MAX_PITCH_TYPES = 6


def classify_session(df: pd.DataFrame, source_name: str = "") -> str:
    """Return 'bullpen' or 'game' from PracticeType / PitchSession, then filename."""
    for col in ("practice_type", "PracticeType"):
        if col in df.columns:
            blob = " ".join(df[col].dropna().astype(str).str.lower().unique())
            if any(token in blob for token in ("livebp", "bullpen", "warmup", "pitching")):
                return "bullpen"
            if blob.strip() and blob.strip() not in {"nan", "none"}:
                return "game"
    for col in ("pitch_session", "PitchSession"):
        if col in df.columns:
            blob = " ".join(df[col].dropna().astype(str).str.lower().unique())
            if "warmup" in blob or "bullpen" in blob:
                return "bullpen"
    name = (source_name or "").lower()
    if any(token in name for token in ("livebp", "bullpen", "pitching_")):
        return "bullpen"
    return "game"


def _missing(val) -> bool:
    if val is None:
        return True
    try:
        return bool(pd.isna(val))
    except Exception:
        return False


def _fmt(val, digits=1, suffix="") -> str:
    if _missing(val):
        return "—"
    return f"{float(val):.{digits}f}{suffix}"


def _pct(val) -> str:
    if _missing(val):
        return "—"
    return f"{float(val):.0f}%"


def _pitch_rows(df: pd.DataFrame) -> list:
    if "pitch_type" not in df.columns:
        return []
    labels = df["pitch_type"].fillna("").astype(str).str.strip()
    labels = labels[~labels.str.lower().isin({"", "nan", "none", "undefined"})]
    counts = labels.value_counts()
    return list(counts.index[:MAX_PITCH_TYPES])


def _result_counts(df: pd.DataFrame) -> Dict[str, int]:
    ks = bbs = hits = 0
    if "KorBB" in df.columns:
        korbb = df["KorBB"].astype(str).str.lower()
        ks = int(korbb.str.contains("strikeout").sum() + korbb.eq("k").sum())
        bbs = int(korbb.str.contains("walk").sum() + korbb.eq("bb").sum())
    if "play_result" in df.columns:
        result = df["play_result"].astype(str).str.lower()
        hits = int(result.str.contains(r"single|double|triple|home", regex=True).sum())
    return {"k": ks, "bb": bbs, "h": hits}


def outing_success_percent(df: pd.DataFrame) -> float:
    """Pitch-weighted Inning Success % for the outing."""
    if df is None or df.empty or "inning" not in df.columns:
        return float("nan")
    work = df[df["inning"].notna()]
    if work.empty:
        return float("nan")
    report = compute_inning_success_metrics(work)
    if report.empty:
        return float("nan")
    counts = work.groupby("inning").size()
    weighted = 0.0
    total = 0
    for _, row in report.iterrows():
        n = int(counts.get(row["Inning"], 0))
        if n <= 0:
            continue
        weighted += float(row["Inning Success %"]) * n
        total += n
    if total == 0:
        return float(report["Inning Success %"].mean())
    return weighted / total


def _style_ax(ax):
    ax.set_facecolor(BG)
    ax.tick_params(colors=MUTED, labelsize=8)
    for spine in ax.spines.values():
        spine.set_color(LINE)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(GOLD)
    ax.grid(True, color="#2a2a2a", linewidth=0.6)


def _scatter_by_pitch(ax, df, xcol, ycol):
    if df is None or df.empty or xcol not in df.columns or ycol not in df.columns:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", va="center", color=MUTED, fontsize=11)
        return
    plotted = False
    for pt in _pitch_rows(df):
        sub = df[df["pitch_type"] == pt].dropna(subset=[xcol, ycol])
        if sub.empty:
            continue
        ax.scatter(
            sub[xcol],
            sub[ycol],
            s=28,
            c=get_pitch_color(pt),
            alpha=0.9,
            edgecolors="#111111",
            linewidths=0.3,
            label=pt,
            zorder=3,
        )
        plotted = True
    if not plotted:
        ax.text(0.5, 0.5, "No data", transform=ax.transAxes, ha="center", va="center", color=MUTED, fontsize=11)


def _draw_location(ax, df):
    _style_ax(ax)
    _scatter_by_pitch(ax, df, "plate_x", "plate_z")
    ax.add_patch(
        Rectangle(
            (-9.97, 18.29),
            19.94,
            25.79,
            fill=False,
            edgecolor=ZONE_EDGE,
            linewidth=1.4,
            zorder=4,
        )
    )
    ax.set_xlim(-24, 24)
    ax.set_ylim(8, 56)
    ax.set_aspect("equal", adjustable="box")
    ax.set_title("Location", fontsize=12, fontweight="bold", pad=8, color=GOLD)
    ax.set_xlabel("Horizontal (in)")
    ax.set_ylabel("Vertical (in)")


def _draw_movement(ax, df):
    _style_ax(ax)
    _scatter_by_pitch(ax, df, "hb", "ivb")
    ax.axhline(0, color="#555555", linewidth=0.8)
    ax.axvline(0, color="#555555", linewidth=0.8)
    ax.set_title("Movement", fontsize=12, fontweight="bold", pad=8, color=GOLD)
    ax.set_xlabel("Horizontal break (in)")
    ax.set_ylabel("Induced vertical break (in)")
def _draw_table(ax, columns, rows):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor(BG)
    if not rows:
        ax.text(0.5, 0.5, "No pitch types", ha="center", va="center", color=MUTED, fontsize=11)
        return
    table = ax.table(cellText=rows, colLabels=columns, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor(LINE)
        cell.set_linewidth(0.4)
        if row == 0:
            cell.set_facecolor("#1c1c1c")
            cell.get_text().set_color(GOLD)
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor("#0c0c0c" if row % 2 else CARD)
            cell.get_text().set_color(WHITE)
            if col == 0:
                pitch = rows[row - 1][0]
                cell.get_text().set_color(get_pitch_color(pitch))


def _header(fig, name, session_label, date_text, throws, pitches):
    fig.text(0.22, 0.945, name or "Pitcher", color=WHITE, fontsize=20, fontweight="bold", va="center")
    fig.text(0.22, 0.905, session_label, color=GOLD, fontsize=11, fontweight="bold", va="center")
    meta = "  ·  ".join(part for part in (date_text, throws, f"{pitches} pitches") if part)
    fig.text(0.96, 0.93, meta, color=MUTED, fontsize=10, ha="right", va="center")
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.875, 0.875], transform=fig.transFigure, color=GOLD, linewidth=1.2))


def _stat_strip(fig, stats, y=0.845):
    n = max(len(stats), 1)
    for i, (label, value) in enumerate(stats):
        x = 0.06 + (0.90 / n) * i
        fig.text(x, y, value, color=GOLD, fontsize=16, fontweight="bold", va="center")
        fig.text(x, y - 0.028, label, color=MUTED, fontsize=8, va="center")


def _logo(fig):
    for candidate in (
        Path(__file__).resolve().parent.parent / "images" / "Dirtbag Data Team baseball logo.png",
        Path("images") / "Dirtbag Data Team baseball logo.png",
    ):
        if not candidate.exists():
            continue
        try:
            img = plt.imread(candidate)
            width_in, height_in = fig.get_size_inches()
            logo_height = 0.55
            logo_width = logo_height * (img.shape[1] / img.shape[0])
            ax = fig.add_axes([0.035, 0.915, logo_width / width_in, logo_height / height_in])
            ax.set_facecolor(BG)
            ax.imshow(img)
            ax.axis("off")
        except Exception:
            pass
        return


def _bullpen_rows(df, pitch_types):
    total = max(len(df), 1)
    rows = []
    for pt in pitch_types:
        sub = df[df["pitch_type"] == pt]
        rows.append(
            [
                pt,
                str(len(sub)),
                f"{len(sub) / total * 100:.0f}%",
                _fmt(calculate_velocity_avg(sub)),
                _fmt(calculate_spin_avg(sub), 0),
                _fmt(calculate_ivb_avg(sub)),
                _fmt(calculate_hb_avg(sub)),
                _fmt(calculate_release_height_avg(sub), 2),
                _fmt(calculate_release_side_avg(sub), 2),
                _fmt(calculate_extension_avg(sub), 2),
            ]
        )
    return rows


def _game_rows(df, pitch_types):
    total = max(len(df), 1)
    rows = []
    for pt in pitch_types:
        sub = df[df["pitch_type"] == pt]
        rows.append(
            [
                pt,
                str(len(sub)),
                f"{len(sub) / total * 100:.0f}%",
                _fmt(calculate_velocity_avg(sub)),
                _fmt(calculate_ivb_avg(sub)),
                _fmt(calculate_hb_avg(sub)),
                _pct(calculate_whiff_rate(sub)),
            ]
        )
    return rows


def _side_line(df, side_prefix: str) -> str:
    if "batter_side" not in df.columns:
        return "—"
    side = df["batter_side"].astype(str).str.upper()
    sub = df[side.str.startswith(side_prefix)]
    if sub.empty:
        return "—"
    counts = _result_counts(sub)
    whiff = calculate_whiff_rate(sub)
    return f"{counts['k']} K   {counts['bb']} BB   {counts['h']} H   {_pct(whiff)} whiff"


def _batted_line(df) -> str:
    contact = calculate_contact_outcomes(df)
    hard = calculate_hard_hit_rate(df)
    return (
        f"GB {_pct(contact['ground_ball_rate'])}    "
        f"FB {_pct(contact['fly_ball_rate'])}    "
        f"LD {_pct(contact['line_drive_rate'])}    "
        f"HH {_pct(hard)}"
    )


def generate_outing_one_pager(
    df: pd.DataFrame,
    output_path: str,
    kind: str = "game",
    name: str = "",
    throws: str = "",
    outing_date: str = "",
) -> None:
    """Write a one-page bullpen or game PDF."""
    kind = "bullpen" if kind == "bullpen" else "game"
    df = df.copy()
    pitches = len(df)
    date_text = outing_date
    if outing_date:
        try:
            date_text = datetime.strptime(outing_date[:10], "%Y-%m-%d").strftime("%b %d, %Y")
        except Exception:
            date_text = outing_date
    hand = ""
    if throws:
        hand = "LHP" if str(throws).upper().startswith("L") else "RHP" if str(throws).upper().startswith("R") else str(throws)

    fig = plt.figure(figsize=(11, 8.5), dpi=140)
    fig.patch.set_facecolor(BG)
    _header(fig, name, "BULLPEN" if kind == "bullpen" else "GAME", date_text, hand, pitches)
    _logo(fig)

    if kind == "bullpen":
        _stat_strip(
            fig,
            [
                ("In-zone %", _pct(calculate_zone_rate(df))),
                ("Heart %", _pct(calculate_heart_rate(df))),
                ("Shadow %", _pct(calculate_shadow_rate(df))),
            ],
        )
        ax_loc = fig.add_axes([0.07, 0.36, 0.40, 0.38])
        ax_mov = fig.add_axes([0.55, 0.36, 0.40, 0.38])
        _draw_location(ax_loc, df)
        _draw_movement(ax_mov, df)
        ax_table = fig.add_axes([0.04, 0.04, 0.92, 0.28])
        _draw_table(
            ax_table,
            ["Pitch", "#", "Use", "Velo", "Spin", "IVB", "HB", "RelH", "RelS", "Ext"],
            _bullpen_rows(df, _pitch_rows(df)),
        )
    else:
        counts = _result_counts(df)
        success = outing_success_percent(df)
        _stat_strip(
            fig,
            [
                ("Pitches", str(pitches)),
                ("K", str(counts["k"])),
                ("BB", str(counts["bb"])),
                ("H", str(counts["h"])),
                ("Whiff %", _pct(calculate_whiff_rate(df))),
                ("Success %", _pct(success)),
            ],
        )
        ax_loc = fig.add_axes([0.07, 0.42, 0.40, 0.32])
        ax_mov = fig.add_axes([0.55, 0.42, 0.40, 0.32])
        _draw_location(ax_loc, df)
        _draw_movement(ax_mov, df)
        ax_table = fig.add_axes([0.04, 0.16, 0.92, 0.22])
        _draw_table(
            ax_table,
            ["Pitch", "#", "Use", "Velo", "IVB", "HB", "Whiff"],
            _game_rows(df, _pitch_rows(df)),
        )
        fig.text(0.06, 0.145, "VS LHH", color=GOLD, fontsize=8, fontweight="bold")
        fig.text(0.16, 0.145, _side_line(df, "L"), color=WHITE, fontsize=9)
        fig.text(0.55, 0.145, "VS RHH", color=GOLD, fontsize=8, fontweight="bold")
        fig.text(0.65, 0.145, _side_line(df, "R"), color=WHITE, fontsize=9)
        fig.text(0.06, 0.085, "BATTED BALL", color=GOLD, fontsize=8, fontweight="bold")
        fig.text(0.18, 0.085, _batted_line(df), color=WHITE, fontsize=9)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(output) as pdf:
        pdf.savefig(fig, facecolor=fig.get_facecolor())
        info = pdf.infodict()
        info["Title"] = f"{'Bullpen' if kind == 'bullpen' else 'Game'} — {name}"
        info["Author"] = "Dirtbags Data Team"
    plt.close(fig)
