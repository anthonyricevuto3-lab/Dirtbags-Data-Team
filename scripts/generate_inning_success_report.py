#!/usr/bin/env python3
"""
Generate Pitcher Inning Success report from Trackman pitch-level data.

Reads a Trackman or outing CSV, computes five success metrics per inning
plus overall Inning Success %, and outputs a clear table for coaches/analysts.

Usage:
    python scripts/generate_inning_success_report.py path/to/data.csv
    python scripts/generate_inning_success_report.py path/to/data.csv --output report.csv
    python scripts/generate_inning_success_report.py --player Smith_John --outing 16
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from src.metrics.inning_success_metrics import compute_inning_success_metrics
from src.schemas import clean_trackman


def load_and_clean(csv_path: Path) -> pd.DataFrame:
    """Load CSV and normalize to canonical schema if needed."""
    df = pd.read_csv(csv_path, low_memory=False)
    # If raw Trackman, clean; if already outing format, may already have canonical names
    if "PitchCall" in df.columns or "PitchNo" in df.columns:
        df = clean_trackman(df, strict=False)
    return df


def format_report_table(report: pd.DataFrame) -> str:
    """Format report DataFrame as a readable table with % suffix for display."""
    out = report.copy()
    for col in ["PA Win %", "Whiff %", "Weak Contact %", "Dominance %", "Inning Success %"]:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")
    return out.to_string(index=False)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Pitcher Inning Success report from Trackman/outing CSV"
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        help="Path to Trackman or outing CSV",
    )
    parser.add_argument(
        "--output", "-o",
        help="Save report to this CSV path",
    )
    parser.add_argument(
        "--player",
        help="Player directory name (e.g. Smith_John). Use with --outing.",
    )
    parser.add_argument(
        "--outing",
        type=int,
        help="Outing number (e.g. 16 for outing_016.csv). Use with --player.",
    )
    parser.add_argument(
        "--exit-speed-threshold",
        type=float,
        default=85.0,
        help="Exit speed threshold for weak contact (mph). Default 85.",
    )
    parser.add_argument(
        "--runs-baseline",
        type=float,
        default=3.0,
        help="Runs per inning baseline for Run Prevention %%. Default 3.",
    )
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    csv_path = None

    if args.player and args.outing is not None:
        player_dir = base_dir / "PlayerProfiles" / args.player
        if not player_dir.is_dir():
            print(f"Error: Player directory not found: {player_dir}", file=sys.stderr)
            sys.exit(1)
        csv_path = player_dir / f"outing_{args.outing:03d}.csv"
        if not csv_path.is_file():
            print(f"Error: Outing file not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
    elif args.csv_path:
        csv_path = Path(args.csv_path)
        if not csv_path.is_absolute():
            csv_path = base_dir / csv_path
        if not csv_path.is_file():
            print(f"Error: File not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        print("\nProvide csv_path or (--player and --outing).", file=sys.stderr)
        sys.exit(1)

    df = load_and_clean(csv_path)
    if len(df) == 0:
        print("No data in file.", file=sys.stderr)
        sys.exit(1)

    report = compute_inning_success_metrics(
        df,
        exit_speed_threshold=args.exit_speed_threshold,
        runs_per_inning_baseline=args.runs_baseline,
    )

    if report.empty:
        print("No inning-level metrics could be computed (e.g. missing Inning column).", file=sys.stderr)
        sys.exit(1)

    # Console: formatted table with % signs
    print("Pitcher Inning Success Report")
    print(f"Source: {csv_path.name}")
    print()
    print(format_report_table(report))
    print()

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = base_dir / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report.to_csv(out_path, index=False)
        print(f"Report saved to: {out_path}")


if __name__ == "__main__":
    main()
