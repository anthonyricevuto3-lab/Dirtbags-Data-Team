#!/usr/bin/env python3
"""
Write a one-page bullpen or game PDF for each saved outing.

Bullpen vs game comes from PracticeType / PitchSession when those columns
exist, otherwise from the source filename stored on the profile.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.profiles.paths import split_player_dir_name
from src.reports.outing_one_pager import classify_session, generate_outing_one_pager


def _outing_date(df: pd.DataFrame, metadata: dict) -> str:
    if metadata.get("date"):
        return str(metadata["date"])[:10]
    if "date" in df.columns:
        parsed = pd.to_datetime(df["date"], errors="coerce").dropna()
        if len(parsed) > 0:
            return parsed.iloc[0].strftime("%Y-%m-%d")
    return "undated"


def main():
    base = Path(__file__).parent.parent
    profiles = base / "PlayerProfiles"
    written = 0
    skipped = 0

    for player_dir in sorted(p for p in profiles.iterdir() if p.is_dir()):
        split = split_player_dir_name(player_dir.name)
        if not split:
            continue
        first, last = split
        meta_path = player_dir / "profile.json"
        outings_meta = []
        throws = ""
        if meta_path.exists():
            payload = json.loads(meta_path.read_text(encoding="utf-8"))
            outings_meta = payload.get("outings_metadata") or []
            throws = payload.get("throws") or ""
            first = payload.get("first_name") or first
            last = payload.get("last_name") or last
        name = f"{first} {last}"

        outing_files = sorted(player_dir.glob("outing_*.csv"))
        used_names = set()
        for index, outing_path in enumerate(outing_files):
            try:
                df = pd.read_csv(outing_path)
            except Exception as exc:
                print(f"[SKIP] {outing_path.name}: {exc}")
                skipped += 1
                continue
            if df.empty:
                skipped += 1
                continue
            metadata = outings_meta[index] if index < len(outings_meta) else {}
            source = metadata.get("source_file") or outing_path.name
            kind = classify_session(df, source)
            date_str = _outing_date(df, metadata)
            label = "Bullpen" if kind == "bullpen" else "Game"
            filename = f"{label}_{date_str}.pdf"
            if filename in used_names:
                filename = f"{label}_{date_str}_{outing_path.stem}.pdf"
            used_names.add(filename)
            output = player_dir / filename
            try:
                generate_outing_one_pager(
                    df,
                    str(output),
                    kind=kind,
                    name=name,
                    throws=metadata.get("throws") or throws,
                    outing_date=date_str,
                )
                written += 1
                print(f"[WROTE] {player_dir.name}/{output.name}")
            except Exception as exc:
                skipped += 1
                print(f"[ERROR] {player_dir.name}/{outing_path.name}: {exc}")

    print(f"\nWrote {written} one-page reports. Skipped {skipped}.")


if __name__ == "__main__":
    main()
