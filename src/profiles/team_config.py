"""
Load team-specific roster, allowed players, and pitch-grouping mappings.

Public repo ships config/team.example.yaml (fictional placeholders).
Local deployments copy it to config/team.local.yaml (gitignored) with real names.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"


def _normalize_name_key(first: str, last: str) -> str:
    return "".join(ch for ch in f"{first}{last}".lower() if ch.isalnum())


@lru_cache(maxsize=1)
def load_team_config() -> dict:
    local_path = _CONFIG_DIR / "team.local.yaml"
    example_path = _CONFIG_DIR / "team.example.yaml"
    path = local_path if local_path.exists() else example_path
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def get_allowed_players() -> List[Tuple[str, str]]:
    cfg = load_team_config()
    players = cfg.get("allowed_players") or []
    return [(p["first"], p["last"]) for p in players if p.get("first") and p.get("last")]


def get_skip_players() -> set:
    cfg = load_team_config()
    skip = cfg.get("skip_players") or []
    return {(p["first"], p["last"]) for p in skip if p.get("first") and p.get("last")}


def get_master_pitcher_splits_players() -> List[Tuple[str, str]]:
    cfg = load_team_config()
    players = cfg.get("master_pitcher_splits") or cfg.get("allowed_players") or []
    return [(p["first"], p["last"]) for p in players if p.get("first") and p.get("last")]


def get_master_hit_outcome_players() -> List[Tuple[str, str]]:
    cfg = load_team_config()
    players = cfg.get("master_hit_outcome") or cfg.get("allowed_players") or []
    return [(p["first"], p["last"]) for p in players if p.get("first") and p.get("last")]


def get_skip_pitchers_for_reports() -> set:
    cfg = load_team_config()
    skip = cfg.get("skip_pitchers_for_reports") or []
    return {str(name).strip() for name in skip if name}


def get_display_name(first: str, last: str) -> str:
    cfg = load_team_config()
    overrides = cfg.get("display_name_overrides") or {}
    key = _normalize_name_key(first, last)
    if key in overrides:
        return overrides[key]
    return f"{first} {last}"


def get_roster_entry(first_name: str, last_name: str) -> Dict[str, str]:
    cfg = load_team_config()
    roster = cfg.get("roster") or []
    first_l = first_name.strip().lower()
    last_l = last_name.strip().lower()
    for entry in roster:
        if (
            entry.get("first", "").strip().lower() == first_l
            and entry.get("last", "").strip().lower() == last_l
        ):
            return {
                k: v
                for k, v in entry.items()
                if k not in ("first", "last")
            }
    return {}


def get_pitch_grouping_style(first_name: str, last_name: str) -> Optional[str]:
    cfg = load_team_config()
    mapping = cfg.get("pitch_grouping") or {}
    first = (first_name or "").strip().lower()
    last = (last_name or "").strip().lower()
    full = f"{first} {last}".strip()

    for key, style in mapping.items():
        key_norm = str(key).lower().replace(" ", "").replace("_", "")
        if key_norm == _normalize_name_key(first_name, last_name):
            return style
        if str(key).lower() == full:
            return style

    # Reversed name order (e.g. hogan/shelby)
    rev_key = _normalize_name_key(last_name, first_name)
    for key, style in mapping.items():
        key_norm = str(key).lower().replace(" ", "").replace("_", "")
        if key_norm == rev_key:
            return style
    return None
