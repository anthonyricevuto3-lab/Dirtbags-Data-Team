"""
Pitcher inning success metrics from Trackman pitch-level data.

Computes five metrics per inning and a combined Inning Success % for
coaches and analysts. Handles missing values and 0 denominators safely.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Optional

# Column name variants (cleaned schema vs raw Trackman)
INNING_COLS = ["inning", "Inning"]
TOP_BOTTOM_COLS = ["top_bottom", "Top/Bottom"]
PA_OF_INNING_COLS = ["pa_of_inning", "PAofInning"]
PITCH_CALL_COLS = ["pitch_call", "PitchCall"]
EXIT_VELOCITY_COLS = ["exit_velocity", "ExitSpeed"]
RUNS_SCORED_COLS = ["runs_scored", "RunsScored"]
KORBB_COLS = ["KorBB", "KorBB"]
OUTS_ON_PLAY_COLS = ["outs_on_play", "OutsOnPlay"]


def _col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    """Return first column name that exists in df."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _safe_pct(num: float, denom: float, default: float = 0.0) -> float:
    """Return num/denom as a 0-1 ratio, or default if denom is 0 or invalid."""
    if denom is None or pd.isna(denom) or denom == 0:
        return default
    if num is None or pd.isna(num):
        return default
    return float(np.clip(num / denom, 0.0, 1.0))


def _safe_pct_100(num: float, denom: float, default: float = 0.0) -> float:
    """Return percentage 0-100."""
    return _safe_pct(num, denom, default) * 100.0


def compute_pa_win_pct_by_inning(df: pd.DataFrame) -> pd.Series:
    """
    PA Win % per inning.
    PA is won if KorBB = Strikeout or OutsOnPlay > 0.
    PA Win % = (PAs with strikeout or out) / total PAs.
    """
    inning_col = _col(df, INNING_COLS)
    top_bottom_col = _col(df, TOP_BOTTOM_COLS)
    pa_col = _col(df, PA_OF_INNING_COLS)
    korbb_col = _col(df, KORBB_COLS)
    outs_col = _col(df, OUTS_ON_PLAY_COLS)

    if not inning_col or not pa_col:
        return pd.Series(dtype=float)

    # Group key for unique PAs: inning and optionally top_bottom + pa_of_inning
    if top_bottom_col and pa_col:
        pa_groups = df.groupby([inning_col, top_bottom_col, pa_col], dropna=False)
    else:
        pa_groups = df.groupby([inning_col, pa_col], dropna=False)

    def pa_won(grp: pd.DataFrame) -> bool:
        if korbb_col and grp[korbb_col].astype(str).str.strip().str.lower().eq("strikeout").any():
            return True
        if outs_col is not None:
            try:
                o = pd.to_numeric(grp[outs_col], errors="coerce").fillna(0)
                if (o > 0).any():
                    return True
            except Exception:
                pass
        return False

    try:
        wins = pa_groups.apply(pa_won, include_groups=False)
    except TypeError:
        wins = pa_groups.apply(pa_won)
    # wins is Series with multi-index (inning, top_bottom, pa_of_inning) -> bool
    # Aggregate by inning: count wins and total PAs per inning
    if isinstance(wins.index, pd.MultiIndex):
        inning_level = wins.index.get_level_values(0)
    else:
        inning_level = wins.index
    by_inning = pd.DataFrame({"won": wins.astype(int), "inn": inning_level}).groupby("inn").agg(
        pa_wins=("won", "sum"), pa_total=("won", "count")
    )
    pct = by_inning["pa_wins"] / by_inning["pa_total"].replace(0, np.nan)
    pct = pct.fillna(0).clip(0, 1)
    return pct


def compute_weak_contact_pct_by_inning(df: pd.DataFrame, exit_speed_threshold: float = 85.0) -> pd.Series:
    """
    Weak Contact % per inning.
    Weak = ball in play with ExitSpeed < threshold (default 85 mph).
    Weak Contact % = weak contact events / total balls in play.
    """
    inning_col = _col(df, INNING_COLS)
    pc_col = _col(df, PITCH_CALL_COLS)
    ev_col = _col(df, EXIT_VELOCITY_COLS)

    if not inning_col or not pc_col:
        return pd.Series(dtype=float)

    in_play = df[df[pc_col].astype(str).str.strip().str.lower().eq("inplay")]
    if in_play.empty:
        return pd.Series(dtype=float)

    if not ev_col:
        return pd.Series(dtype=float)

    ev = pd.to_numeric(in_play[ev_col], errors="coerce")
    valid_bip = ev.notna()
    weak = (ev < exit_speed_threshold) & valid_bip
    by_inning = in_play.assign(
        _ev=ev,
        _weak=weak.astype(int),
        _bip=valid_bip.astype(int),
    ).groupby(inning_col).agg(weak=("_weak", "sum"), bip=("_bip", "sum"))
    pct = by_inning["weak"] / by_inning["bip"].replace(0, np.nan)
    pct = pct.fillna(0).clip(0, 1)
    return pct


def compute_whiff_pct_by_inning(df: pd.DataFrame) -> pd.Series:
    """
    Whiff % per inning.
    Swings = StrikeSwinging, FoulBall (and FoulBallNotFieldable), InPlay.
    Whiffs = StrikeSwinging.
    Whiff % = swinging strikes / total swings.
    """
    inning_col = _col(df, INNING_COLS)
    pc_col = _col(df, PITCH_CALL_COLS)

    if not inning_col or not pc_col:
        return pd.Series(dtype=float)

    pc = df[pc_col].astype(str).str.strip().str.lower()
    swing_values = {"strikeswinging", "foulball", "foulballnotfieldable", "inplay"}
    swings = pc.isin(swing_values)
    whiffs = pc.eq("strikeswinging")

    by_inning = df.assign(_swing=swings.astype(int), _whiff=whiffs.astype(int)).groupby(inning_col).agg(
        swings=("_swing", "sum"), whiffs=("_whiff", "sum")
    )
    pct = by_inning["whiffs"] / by_inning["swings"].replace(0, np.nan)
    pct = pct.fillna(0).clip(0, 1)
    return pct


def compute_run_prevention_pct_by_inning(df: pd.DataFrame, runs_per_inning_baseline: float = 3.0) -> pd.Series:
    """
    Run Prevention % per inning.
    Run Prevention % = 1 - (RunsScored in inning / baseline), clamped to [0, 1].
    """
    inning_col = _col(df, INNING_COLS)
    runs_col = _col(df, RUNS_SCORED_COLS)

    if not inning_col:
        return pd.Series(dtype=float)

    if not runs_col:
        uniq = df[inning_col].dropna().unique()
        return pd.Series(1.0, index=pd.Index(uniq))

    runs = pd.to_numeric(df[runs_col], errors="coerce").fillna(0)
    by_inning = df.assign(_runs=runs).groupby(inning_col)["_runs"].sum()
    pct = 1.0 - (by_inning / runs_per_inning_baseline)
    pct = pct.clip(0.0, 1.0)
    return pct


def compute_strike_pct_by_inning(df: pd.DataFrame) -> pd.Series:
    """
    Strike % per inning for dominance.
    Strikes = StrikeCalled (CalledStrike), StrikeSwinging, FoulBall, InPlay.
    """
    inning_col = _col(df, INNING_COLS)
    pc_col = _col(df, PITCH_CALL_COLS)

    if not inning_col or not pc_col:
        return pd.Series(dtype=float)

    pc = df[pc_col].astype(str).str.strip().str.lower()
    strike_values = {
        "strikecalled", "calledstrike", "strikeswinging",
        "foulball", "foulballnotfieldable", "inplay",
    }
    strikes = pc.isin(strike_values)
    g = df.assign(_strike=strikes.astype(int)).groupby(inning_col)
    by_inning = g["_strike"].sum().to_frame("strikes")
    by_inning["total"] = g.size()
    pct = by_inning["strikes"] / by_inning["total"].replace(0, np.nan)
    pct = pct.fillna(0).clip(0, 1)
    return pct


def compute_dominance_pct_by_inning(
    df: pd.DataFrame,
    weak_contact_pct: Optional[pd.Series] = None,
    whiff_pct: Optional[pd.Series] = None,
    exit_speed_threshold: float = 85.0,
) -> pd.Series:
    """
    Pitch Dominance % per inning.
    Dominance % = 0.5 * Strike % + 0.3 * Whiff % + 0.2 * Weak Contact %
    """
    strike_pct = compute_strike_pct_by_inning(df)
    if whiff_pct is None:
        whiff_pct = compute_whiff_pct_by_inning(df)
    if weak_contact_pct is None:
        weak_contact_pct = compute_weak_contact_pct_by_inning(df, exit_speed_threshold)

    # Align indices (innings present in any metric)
    innings = strike_pct.index.union(whiff_pct.index).union(weak_contact_pct.index).unique()
    strike_pct = strike_pct.reindex(innings).fillna(0)
    whiff_pct = whiff_pct.reindex(innings).fillna(0)
    weak_contact_pct = weak_contact_pct.reindex(innings).fillna(0)

    dominance = 0.5 * strike_pct + 0.3 * whiff_pct + 0.2 * weak_contact_pct
    return dominance.clip(0, 1)


def compute_inning_success_pct(
    pa_win: pd.Series,
    whiff: pd.Series,
    weak_contact: pd.Series,
    dominance: pd.Series,
    weights: Optional[dict[str, float]] = None,
) -> pd.Series:
    """
    Combined Inning Success % = weighted sum of the four metrics, scaled 0–100%.
    Default weights: 0.30 PA Win, 0.25 Whiff, 0.25 Weak Contact, 0.20 Dominance.
    """
    if weights is None:
        weights = {
            "pa_win": 0.30,
            "whiff": 0.25,
            "weak_contact": 0.25,
            "dominance": 0.20,
        }
    innings = (
        pa_win.index.union(whiff.index)
        .union(weak_contact.index)
        .union(dominance.index)
        .unique()
    )
    pa_win = pa_win.reindex(innings).fillna(0)
    whiff = whiff.reindex(innings).fillna(0)
    weak_contact = weak_contact.reindex(innings).fillna(0)
    dominance = dominance.reindex(innings).fillna(0)

    total = (
        weights["pa_win"] * pa_win
        + weights["whiff"] * whiff
        + weights["weak_contact"] * weak_contact
        + weights["dominance"] * dominance
    )
    return (total.clip(0, 1) * 100.0).round(2)


def compute_inning_success_metrics(
    df: pd.DataFrame,
    exit_speed_threshold: float = 85.0,
    runs_per_inning_baseline: float = 3.0,
) -> pd.DataFrame:
    """
    Compute four metrics and Inning Success % per inning.
    Returns a DataFrame with columns:
    Inning, PA Win %, Whiff %, Weak Contact %, Dominance %, Inning Success %
    Percentages are 0–100. Missing values and zero denominators handled safely.
    """
    # Drop rows with no inning
    inning_col = _col(df, INNING_COLS)
    if not inning_col:
        return pd.DataFrame(
            columns=[
                "Inning",
                "PA Win %",
                "Whiff %",
                "Weak Contact %",
                "Dominance %",
                "Inning Success %",
            ]
        )
    work = df[df[inning_col].notna()].copy()
    if work.empty:
        return pd.DataFrame(
            columns=[
                "Inning",
                "PA Win %",
                "Whiff %",
                "Weak Contact %",
                "Dominance %",
                "Inning Success %",
            ]
        )

    pa_win = compute_pa_win_pct_by_inning(work)
    whiff = compute_whiff_pct_by_inning(work)
    weak_contact = compute_weak_contact_pct_by_inning(work, exit_speed_threshold)
    dominance = compute_dominance_pct_by_inning(work, weak_contact_pct=weak_contact, whiff_pct=whiff)

    innings = (
        pa_win.index.union(whiff.index)
        .union(weak_contact.index)
        .union(dominance.index)
        .unique()
    )
    innings = sorted([i for i in innings if pd.notna(i)], key=lambda x: (float("-inf") if x == "" else x))

    pa_win = pa_win.reindex(innings).fillna(0) * 100
    whiff = whiff.reindex(innings).fillna(0) * 100
    weak_contact = weak_contact.reindex(innings).fillna(0) * 100
    dominance = dominance.reindex(innings).fillna(0) * 100

    inning_success = compute_inning_success_pct(
        pa_win / 100.0, whiff / 100.0, weak_contact / 100.0, dominance / 100.0
    )

    report = pd.DataFrame(
        {
            "Inning": innings,
            "PA Win %": pa_win.values.round(1),
            "Whiff %": whiff.values.round(1),
            "Weak Contact %": weak_contact.values.round(1),
            "Dominance %": dominance.values.round(1),
            "Inning Success %": inning_success.values,
        }
    )
    return report
