"""
Helpers for resolving player profile directory paths.
"""

from pathlib import Path
import shutil
from typing import Optional, Tuple


def get_player_dir(profiles_dir: Path, first_name: str, last_name: str) -> Path:
    """Return the canonical player directory path using Last_First format."""
    return Path(profiles_dir) / f"{last_name}_{first_name}"


def get_legacy_player_dir(profiles_dir: Path, first_name: str, last_name: str) -> Path:
    """Return the legacy player directory path (Last/First)."""
    return Path(profiles_dir) / last_name / first_name


def ensure_player_dir(profiles_dir: Path, first_name: str, last_name: str) -> Path:
    """
    Ensure the canonical player directory exists, migrating legacy structure if present.
    """
    target_dir = get_player_dir(profiles_dir, first_name, last_name)
    legacy_dir = get_legacy_player_dir(profiles_dir, first_name, last_name)

    if not target_dir.exists() and legacy_dir.exists():
        try:
            legacy_dir.rename(target_dir)
        except Exception:
            shutil.copytree(legacy_dir, target_dir, dirs_exist_ok=True)

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def split_player_dir_name(dir_name: str) -> Optional[Tuple[str, str]]:
    """
    Split a canonical directory name `Last_First` into (first, last).
    Returns None if the pattern is not matched.
    """
    if "_" not in dir_name:
        return None
    last_name, first_name = dir_name.split("_", 1)
    if not last_name or not first_name:
        return None
    return first_name, last_name
