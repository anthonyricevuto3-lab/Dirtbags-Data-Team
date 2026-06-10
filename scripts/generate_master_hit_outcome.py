#!/usr/bin/env python3
"""
Generate the Master Hit Outcome Report (consolidated).

Landscape PDF (1-2 pages) with every allowed pitcher in a single compact
table.  Columns show Whiff%, 95+ EV%, and Batting Average for vs-RHH and
vs-LHH side by side, organized by pitch type within each pitcher.

Output
------
Master Reports/Master_Hit_Outcome_Report.pdf
"""

import sys
import re
import pandas as pd
from pathlib import Path
from datetime import date
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.pitch_colors import get_pitch_color  # noqa: E402
from src.profiles.team_config import get_master_hit_outcome_players, get_display_name  # noqa: E402
from src.reports.pitch_grouping import apply_pitch_grouping_for_player  # noqa: E402

DATE_CUTOFF = date(2026, 2, 13)

ALLOWED_PLAYERS = get_master_hit_outcome_players()

PITCH_TYPE_ORDER = [
    "Fastball", "Four-Seam", "Sinker", "2-Seam Fastball",
    "Cutter", "Slider", "Sweeper", "Curveball", "Changeup",
    "Splitter", "Knuckleball",
]

SWING_CALLS = {
    "StrikeSwinging", "FoulBall", "FoulBallNotFieldable",
    "FoulBallFieldable", "InPlay",
}

HIT_RESULTS = {"single", "double", "triple", "homerun", "home run"}

MAX_ROWS_PER_PAGE = 70


# ---------------------------------------------------------------------------
# Name helpers
# ---------------------------------------------------------------------------

def _alnum(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _name_key(a: str, b: str) -> tuple:
    return tuple(sorted((_alnum(a), _alnum(b))))


def _build_allowed_map():
    m = {}
    for first, last in ALLOWED_PLAYERS:
        key = _name_key(first, last)
        display = get_display_name(first, last)
        m[key] = (first, last, display)
    return m


def _csv_pitcher_key(csv_name: str) -> tuple:
    parts = csv_name.split(",", 1)
    if len(parts) == 2:
        return _name_key(parts[1].strip(), parts[0].strip())
    return _name_key("", csv_name.strip())


# ---------------------------------------------------------------------------
# CSV loading
# ---------------------------------------------------------------------------

def parse_csv_date(filename: str):
    m = re.match(r"^(\d{8})-", filename)
    if m:
        ds = m.group(1)
    else:
        m = re.match(r"^\d{8}_\d{6}_(\d{8})-", filename)
        if not m:
            return None
        ds = m.group(1)
    try:
        return date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
    except ValueError:
        return None


def load_raw_data(csv_dir: Path) -> pd.DataFrame:
    frames = []
    for csv_path in sorted(csv_dir.glob("*.csv")):
        if "playerpositioning" in csv_path.name.lower():
            continue
        d = parse_csv_date(csv_path.name)
        if d is None or d < DATE_CUTOFF:
            continue
        try:
            df = pd.read_csv(csv_path, low_memory=False)
            frames.append(df)
            print(f"  Loaded {csv_path.name}  ({len(df)} pitches)")
        except Exception as e:
            print(f"  Skipping {csv_path.name}: {e}")
    if not frames:
        print("No qualifying CSVs found.")
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    print(f"\nTotal pitches: {len(combined)}")
    return combined


# ---------------------------------------------------------------------------
# Pitch-type standardization
# ---------------------------------------------------------------------------

def standardize_pitch_type(s) -> str:
    if not isinstance(s, str) or s.strip().lower() in ("", "undefined", "nan", "none"):
        return ""
    raw = s.strip()
    normalized = _alnum(raw)
    alias = {
        "twoseamfastball": "2-Seam Fastball",
        "twoseam": "2-Seam Fastball",
        "2seam": "2-Seam Fastball",
        "2seamfastball": "2-Seam Fastball",
        "fourseamfastball": "Four-Seam",
        "fourseam": "Four-Seam",
        "4seam": "Four-Seam",
        "4seamfastball": "Four-Seam",
        "knucklecurve": "Curveball",
        "oneseamfastball": "Fastball",
        "oneseam": "Fastball",
    }
    if normalized in alias:
        return alias[normalized]
    return raw.title()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_metrics(df: pd.DataFrame) -> dict:
    if len(df) == 0:
        return {"whiff_pct": np.nan, "ev95_pct": np.nan, "batting_avg": np.nan}

    pc = df["PitchCall"].astype(str).str.strip()

    swings = pc.isin(SWING_CALLS).sum()
    whiffs = (pc == "StrikeSwinging").sum()
    whiff_pct = (whiffs / swings * 100.0) if swings > 0 else np.nan

    inplay = pc == "InPlay"
    ev = pd.to_numeric(df.loc[inplay, "ExitSpeed"], errors="coerce")
    ev_valid = ev.dropna()
    ev95_pct = ((ev_valid >= 95).sum() / len(ev_valid) * 100.0) if len(ev_valid) > 0 else np.nan

    pr = df.loc[inplay, "PlayResult"].astype(str).str.strip().str.lower()
    hits = pr.isin(HIT_RESULTS).sum()
    sac = pr.str.contains("sacrifice|sacbunt|sacfly", na=False, regex=True).sum()
    inplay_ab = inplay.sum() - sac
    korbb = df["KorBB"].astype(str).str.strip().str.lower()
    ks = (korbb.str.contains("strikeout", na=False) | korbb.eq("k")).sum()
    ab = inplay_ab + ks
    batting_avg = (hits / ab) if ab > 0 else np.nan

    return {"whiff_pct": whiff_pct, "ev95_pct": ev95_pct, "batting_avg": batting_avg}


def fmt_pct(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    return f"{v:.1f}%"


def fmt_avg(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "-"
    if v >= 1.0:
        return "1.000"
    return f".{int(round(v * 1000)):03d}"


# ---------------------------------------------------------------------------
# Consolidated row builder
# ---------------------------------------------------------------------------

def build_all_rows(df: pd.DataFrame):
    """
    Build consolidated rows with RHH / LHH metrics side by side.

    Each row: [Pitcher, Pitch Type, Whiff%(R), 95+EV%(R), AVG(R),
                                     Whiff%(L), 95+EV%(L), AVG(L)]

    Returns (rows, row_meta) where row_meta is a list of dicts with keys:
        is_summary  – True for the "All" row of a pitcher
        is_first    – True for the first row of a pitcher group
        pitcher_idx – sequential index of the pitcher (for alternating colors)
    """
    allowed_map = _build_allowed_map()
    df = df.copy()
    df["_pitcher_key"] = df["Pitcher"].astype(str).apply(_csv_pitcher_key)
    df["_pt"] = df["TaggedPitchType"].apply(standardize_pitch_type)
    df["_side"] = df["BatterSide"].astype(str).str.strip().str.upper()
    df = df[df["_pt"] != ""]

    rows = []
    meta = []
    pitcher_idx = 0

    for first, last in ALLOWED_PLAYERS:
        key = _name_key(first, last)
        _, _, display = allowed_map[key]
        pitcher_df = df[df["_pitcher_key"] == key]
        if pitcher_df.empty:
            continue

        # Pitcher-specific pitch grouping (from team config)
        pitcher_df = pitcher_df.copy()
        pitcher_df["pitch_type"] = pitcher_df["_pt"]
        pitcher_df = apply_pitch_grouping_for_player(pitcher_df, first, last)
        pitcher_df["_pt"] = pitcher_df["pitch_type"]
        pitcher_df = pitcher_df.drop(columns=["pitch_type"])

        type_counts = pitcher_df["_pt"].value_counts()
        ordered = [pt for pt in PITCH_TYPE_ORDER if pt in type_counts.index]
        for pt in type_counts.index:
            if pt not in ordered:
                ordered.append(pt)

        def _side_metrics(sub_df, code):
            return compute_metrics(sub_df[sub_df["_side"].str.startswith(code)])

        # "All" summary row
        r = _side_metrics(pitcher_df, "R")
        l = _side_metrics(pitcher_df, "L")
        rows.append([
            display, "All",
            fmt_pct(r["whiff_pct"]), fmt_pct(r["ev95_pct"]), fmt_avg(r["batting_avg"]),
            fmt_pct(l["whiff_pct"]), fmt_pct(l["ev95_pct"]), fmt_avg(l["batting_avg"]),
        ])
        meta.append({"is_summary": True, "is_first": True, "pitcher_idx": pitcher_idx})

        # Per pitch type
        for pt in ordered:
            pt_df = pitcher_df[pitcher_df["_pt"] == pt]
            r = _side_metrics(pt_df, "R")
            l = _side_metrics(pt_df, "L")
            rows.append([
                "", pt,
                fmt_pct(r["whiff_pct"]), fmt_pct(r["ev95_pct"]), fmt_avg(r["batting_avg"]),
                fmt_pct(l["whiff_pct"]), fmt_pct(l["ev95_pct"]), fmt_avg(l["batting_avg"]),
            ])
            meta.append({"is_summary": False, "is_first": False, "pitcher_idx": pitcher_idx})

        pitcher_idx += 1

    return rows, meta


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def paginate(rows, meta, max_per_page):
    """Split rows into pages, never breaking a pitcher group across pages."""
    pages = []
    page_rows, page_meta = [], []
    i = 0
    while i < len(rows):
        # Find the end of the current pitcher group
        j = i + 1
        while j < len(rows) and not meta[j]["is_first"]:
            j += 1
        group = (rows[i:j], meta[i:j])

        if page_rows and len(page_rows) + len(group[0]) > max_per_page:
            pages.append((page_rows, page_meta))
            page_rows, page_meta = [], []

        page_rows.extend(group[0])
        page_meta.extend(group[1])
        i = j

    if page_rows:
        pages.append((page_rows, page_meta))
    return pages


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

HEADER_LABELS = ["Pitcher", "Pitch",
                 "Whiff%", "95+EV%", "AVG",
                 "Whiff%", "95+EV%", "AVG"]

COL_WIDTHS = [0.17, 0.10, 0.09, 0.09, 0.08, 0.09, 0.09, 0.08]


def render_page(fig, ax, page_rows, page_meta, page_num, total_pages):
    ax.axis("off")

    # Title
    ax.text(0.5, 0.975, "Master Hit Outcome Report",
            transform=ax.transAxes, fontsize=13, fontweight="bold",
            ha="center", va="top", family="sans-serif")
    page_label = f"      Page {page_num}/{total_pages}" if total_pages > 1 else ""
    if page_label:
        ax.text(0.5, 0.957, page_label,
                transform=ax.transAxes, fontsize=7, ha="center", va="top",
                color="#555555", family="sans-serif")

    # "vs RHH" / "vs LHH" group labels
    tbl_left = 0.07
    tbl_width = 0.86
    col_starts = []
    x = tbl_left
    for w in COL_WIDTHS:
        col_starts.append(x)
        x += w * tbl_width

    rhh_x = (col_starts[2] + col_starts[4] + COL_WIDTHS[4] * tbl_width) / 2
    lhh_x = (col_starts[5] + col_starts[7] + COL_WIDTHS[7] * tbl_width) / 2
    ax.text(rhh_x, 0.942, "vs RHH", transform=ax.transAxes,
            fontsize=8, fontweight="bold", ha="center", va="top", color="#2c3e50")
    ax.text(lhh_x, 0.942, "vs LHH", transform=ax.transAxes,
            fontsize=8, fontweight="bold", ha="center", va="top", color="#2c3e50")

    # Table: use uniform row height across pages (same as page 1)
    n_rows = len(page_rows)
    table_top = 0.93
    full_table_h = table_top - 0.01  # nominal height for a full page
    total_cells = 1 + MAX_ROWS_PER_PAGE  # header + max data rows
    row_height_frac = full_table_h / total_cells
    table_h = (1 + n_rows) * row_height_frac  # header + this page's rows
    table_bot = table_top - table_h

    table = ax.table(
        cellText=page_rows,
        colLabels=HEADER_LABELS,
        cellLoc="center",
        loc="upper center",
        colWidths=COL_WIDTHS,
        bbox=[tbl_left, table_bot, tbl_width, table_h],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(6)

    # Style header
    for j in range(len(HEADER_LABELS)):
        cell = table[0, j]
        cell.set_facecolor("#2c3e50")
        cell.set_text_props(color="white", fontweight="bold", fontsize=6.5)
        cell.set_edgecolor("#1a252f")

    # Style data rows
    for i in range(1, n_rows + 1):
        m = page_meta[i - 1]
        pidx = m["pitcher_idx"]
        even_pitcher = pidx % 2 == 0

        for j in range(len(HEADER_LABELS)):
            cell = table[i, j]

            if m["is_summary"]:
                cell.set_facecolor("#d5e8d4" if even_pitcher else "#cce5cc")
                cell.set_text_props(fontweight="bold", fontsize=6)
            else:
                cell.set_facecolor("#ffffff" if even_pitcher else "#f5f7fa")
                cell.set_text_props(fontsize=6)

            cell.set_edgecolor("#d0d0d0")

            if j == 5:
                cell.set_edgecolor("#999999")

        # Color-code pitch type names
        pt_cell = table[i, 1]
        pt_txt = pt_cell.get_text().get_text()
        if pt_txt and pt_txt != "All":
            pt_cell.set_text_props(color=get_pitch_color(pt_txt), fontweight="bold",
                                   fontsize=6)

        # Bold pitcher name
        name_cell = table[i, 0]
        name_txt = name_cell.get_text().get_text()
        if name_txt:
            name_cell.set_text_props(fontweight="bold", fontsize=6)


def main():
    base = Path(__file__).parent.parent
    csv_dir = base / "Trackman CSVs"
    out_dir = base / "Master Reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_pdf = out_dir / "Master_Hit_Outcome_Report.pdf"

    print(f"Loading Trackman CSVs from {csv_dir}")
    print(f"Date filter: >= {DATE_CUTOFF}\n")

    df = load_raw_data(csv_dir)
    if df.empty:
        print("No data found. Exiting.")
        return

    required = {"PitchCall", "TaggedPitchType", "BatterSide", "ExitSpeed",
                "PlayResult", "KorBB", "Pitcher"}
    missing = required - set(df.columns)
    if missing:
        print(f"ERROR: Missing columns in CSV data: {missing}")
        return

    rows, meta = build_all_rows(df)
    pages = paginate(rows, meta, MAX_ROWS_PER_PAGE)
    total_pages = len(pages)

    print(f"\n  {len(rows)} total rows -> {total_pages} page(s)")

    with PdfPages(out_pdf) as pdf:
        for pg_num, (pg_rows, pg_meta) in enumerate(pages, 1):
            fig, ax = plt.subplots(figsize=(8.5, 11))
            render_page(fig, ax, pg_rows, pg_meta, pg_num, total_pages)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            print(f"  Wrote page {pg_num}")

    print(f"\nWrote {out_pdf}")


if __name__ == "__main__":
    main()
