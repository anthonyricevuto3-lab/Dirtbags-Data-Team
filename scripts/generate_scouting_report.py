#!/usr/bin/env python3
"""
Generate opponent scouting report PDF.

Usage:
    python scripts/generate_scouting_report.py --opponent "UCLA" --hitters hitters.csv --pitchers pitchers.csv
"""

import sys
import argparse
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reports.scouting_report import generate_scouting_report


def main():
    """Main scouting report generation function."""
    parser = argparse.ArgumentParser(description='Generate opponent scouting report PDF')
    parser.add_argument('--opponent', required=True, help='Opponent team name')
    parser.add_argument('--hitters', help='Path to hitter scouting CSV')
    parser.add_argument('--pitchers', help='Path to pitcher scouting CSV')
    parser.add_argument('--usage', help='Path to usage pattern CSV')
    parser.add_argument('--output', '-o', help='Output PDF path (default: scouting_report.pdf)')
    parser.add_argument('--date', help='Series date')
    parser.add_argument('--location', help='Series location')
    parser.add_argument('--notes', help='Path to JSON file with internal notes')
    
    args = parser.parse_args()
    
    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = f"{args.opponent}_scouting_report.pdf"
    
    # Build series info
    series_info = {}
    if args.date:
        series_info['date'] = args.date
    if args.location:
        series_info['location'] = args.location
    
    # Load internal notes if provided
    internal_notes = {}
    if args.notes and Path(args.notes).exists():
        with open(args.notes, 'r') as f:
            internal_notes = json.load(f)
    
    print(f"Generating scouting report for {args.opponent}...")
    print(f"  Output: {output_path}")
    
    try:
        generate_scouting_report(
            hitter_data_path=args.hitters,
            pitcher_data_path=args.pitchers,
            usage_pattern_path=args.usage,
            output_path=output_path,
            opponent_name=args.opponent,
            series_info=series_info if series_info else None,
            internal_notes=internal_notes if internal_notes else None,
        )
        print(f"  [SUCCESS] Report generated successfully: {output_path}")
    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

