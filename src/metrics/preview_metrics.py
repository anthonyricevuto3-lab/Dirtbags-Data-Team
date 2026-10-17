"""
Stats for the preview outing sheet and the preview pitcher profile.

Stuff+ and Location+ use this Dirtbags group as the baseline: 100 is the
group average for that pitch type. wOBA uses published linear weights.
xwOBA uses those same weights for walks, hit-by-pitches, and strikeouts, and
a contact table built from the public Statcast barrel definition plus typical
batted-ball weights. It is not MLB's private xwOBA model.

Outing grade (games): strike rate, whiff rate, strikeouts minus walks per
plate appearance, and hard-hit rate.
Finish grade: two-strike whiff rate and two-strike put-away rate.
Bullpen grade: 65% stuff, 25% control, 10% release. Control is the in-zone
rate (used as the strike rate), the shadow rate, and the heart rate.
Stuff is Stuff+. Release is how steady release height, release side, and
extension are.

Game grade: the letter comes from runs per inning. One run every 3
innings is an A, every 2.5 innings is a B, and every 1.5 innings is a C.
A reliever who enters after the first inning gets a C for one run per
inning. Worse than a run every two-thirds of an inning is an F. In an
in-season game, a pitcher who starts is dropped one letter under 5 innings
and raised one letter over 6. Fall games are not dropped for a short start.
One inning with fewer than 3 runs is treated as an opener and is not
dropped. With no run total, the letter comes from the results: walks, hits, and outs, with
weak contact scoring much better than hard contact. Those same results
only add a plus or a minus when a run total exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from ..schemas.custom_tags import infer_results_from_batter_change
from .pitch_metrics import _location_masks

# FanGraphs-style linear weights (the commonly published unadjusted scale).
W_BB = 0.690
W_HBP = 0.722
W_1B = 0.888
W_2B = 1.271
W_3B = 1.616
W_HR = 2.101

STUFF_FEATURES = ("velocity", "spin_rate", "extension", "movement")


def _text(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series("", index=df.index)
    return df[column].astype(str).str.strip()


def _flag(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    series = df[column]
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin(["true", "1", "yes", "t"])


def _num(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return pd.to_numeric(df[column], errors="coerce")


def prepare_pitches(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize the columns the preview stats read."""
    work = df.copy()
    if "batter_name" not in work.columns and "batter_id" in work.columns:
        work["batter_name"] = work["batter_id"]
    work = infer_results_from_batter_change(work)
    work["pitch_type"] = _text(work, "pitch_type").replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaN": pd.NA})
    work["pitch_call"] = _text(work, "pitch_call")
    work["KorBB"] = _text(work, "KorBB")
    work["play_result"] = _text(work, "play_result")
    work["batter_side"] = _text(work, "batter_side")
    work["strike_flag"] = _flag(work, "strike")
    work["swing_flag"] = _flag(work, "swing")
    work["whiff_flag"] = _flag(work, "whiff")
    for column in (
        "velocity",
        "spin_rate",
        "ivb",
        "hb",
        "extension",
        "release_height",
        "release_side",
        "plate_x",
        "plate_z",
        "exit_velocity",
        "launch_angle",
        "vaa",
        "balls",
        "strikes",
        "outs_on_play",
        "inning",
    ):
        work[column] = _num(work, column)
    work["movement"] = np.sqrt(work["ivb"] ** 2 + work["hb"] ** 2)
    in_zone, in_heart, in_shadow = _location_masks(work)
    work["in_zone"] = in_zone.fillna(False)
    work["in_heart"] = in_heart.fillna(False)
    work["in_shadow"] = in_shadow.fillna(False)
    return work


def _call(work: pd.DataFrame) -> pd.Series:
    return work["pitch_call"].str.lower()


def _result(work: pd.DataFrame) -> pd.Series:
    return work["play_result"].str.lower()


def _korbb(work: pd.DataFrame) -> pd.Series:
    return work["KorBB"].str.lower()


def pa_end_mask(work: pd.DataFrame) -> pd.Series:
    """True on the pitch that ends a plate appearance."""
    call = _call(work)
    result = _result(work)
    korbb = _korbb(work)
    return (
        korbb.str.contains("strikeout|walk", regex=True)
        | call.str.contains("hitbypitch|hit by pitch|inplay", regex=True)
        | result.str.contains(r"single|double|triple|home|out|walk|hitbypitch", regex=True)
    )


def _event_weight(row) -> float:
    call = str(row["pitch_call"]).lower()
    result = str(row["play_result"]).lower()
    korbb = str(row["KorBB"]).lower()
    if "walk" in korbb or result == "walk":
        return W_BB
    if "hitbypitch" in call or "hit by pitch" in call or "hitbypitch" in result:
        return W_HBP
    if "home" in result:
        return W_HR
    if "triple" in result:
        return W_3B
    if "double" in result:
        return W_2B
    if "single" in result:
        return W_1B
    return 0.0


def contact_xwoba(exit_velocity: float, launch_angle: float) -> float:
    """
    Expected wOBA on contact.

    Barrels follow the public Statcast window: at 98 mph the launch-angle
    band is 26–30 degrees, widening to 8–50 degrees at 116 mph. Other
    batted balls use typical weights for weak, topped, line-drive, fly-ball,
    and popup contact.
    """
    if pd.isna(exit_velocity) or pd.isna(launch_angle):
        return np.nan
    ev = float(exit_velocity)
    la = float(launch_angle)
    if ev >= 98:
        span = min(ev, 116) - 98
        low = 26 - span
        high = 30 + span * (20 / 18)
        if ev >= 116:
            low, high = 8, 50
        if low <= la <= high:
            return float(np.clip(1.15 + (min(ev, 116) - 98) * 0.03, 1.15, 1.70))
    if ev < 70:
        return 0.08
    if la < 8:
        return 0.40 if ev >= 95 else 0.18
    if la <= 20:
        if ev < 85:
            return 0.30
        return 0.85 if ev >= 95 else 0.55
    if la <= 32:
        if ev < 85:
            return 0.15
        return 0.90 if ev >= 95 else 0.45
    if la <= 45:
        return 0.40 if ev >= 90 else 0.10
    return 0.05


def _xwoba_event(row) -> float:
    call = str(row["pitch_call"]).lower()
    result = str(row["play_result"]).lower()
    korbb = str(row["KorBB"]).lower()
    if "walk" in korbb or result == "walk":
        return W_BB
    if "hitbypitch" in call or "hit by pitch" in call or "hitbypitch" in result:
        return W_HBP
    if "strikeout" in korbb:
        return 0.0
    if "inplay" in call or any(token in result for token in ("single", "double", "triple", "home", "out")):
        expected = contact_xwoba(row["exit_velocity"], row["launch_angle"])
        if pd.notna(expected):
            return expected
        return _event_weight(row)
    return _event_weight(row)


def plate_appearances(work: pd.DataFrame) -> pd.DataFrame:
    if work.empty:
        return work.iloc[0:0].copy()
    ends = work.loc[pa_end_mask(work)].copy()
    if ends.empty:
        return ends
    ends["woba_weight"] = ends.apply(_event_weight, axis=1)
    ends["xwoba_weight"] = ends.apply(_xwoba_event, axis=1)
    return ends


def rate(numerator: float, denominator: float) -> float:
    if denominator is None or denominator == 0 or pd.isna(denominator):
        return np.nan
    return float(numerator) / float(denominator)


def pct(numerator: float, denominator: float) -> float:
    value = rate(numerator, denominator)
    if pd.isna(value):
        return np.nan
    return 100.0 * value


def strike_pct(work: pd.DataFrame) -> float:
    return pct(int(work["strike_flag"].sum()), len(work))


def whiff_pct(work: pd.DataFrame) -> float:
    swings = int(work["swing_flag"].sum())
    return pct(int(work["whiff_flag"].sum()), swings)


def zone_pct(work: pd.DataFrame) -> float:
    located = work["plate_x"].notna() & work["plate_z"].notna()
    return pct(int(work.loc[located, "in_zone"].sum()), int(located.sum()))


def heart_pct(work: pd.DataFrame) -> float:
    located = work["plate_x"].notna() & work["plate_z"].notna()
    return pct(int(work.loc[located, "in_heart"].sum()), int(located.sum()))


def _pitch_family(pitch: str) -> str:
    key = pitch.lower().replace("-", "").replace(" ", "")
    if any(token in key for token in ("change", "split")):
        return "change"
    if any(token in key for token in ("slider", "curve", "sweeper", "slurve", "cutter")):
        return "break"
    if any(token in key for token in ("fast", "sink", "seam")):
        return "fast"
    return "other"


def build_whiff_spots(team: pd.DataFrame) -> dict:
    """
    Usual out-of-zone swing-and-miss location for each pitch type.

    Each spot is the mean plate location of this group's whiffs outside the
    zone, with the spread capped so the pocket stays a real chase spot.
    """
    work = team if "whiff_flag" in team.columns else prepare_pitches(team)
    whiffs = work[work["whiff_flag"] & ~work["in_zone"] & work["plate_x"].notna() & work["plate_z"].notna()]
    spots = {}
    for pitch, group in whiffs.groupby(whiffs["pitch_type"].map(_pitch_key)):
        if not pitch or len(group) < 8:
            continue
        spots[pitch] = (
            float(group["plate_x"].mean()),
            float(group["plate_z"].mean()),
            float(np.clip(group["plate_x"].std(ddof=0), 4, 8)),
            float(np.clip(group["plate_z"].std(ddof=0), 4, 8)),
        )
    return spots


def _family_pocket(pitch: str, plate_x: pd.Series, plate_z: pd.Series, arm_sign: float) -> pd.Series:
    """Chase pocket used when this pitch type does not have enough whiffs yet."""
    family = _pitch_family(pitch)
    if family == "fast":
        return (plate_z > 42) & (plate_z <= 50) & (plate_x.abs() <= 12)
    down = (plate_z >= 10) & (plate_z < 18)
    if family == "change":
        arm = arm_sign * plate_x
        return down & (arm >= -4) & (arm <= 14)
    if family == "break":
        glove = -arm_sign * plate_x
        return down & (glove >= -4) & (glove <= 14)
    return pd.Series(False, index=plate_x.index)


def typical_whiff_mask(work: pd.DataFrame, throws: str, spots: dict | None) -> pd.Series:
    """True when the pitch sits where that pitch type usually gets a swing and miss."""
    spots = spots or {}
    plate_x = work["plate_x"]
    plate_z = work["plate_z"]
    mask = pd.Series(False, index=work.index)
    arm_sign = -1.0 if str(throws).upper().startswith("L") else 1.0
    keys = work["pitch_type"].map(_pitch_key)
    for pitch, indexes in work.groupby(keys).groups.items():
        if not pitch:
            continue
        chosen = list(indexes)
        if pitch in spots:
            mean_x, mean_z, scale_x, scale_z = spots[pitch]
            distance = ((plate_x.loc[chosen] - mean_x) / scale_x) ** 2 + ((plate_z.loc[chosen] - mean_z) / scale_z) ** 2
            mask.loc[chosen] = distance <= 2.25
        else:
            mask.loc[chosen] = _family_pocket(pitch, plate_x.loc[chosen], plate_z.loc[chosen], arm_sign).to_numpy()
    return mask.fillna(False) & plate_x.notna() & plate_z.notna()


def competitive_mask(work: pd.DataFrame, throws: str, spots: dict | None) -> pd.Series:
    """
    In the zone, a swing and miss, or a pitch in that pitch type's usual
    swing-and-miss location.
    """
    return work["in_zone"].fillna(False) | work["whiff_flag"].fillna(False) | typical_whiff_mask(work, throws, spots)


def competitive_pct(work: pd.DataFrame, throws: str = "", spots: dict | None = None) -> float:
    """Share of located pitches in the zone, a swing and miss, or a usual whiff spot."""
    located = work["plate_x"].notna() & work["plate_z"].notna()
    if int(located.sum()) == 0:
        return np.nan
    mask = competitive_mask(work.loc[located], throws, spots)
    return pct(int(mask.fillna(False).sum()), int(located.sum()))


def shadow_pct(work: pd.DataFrame) -> float:
    located = work["plate_x"].notna() & work["plate_z"].notna()
    return pct(int(work.loc[located, "in_shadow"].sum()), int(located.sum()))


def csw_pct(work: pd.DataFrame) -> float:
    call = _call(work)
    called = call.str.contains("strikecalled")
    swinging = work["whiff_flag"]
    return pct(int((called | swinging).sum()), len(work))


def chase_pct(work: pd.DataFrame) -> float:
    outside = work["plate_x"].notna() & ~work["in_zone"]
    swings = int((outside & work["swing_flag"]).sum())
    return pct(swings, int(outside.sum()))


def hard_hit_pct(work: pd.DataFrame) -> float:
    bip = work["pitch_call"].str.lower().str.contains("inplay") & work["exit_velocity"].notna()
    if int(bip.sum()) == 0:
        return np.nan
    hard = bip & (work["exit_velocity"] >= 95)
    return pct(int(hard.sum()), int(bip.sum()))


def called_strike_whiff_mask(work: pd.DataFrame) -> pd.Series:
    return _call(work).str.contains("strikecalled") | work["whiff_flag"]


@dataclass
class PlusBaseline:
    stuff: dict
    location: dict


def _pitch_key(value) -> str:
    text = str(value).strip()
    if text.lower() in {"", "nan", "none"}:
        return ""
    return text


def build_baseline(team: pd.DataFrame) -> PlusBaseline:
    """
    100 is this group's average for that pitch type.

    Stuff uses each pitcher's average, then the average of those averages, so
    a pitcher with more pitches does not count more than once. A pitcher needs
    at least 8 pitches of that type to be included.
    """
    work = prepare_pitches(team) if "strike_flag" not in team.columns else team
    stuff: dict = {}
    location: dict = {}
    work = work.copy()
    work["movement"] = np.sqrt(work["ivb"] ** 2 + work["hb"] ** 2)
    work["loc_score"] = location_score(work["plate_x"], work["plate_z"])
    if "pitcher_id" in work.columns:
        work["pitcher_key"] = work["pitcher_id"].map(_pitch_key)
    else:
        work["pitcher_key"] = ""
    for pitch, group in work.groupby(work["pitch_type"].map(_pitch_key)):
        if not pitch or len(group) < 8:
            continue
        pitcher_means = []
        qualifying = []
        for pitcher, pitches in group.groupby("pitcher_key"):
            if not pitcher or len(pitches) < 8:
                continue
            means = {}
            complete = True
            for feature in STUFF_FEATURES:
                values = pd.to_numeric(pitches[feature], errors="coerce").dropna()
                if len(values) < 8:
                    complete = False
                    break
                means[feature] = float(values.mean())
            if not complete:
                continue
            pitcher_means.append(means)
            qualifying.append(pitches)
        if pitcher_means:
            stats = {}
            for feature in STUFF_FEATURES:
                averages = pd.Series([row[feature] for row in pitcher_means])
                if len(averages) >= 2:
                    scale = float(averages.std(ddof=0))
                else:
                    pooled = pd.to_numeric(pd.concat(qualifying)[feature], errors="coerce").dropna()
                    scale = float(pooled.std(ddof=0)) if len(pooled) else 0.0
                stats[feature] = (float(averages.mean()), scale)
            stuff[pitch] = stats
        scores = group["loc_score"].dropna()
        if len(scores) >= 8 and float(scores.mean()) > 0:
            location[pitch] = float(scores.mean())
    return PlusBaseline(stuff=stuff, location=location)


def location_score(plate_x: pd.Series, plate_z: pd.Series) -> pd.Series:
    """
    Shadow locations score highest, the heart scores lower, and pitches
    farther from the zone score down to zero.
    """
    px = pd.to_numeric(plate_x, errors="coerce")
    pz = pd.to_numeric(plate_z, errors="coerce")
    outside_x = np.maximum(np.abs(px) - 8.5, 0)
    outside_z = np.maximum(pz - 42.0, 0) + np.maximum(18.0 - pz, 0)
    outside = np.sqrt(outside_x ** 2 + outside_z ** 2)
    in_zone = outside <= 0
    in_heart = in_zone & px.between(-6, 6) & pz.between(24, 36)
    score = np.where(in_heart, 0.35, np.where(in_zone, 1.0, np.maximum(0, 1 - outside / 10.0) * 0.55))
    return pd.Series(score, index=plate_x.index).where(px.notna() & pz.notna())


def assign_plus(work: pd.DataFrame, baseline: PlusBaseline) -> pd.DataFrame:
    stuff_values = []
    loc_values = []
    scores = location_score(work["plate_x"], work["plate_z"])
    for idx, row in work.iterrows():
        pitch = _pitch_key(row.get("pitch_type"))
        feature_stats = baseline.stuff.get(pitch, {})
        zs = []
        for feature, (mean, std) in feature_stats.items():
            value = row.get(feature)
            if std and std > 1e-6 and pd.notna(value):
                zs.append((float(value) - mean) / std)
        stuff_values.append(100 + 10 * float(np.mean(zs)) if zs else np.nan)
        team_loc = baseline.location.get(pitch)
        loc = scores.get(idx, np.nan)
        if team_loc and pd.notna(loc):
            loc_values.append(100.0 * float(loc) / team_loc)
        else:
            loc_values.append(np.nan)
    work = work.copy()
    work["stuff_plus"] = stuff_values
    work["location_plus"] = loc_values
    return work


def _plus_score(plus: float) -> float:
    """100 on the plus scale scores 80. Each point above or below moves the score by 2."""
    if pd.isna(plus):
        return np.nan
    return float(np.clip(80 + (float(plus) - 100) * 2, 0, 100))


def mean_plus(work: pd.DataFrame, column: str, pitch: str | None = None) -> float:
    group = work if pitch is None else work[work["pitch_type"].map(_pitch_key) == pitch]
    values = pd.to_numeric(group[column], errors="coerce").dropna()
    if values.empty:
        return np.nan
    return float(values.mean())


def _scale_high(value: float, low: float, high: float) -> float:
    if pd.isna(value):
        return np.nan
    return float(np.clip((value - low) / (high - low) * 100.0, 0, 100))


def _scale_low(value: float, good: float, bad: float) -> float:
    if pd.isna(value):
        return np.nan
    return float(np.clip((bad - value) / (bad - good) * 100.0, 0, 100))


def letter_grade(score: float) -> str:
    if pd.isna(score):
        return "—"
    cuts = (
        (97, "A+"),
        (93, "A"),
        (90, "A-"),
        (87, "B+"),
        (83, "B"),
        (80, "B-"),
        (77, "C+"),
        (73, "C"),
        (70, "C-"),
        (67, "D+"),
        (63, "D"),
        (60, "D-"),
    )
    for threshold, label in cuts:
        if score >= threshold:
            return label
    return "F"


def _average(values: list[float]) -> float:
    usable = [value for value in values if pd.notna(value)]
    if not usable:
        return np.nan
    return float(np.mean(usable))


def two_strike(work: pd.DataFrame) -> pd.DataFrame:
    """Pitches thrown with two strikes, plus any swinging or called strikeout.

    A strikeout is a two-strike pitch even when the count column is short.
    """
    strikes = pd.to_numeric(work["strikes"], errors="coerce")
    korbb = work["KorBB"].astype(str).str.lower() if "KorBB" in work.columns else pd.Series("", index=work.index)
    return work[(strikes >= 2) | korbb.str.contains("strikeout", na=False)]


def putaway_pct(work: pd.DataFrame) -> float:
    """Share of two-strike plate appearances that end in a strikeout or an out."""
    ends = plate_appearances(two_strike(work))
    if ends.empty:
        return np.nan
    korbb = ends["KorBB"].str.lower()
    result = ends["play_result"].str.lower()
    putaway = korbb.str.contains("strikeout") | result.eq("out")
    return pct(int(putaway.sum()), len(ends))


def finish_grade(work: pd.DataFrame) -> dict:
    """
    Separate from the outing grade. Two-strike whiff rate scores 0 at 10% and
    100 at 40%. Put-away rate scores 0 at 30% and 100 at 80%. The finish
    letter is the average of those two scores.
    """
    late = two_strike(work)
    whiff = whiff_pct(late) if len(late) else np.nan
    putaway = putaway_pct(work)
    if len(late) < 3:
        score = np.nan
    else:
        score = _average([_scale_high(whiff, 10, 40), _scale_high(putaway, 30, 80)])
    return {
        "finish_score": score,
        "finish_letter": letter_grade(score),
        "finish_whiff": whiff,
        "finish_putaway": putaway,
        "finish_pitches": int(len(late)),
    }


# Standard deviations that score 100. A 3.6-inch standard deviation scores 0.
RELEASE_GOOD_INCHES = {
    "release_height": 1.2,
    "release_side": 1.4,
    "extension": 1.8,
}
RELEASE_POOR_INCHES = 3.6


def _spread(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if len(values) < 3:
        return np.nan
    return float(values.std(ddof=0))


def _weighted(parts: list[tuple[float, float]]) -> float:
    weighted = []
    weights = []
    for score, weight in parts:
        if pd.notna(score):
            weighted.append(score * weight)
            weights.append(weight)
    if not weights:
        return np.nan
    return float(sum(weighted) / sum(weights))


def runs_allowed(work: pd.DataFrame) -> float:
    """Runs scored on the pitches in this outing."""
    if "runs_scored" not in work.columns:
        return np.nan
    values = pd.to_numeric(work["runs_scored"], errors="coerce")
    if values.notna().sum() == 0:
        return np.nan
    return float(values.fillna(0).sum())


def innings_pitched(work: pd.DataFrame) -> float:
    """
    Outs recorded divided by 3.

    Within each inning, outs are read from the change in the outs column.
    A final strikeout or in-play out counts even when outs_on_play was not filled in.
    """
    if "inning" in work.columns and work["inning"].notna().any() and "outs" in work.columns:
        ordered = work.sort_values("pitch_number") if "pitch_number" in work.columns else work
        total_outs = 0.0
        found = False
        for _, group in ordered.dropna(subset=["inning"]).groupby("inning", sort=False):
            outs = pd.to_numeric(group["outs"], errors="coerce").tolist()
            gained = 0.0
            previous = None
            for value in outs:
                if pd.isna(value):
                    continue
                if previous is not None and value > previous:
                    gained += float(value - previous)
                previous = value
            last = group.iloc[-1]
            korbb = str(last.get("KorBB", "")).lower()
            result = str(last.get("play_result", "")).lower()
            call = str(last.get("pitch_call", "")).lower()
            on_play = pd.to_numeric(last.get("outs_on_play"), errors="coerce")
            terminal_out = "strikeout" in korbb or result == "out"
            if pd.notna(on_play) and on_play > 0:
                gained += float(on_play)
                found = True
            elif terminal_out or ("inplay" in call and result == "out"):
                gained += 1
                found = True
            elif gained > 0:
                found = True
            total_outs += gained
        if found and total_outs > 0:
            return total_outs / 3.0
    if "outs_on_play" not in work.columns:
        return np.nan
    recorded = pd.to_numeric(work["outs_on_play"], errors="coerce").sum(min_count=1)
    if pd.isna(recorded):
        return np.nan
    return float(recorded) / 3.0


def _far_miss_count(work: pd.DataFrame) -> int:
    """Pitches whose location is 18 inches or more past the edge of the plate."""
    if "plate_x" not in work.columns:
        return 0
    plate_x = pd.to_numeric(work["plate_x"], errors="coerce")
    return int(((plate_x.abs() - 8.5) >= 18).sum())


def bullpen_grade(work: pd.DataFrame, throws: str = "", whiff_spots: dict | None = None) -> dict:
    """
    65% stuff, 25% control, 10% release.

    Control counts a pitch in the zone, a swing and miss, or a pitch in that
    pitch type's usual swing-and-miss location. More shadow and less heart
    score higher. Stuff+ of 100 scores 80. Release scores the standard
    deviation of height, side, and extension. Height scores 100 at 1.2 inches,
    side at 1.4 inches, and extension at 1.8 inches. Each scores 0 at 3.6 inches.
    """
    competitive = competitive_pct(work, throws, whiff_spots)
    control = _average(
        [
            _scale_high(competitive, 40, 70),
            _scale_high(shadow_pct(work), 15, 45),
            _scale_low(heart_pct(work), 8, 35),
        ]
    )
    stuff = mean_plus(work, "stuff_plus") if "stuff_plus" in work.columns else np.nan
    stuff_score = _plus_score(stuff)
    poor_ft = RELEASE_POOR_INCHES / 12.0
    release = _average(
        [
            _scale_low(_spread(work[column]), RELEASE_GOOD_INCHES[column] / 12.0, poor_ft)
            for column in ("release_height", "release_side", "extension")
        ]
    )
    overall = _weighted([(stuff_score, 0.65), (control, 0.25), (release, 0.10)])
    misses = _far_miss_count(work)
    if pd.notna(overall):
        overall = float(np.clip(overall - 1.25 * misses, 0, 100))
    return {
        "outing_score": overall,
        "outing_letter": letter_grade(overall),
        "finish_score": np.nan,
        "finish_letter": "—",
        "control_score": control,
        "competitive_pct": competitive,
        "stuff_score": stuff_score,
        "release_score": release,
        "far_misses": misses,
    }


def _contact_flags(row) -> tuple[str, bool, bool, bool]:
    """Return batted-ball type, hard, weak, and deep-fly flags."""
    hit = str(row.get("hit_type", "")).lower()
    if hit in {"", "nan", "none"}:
        hit = str(row.get("tagged_hit_type", "")).lower()
    ev = pd.to_numeric(row.get("exit_velocity"), errors="coerce")
    launch = pd.to_numeric(row.get("launch_angle"), errors="coerce")
    distance = pd.to_numeric(row.get("distance"), errors="coerce")
    hard = pd.notna(ev) and ev >= 95
    weak = pd.notna(ev) and ev < 80
    if "ground" in hit or (pd.notna(launch) and launch < 10):
        kind = "ground"
    elif "line" in hit or (pd.notna(launch) and launch < 25):
        kind = "line"
    elif "pop" in hit or (pd.notna(launch) and launch >= 50):
        kind = "popup"
    elif "fly" in hit or (pd.notna(launch) and launch >= 25):
        kind = "fly"
    else:
        kind = "unknown"
    deep = kind == "fly" and (
        (pd.notna(distance) and distance >= 300)
        or (pd.notna(ev) and ev >= 90 and pd.notna(launch) and 25 <= launch <= 45)
    )
    return kind, bool(hard), bool(weak), bool(deep)


def _pa_result_score(row) -> float:
    """
    100 is the best result for the pitcher. Strikeouts and weak outs score
    high. Hard line drives, extra-base hits, and home runs score low.
    """
    korbb = str(row.get("KorBB", "")).lower()
    result = str(row.get("play_result", "")).lower()
    call = str(row.get("pitch_call", "")).lower()
    if "strikeout" in korbb:
        return 100.0
    if "walk" in korbb or result == "walk":
        return 40.0
    if "hitbypitch" in call or "hit by pitch" in call:
        return 38.0
    if "home" in result:
        return 0.0
    if "triple" in result:
        return 6.0
    kind, hard, weak, deep = _contact_flags(row)
    if "double" in result:
        return 8.0 if hard else 16.0
    if "single" in result:
        if weak:
            return 50.0
        return 24.0 if hard else 34.0
    if result == "out" or "inplay" in call:
        if kind == "popup" or (kind == "ground" and weak):
            return 94.0
        if weak:
            return 88.0
        if kind == "line" and hard:
            return 36.0
        if deep and hard:
            return 48.0
        if deep:
            return 62.0
        if hard and kind == "ground":
            return 58.0
        if hard:
            return 52.0
        if kind == "ground":
            return 82.0
        if kind == "fly":
            return 74.0
        return 70.0
    return np.nan


def _other_results_score(work: pd.DataFrame) -> float:
    """Average result score. Weak contact and strikeouts raise it. Hard contact and hits lower it."""
    appearances = plate_appearances(work)
    if appearances.empty:
        return np.nan
    scores = appearances.apply(_pa_result_score, axis=1).dropna()
    if scores.empty:
        return np.nan
    return float(scores.mean())


def _entry_inning(work: pd.DataFrame) -> float:
    if "inning" not in work.columns:
        return np.nan
    innings = pd.to_numeric(work["inning"], errors="coerce").dropna()
    if innings.empty:
        return np.nan
    return float(innings.min())


def _run_rate_letter(runs: float, innings: float, reliever: bool = False) -> str:
    """
    A is one run every 3 innings, B every 2.5, C every 1.5.
    A reliever who enters after the first inning gets a C at one run per inning.
    An F is worse than one run every two-thirds of an inning. The band
    between C and that is a D.
    """
    if pd.isna(runs) or pd.isna(innings) or innings <= 0:
        return ""
    if runs <= 0:
        return "A"
    rate = runs / innings
    if rate <= 1 / 3:
        return "A"
    if rate <= 1 / 2.5:
        return "B"
    c_line = 1.0 if reliever else 1 / 1.5
    if rate <= c_line:
        return "C"
    if rate <= 1.5:
        return "D"
    return "F"


_LETTER_LADDER = ("F", "D", "C", "B", "A")
IN_SEASON_START = date(2026, 2, 13)
FALL_START = date(2026, 9, 1)


def _shift_letter(base: str, steps: int) -> str:
    if base not in _LETTER_LADDER or steps == 0:
        return base
    index = _LETTER_LADDER.index(base) + steps
    index = max(0, min(len(_LETTER_LADDER) - 1, index))
    return _LETTER_LADDER[index]


def _started_game(work: pd.DataFrame) -> bool:
    """True when this outing includes the first inning."""
    entry = _entry_inning(work)
    return pd.notna(entry) and entry <= 1


def _entered_later(work: pd.DataFrame) -> bool:
    """True when the pitcher comes in after the first inning."""
    entry = _entry_inning(work)
    return pd.notna(entry) and entry > 1


def _in_season_game(work: pd.DataFrame) -> bool:
    """True for games from 2026-02-13 through 2026-08-31."""
    if "date" not in work.columns:
        return False
    parsed = pd.to_datetime(work["date"], errors="coerce").dropna()
    if parsed.empty:
        return False
    outing = parsed.min().date()
    return IN_SEASON_START <= outing < FALL_START


def _starter_length_letter(base: str, innings: float, runs: float, started: bool, penalize_short: bool) -> tuple[str, str]:
    """
    In-season starters drop a letter under 5 innings and rise one over 6.
    Fall starts are not dropped, because pitch limits set the length.
    One inning with fewer than 3 runs is an opener and is not dropped.
    """
    if not base or not started or pd.isna(innings):
        return base, ""
    if innings <= 1 and penalize_short and (pd.isna(runs) or runs < 3):
        return base, "opener"
    if innings < 5:
        if not penalize_short:
            return base, ""
        return _shift_letter(base, -1), "short"
    if innings > 6:
        return _shift_letter(base, 1), "deep"
    return base, ""


def _play_kind(row) -> str:
    korbb = str(row.get("KorBB", "")).lower()
    result = str(row.get("play_result", "")).lower()
    call = str(row.get("pitch_call", "")).lower()
    if "strikeout" in korbb:
        return "strikeout"
    if "walk" in korbb or result == "walk":
        return "walk"
    if "hitbypitch" in call or "hit by pitch" in call or "hitbypitch" in result:
        return "hitbypitch"
    if "home" in result:
        return "homer"
    if "triple" in result:
        return "triple"
    if "double" in result:
        return "double"
    if "single" in result:
        return "single"
    if "error" in result:
        return "error"
    if result == "out":
        return "out"
    return ""


def _score_lead_runners(bases: list, count: int) -> int:
    """Remove the closest runners and return how many inherited runners scored."""
    inherited = 0
    scored = 0
    for spot in (2, 1, 0):
        if scored >= count:
            break
        runner = bases[spot]
        if runner is None:
            continue
        if runner.get("inherited"):
            inherited += 1
        bases[spot] = None
        scored += 1
    return inherited


def _apply_base_play(bases: list, kind: str, outs_added: int, runs: int) -> int:
    """Update the bases and return how many inherited runners scored."""
    inherited = 0
    batter = {"inherited": False}
    if kind in {"single", "error"}:
        if bases[2] is not None and bases[2].get("inherited"):
            inherited += 1
        bases[2] = bases[1]
        bases[1] = bases[0]
        bases[0] = batter
    elif kind == "double":
        inherited += _score_lead_runners(bases, 2)
        bases[2] = bases[0]
        bases[1] = batter
        bases[0] = None
    elif kind == "triple":
        inherited += _score_lead_runners(bases, 3)
        bases[2] = batter
    elif kind == "homer":
        inherited += _score_lead_runners(bases, 3)
    elif kind in {"walk", "hitbypitch"}:
        if all(base is not None for base in bases):
            inherited += _score_lead_runners(bases, 1)
        if bases[0] is not None and bases[1] is not None:
            bases[2] = bases[1]
            bases[1] = bases[0]
        elif bases[0] is not None:
            bases[1] = bases[0]
        bases[0] = batter
    elif kind == "out":
        if runs > 0:
            inherited += _score_lead_runners(bases, int(runs))
        if outs_added >= 2 and bases[0] is not None:
            bases[0] = None
    elif kind == "strikeout" and runs > 0:
        inherited += _score_lead_runners(bases, int(runs))
    return inherited


def _lineup_spots(game: pd.DataFrame, side: str) -> dict:
    """Batting-order spot for each hitter, taken from the first inning of that half."""
    half = game
    if side and "top_bottom" in game.columns:
        half = game[game["top_bottom"].astype(str).str.lower() == side]
    if half.empty or "inning" not in half.columns or "batter_id" not in half.columns:
        return {}
    innings = pd.to_numeric(half["inning"], errors="coerce")
    ordered = half.assign(_inning=innings, _pitch=pd.to_numeric(half["pitch_number"], errors="coerce"))
    ordered = ordered.sort_values(["_inning", "_pitch"])
    order = []
    for batter in ordered["batter_id"].astype(str):
        if batter.lower() in {"", "nan", "none"}:
            continue
        if batter not in order:
            order.append(batter)
        if len(order) == 9:
            break
    return {batter: index + 1 for index, batter in enumerate(order)}


def _lineup_weight(spot: int | None) -> float:
    """Heart of the order is the full weight. The 9-hole is the minimum."""
    if spot in {3, 4, 5}:
        return 1.0
    if spot in {2, 6}:
        return 0.8
    if spot in {1, 7}:
        return 0.6
    if spot == 8:
        return 0.4
    if spot == 9:
        return 0.25
    return 0.6


def _base_phrase(runners: list[str]) -> str:
    if not runners:
        return ""
    if len(runners) == 1:
        return runners[0]
    if len(runners) == 2:
        return f"{runners[0]} and {runners[1]}"
    return "first, second, and third"


def _inherited_runner_bonus(work: pd.DataFrame, game: pd.DataFrame | None) -> dict:
    """
    Relievers who enter with runners on and strand them get a bonus.

    Bases loaded with one out is the top of the scale. A runner on first with
    two outs is the bottom. The heart of the order raises it, and the 9-hole
    lowers it. Any inherited runner who scores removes the bonus.
    """
    empty = {
        "inherited_bonus": 0.0,
        "inherited_runners": 0,
        "inherited_bases": "",
        "inherited_outs": None,
        "inherited_spot": None,
        "inherited_scored": False,
    }
    if game is None or game.empty or "pitch_number" not in work.columns:
        return empty
    numbers = pd.to_numeric(work["pitch_number"], errors="coerce")
    entry_number = numbers.min()
    last_pitch = numbers.max()
    if pd.isna(entry_number):
        return empty
    ordered = game.copy()
    ordered["_pitch_number"] = pd.to_numeric(ordered["pitch_number"], errors="coerce")
    ordered = ordered.dropna(subset=["_pitch_number"]).sort_values("_pitch_number")
    entry_rows = ordered[ordered["_pitch_number"] == entry_number]
    if entry_rows.empty:
        return empty
    side = str(entry_rows.iloc[0].get("top_bottom", "")).lower()
    bases = [None, None, None]
    outs = 0
    inning = None
    entry_bases = None
    entry_outs = None
    entry_batter = None
    inherited_scored = 0
    tracking = False
    for _, row in ordered.iterrows():
        if side and "top_bottom" in ordered.columns and str(row.get("top_bottom", "")).lower() != side:
            continue
        this_inning = pd.to_numeric(row.get("inning"), errors="coerce")
        if pd.notna(this_inning) and this_inning != inning:
            bases = [None, None, None]
            outs = 0
            inning = this_inning
        if not tracking and row["_pitch_number"] == entry_number:
            tracking = True
            entry_bases = [dict(runner) if runner else None for runner in bases]
            for runner in entry_bases:
                if runner is not None:
                    runner["inherited"] = True
            bases = [dict(runner) if runner else None for runner in entry_bases]
            entry_outs = pd.to_numeric(row.get("outs"), errors="coerce")
            entry_batter = str(row.get("batter_id", ""))
        kind = _play_kind(row)
        runs = pd.to_numeric(row.get("runs_scored"), errors="coerce")
        runs = 0 if pd.isna(runs) else int(runs)
        added = pd.to_numeric(row.get("outs_on_play"), errors="coerce")
        added = 1 if pd.isna(added) or added <= 0 else int(added)
        if not kind:
            if tracking and runs > 0:
                inherited_scored += _score_lead_runners(bases, runs)
            continue
        if kind in {"strikeout", "out"}:
            outs += added
        inherited_scored += _apply_base_play(bases, kind, added, runs)
        if outs >= 3:
            bases = [None, None, None]
            outs = 0
        if tracking and row["_pitch_number"] >= last_pitch:
            break
    runners = [label for label, runner in zip(("first", "second", "third"), entry_bases or []) if runner is not None]
    outs_now = None if entry_outs is None or pd.isna(entry_outs) else int(entry_outs)
    spots = _lineup_spots(ordered, side)
    spot = spots.get(entry_batter or "")
    bonus = 0.0
    if runners and inherited_scored == 0:
        outs_for_scale = 0 if outs_now is None else outs_now
        base_weight = sum(weight for label, weight in (("first", 1), ("second", 2), ("third", 3)) if label in runners)
        out_mult = {0: 1.0, 1: 0.9, 2: 0.4}.get(min(outs_for_scale, 2), 0.4)
        # Bases loaded with one out is the top. A runner on first with two outs is the bottom.
        ceiling = 6 * 0.9
        normal = float(np.clip((base_weight * out_mult - 0.4) / (ceiling - 0.4), 0, 1))
        bonus = (2.0 + 8.0 * normal) * _lineup_weight(spot)
    return {
        "inherited_bonus": float(bonus),
        "inherited_runners": len(runners),
        "inherited_bases": _base_phrase(runners),
        "inherited_outs": outs_now,
        "inherited_spot": spot,
        "inherited_scored": inherited_scored > 0,
    }


def _pa_slices(work: pd.DataFrame) -> list[pd.DataFrame]:
    if work.empty:
        return []
    if "pa_of_inning" in work.columns and pd.to_numeric(work["pa_of_inning"], errors="coerce").notna().any():
        keys = [column for column in ("inning", "top_bottom", "pa_of_inning", "batter_id") if column in work.columns]
        return [group for _, group in work.groupby(keys, sort=False)]
    slices = []
    current = []
    for index, ended in pa_end_mask(work).items():
        current.append(index)
        if ended:
            slices.append(work.loc[current])
            current = []
    if current:
        slices.append(work.loc[current])
    return slices


def _reached_base(row) -> bool:
    return _play_kind(row) in {"walk", "hitbypitch", "single", "double", "triple", "homer", "error"}


def _is_out(row) -> bool:
    return _play_kind(row) in {"strikeout", "out"}


def situation_adjustment(work: pd.DataFrame, game: pd.DataFrame | None = None, reliever: bool = False) -> dict:
    """
    Points added to the results score.

    Relievers can earn a bonus for stranding inherited runners. Every pitcher
    loses a little for pitches 18 inches or more off the plate, and more when
    a runner scores on that miss. At-bats of 6 or more pitches lower the score,
    and more if the hitter reaches. Outs in 3 pitches or fewer raise it.
    """
    if reliever:
        inherited = _inherited_runner_bonus(work, game)
    else:
        inherited = {
            "inherited_bonus": 0.0,
            "inherited_runners": 0,
            "inherited_bases": "",
            "inherited_outs": None,
            "inherited_spot": None,
            "inherited_scored": False,
        }
    far_misses = _far_miss_count(work)
    far_miss_runs = 0
    if far_misses and "plate_x" in work.columns:
        plate_x = pd.to_numeric(work["plate_x"], errors="coerce")
        misses = work[(plate_x.abs() - 8.5) >= 18]
        if "runs_scored" in misses.columns:
            for _, row in misses.iterrows():
                runs = pd.to_numeric(row.get("runs_scored"), errors="coerce")
                if pd.notna(runs) and runs > 0 and _play_kind(row) not in {"single", "double", "triple", "homer", "walk", "hitbypitch"}:
                    far_miss_runs += int(runs)
    long_pas = 0
    long_reached = 0
    short_outs = 0
    for appearance in _pa_slices(work):
        last = appearance.iloc[-1]
        if len(appearance) >= 6:
            long_pas += 1
            if _reached_base(last):
                long_reached += 1
        elif len(appearance) <= 3 and _is_out(last):
            short_outs += 1
    delta = float(inherited["inherited_bonus"])
    delta -= 1.25 * far_misses
    delta -= 4.0 * far_miss_runs
    delta -= 3.0 * long_pas
    delta -= 3.0 * long_reached
    delta += 2.0 * short_outs
    return {
        **inherited,
        "far_misses": far_misses,
        "far_miss_runs": far_miss_runs,
        "long_pas": long_pas,
        "long_reached": long_reached,
        "short_outs": short_outs,
        "score_delta": delta,
    }


def _apply_letter_modifier(base: str, other: float) -> str:
    """Other results can add a plus or a minus. An F stays an F."""
    if base == "F" or pd.isna(other):
        return base
    if other >= 65:
        step = "+"
    elif other <= 35:
        step = "-"
    else:
        return base
    return f"{base}{step}"


def game_grade(work: pd.DataFrame, intrasquad: bool = False, game: pd.DataFrame | None = None) -> dict:
    """
    The letter comes from runs per inning. Other results only add + or -.

    A pitcher who starts an in-season game drops one letter under 5 innings
    and gains one over 6. A fall start is not dropped for finishing under 5.
    One inning with fewer than 3 runs is an opener and is not dropped. With
    no run total, the letter is the results score itself, so the outing can
    be an A or an F. An intrasquad with no run total also uses Stuff+ and
    Location+.
    """
    runs = runs_allowed(work)
    innings = innings_pitched(work)
    other = _other_results_score(work)
    reliever = _entered_later(work)
    situation = situation_adjustment(work, game, reliever=reliever)
    adjusted = other
    if pd.notna(other):
        adjusted = float(np.clip(other + situation["score_delta"], 0, 100))
    stuff = mean_plus(work, "stuff_plus") if "stuff_plus" in work.columns else np.nan
    location = mean_plus(work, "location_plus") if "location_plus" in work.columns else np.nan
    base = _run_rate_letter(runs, innings, reliever=reliever)
    adjust = ""
    if not base and intrasquad:
        blended = _average([adjusted, _plus_score(stuff), _plus_score(location)])
        letter = letter_grade(blended)
    elif not base:
        letter = letter_grade(adjusted)
    else:
        shifted, adjust = _starter_length_letter(
            base, innings, runs, _started_game(work), _in_season_game(work)
        )
        if adjust == "deep" and base == "A" and shifted == "A":
            letter = "A" if pd.notna(adjusted) and adjusted <= 35 else "A+"
        else:
            letter = _apply_letter_modifier(shifted, adjusted)
    return {
        "outing_score": other,
        "outing_letter": letter,
        "run_letter": base,
        "reliever": reliever,
        "length_adjust": adjust,
        **situation,
        "intrasquad": intrasquad and not base,
        "stuff_plus": stuff,
        "location_plus": location,
        **finish_grade(work),
        "runs_score": runs,
        "innings_score": innings,
        "other_score": other,
        "runs_allowed": runs,
        "innings_pitched": innings,
    }


def grade_block(
    work: pd.DataFrame,
    kind: str,
    throws: str = "",
    whiff_spots: dict | None = None,
    intrasquad: bool = False,
    game: pd.DataFrame | None = None,
) -> dict:
    if kind == "bullpen":
        return bullpen_grade(work, throws, whiff_spots)
    return game_grade(work, intrasquad=intrasquad, game=game)


def woba_value(work: pd.DataFrame) -> float:
    pas = plate_appearances(work)
    if pas.empty:
        return np.nan
    return float(pas["woba_weight"].mean())


def xwoba_value(work: pd.DataFrame) -> float:
    pas = plate_appearances(work)
    if pas.empty:
        return np.nan
    return float(pas["xwoba_weight"].mean())


def result_counts(work: pd.DataFrame) -> dict:
    pas = plate_appearances(work)
    result = pas["play_result"].str.lower() if len(pas) else pd.Series(dtype=str)
    korbb = pas["KorBB"].str.lower() if len(pas) else pd.Series(dtype=str)
    call = pas["pitch_call"].str.lower() if len(pas) else pd.Series(dtype=str)
    singles = int(result.str.contains("single").sum()) if len(pas) else 0
    doubles = int(result.str.contains("double").sum()) if len(pas) else 0
    triples = int(result.str.contains("triple").sum()) if len(pas) else 0
    homers = int(result.str.contains("home").sum()) if len(pas) else 0
    walks = int(korbb.str.contains("walk").sum()) if len(pas) else 0
    strikeouts = int(korbb.str.contains("strikeout").sum()) if len(pas) else 0
    hbp = int(call.str.contains("hitbypitch|hit by pitch").sum()) if len(pas) else 0
    hits = singles + doubles + triples + homers
    outs_recorded = innings_pitched(work)
    hard = pas[pas["exit_velocity"] >= 95] if len(pas) and "exit_velocity" in pas.columns else pas.iloc[0:0]
    hard_hits = 0
    hard_outs = 0
    if len(hard):
        hard_result = hard["play_result"].str.lower()
        hard_hits = int(hard_result.str.contains(r"single|double|triple|home").sum())
        hard_outs = int(hard_result.eq("out").sum())
    return {
        "pa": len(pas),
        "k": strikeouts,
        "bb": walks,
        "hbp": hbp,
        "h": hits,
        "tb": singles + 2 * doubles + 3 * triples + 4 * homers,
        "singles": singles,
        "outs": float(outs_recorded) * 3 if pd.notna(outs_recorded) else np.nan,
        "ip": float(outs_recorded) if pd.notna(outs_recorded) else np.nan,
        "runs": runs_allowed(work),
        "hard_hits": hard_hits,
        "hard_outs": hard_outs,
        "ab": len(pas) - walks - hbp,
    }
