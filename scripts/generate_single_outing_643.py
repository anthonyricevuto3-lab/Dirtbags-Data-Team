#!/usr/bin/env python3
"""
Generate 643-style single-outing PDFs for each pitcher, using their longest outing.

Usage:
    python scripts/generate_single_outing_643.py
"""

import sys
from pathlib import Path
import re
import pandas as pd
from datetime import datetime, date

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reports import generate_single_outing_643
from src.reports.pitch_grouping import apply_pitch_grouping_for_player
from src.profiles.roster import get_roster_entry
from src.profiles.paths import ensure_player_dir, split_player_dir_name


def parse_date_from_file(f: Path, df: pd.DataFrame) -> datetime:
    # Try date column (Date or date)
    for col in ("Date", "date"):
        if col in df.columns:
            d = pd.to_datetime(df[col], errors="coerce").dropna()
            if len(d) > 0:
                return d.iloc[0].to_pydatetime()
    # Fallback to filename YYYYMMDD
    m = re.search(r"(20\d{6})", f.name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y%m%d")
        except Exception:
            pass
    # Fallback to outing_<num> ordering
    m2 = re.search(r"outing_(\d+)", f.name, re.IGNORECASE)
    if m2:
        try:
            num = int(m2.group(1))
            # map outing number to a synthetic date ordering
            return datetime.fromtimestamp(num)
        except Exception:
            pass
    # Fallback to file modified time
    try:
        return datetime.fromtimestamp(f.stat().st_mtime)
    except Exception:
        pass
    # Fallback epoch
    return datetime.fromtimestamp(0)


def find_most_recent_outing(player_dir: Path):
    outing_files = sorted(player_dir.glob("outing_*.csv"))
    most_recent = None
    latest_dt = datetime.fromtimestamp(0)
    for f in outing_files:
        try:
            df = pd.read_csv(f)
        except Exception:
            continue
        dt = parse_date_from_file(f, df)
        if dt > latest_dt and len(df) > 0:
            latest_dt = dt
            most_recent = f
    return most_recent


def iter_outings_by_date(player_dir: Path):
    """Yield (outing_path, date) for each outing CSV, sorted by date (most recent last)."""
    outing_files = sorted(player_dir.glob("outing_*.csv"))
    dated = []
    for f in outing_files:
        try:
            df = pd.read_csv(f)
        except Exception:
            continue
        if len(df) == 0:
            continue
        dt = parse_date_from_file(f, df)
        dated.append((f, dt))
    dated.sort(key=lambda x: x[1])
    return dated


def iter_player_dirs(base: Path):
    """Yield (first, last, player_dir) for both canonical and legacy layouts."""
    for entry in base.iterdir():
        if not entry.is_dir():
            continue

        split = split_player_dir_name(entry.name)
        if split:
            first_name, last_name = split
            yield first_name, last_name, entry
            continue

        # Legacy Last/First layout
        for first_dir in entry.iterdir():
            if not first_dir.is_dir():
                continue
            first_name = first_dir.name
            last_name = entry.name
            player_dir = ensure_player_dir(base, first_name, last_name)
            yield first_name, last_name, player_dir


# Only generate single-outing PDFs for outings on or after this date (None = all outings)
SINGLE_OUTING_DATE_CUTOFF = date(2026, 2, 13)


def main():
    base = Path(__file__).parent.parent / "PlayerProfiles"
    if not base.exists():
        print("PlayerProfiles directory not found.")
        return

    for first_name, last_name, player_dir in iter_player_dirs(base):
        outings = list(iter_outings_by_date(player_dir))
        if not outings:
            continue
        if SINGLE_OUTING_DATE_CUTOFF is not None:
            def _on_or_after_cutoff(outing_dt):
                if outing_dt is None:
                    return False
                d = outing_dt.date() if hasattr(outing_dt, "date") else outing_dt
                return d >= SINGLE_OUTING_DATE_CUTOFF
            outings = [(p, dt) for p, dt in outings if _on_or_after_cutoff(dt)]
        if not outings:
            continue
        pitcher_name = f"{first_name} {last_name}"

        for outing_path, outing_dt in outings:
            try:
                df = pd.read_csv(outing_path)
            except Exception as e:
                print(f"Failed to read {outing_path}: {e}")
                continue
            if len(df) == 0:
                continue

            # Determine outing date: prefer 'date' column in CSV
            date_str = outing_dt.strftime("%m-%d-%Y") if outing_dt else "UnknownDate"
            if "date" in df.columns:
                dt_series = pd.to_datetime(df["date"], errors="coerce").dropna()
                if len(dt_series) > 0:
                    date_str = dt_series.iloc[0].strftime("%m-%d-%Y")

            out_pdf = player_dir / f"{first_name}_{last_name}_Appearance_{date_str}.pdf"
            print(f"Generating {out_pdf.name} from {outing_path.name}")
            # Pitcher-specific pitch grouping (from team config)
            df = apply_pitch_grouping_for_player(df, first_name, last_name)

            try:
                roster = get_roster_entry(first_name, last_name)
                header = {
                    "name": pitcher_name,
                    "position": roster.get("position"),
                    "bats": roster.get("bats"),
                    "throws": roster.get("throws"),
                }
                generate_single_outing_643(df, str(out_pdf), title=f"{pitcher_name} - Single Outing", header=header)
            except Exception as e:
                print(f"Error generating {out_pdf}: {e}")


if __name__ == "__main__":
    main()
