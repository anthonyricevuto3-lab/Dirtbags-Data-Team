#!/usr/bin/env python3
"""
Generate Trackman postgame PDF report from CSV.

Usage:
    python scripts/generate_report.py <trackman.csv> --pitcher "Name" --game "Game1" --opponent "UCLA"
    python scripts/generate_report.py data.csv --pitcher "Smith" --output report.pdf
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reports import generate_trackman_report


def main():
    """Main report generation function."""
    parser = argparse.ArgumentParser(description='Generate Trackman postgame PDF report')
    parser.add_argument('csv_path', help='Path to Trackman CSV file')
    parser.add_argument('--pitcher', required=True, help='Pitcher name')
    parser.add_argument('--output', '-o', help='Output PDF path (default: <csv_name>_report.pdf)')
    parser.add_argument('--opponent', help='Opponent name')
    parser.add_argument('--game', help='Game identifier (e.g., Game1)')
    parser.add_argument('--date', help='Game date')
    
    args = parser.parse_args()
    
    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"Error: CSV file does not exist: {csv_path}")
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = csv_path.parent / f"{csv_path.stem}_report.pdf"
    
    # Build game info
    game_info = {}
    if args.opponent:
        game_info['opponent'] = args.opponent
    if args.game:
        game_info['game'] = args.game
    if args.date:
        game_info['date'] = args.date
    
    print(f"Generating report for {args.pitcher}...")
    print(f"  Input: {csv_path}")
    print(f"  Output: {output_path}")
    
    try:
        generate_trackman_report(
            csv_path=str(csv_path),
            output_path=str(output_path),
            pitcher_name=args.pitcher,
            game_info=game_info if game_info else None,
        )
        print(f"  [SUCCESS] Report generated successfully: {output_path}")
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

