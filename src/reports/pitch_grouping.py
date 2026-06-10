"""
Configurable pitch-type grouping for pitcher reports.

Styles are named templates (no player names). Map players to styles via
config/team.local.yaml or config/team.example.yaml.
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Set

import pandas as pd

from ..profiles.team_config import get_pitch_grouping_style


def normalize_pitch_type_key(val: str) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    key = str(val).strip().lower()
    key = key.replace("-", "").replace(" ", "").replace("_", "")
    return key


# Shared source pitch-type buckets
_TO_2SEAM = {"2seamfastball", "twoseamfastball", "2seam", "twoseam", "2seamfast ball"}
_TO_4SEAM_FASTBALL = {
    "oneseamfastball", "oneseamfast ball", "cutter",
    "fourseamfastball", "4seamfastball", "fourseam", "4seam", "fastball",
}
_TO_SINKER = {"sinker", "sinkers"}
_TO_CURVE = {"curveball", "curve"}
_TO_CHANGE = {"changeup", "change", "changeups"}
_TO_SWEEPER = {"sweeper", "sweepers"}


PITCH_GROUPING_STYLES: Dict[str, Dict[str, Set[str]]] = {
    "multi_fastball_sinker_slider": {
        "Fastball": _TO_4SEAM_FASTBALL,
        "Sinker": _TO_2SEAM,
        "Slider": _TO_CURVE,
    },
    "slider_to_2seam": {
        "Slider": _TO_CURVE,
        "2-Seam Fastball": _TO_SINKER,
    },
    "sinker_splitter": {
        "Sinker": _TO_2SEAM,
        "Splitter": _TO_CHANGE,
    },
    "sweeper_to_slider": {
        "Slider": _TO_SWEEPER,
    },
    "2seam_to_fastball": {
        "Fastball": _TO_2SEAM,
    },
    "change_to_splitter": {
        "Splitter": _TO_CHANGE,
    },
    "2seam_to_sinker": {
        "Sinker": _TO_2SEAM,
    },
    "4seam_fastball_2seam_sinker": {
        "Fastball": _TO_4SEAM_FASTBALL,
        "Sinker": _TO_2SEAM,
    },
    "2seam_sinker_curve_slider": {
        "Sinker": _TO_2SEAM,
        "Slider": _TO_CURVE,
    },
    "2seam_fastball": {
        "Fastball": _TO_2SEAM,
    },
    "curve_to_sweeper": {
        "Sweeper": _TO_CURVE,
    },
    "2seam_sinker_to_fastball": {
        "Fastball": _TO_2SEAM | _TO_SINKER,
    },
}


def _resolve_pitch_type_column(df: pd.DataFrame) -> Optional[str]:
    for col in ("pitch_type", "Pitch Type", "TaggedPitchType", "AutoPitchType"):
        if col in df.columns:
            return col
    return None


def apply_pitch_grouping_style(df: pd.DataFrame, style_name: str) -> pd.DataFrame:
    """Apply a named pitch-grouping style to a DataFrame."""
    if df is None or df.empty:
        return df
    rules = PITCH_GROUPING_STYLES.get(style_name)
    if not rules:
        return df

    df = df.copy()
    pt_col = _resolve_pitch_type_column(df)
    if pt_col is None:
        return df
    if pt_col != "pitch_type":
        df["pitch_type"] = df[pt_col].astype(str)

    pt = df["pitch_type"].astype(str)
    new_pt = pt.copy()
    for i, val in enumerate(pt):
        key = normalize_pitch_type_key(val)
        if not key:
            continue
        for target_label, sources in rules.items():
            if key in sources:
                new_pt.iloc[i] = target_label
                break

    df["pitch_type"] = new_pt
    return df


def apply_pitch_grouping_for_player(
    df: pd.DataFrame,
    first_name: str,
    last_name: str,
) -> pd.DataFrame:
    style = get_pitch_grouping_style(first_name, last_name)
    if style:
        return apply_pitch_grouping_style(df, style)
    return df


def get_pitch_grouping_fn(profile) -> Optional[Callable[[pd.DataFrame], pd.DataFrame]]:
    style = get_pitch_grouping_style(
        getattr(profile, "first_name", ""),
        getattr(profile, "last_name", ""),
    )
    if style:
        return lambda df: apply_pitch_grouping_style(df, style)
    return None
