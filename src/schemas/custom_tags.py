"""
Parse Trackman CustomTags into pitch call, contact, and plate-appearance result.

PitchSession rows marked Warmup are dropped only when the same file also
contains Live pitches, so a warmup-only bullpen file is left intact.
"""

from __future__ import annotations

import pandas as pd


def _tag_set(value) -> set[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return set()
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return set()
    return {part.strip() for part in text.split("|") if part.strip()}


def filter_warmup_when_live_present(df: pd.DataFrame) -> pd.DataFrame:
    """Keep Live pitches when a file mixes Live and Warmup."""
    column = next((c for c in ("pitch_session", "PitchSession") if c in df.columns), None)
    if column is None:
        return df
    session = df[column].astype(str).str.strip().str.lower()
    if (session == "live").any() and (session == "warmup").any():
        return df.loc[session == "live"].copy()
    return df


def apply_custom_tag_calls(df: pd.DataFrame) -> pd.DataFrame:
    """
    Override pitch call fields from CustomTags.

    PI_* and PQ_* tags are ignored. Blank tags keep the Trackman pitch call.

    When a pitch-call tag disagrees with contact or a play result, the
    contact or play result wins:
    - HC_FOUL: foul ball (a swing, not a whiff), even with PC_BALL or PC_STRIKE
    - PC_BALL with PR_Single: walk, not a single
    - HC_IN_PLAY, PC_InPlay, PR_Single, PR_Double, PR_Out: ball in play
    - PC_StSw or HC_WHIFF with PR_Out, and no in-play or hit tag: swinging strikeout
    - PC_StSw or HC_WHIFF: swinging strike
    - PC_STRIKE: strike looking
    - PC_BALL: ball
    """
    column = next((c for c in ("custom_tags", "CustomTags") if c in df.columns), None)
    if column is None or df.empty:
        return df

    df = df.copy()
    for name in ("pitch_call", "KorBB", "play_result", "outs_on_play"):
        if name not in df.columns:
            df[name] = pd.NA

    for idx, raw in df[column].items():
        tags = _tag_set(raw)
        if not tags:
            continue

        swinging = "PC_StSw" in tags
        looking = "PC_STRIKE" in tags
        ball = "PC_BALL" in tags
        in_play = "PC_InPlay" in tags or "HC_IN_PLAY" in tags
        foul = "HC_FOUL" in tags
        whiff = "HC_WHIFF" in tags
        out = "PR_Out" in tags
        single = "PR_Single" in tags
        double = "PR_Double" in tags
        hit = single or double
        has_result = single or double or out

        call = None
        is_strike = is_swing = is_whiff = None
        korbb = pd.NA
        result = pd.NA
        outs = pd.NA
        write_result = True

        if foul:
            call, is_strike, is_swing, is_whiff = "FoulBall", True, True, False
            outs = 0
        elif ball and single:
            call, is_strike, is_swing, is_whiff = "BallCalled", False, False, False
            korbb, result, outs = "Walk", "Walk", 0
        elif (swinging or whiff) and out and not in_play and not hit:
            call, is_strike, is_swing, is_whiff = "StrikeSwinging", True, True, True
            korbb, outs = "Strikeout", 1
        elif in_play or has_result:
            call, is_strike, is_swing, is_whiff = "InPlay", True, True, False
            korbb = pd.NA
            if single:
                result, outs = "Single", 0
            elif double:
                result, outs = "Double", 0
            elif out:
                result, outs = "Out", 1
            else:
                write_result = False
        elif swinging or whiff:
            call, is_strike, is_swing, is_whiff = "StrikeSwinging", True, True, True
            outs = 0
        elif looking:
            call, is_strike, is_swing, is_whiff = "StrikeCalled", True, False, False
            outs = 0
        elif ball:
            call, is_strike, is_swing, is_whiff = "BallCalled", False, False, False
            outs = 0
        else:
            continue

        df.at[idx, "pitch_call"] = call
        if "strike" in df.columns:
            df.at[idx, "strike"] = is_strike
        if "swing" in df.columns:
            df.at[idx, "swing"] = is_swing
        if "whiff" in df.columns:
            df.at[idx, "whiff"] = is_whiff
        df.at[idx, "KorBB"] = korbb
        if write_result:
            df.at[idx, "play_result"] = result
        if outs is not pd.NA:
            df.at[idx, "outs_on_play"] = outs

    return df


def _blank_result(value) -> bool:
    text = str(value).strip().lower()
    return text in {"", "nan", "none", "<na>", "nat"}


def _batter_key(value) -> str:
    text = str(value).strip()
    if _blank_result(text):
        return ""
    try:
        number = float(text)
    except ValueError:
        return text.lower()
    if number.is_integer():
        return str(int(number))
    return text.lower()


def infer_results_from_batter_change(df: pd.DataFrame) -> pd.DataFrame:
    """
    When the hitter changes, fill an untagged plate appearance.

    A called strike is a strikeout only with two strikes already in the count.
    A ball is a walk only with three balls already in the count. A pitch that
    ends the appearance without that count is a hit-by-pitch when it is off
    the plate on the hitter's side, between the ankles and the head.
    """
    if df.empty:
        return df
    name = df["batter_name"] if "batter_name" in df.columns else None
    ident = df["batter_id"] if "batter_id" in df.columns else None
    if name is None and ident is None:
        return df

    df = df.copy()
    for column in ("KorBB", "play_result", "pitch_call"):
        if column not in df.columns:
            df[column] = pd.Series(pd.NA, index=df.index, dtype="object")
        else:
            df[column] = df[column].astype("object")
    if "outs_on_play" not in df.columns:
        df["outs_on_play"] = pd.NA

    keys = []
    for idx in df.index:
        chosen = ""
        if name is not None:
            chosen = _batter_key(name.at[idx])
        if not chosen and ident is not None:
            chosen = _batter_key(ident.at[idx])
        keys.append(chosen)

    previous = None
    for position, key in enumerate(keys):
        if not key:
            continue
        if previous is not None and key != keys[previous]:
            _finish_pa_from_batter_change(df, df.index[previous])
        previous = position
    return df


def _count_before(df: pd.DataFrame, idx, column: str) -> float:
    if column not in df.columns:
        return float("nan")
    value = pd.to_numeric(df.at[idx, column], errors="coerce")
    if pd.isna(value):
        return float("nan")
    return float(value)


def _plausible_hit_by_pitch(df: pd.DataFrame, idx) -> bool:
    """True when the pitch is off the plate on the hitter's body side."""
    if "batter_side" not in df.columns or "plate_x" not in df.columns or "plate_z" not in df.columns:
        return False
    side = str(df.at[idx, "batter_side"]).strip().upper()
    if side.startswith("R"):
        sign = 1.0
    elif side.startswith("L"):
        sign = -1.0
    else:
        return False
    plate_x = pd.to_numeric(df.at[idx, "plate_x"], errors="coerce")
    plate_z = pd.to_numeric(df.at[idx, "plate_z"], errors="coerce")
    if pd.isna(plate_x) or pd.isna(plate_z):
        return False
    inside = sign * float(plate_x)
    return 8.5 < inside <= 26 and 12 <= float(plate_z) <= 60


def _finish_pa_from_batter_change(df: pd.DataFrame, idx) -> None:
    korbb = str(df.at[idx, "KorBB"]).lower()
    result = str(df.at[idx, "play_result"]).lower()
    if "strikeout" in korbb or "walk" in korbb or "hitbypitch" in korbb:
        return
    if any(token in result for token in ("single", "double", "triple", "home", "out", "walk", "strikeout", "hitbypitch", "hit by pitch")):
        return
    call = str(df.at[idx, "pitch_call"]).lower()
    if "inplay" in call:
        return
    balls = _count_before(df, idx, "balls")
    strikes = _count_before(df, idx, "strikes")
    called_strike = "strikecalled" in call
    swinging_strike = "strikeswinging" in call or "whiff" in call
    ball = "ballcalled" in call or call == "ball"
    if (called_strike or swinging_strike) and pd.notna(strikes) and strikes >= 2:
        df.at[idx, "KorBB"] = "Strikeout"
        df.at[idx, "play_result"] = "Strikeout"
        df.at[idx, "outs_on_play"] = 1
    elif ball and pd.notna(balls) and balls >= 3:
        df.at[idx, "KorBB"] = "Walk"
        df.at[idx, "play_result"] = "Walk"
        df.at[idx, "outs_on_play"] = 0
    elif _plausible_hit_by_pitch(df, idx):
        df.at[idx, "pitch_call"] = "HitByPitch"
        df.at[idx, "play_result"] = "HitByPitch"
        df.at[idx, "outs_on_play"] = 0

