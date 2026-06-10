#!/usr/bin/env python3
"""
Generate a single-page master summary table for allowed pitchers.

Output:
- Master Reports/Master_Pitcher_Splits.pdf (8.5 x 11 in)
"""

import sys
import csv
import pandas as pd
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.profiles import load_player_profile  # noqa: E402
from src.profiles.team_config import get_master_pitcher_splits_players, get_display_name  # noqa: E402
from src.metrics.pitch_metrics import calculate_whiff_rate  # noqa: E402
from src.metrics.contact_metrics import (  # noqa: E402
    calculate_contact_outcomes,
    calculate_spray_distribution,
    calculate_hard_hit_rate,
)


DATE_CUTOFF = date(2026, 2, 13)


ALLOWED_PLAYERS = get_master_pitcher_splits_players()


def format_val(val: float) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "-"
    return f"{val:.1f}"


def tagged_hit_type_rates(df):
    if df is None or len(df) == 0 or "tagged_hit_type" not in df.columns:
        return {"gb": np.nan, "fb": np.nan, "ld": np.nan, "pu": np.nan, "total": 0}
    tags_raw = df["tagged_hit_type"].astype(str).str.strip().str.lower()
    # Keep only GB/FB/LD/PU tags; drop bunts and undefined/blank
    valid_mask = tags_raw.str.contains("ground|fly|line|pop", regex=True)
    tags = tags_raw[valid_mask]
    tags = tags[~tags.isin(["", "nan", "none", "undefined", "bunt", "bunted ball", "bunted"])]
    total = len(tags)
    if total == 0:
        return {"gb": np.nan, "fb": np.nan, "ld": np.nan, "pu": np.nan, "total": 0}
    gb = tags.str.contains("ground").sum() / total * 100.0
    fb = tags.str.contains("fly").sum() / total * 100.0
    ld = tags.str.contains("line").sum() / total * 100.0
    pu = tags.str.contains("pop").sum() / total * 100.0
    return {"gb": gb, "fb": fb, "ld": ld, "pu": pu, "total": total}


def compute_side_stats(df):
    if df is None or len(df) == 0:
        return {"kbb": np.nan, "whiff": np.nan, "gb_t": np.nan, "fb_t": np.nan, "ld_t": np.nan, "pu": np.nan, "hh": np.nan, "pull": np.nan, "middle": np.nan, "oppo": np.nan}

    korbb = df.get("KorBB")
    ks = 0
    bbs = 0
    if korbb is not None:
        korbb_str = korbb.astype(str).str.lower()
        ks = korbb_str.str.contains("strikeout").sum()
        # include simple "k" if present, but avoid counting blanks
        ks += korbb_str.eq("k").sum()
        bbs = korbb_str.str.contains("walk").sum() + korbb_str.eq("bb").sum()
    kbb_ratio = np.nan
    if bbs > 0:
        kbb_ratio = ks / bbs
    elif ks > 0:
        kbb_ratio = np.nan

    whiff = calculate_whiff_rate(df)
    tagged = tagged_hit_type_rates(df)
    # Use tagged hit types for batted-ball splits and popup rate as requested
    co = calculate_contact_outcomes(df)
    spray = calculate_spray_distribution(df)
    hh = calculate_hard_hit_rate(df)
    return {
        "kbb": kbb_ratio,
        "whiff": whiff,
        "gb_t": tagged["gb"],
        "fb_t": tagged["fb"],
        "ld_t": tagged["ld"],
        "pu": tagged["pu"],
        "hh": hh,
        "pull": spray["pull_rate"],
        "middle": spray["middle_rate"],
        "oppo": spray["oppo_rate"],
    }


def _normalize_name(first: str, last: str) -> str:
    return "".join(ch for ch in f"{first}{last}".lower() if ch.isalnum())


def _parse_outing_date(dstr):
    if not dstr:
        return None
    s = str(dstr)
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except Exception:
            return None


def get_cumulative_since(profile, cutoff: date) -> pd.DataFrame:
    """
    Combine only outings on/after the given cutoff date.
    Falls back to empty DataFrame if nothing qualifies.
    """
    frames = []
    for outing in getattr(profile, "outings", []):
        meta = outing.get("metadata", {})
        dt = _parse_outing_date(meta.get("date"))
        if not dt or dt.date() < cutoff:
            continue
        frames.append(outing.get("data"))
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()


def bip_direction_rates(df_side: pd.DataFrame) -> dict:
    """
    Compute Pull/Middle/Oppo% from balls in play with direction data (Trackman CSVs).
    Exclude bunts and undefined directions.
    """
    if df_side is None or len(df_side) == 0:
        return {"pull": np.nan, "middle": np.nan, "oppo": np.nan}

    if "pitch_call" in df_side.columns:
        df_bip = df_side[df_side["pitch_call"] == "InPlay"].copy()
    else:
        df_bip = df_side.copy()

    # Exclude bunts
    if "tagged_hit_type" in df_bip.columns:
        tags = df_bip["tagged_hit_type"].astype(str).str.lower()
        df_bip = df_bip[~tags.str.contains("bunt", na=False)]

    if "direction" not in df_bip.columns:
        return {"pull": np.nan, "middle": np.nan, "oppo": np.nan}

    directions = pd.to_numeric(df_bip["direction"], errors="coerce")
    valid = directions.notna()
    if valid.sum() == 0:
        return {"pull": np.nan, "middle": np.nan, "oppo": np.nan}

    middle_deg = 15
    dirs = directions[valid]
    bs_col = df_bip["batter_side"].astype(str).str.upper() if "batter_side" in df_bip else pd.Series(["R"] * len(df_bip))
    bs_side = bs_col[valid]

    pull = middle = oppo = 0
    total = len(dirs)

    for d, bs in zip(dirs, bs_side):
        if "L" in bs:
            if d > middle_deg:
                pull += 1
            elif d < -middle_deg:
                oppo += 1
            else:
                middle += 1
        else:
            if d < -middle_deg:
                pull += 1
            elif d > middle_deg:
                oppo += 1
            else:
                middle += 1

    return {
        "pull": (pull / total) * 100.0 if total else np.nan,
        "middle": (middle / total) * 100.0 if total else np.nan,
        "oppo": (oppo / total) * 100.0 if total else np.nan,
    }


def main():
    base = Path(__file__).parent.parent
    profiles_dir = base / "PlayerProfiles"
    out_dir = base / "Master Reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / "Master_Pitcher_Splits.pdf"

    columns = ["Pitcher", "Split", "K/BB", "Whiff%", "GB%", "FB%", "LD%", "PU%", "HH%", "Pull%", "Middle%", "Oppo%"]
    rows = []

    for first, last in ALLOWED_PLAYERS:
        profile = load_player_profile(first, last, profiles_dir)
        if profile is None:
            # Add placeholder rows if profile missing
            for split in ("RHH", "LHH"):
                rows.append([f"{first} {last}", split] + ["-"] * (len(columns) - 2))
            continue

        df = get_cumulative_since(profile, DATE_CUTOFF)
        if "batter_side" in df.columns:
            side_col = df["batter_side"].astype(str).str.upper()
            df_r = df[side_col.str.startswith("R")]
            df_l = df[side_col.str.startswith("L")]
        else:
            df_r = df_l = df.iloc[0:0]

        stats_r = compute_side_stats(df_r)
        stats_l = compute_side_stats(df_l)

        dir_r = bip_direction_rates(df_r)
        dir_l = bip_direction_rates(df_l)

        def row_for(split, stats):
            return [
                "",  # name placeholder; fill once per pitcher
                split,
                format_val(stats["kbb"]),
                format_val(stats["whiff"]),
                format_val(stats["gb_t"]),
                format_val(stats["fb_t"]),
                format_val(stats["ld_t"]),
                format_val(stats["pu"]),
                format_val(stats["hh"]),
                format_val(dir_r["pull"] if split == "RHH" else dir_l["pull"]),
                format_val(dir_r["middle"] if split == "RHH" else dir_l["middle"]),
                format_val(dir_r["oppo"] if split == "RHH" else dir_l["oppo"]),
            ]

        pair = [row_for("RHH", stats_r), row_for("LHH", stats_l)]
        # set name once for the pair (RHH row)
        display_name = get_display_name(first, last)
        pair[0][0] = display_name

        rows.extend(pair)

    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis("off")
    ax.set_title(
        "Pitcher Batted-Ball & Whiff Splits (RHH / LHH)",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    # 12 columns => 12 widths
    table = ax.table(
        cellText=rows,
        colLabels=columns,
        cellLoc="center",
        loc="upper left",
        colWidths=[0.17, 0.06, 0.08, 0.08, 0.08, 0.08, 0.08, 0.07, 0.07, 0.07, 0.07, 0.07],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1, 1.2)

    # Header styling
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#4f7f3b")
            cell.set_text_props(color="white", fontweight="bold")
        # Name already placed in RHH row; blank on LHH row
        if row > 0 and col == 0 and row % 2 == 0:
            cell.get_text().set_text("")

    plt.tight_layout()
    with PdfPages(out_pdf) as pdf:
        pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)

    print(f"Wrote {out_pdf}")


if __name__ == "__main__":
    main()

