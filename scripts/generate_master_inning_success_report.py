#!/usr/bin/env python3
"""
Generate Master Inning Success report: inning success metrics per pitcher (outings since 2/13/2026)
and tables showing which pitcher has the best numbers per inning.

Usage:
    python scripts/generate_master_inning_success_report.py
    python scripts/generate_master_inning_success_report.py --output-dir "Master Reports"
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime, date

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np

from src.profiles import load_player_profile
from src.profiles.paths import split_player_dir_name
from src.profiles.team_config import get_skip_pitchers_for_reports
from src.metrics.inning_success_metrics import compute_inning_success_metrics

# In-season cutoff (same as in-season player reports)
DATE_CUTOFF = date(2026, 2, 13)


def _parse_outing_date(meta_date):
    """Best-effort parse of outing date from metadata."""
    if not meta_date:
        return None
    s = str(meta_date)
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


# Minimum in-season outings required to qualify for the leaderboard
LEADERBOARD_MIN_OUTINGS = 3

# Pitchers to exclude from in-season success reports (full names in team config)
SKIP_PITCHERS = get_skip_pitchers_for_reports()


def get_inseason_data(profile):
    """Return (combined DataFrame of all outings on or after DATE_CUTOFF, count of those outings)."""
    frames = []
    for outing in getattr(profile, "outings", []):
        meta = outing.get("metadata", {})
        dt = _parse_outing_date(meta.get("date"))
        if not dt or dt.date() < DATE_CUTOFF:
            continue
        data = outing.get("data")
        if data is not None and isinstance(data, pd.DataFrame) and len(data) > 0:
            frames.append(data)
    if not frames:
        return None, 0
    return pd.concat(frames, ignore_index=True), len(frames)


def collect_pitcher_metrics(profiles_dir: Path):
    """Load each player profile, filter in-season outings, compute inning success.
    Returns list of (name, report_df, num_inseason_outings)."""
    results = []
    for entry in sorted(profiles_dir.iterdir()):
        if not entry.is_dir():
            continue
        split = split_player_dir_name(entry.name)
        if not split:
            continue
        first_name, last_name = split
        full_name = f"{first_name} {last_name}"
        if full_name in SKIP_PITCHERS:
            continue
        profile = load_player_profile(first_name, last_name, profiles_dir)
        if not profile:
            continue
        combined, num_outings = get_inseason_data(profile)
        if combined is None or len(combined) == 0:
            continue
        report = compute_inning_success_metrics(combined)
        if report.empty:
            continue
        results.append((full_name, report, num_outings))
    return results


def build_per_inning_leaders(pitcher_reports: list) -> pd.DataFrame:
    """For each inning and each metric, who had the best value? Columns: Inning, then for each metric: name, value (no 'Leader'/'Value' suffix for readability)."""
    # (display name for pitcher column, report column name for value)
    metrics = [
        ("PA Win", "PA Win %"),
        ("Whiff", "Whiff %"),
        ("Weak Contact", "Weak Contact %"),
        ("Dominance", "Dominance %"),
        ("Inning Success", "Inning Success %"),
    ]
    all_innings = set()
    for item in pitcher_reports:
        _, df, _ = item[0], item[1], item[2]
        all_innings.update(df["Inning"].dropna().astype(int).tolist())
    innings = sorted(all_innings)

    rows = []
    for inn in innings:
        row = {"Inning": inn}
        for name_col, report_col in metrics:
            best_val = None
            best_name = None
            for item in pitcher_reports:
                name, df, _ = item[0], item[1], item[2]
                r = df[df["Inning"] == inn]
                if r.empty:
                    continue
                val = r[report_col].iloc[0]
                if pd.isna(val):
                    continue
                if best_val is None or val > best_val:
                    best_val = val
                    best_name = name
            row[name_col] = best_name or "—"
            row[report_col] = f"{best_val:.1f}%" if best_val is not None else "—"
        rows.append(row)
    return pd.DataFrame(rows)


def build_overall_summary(pitcher_reports: list) -> pd.DataFrame:
    """One row per pitcher: name and average (or overall) Inning Success % and key metrics. Sorted by Inning Success % (highest first)."""
    rows = []
    for item in pitcher_reports:
        name, df = item[0], item[1]
        if df.empty:
            continue
        # Average across innings (keep numeric for sorting)
        pct_cols = ["PA Win %", "Whiff %", "Weak Contact %", "Dominance %", "Inning Success %"]
        row = {"Pitcher": name}
        for col in pct_cols:
            if col in df.columns:
                row[col] = df[col].mean()
        rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty and "Inning Success %" in out.columns:
        out = out.sort_values("Inning Success %", ascending=False).reset_index(drop=True)
    # Format as display strings
    for col in pct_cols:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"{float(x):.1f}%" if pd.notna(x) else "—")
    return out


def build_leaderboard_ranked(pitcher_reports: list, min_outings: int = LEADERBOARD_MIN_OUTINGS) -> pd.DataFrame:
    """Rank pitchers by average Inning Success % (best first). Only includes pitchers with >= min_outings. Best Inning = inning where they had their highest Inning Success %."""
    summary = []
    for item in pitcher_reports:
        name, df, num_outings = item[0], item[1], item[2]
        if num_outings < min_outings:
            continue
        if df.empty or "Inning Success %" not in df.columns:
            continue
        avg_success = df["Inning Success %"].mean()
        # Best Inning = inning number where Inning Success % was highest
        best_idx = df["Inning Success %"].idxmax()
        best_inning = int(df.loc[best_idx, "Inning"]) if best_idx is not None and pd.notna(best_idx) else None
        summary.append({
            "Pitcher": name,
            "Best Inning": best_inning if best_inning is not None else "—",
            "Inning Success %": avg_success,
        })
    if not summary:
        return pd.DataFrame()
    sdf = pd.DataFrame(summary)
    sdf = sdf.sort_values("Inning Success %", ascending=False).reset_index(drop=True)
    sdf["Rank"] = range(1, len(sdf) + 1)
    sdf["Inning Success %"] = sdf["Inning Success %"].apply(lambda x: f"{x:.1f}%")
    return sdf[["Rank", "Pitcher", "Best Inning", "Inning Success %"]]


def main():
    base_dir = Path(__file__).parent.parent
    profiles_dir = base_dir / "PlayerProfiles"
    output_dir = base_dir / "Master Reports"
    parser = argparse.ArgumentParser(description="Generate Master Inning Success report")
    parser.add_argument("--output-dir", "-o", type=Path, default=output_dir, help="Output directory")
    args = parser.parse_args()
    out_dir = args.output_dir if args.output_dir.is_absolute() else base_dir / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pitcher_reports = collect_pitcher_metrics(profiles_dir)
    if not pitcher_reports:
        print("No in-season data (outings since 2/13/2026) found for any pitcher.", file=sys.stderr)
        sys.exit(1)

    # Build data for the single output PDF
    leaders_df = build_per_inning_leaders(pitcher_reports)
    summary_df = build_overall_summary(pitcher_reports)
    rank_df = build_leaderboard_ranked(pitcher_reports, min_outings=LEADERBOARD_MIN_OUTINGS)

    # Only output: Master_Inning_Success_Report.pdf
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        pdf_path = out_dir / "Master_Inning_Success_Report.pdf"
        with PdfPages(pdf_path) as pdf:
            # Title
            fig, ax = plt.subplots(figsize=(11, 1.5), dpi=100)
            ax.axis("off")
            ax.text(0.5, 0.5, "Master Inning Success Report — In-Season", ha="center", va="center", fontsize=18, fontweight="bold")
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

            # Leaderboard (qualified: min 3 outings)
            if not rank_df.empty:
                fig, ax = plt.subplots(figsize=(11, 8.5), dpi=100)
                ax.axis("off")
                ax.set_title(f"Pitcher Leaderboard — Inning Success % — In-Season (min {LEADERBOARD_MIN_OUTINGS} outings)", fontsize=12, fontweight="bold", pad=20)
                cell_text = rank_df.values.tolist()
                table = ax.table(cellText=cell_text, colLabels=rank_df.columns, cellLoc="center", loc="center", bbox=[0, 0, 1, 1])
                table.auto_set_font_size(False)
                table.set_fontsize(10)
                table.scale(1, 2)
                for i in range(len(rank_df.columns)):
                    table[(0, i)].set_facecolor("#4CAF50")
                    table[(0, i)].set_text_props(weight="bold", color="white")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

            # Per-inning leaders (compact) — same table as standalone PDF
            if not leaders_df.empty:
                fig, ax = plt.subplots(figsize=(11, 8.5), dpi=100)
                ax.axis("off")
                ax.set_title("Per-Inning Leaders (Best Pitcher per Metric per Inning)", fontsize=12, fontweight="bold", pad=20)
                display = leaders_df.copy()
                cell_text = display.values.tolist()
                table = ax.table(cellText=cell_text, colLabels=display.columns, cellLoc="center", loc="center", bbox=[0, 0, 1, 1])
                table.auto_set_font_size(False)
                table.set_fontsize(7)
                table.scale(1, 1.8)
                for i in range(len(display.columns)):
                    table[(0, i)].set_facecolor("#673AB7")
                    table[(0, i)].set_text_props(weight="bold", color="white")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

            # Overall summary table
            if not summary_df.empty:
                fig, ax = plt.subplots(figsize=(11, 8.5), dpi=100)
                ax.axis("off")
                ax.set_title("In-Season Inning Success Summary (Avg per Pitcher)", fontsize=12, fontweight="bold", pad=20)
                cell_text = summary_df.values.tolist()
                table = ax.table(cellText=cell_text, colLabels=summary_df.columns, cellLoc="center", loc="center", bbox=[0, 0, 1, 1])
                table.auto_set_font_size(False)
                table.set_fontsize(9)
                table.scale(1, 2)
                for i in range(len(summary_df.columns)):
                    table[(0, i)].set_facecolor("#2196F3")
                    table[(0, i)].set_text_props(weight="bold", color="white")
                pdf.savefig(fig, bbox_inches="tight")
                plt.close(fig)

        print(f"Master PDF report saved: {pdf_path}")
    except Exception as e:
        print(f"Could not generate PDF: {e}", file=sys.stderr)

    print("Done.")


if __name__ == "__main__":
    main()
