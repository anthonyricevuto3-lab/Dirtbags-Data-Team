#!/usr/bin/env python3
"""Write preview outing sheets and pitcher profiles without replacing current PDFs."""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics.preview_metrics import build_baseline, build_whiff_spots
from src.schemas import clean_trackman
from src.profiles.paths import split_player_dir_name
from src.reports.outing_one_pager import classify_session
from src.reports.player_profile_report import (
    FALL_2026_END,
    FALL_2026_START,
    DATE_CUTOFF_2026,
    _parse_outing_date,
)
from src.reports.preview_reports import generate_preview_outing, generate_preview_profile


def _outing_date(df: pd.DataFrame, metadata: dict) -> str:
    if metadata.get("date"):
        return str(metadata["date"])[:10]
    if "date" in df.columns:
        parsed = pd.to_datetime(df["date"], errors="coerce").dropna()
        if len(parsed):
            return parsed.iloc[0].strftime("%Y-%m-%d")
    return "undated"


def _kind(df: pd.DataFrame, source: str) -> str:
    name = Path(source).name.lower()
    if "intrasquad" in name or " is." in name or " vs" in name:
        return "game"
    return classify_session(df, source)


def _subtitle(kind: str, source: str, outing_date: str) -> str:
    stem = Path(source).stem
    if "intrasquad" in stem.lower() or re.search(r"\bis\b", stem, flags=re.I):
        return f"Intrasquad {outing_date}"
    if kind == "bullpen":
        return f"Bullpen {outing_date}"
    return f"Game {outing_date}"


def _attach_approach(df: pd.DataFrame, source_path: str, pitcher: str) -> pd.DataFrame:
    path = Path(source_path) if source_path else None
    if path is None or not path.exists() or "pitch_number" not in df.columns:
        return df
    raw = pd.read_csv(path, low_memory=False)
    needed = [column for column in ("PitchNo", "VertApprAngle", "InducedVertBreak") if column in raw.columns]
    if "PitchNo" not in needed:
        return df
    if "Pitcher" in raw.columns and pitcher:
        raw = raw[raw["Pitcher"].astype(str).str.strip() == pitcher.strip()]
    extra = raw[needed].rename(
        columns={"PitchNo": "pitch_number", "VertApprAngle": "vaa_raw", "InducedVertBreak": "ivb_raw"}
    )
    extra["pitch_number"] = pd.to_numeric(extra["pitch_number"], errors="coerce")
    extra = extra.drop_duplicates("pitch_number")
    work = df.copy()
    work["pitch_number"] = pd.to_numeric(work["pitch_number"], errors="coerce")
    merged = work.merge(extra, on="pitch_number", how="left")
    if "vaa_raw" in merged.columns:
        merged["vaa"] = pd.to_numeric(merged["vaa_raw"], errors="coerce")
        merged = merged.drop(columns=["vaa_raw"])
    if "ivb_raw" in merged.columns:
        induced = pd.to_numeric(merged["ivb_raw"], errors="coerce")
        merged["ivb"] = induced.where(induced.notna(), pd.to_numeric(merged.get("ivb"), errors="coerce"))
        merged = merged.drop(columns=["ivb_raw"])
    return merged


def _in_window(metadata: dict, start: date | None, end: date | None) -> bool:
    parsed = _parse_outing_date(metadata.get("date"))
    if parsed is None:
        return start is None
    outing_date = parsed.date() if isinstance(parsed, datetime) else parsed
    if start is not None and outing_date < start:
        return False
    if end is not None and outing_date > end:
        return False
    return True


def _in_season_outing(frame: pd.DataFrame, meta: dict) -> bool:
    """In-season starts 2/13/2026. Games on or after 9/1/2026 stay in the fall profile."""
    if not _in_window(meta, DATE_CUTOFF_2026, None):
        return False
    parsed = _parse_outing_date(meta.get("date"))
    if parsed is None:
        return True
    outing_date = parsed.date() if isinstance(parsed, datetime) else parsed
    if outing_date >= FALL_2026_START and _kind(frame, meta.get("source_file") or "") == "game":
        return False
    return True


def _only_since(loaded: list, start: date) -> bool:
    """True when every outing has a date on or after start."""
    dates = []
    for _, _, meta in loaded:
        parsed = _parse_outing_date(meta.get("date"))
        if parsed is None:
            return False
        dates.append(parsed.date() if isinstance(parsed, datetime) else parsed)
    return bool(dates) and all(outing_date >= start for outing_date in dates)


def _game_table(source_path: str, cache: dict) -> pd.DataFrame | None:
    if not source_path:
        return None
    if source_path not in cache:
        path = Path(source_path)
        if not path.exists():
            cache[source_path] = None
        else:
            cache[source_path] = clean_trackman(pd.read_csv(path, low_memory=False), strict=False)
    return cache[source_path]


def _combine(frames: list[pd.DataFrame]) -> pd.DataFrame:
    usable = [frame for frame in frames if frame is not None and len(frame)]
    if not usable:
        return pd.DataFrame()
    return pd.concat(usable, ignore_index=True)


def main():
    bullpens_only = "--bullpens" in sys.argv
    games_only = "--games" in sys.argv
    profiles_only = "--profiles" in sys.argv
    base = Path(__file__).parent.parent
    profiles = base / "PlayerProfiles"
    outing_frames = []
    players = []
    for player_dir in sorted(path for path in profiles.iterdir() if path.is_dir()):
        split = split_player_dir_name(player_dir.name)
        if not split:
            continue
        meta_path = player_dir / "profile.json"
        if not meta_path.exists():
            continue
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
        metadata = payload.get("outings_metadata") or []
        files = sorted(player_dir.glob("outing_*.csv"))
        loaded = []
        for index, path in enumerate(files):
            frame = pd.read_csv(path)
            meta = metadata[index] if index < len(metadata) else {}
            source = meta.get("source_path") or ""
            pitcher = meta.get("player_id") or payload.get("player_id") or ""
            frame = _attach_approach(frame, source, str(pitcher))
            loaded.append((path, frame, meta))
            outing_frames.append(frame)
        if loaded:
            players.append((player_dir, payload, loaded))

    combined = _combine(outing_frames)
    baseline = build_baseline(combined)
    whiff_spots = build_whiff_spots(combined)
    game_cache: dict = {}
    written = 0
    for player_dir, payload, loaded in players:
        first = payload.get("first_name") or split_player_dir_name(player_dir.name)[0]
        last = payload.get("last_name") or split_player_dir_name(player_dir.name)[1]
        name = f"{first} {last}"
        throws = payload.get("throws") or ""
        ordered = sorted(loaded, key=lambda item: _outing_date(item[1], item[2]))
        previous = None
        used = set()
        for path, frame, meta in ordered:
            source = meta.get("source_file") or path.name
            source_path = meta.get("source_path") or ""
            kind = _kind(frame, source)
            outing_date = _outing_date(frame, meta)
            if profiles_only:
                previous = frame
                continue
            if bullpens_only and kind != "bullpen":
                previous = frame
                continue
            if games_only and kind != "game":
                previous = frame
                continue
            label = "Bullpen" if kind == "bullpen" else "Game"
            filename = f"{label}_{outing_date}.pdf"
            if filename in used:
                filename = f"{label}_{outing_date}_{path.stem}.pdf"
            used.add(filename)
            generate_preview_outing(
                frame,
                str(player_dir / filename),
                kind=kind,
                name=name,
                throws=throws,
                outing_date=outing_date,
                subtitle=_subtitle(kind, source, outing_date),
                baseline=baseline,
                previous=previous,
                whiff_spots=whiff_spots,
                game=_game_table(source_path, game_cache) if kind == "game" else None,
            )
            previous = frame
            written += 1
            print(f"[WROTE] {player_dir.name}/{filename}")

        if bullpens_only or games_only:
            continue
        fall_only = _only_since(ordered, FALL_2026_START)
        windows = [
            (f"{name.replace(' ', '_')}_Profile.pdf", "Player Profile", None, None),
            (f"2026_In-Season_{name.replace(' ', '_')}_Player_Profile.pdf", "2026 In-Season", DATE_CUTOFF_2026, None),
            (
                f"Fall_2026_{name.replace(' ', '_')}_Player_Profile.pdf",
                "Fall 2026",
                FALL_2026_START,
                FALL_2026_END,
            ),
        ]
        for filename, title, start, end in windows:
            if title == "2026 In-Season" and fall_only:
                existing = player_dir / filename
                if existing.exists():
                    existing.unlink()
                    print(f"[REMOVED] {player_dir.name}/{filename}")
                continue
            if title == "2026 In-Season":
                selected = [(frame, meta) for _, frame, meta in ordered if _in_season_outing(frame, meta)]
            else:
                selected = [(frame, meta) for _, frame, meta in ordered if _in_window(meta, start, end)]
            chosen = _combine([frame for frame, _ in selected])
            if chosen.empty:
                continue
            dates = [_outing_date(frame, meta) for frame, meta in selected]
            span = f"{min(dates)} – {max(dates)}" if dates else ""
            generate_preview_profile(
                chosen,
                str(player_dir / filename),
                name=name,
                throws=throws,
                title=title,
                date_span=span,
                baseline=baseline,
            )
            written += 1
            print(f"[WROTE] {player_dir.name}/{filename}")
    print(f"Wrote {written} preview reports.")


if __name__ == "__main__":
    main()
