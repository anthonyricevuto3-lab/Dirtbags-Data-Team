"""
Game, bullpen, and pitcher profile reports.

Game and bullpen sheets follow the outing layout. Pitcher profiles are two pages.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Ellipse, Rectangle
import numpy as np
import pandas as pd

from ..metrics.preview_metrics import (
    assign_plus,
    chase_pct,
    competitive_mask,
    csw_pct,
    grade_block,
    hard_hit_pct,
    heart_pct,
    RELEASE_GOOD_INCHES,
    mean_plus,
    pa_end_mask,
    plate_appearances,
    prepare_pitches,
    putaway_pct,
    result_counts,
    shadow_pct,
    strike_pct,
    two_strike,
    whiff_pct,
    woba_value,
    xwoba_value,
    zone_pct,
)
from ..pitch_colors import get_pitch_color

BG = "#000000"
GOLD = "#F5C518"
WHITE = "#FFFFFF"
MUTED = "#B5B5B5"
CARD = "#141414"
LINE = "#333333"
HEAT = LinearSegmentedColormap.from_list("loc", ["#1d4e89", "#f7f7f7", "#e53935"])


def _fmt(value, digits=1, suffix=""):
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):.{digits}f}{suffix}"


def _ip_text(value) -> str:
    """Baseball innings: 4.666 displays as 4 2/3."""
    if value is None or pd.isna(value):
        return "—"
    outs = int(round(float(value) * 3))
    whole, remainder = divmod(max(outs, 0), 3)
    fraction = ("", "1/3", "2/3")[remainder]
    if whole and fraction:
        return f"{whole} {fraction}"
    return fraction or str(whole)


def _pct(value):
    return _fmt(value, 1, "%")


def _panel(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_facecolor(CARD)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_color(LINE)
    return ax


def _title(ax, text):
    ax.set_title(text, loc="left", color=GOLD, fontsize=9, fontweight="bold", pad=4)


def _pitch_order(work: pd.DataFrame) -> list[str]:
    labeled = work["pitch_type"].dropna().astype(str)
    labeled = labeled[~labeled.str.lower().isin({"", "nan", "none"})]
    return list(labeled.value_counts().index)


def _short(pitch: str) -> str:
    key = pitch.lower().replace("-", "").replace(" ", "")
    aliases = {
        "changeup": "CH",
        "fastball": "FB",
        "sinker": "SI",
        "slider": "SL",
        "curveball": "CB",
        "curve": "CB",
        "sweeper": "SW",
        "cutter": "CT",
        "splitter": "SP",
        "2seamfastball": "2S",
        "4seamfastball": "4S",
        "fourseamfastball": "4S",
        "twoseamfastball": "2S",
    }
    return aliases.get(key, pitch[:3].upper())


def _result_label(row) -> str:
    call = str(row["pitch_call"]).lower()
    result = str(row["play_result"]).lower()
    korbb = str(row["KorBB"]).lower()
    if "walk" in korbb or result == "walk":
        return "Walk"
    if "strikeout" in korbb:
        return "K"
    if "hitbypitch" in call or "hit by pitch" in call:
        return "HBP"
    if "foul" in call:
        return "Foul"
    if bool(row["whiff_flag"]):
        return "SwStr"
    if "strikecalled" in call:
        return "CallStr"
    if "inplay" in call or any(token in result for token in ("single", "double", "triple", "home", "out")):
        if "home" in result:
            return "HR"
        if "triple" in result:
            return "3B"
        if "double" in result:
            return "2B"
        if "single" in result:
            return "1B"
        if result == "out":
            return "Out"
        return "InPlay"
    if "ball" in call:
        return "Ball"
    return "—"


def _pa_numbers(work: pd.DataFrame) -> pd.Series:
    numbers = []
    current = 0
    for ended in pa_end_mask(work):
        current += 1
        numbers.append(current)
        if ended:
            current = 0
    return pd.Series(numbers, index=work.index)


def _miss_profile(work: pd.DataFrame, throws: str, spots: dict | None = None, expand_chase: bool = False) -> dict:
    located = work[work["plate_x"].notna() & work["plate_z"].notna()]
    if located.empty:
        return {}
    if expand_chase:
        competitive = competitive_mask(located, throws, spots)
    else:
        competitive = located["in_zone"]
    arm_sign = -1.0 if str(throws).upper().startswith("L") else 1.0
    misses = located[~competitive]
    counts = {"Arm-Side": 0, "Glove-Side": 0, "Up": 0, "Down": 0}
    for _, row in misses.iterrows():
        options = {
            "Up": row["plate_z"] - 42.0,
            "Down": 18.0 - row["plate_z"],
            "Arm-Side": arm_sign * row["plate_x"] - 8.5,
            "Glove-Side": -arm_sign * row["plate_x"] - 8.5,
        }
        counts[max(options, key=options.get)] += 1
    total = len(misses) or 1
    return {
        "comp": 100.0 * float(competitive.mean()),
        "noncomp": 100.0 * float((~competitive).mean()),
        **{key: 100.0 * value / total for key, value in counts.items()},
    }


def _zone(ax):
    ax.add_patch(Rectangle((-8.5, 18), 17, 24, fill=False, edgecolor=WHITE, linewidth=1.0, zorder=4))
    ax.set_xlim(-24, 24)
    ax.set_ylim(6, 54)
    ax.set_aspect("equal", adjustable="box")
    ax.tick_params(colors=MUTED, labelsize=7.5)
    for spine in ax.spines.values():
        spine.set_color(LINE)
    ax.set_facecolor(CARD)


def _scatter_locations(ax, work: pd.DataFrame, mark_results: bool = True):
    _zone(ax)
    if work.empty:
        ax.text(0.5, 0.5, "No pitches", transform=ax.transAxes, ha="center", color=MUTED, fontsize=9)
        return
    for pitch in _pitch_order(work):
        sub = work[work["pitch_type"] == pitch]
        ax.scatter(sub["plate_x"], sub["plate_z"], s=16, c=get_pitch_color(pitch), zorder=3)
    if not mark_results:
        return
    ends = plate_appearances(work)
    if len(ends):
        strikeouts = ends[ends["KorBB"].str.lower().str.contains("strikeout")]
        hits = ends[ends["play_result"].str.lower().str.contains(r"single|double|triple|home")]
        ax.scatter(strikeouts["plate_x"], strikeouts["plate_z"], s=46, facecolors="none", edgecolors="#43a047", linewidths=1.2, zorder=5)
        ax.scatter(hits["plate_x"], hits["plate_z"], s=46, facecolors="none", edgecolors="#e53935", linewidths=1.2, zorder=5)


def _run_phrase(runs, innings) -> str:
    run_word = "run" if pd.notna(runs) and float(runs) == 1 else "runs"
    return f"{_fmt(runs, 0)} {run_word} in {_ip_text(innings)} innings"


def _situation_clause(grades: dict) -> str:
    bits = []
    if grades.get("inherited_bonus", 0) > 0:
        outs = grades.get("inherited_outs")
        out_word = "out" if outs == 1 else "outs"
        spot = grades.get("inherited_spot")
        if spot in {3, 4, 5}:
            order = " against the heart of the order"
        elif spot == 9:
            order = " with the 9-hole up"
        else:
            order = ""
        count = int(grades.get("inherited_runners") or 0)
        runner_word = "runner" if count == 1 else "runners"
        bits.append(
            f"Stranded {count} inherited {runner_word} on {grades.get('inherited_bases')} "
            f"with {outs} {out_word}{order}."
        )
    if grades.get("far_misses"):
        extra = ""
        if grades.get("far_miss_runs"):
            extra = f", and a runner scored on {int(grades['far_miss_runs'])} of them"
        misses = int(grades["far_misses"])
        miss_word = "pitch was" if misses == 1 else "pitches were"
        bits.append(f"{misses} {miss_word} 18 inches or more off the plate{extra}.")
    if grades.get("long_pas"):
        reached = int(grades.get("long_reached") or 0)
        extra = f", and the hitter reached in {reached} of them" if reached else ""
        count = int(grades["long_pas"])
        ab_word = "at-bat lasted" if count == 1 else "at-bats lasted"
        bits.append(f"{count} {ab_word} 6 pitches or more{extra}.")
    if grades.get("short_outs"):
        count = int(grades["short_outs"])
        out_word = "out came" if count == 1 else "outs came"
        bits.append(f"{count} {out_word} in 3 pitches or fewer.")
    return " ".join(bits)


def _grade_reason(grades: dict) -> str:
    """One or two sentences on why this outing received its letter."""
    letter = str(grades.get("outing_letter") or "—")
    other = grades.get("other_score")
    runs = grades.get("runs_allowed")
    innings = grades.get("innings_pitched")
    if pd.isna(runs) and grades.get("intrasquad"):
        reason = (
            f"{letter} from a results score of {_fmt(other, 0)}, "
            f"a Stuff+ of {_fmt(grades.get('stuff_plus'), 0)}, "
            f"and a Location+ of {_fmt(grades.get('location_plus'), 0)}."
        )
        clause = _situation_clause(grades)
        return f"{reason} {clause}".strip() if clause else reason
    if pd.isna(runs):
        reason = (
            f"{letter} from the results score of {_fmt(other, 0)}. "
            "Strikeouts and weak outs raise it. Walks, hard contact, and extra-base hits lower it."
        )
        clause = _situation_clause(grades)
        return f"{reason} {clause}".strip() if clause else reason
    phrase = _run_phrase(runs, innings)
    run_letter = str(grades.get("run_letter") or letter[:1])
    adjust = grades.get("length_adjust") or ""
    plain = letter[:1]
    if adjust == "opener":
        reason = f"{run_letter} from {phrase}. One inning with fewer than 3 runs is graded as an opener."
    elif adjust == "short" and run_letter != plain:
        reason = f"{run_letter} from {phrase}, then one letter lower because the start finished under 5 innings."
    elif adjust == "deep" and (run_letter != plain or letter == "A+"):
        reason = f"{run_letter} from {phrase}, then one letter higher for going more than 6 innings."
    elif grades.get("reliever"):
        reason = f"{plain} from {phrase} as a reliever."
    else:
        reason = f"{plain} from {phrase}."
    depth_plus = adjust == "deep" and run_letter == "A" and letter == "A+"
    if letter.endswith("+") and not depth_plus and pd.notna(other) and other >= 65:
        reason += " Contact results added a plus."
    elif letter.endswith("+") and not depth_plus and grades.get("score_delta", 0) > 0:
        reason += " The situation added a plus."
    elif letter.endswith("-") and pd.notna(other) and other <= 35:
        reason += " Contact results added a minus."
    elif letter.endswith("-") and grades.get("score_delta", 0) < 0:
        reason += " The situation added a minus."
    clause = _situation_clause(grades)
    return f"{reason} {clause}".strip() if clause else reason


def _spread_ft(work: pd.DataFrame, column: str) -> float:
    if column not in work.columns:
        return np.nan
    values = pd.to_numeric(work[column], errors="coerce").dropna()
    if len(values) < 3:
        return np.nan
    return float(values.std(ddof=0))


def _inches(feet) -> str:
    """Standard deviation in inches. Release and extension are stored in feet."""
    if feet is None or pd.isna(feet):
        return "—"
    return f"{float(feet) * 12:.1f}"


def _bullpen_notes(work: pd.DataFrame, grades: dict) -> tuple[str, str]:
    """Two sentences: Stuff+ versus the group, then location and release from the outing."""
    letter = grades.get("outing_letter") or "—"
    stuff = mean_plus(work, "stuff_plus") if "stuff_plus" in work.columns else np.nan
    if pd.isna(stuff):
        stuff_line = f"The {letter} has no Stuff+ for this session."
    else:
        gap = float(stuff) - 100
        if gap >= 3:
            relation = "above"
        elif gap <= -3:
            relation = "below"
        else:
            relation = "near"
        stuff_line = (
            f"The {letter} comes from a Stuff+ of {_fmt(stuff, 0)}, "
            f"{relation} this group's average of 100."
        )
    location = (
        f"Location scored {_fmt(grades.get('control_score'), 0)} because "
        f"{_pct(grades.get('competitive_pct'))} of pitches were in the zone, a whiff, or a usual swing-and-miss spot, "
        f"with {_pct(shadow_pct(work))} shadow and {_pct(heart_pct(work))} heart, and release scored "
        f"{_fmt(grades.get('release_score'), 0)} with height, side, and extension varying "
        f"{_inches(_spread_ft(work, 'release_height'))}, {_inches(_spread_ft(work, 'release_side'))}, "
        f"and {_inches(_spread_ft(work, 'extension'))} in, against good marks of "
        f"{RELEASE_GOOD_INCHES['release_height']:.1f}, "
        f"{RELEASE_GOOD_INCHES['release_side']:.1f}, and {RELEASE_GOOD_INCHES['extension']:.1f} in."
    )
    misses = int(grades.get("far_misses") or 0)
    if misses:
        miss_word = "pitch was" if misses == 1 else "pitches were"
        location = f"{location} {misses} {miss_word} 18 inches or more off the plate."
    return stuff_line, location


def _finish_reason(grades: dict) -> str:
    """Same shape as the outing note: the line, then why the finish letter is that letter."""
    letter = str(grades.get("finish_letter") or "—")
    pitches = int(grades.get("finish_pitches") or 0)
    if letter == "—" or pitches < 3:
        return "No finish grade. There were no two-strike pitches."
    whiff = _pct(grades.get("finish_whiff"))
    putaway = grades.get("finish_putaway")
    if pd.isna(putaway):
        line = f"{letter} finish: {whiff} whiff on {pitches} two-strike pitches."
        why = f"{letter} from two-strike swings missing the bat."
    else:
        line = (
            f"{letter} finish: {whiff} whiff and {_pct(putaway)} put away "
            f"on {pitches} two-strike pitches."
        )
        why = (
            f"{letter} from two-strike swings missing the bat and two-strike at-bats "
            "ending in a strikeout or an out."
        )
    return f"{line} {why}"


def _notes(work: pd.DataFrame, kind: str, grades: dict) -> tuple[str, str]:
    counts = result_counts(work)
    if kind == "bullpen":
        return _bullpen_notes(work, grades)
    ip = _ip_text(counts.get("ip"))
    runs = _fmt(counts.get("runs"), 0) if pd.notna(counts.get("runs")) else "—"
    outing = (
        f"{grades['outing_letter']} outing: {runs} R in {ip} IP, {counts['h']} H, {counts['k']} K "
        f"and {counts['bb']} BB on {len(work)} pitches. {_grade_reason(grades)}"
    )
    return outing, _finish_reason(grades)


def _logo(fig):
    """Dirtbag Data Team mark in the top-right corner."""
    image = getattr(_logo, "image", None)
    if image is None:
        image = False
        for candidate in (
            Path(__file__).resolve().parent.parent / "images" / "Dirtbag Data Team baseball logo.png",
            Path("images") / "Dirtbag Data Team baseball logo.png",
        ):
            if candidate.exists():
                image = plt.imread(candidate)
                break
        _logo.image = image
    if image is False:
        return
    width_in, height_in = fig.get_size_inches()
    logo_height = 0.82 if height_in > 14 else 0.62
    logo_width = logo_height * (image.shape[1] / image.shape[0])
    box_w = logo_width / width_in
    box_h = logo_height / height_in
    ax = fig.add_axes([0.975 - box_w, 0.992 - box_h, box_w, box_h])
    ax.set_facecolor(BG)
    ax.imshow(image)
    ax.axis("off")


def _header(fig, name, throws, subtitle, line):
    fig.patch.set_facecolor(BG)
    fig.text(0.04, 0.972, name.upper(), color=WHITE, fontsize=16, fontweight="bold")
    fig.text(0.04, 0.952, f"{throws or '—'}  ·  {subtitle}", color=MUTED, fontsize=9)
    fig.text(0.04, 0.935, line, color=WHITE, fontsize=9)
    fig.add_artist(plt.Line2D([0.04, 0.96], [0.922, 0.922], transform=fig.transFigure, color=GOLD, linewidth=1))


def _grade_row(fig, y, items: list[tuple[str, str]]):
    width = 0.92 / len(items)
    for index, (label, value) in enumerate(items):
        ax = _panel(fig, [0.04 + index * width, y, width - 0.008, 0.045])
        ax.text(0.5, 0.68, label, ha="center", va="center", color=GOLD, fontsize=7.5, transform=ax.transAxes)
        ax.text(0.5, 0.30, value, ha="center", va="center", color=WHITE, fontsize=9, fontweight="bold", transform=ax.transAxes)


def _movement(ax, work):
    ax.set_facecolor(CARD)
    for spine in ax.spines.values():
        spine.set_color(LINE)
    ax.axhline(0, color="#444444", linewidth=0.6)
    ax.axvline(0, color="#444444", linewidth=0.6)
    for pitch in _pitch_order(work):
        sub = work[work["pitch_type"] == pitch].dropna(subset=["hb", "ivb"])
        if sub.empty:
            continue
        ax.scatter(sub["hb"], sub["ivb"], s=18, c=get_pitch_color(pitch), label=pitch, zorder=3)
    xs = pd.to_numeric(work.get("hb"), errors="coerce").dropna()
    ys = pd.to_numeric(work.get("ivb"), errors="coerce").dropna()
    if len(xs) and len(ys):
        pad = 4
        ax.set_xlim(min(-8, float(xs.min()) - pad), max(8, float(xs.max()) + pad))
        ax.set_ylim(min(-8, float(ys.min()) - pad), max(8, float(ys.max()) + pad))
    ax.set_xlabel("Horizontal break (in)", color=MUTED, fontsize=8)
    ax.set_ylabel("Induced vertical break (in)", color=MUTED, fontsize=8)
    ax.tick_params(colors=MUTED, labelsize=7.5)
    ax.set_title("Movement", loc="left", color=GOLD, fontsize=9, fontweight="bold")
    if _pitch_order(work):
        ax.legend(frameon=False, fontsize=7.5, labelcolor=WHITE, loc="upper right")


def _donut(ax, work):
    ax.set_facecolor(CARD)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    order = _pitch_order(work)
    if not order:
        return
    pairs = [(pitch, int((work["pitch_type"] == pitch).sum())) for pitch in order]
    pairs = [(pitch, count) for pitch, count in pairs if count > 0]
    if not pairs:
        return
    ax.pie(
        [count for _, count in pairs],
        colors=[get_pitch_color(pitch) for pitch, _ in pairs],
        startangle=90,
        wedgeprops={"width": 0.42, "edgecolor": CARD},
    )
    ax.text(0, 0, str(len(work)), ha="center", va="center", color=WHITE, fontsize=12, fontweight="bold")
    ax.set_title("Pitch usage", loc="left", color=GOLD, fontsize=9, fontweight="bold")


def generate_preview_outing(
    df: pd.DataFrame,
    output_path: str,
    *,
    kind: str,
    name: str,
    throws: str,
    outing_date: str,
    subtitle: str,
    baseline,
    previous: pd.DataFrame | None = None,
    whiff_spots: dict | None = None,
    game: pd.DataFrame | None = None,
) -> None:
    work = assign_plus(prepare_pitches(df), baseline)
    grades = grade_block(
        work,
        kind,
        throws=throws,
        whiff_spots=whiff_spots,
        intrasquad=subtitle.lower().startswith("intrasquad"),
        game=game,
    )
    counts = result_counts(work)
    order = _pitch_order(work)
    fig = plt.figure(figsize=(8.5, 17.2))
    _header(
        fig,
        name,
        "RHP" if str(throws).upper().startswith("R") else "LHP" if str(throws).upper().startswith("L") else throws,
        subtitle,
        _outing_line(work, kind, counts),
    )
    if kind == "bullpen":
        grade_items = [
            ("GRADE", f"{grades['outing_letter']}  {_fmt(grades['outing_score'], 0)}"),
            ("CONTROL", _fmt(grades.get("control_score"), 0)),
            ("STUFF", _fmt(grades.get("stuff_score"), 0)),
            ("RELEASE", _fmt(grades.get("release_score"), 0)),
            ("STRIKE%", _pct(zone_pct(work))),
            ("HEART%", _pct(heart_pct(work))),
            ("SHADOW%", _pct(shadow_pct(work))),
        ]
    else:
        grade_items = [
            ("GRADE", grades["outing_letter"]),
            ("RUNS", _fmt(grades.get("runs_allowed"), 0)),
            ("INNINGS", _ip_text(grades.get("innings_pitched"))),
            ("OTHER", _fmt(grades.get("other_score"), 0)),
            ("STRIKE%", _pct(strike_pct(work))),
            ("WHIFF%", _pct(whiff_pct(work))),
            ("CSW%", _pct(csw_pct(work))),
            ("95+ H/O", f"{counts['hard_hits']}/{counts['hard_outs']}"),
        ]
    _grade_row(fig, 0.86, grade_items)

    info = _panel(fig, [0.04, 0.745, 0.28, 0.10])
    _title(info, "Inning splits" if kind == "game" else "Control")
    _command_or_innings(info, work, kind)

    primary = _panel(fig, [0.33, 0.745, 0.32, 0.10])
    _primary_card(primary, work, order, kind)

    usage = _panel(fig, [0.66, 0.745, 0.30, 0.10])
    _usage_list(usage, work, order)

    move = fig.add_axes([0.06, 0.545, 0.40, 0.18])
    _movement(move, work)
    last = _panel(fig, [0.50, 0.545, 0.18, 0.18])
    _versus_last(last, work, previous, kind)
    side_card = _panel(fig, [0.70, 0.545, 0.26, 0.18])
    if kind == "bullpen":
        _release_card(side_card, work)
    else:
        _finish_card(side_card, work, order, str(grades.get("finish_letter") or "—"))

    if kind == "bullpen":
        locations = [("All pitches", work)]
        locations.extend((pitch, work[work["pitch_type"] == pitch]) for pitch in order[:3])
    else:
        locations = [
            ("vs LHB", _side(work, "L")),
            ("vs RHB", _side(work, "R")),
            ("2K vs LHB", _side(two_strike(work), "L")),
            ("2K vs RHB", _side(two_strike(work), "R")),
        ]
    for index, (label, subset) in enumerate(locations):
        column = index % 2
        row = index // 2
        ax = fig.add_axes([0.05 + column * 0.24, 0.345 - row * 0.145, 0.20, 0.13])
        _scatter_locations(ax, subset, mark_results=kind != "bullpen")
        ax.set_title(label, color=GOLD, fontsize=9, loc="left")

    miss = _panel(fig, [0.55, 0.205, 0.41, 0.27])
    _miss_card(miss, work, throws, kind=kind, whiff_spots=whiff_spots)

    table = _panel(fig, [0.04, 0.12, 0.92, 0.075])
    _outing_table(table, work, order, kind)
    note_left, note_right = _notes(work, kind, grades)
    notes = _panel(fig, [0.04, 0.028, 0.92, 0.082])
    notes.text(0.01, 0.72, "FIELD NOTES", color=GOLD, fontsize=8, fontweight="bold", transform=notes.transAxes)
    if kind == "bullpen":
        wrapped = textwrap.fill(f"{note_left} {note_right}", width=100)
        notes.text(0.01, 0.52, wrapped, color=WHITE, fontsize=8, transform=notes.transAxes, va="top")
    else:
        notes.text(0.01, 0.52, textwrap.fill(note_left, width=62), color=WHITE, fontsize=8, transform=notes.transAxes, va="top")
        notes.text(0.52, 0.52, textwrap.fill(note_right, width=62), color=WHITE, fontsize=8, transform=notes.transAxes, va="top")

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(path) as pdf:
        _logo(fig)
        pdf.savefig(fig)
        plt.close(fig)
        innings = grades.get("innings_pitched")
        short_outing = kind == "game" and pd.notna(innings) and innings <= 1
        if kind == "bullpen" or len(work) <= 15 or short_outing:
            _pitch_log(pdf, work, name, subtitle, kind)
        _location_page(pdf, work, name, subtitle, kind)


def _outing_line(work, kind, counts) -> str:
    if kind == "bullpen":
        return (
            f"{len(work)} pitches  ·  {_pct(zone_pct(work))} strikes  ·  "
            f"{_pct(heart_pct(work))} heart  ·  {_pct(shadow_pct(work))} shadow"
        )
    ip = _ip_text(counts.get("ip"))
    return (
        f"{_fmt(counts.get('runs'), 0) if pd.notna(counts.get('runs')) else '—'} R  ·  {ip} IP  ·  {counts['h']} H  ·  {counts['tb']} TB  ·  {counts['k']} K  ·  "
        f"{counts['bb']} BB  ·  {counts['hbp']} HBP  ·  {_pct(strike_pct(work))} strikes  ·  "
        f"{_pct(whiff_pct(work))} whiff  ·  {len(work)} pitches"
    )


def _command_or_innings(ax, work, kind):
    if kind == "bullpen" or work["inning"].dropna().empty:
        shadow = shadow_pct(work)
        if kind == "bullpen":
            lines = [
                f"Strike    {_pct(zone_pct(work))}",
                f"Heart     {_pct(heart_pct(work))}",
                f"Shadow    {_pct(shadow)}",
            ]
        else:
            lines = [
                f"In zone   {_pct(zone_pct(work))}",
                f"Heart     {_pct(heart_pct(work))}",
                f"Shadow    {_pct(shadow)}",
                f"Strike    {_pct(strike_pct(work))}",
            ]
    else:
        lines = ["INN   VELO   STR%   N"]
        for inning, group in work.dropna(subset=["inning"]).groupby("inning"):
            lines.append(
                f"{int(inning):<4}  {_fmt(group['velocity'].mean(), 1):<6} {_pct(strike_pct(group)):<6} {len(group)}"
            )
    for index, line in enumerate(lines[:6]):
        ax.text(0.05, 0.78 - index * 0.14, line, color=WHITE, fontsize=8, family="monospace", transform=ax.transAxes)


def _primary_card(ax, work, order, kind: str):
    _title(ax, "Primary pitch")
    if not order:
        return
    pitch = order[0]
    group = work[work["pitch_type"] == pitch]
    ax.text(0.05, 0.62, pitch, color=get_pitch_color(pitch), fontsize=10, fontweight="bold", transform=ax.transAxes)
    if kind == "bullpen":
        third = f"Strike {_pct(zone_pct(group))}   Stuff+ {_fmt(mean_plus(group, 'stuff_plus'), 0)}"
    else:
        third = f"CSW {_pct(csw_pct(group))}"
    detail = (
        f"{_fmt(group['velocity'].mean())} mph   max {_fmt(group['velocity'].max())}   "
        f"IVB {_fmt(group['ivb'].mean())}\"   HB {_fmt(group['hb'].mean())}\"\n"
        f"VAA {_fmt(group['vaa'].mean())}°   Ext {_fmt(group['extension'].mean(), 2)}'   "
        f"{third}"
    )
    ax.text(0.05, 0.28, detail, color=WHITE, fontsize=8, transform=ax.transAxes)


def _usage_list(ax, work, order):
    _title(ax, "Mix")
    for index, pitch in enumerate(order[:5]):
        count = int((work["pitch_type"] == pitch).sum())
        share = 100.0 * count / len(work) if len(work) else 0
        ax.text(0.06, 0.78 - index * 0.15, f"{_short(pitch)}  {count}", color=get_pitch_color(pitch), fontsize=9, transform=ax.transAxes)
        ax.text(0.55, 0.78 - index * 0.15, _pct(share), color=WHITE, fontsize=9, transform=ax.transAxes)


def _signed(value) -> tuple[str, str]:
    if value is None or pd.isna(value):
        return "—", MUTED
    number = float(value)
    if number > 0:
        return f"{number:+.1f}", "#43a047"
    if number < 0:
        return f"{number:+.1f}", "#e53935"
    return f"{number:+.1f}", WHITE


def _versus_last(ax, work, previous, kind: str):
    _title(ax, "Vs last Trackman")
    if previous is None or previous.empty:
        ax.text(0.05, 0.5, "No prior outing", color=MUTED, fontsize=9, transform=ax.transAxes)
        return
    prior = prepare_pitches(previous)
    if kind == "bullpen":
        rows = [
            ("Velo", _fmt(work["velocity"].mean()), work["velocity"].mean() - prior["velocity"].mean()),
            ("Str%", _pct(zone_pct(work)), zone_pct(work) - zone_pct(prior)),
            ("Heart", _pct(heart_pct(work)), heart_pct(work) - heart_pct(prior)),
        ]
    else:
        rows = [
            ("Velo", _fmt(work["velocity"].mean()), work["velocity"].mean() - prior["velocity"].mean()),
            ("Str%", _pct(strike_pct(work)), strike_pct(work) - strike_pct(prior)),
            ("Whiff", _pct(whiff_pct(work)), whiff_pct(work) - whiff_pct(prior)),
        ]
    for index, (label, value, delta) in enumerate(rows):
        y_pos = 0.7 - index * 0.22
        signed, color = _signed(delta)
        ax.text(0.05, y_pos, f"{label}  {value}", color=WHITE, fontsize=8, transform=ax.transAxes)
        ax.text(0.58, y_pos, f"({signed})", color=color, fontsize=8, transform=ax.transAxes)


def _release_card(ax, work):
    _title(ax, "Release")
    rows = [
        ("Height", work["release_height"]),
        ("Side", work["release_side"]),
        ("Extension", work["extension"]),
    ]
    for index, (label, series) in enumerate(rows):
        values = pd.to_numeric(series, errors="coerce").dropna()
        spread = float(values.std(ddof=0)) if len(values) >= 2 else np.nan
        ax.text(
            0.05,
            0.72 - index * 0.22,
            f"{label}  {_fmt(values.mean() if len(values) else np.nan, 2)}'   ± {_inches(spread)} in",
            color=WHITE,
            fontsize=9,
            transform=ax.transAxes,
        )
    ax.text(
        0.05,
        0.06,
        "Good SD  "
        f"{RELEASE_GOOD_INCHES['release_height']:.1f} / "
        f"{RELEASE_GOOD_INCHES['release_side']:.1f} / "
        f"{RELEASE_GOOD_INCHES['extension']:.1f} in",
        color=MUTED,
        fontsize=8,
        transform=ax.transAxes,
    )


def _finish_card(ax, work, order, letter: str = "—"):
    _title(ax, f"Finish  {letter}")
    late = two_strike(work)
    ax.text(0.05, 0.78, f"2K pitches {len(late)}", color=WHITE, fontsize=8, transform=ax.transAxes)
    for index, pitch in enumerate(order[:4]):
        group = late[late["pitch_type"] == pitch]
        share = 100.0 * len(group) / len(late) if len(late) else 0
        ax.text(
            0.05,
            0.60 - index * 0.16,
            f"{_short(pitch)}  {len(group):<3} {_pct(share)}  whiff {_pct(whiff_pct(group))}",
            color=get_pitch_color(pitch),
            fontsize=8,
            transform=ax.transAxes,
        )


def _miss_card(ax, work, throws, kind: str = "game", whiff_spots: dict | None = None):
    _title(ax, "Miss profile")
    profile = _miss_profile(work, throws, whiff_spots, expand_chase=True)
    if not profile:
        return
    rows = [
        ("Competitive", profile["comp"]),
        ("Non-competitive", profile["noncomp"]),
        ("Arm side", profile["Arm-Side"]),
        ("Glove side", profile["Glove-Side"]),
        ("Up", profile["Up"]),
        ("Down", profile["Down"]),
    ]
    for index, (label, value) in enumerate(rows):
        ax.text(0.06, 0.78 - index * 0.12, label, color=MUTED, fontsize=9, transform=ax.transAxes)
        ax.text(0.62, 0.78 - index * 0.12, _pct(value), color=WHITE, fontsize=9, transform=ax.transAxes)


def _outing_table(ax, work, order, kind: str):
    ax.axis("off")
    if kind == "bullpen":
        headers = ["PITCH", "#", "VELO", "IVB", "HB", "RPM", "EXT", "STR%", "HEART%", "SHAD%", "VAA", "STF+", "LOC+"]
    else:
        headers = ["PITCH", "#", "VELO", "IVB", "HB", "RPM", "EXT", "ZN%", "STR%", "WHF%", "CSW%", "VAA", "STF+", "LOC+"]
    rows = []
    colors = []
    for pitch in order[:6]:
        group = work[work["pitch_type"] == pitch]
        shared = [
            pitch,
            str(len(group)),
            _fmt(group["velocity"].mean()),
            _fmt(group["ivb"].mean()),
            _fmt(group["hb"].mean()),
            _fmt(group["spin_rate"].mean(), 0),
            _fmt(group["extension"].mean(), 2),
        ]
        if kind == "bullpen":
            shared.extend(
                [
                    _pct(zone_pct(group)),
                    _pct(heart_pct(group)),
                    _pct(shadow_pct(group)),
                    _fmt(group["vaa"].mean()),
                    _fmt(mean_plus(group, "stuff_plus"), 0),
                    _fmt(mean_plus(group, "location_plus"), 0),
                ]
            )
        else:
            shared.extend(
                [
                    _pct(zone_pct(group)),
                    _pct(strike_pct(group)),
                    _pct(whiff_pct(group)),
                    _pct(csw_pct(group)),
                    _fmt(group["vaa"].mean()),
                    _fmt(mean_plus(group, "stuff_plus"), 0),
                    _fmt(mean_plus(group, "location_plus"), 0),
                ]
            )
        rows.append(shared)
        colors.append(get_pitch_color(pitch))
    _text_table(ax, headers, rows, colors)


def _text_table(ax, headers, rows, colors):
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    columns = max(len(headers), 1)
    size = 8 if columns <= 8 else 6.5

    def cell(text, column, y_pos, color):
        ax.text(
            (column + 0.5) / columns,
            y_pos,
            str(text),
            ha="center",
            va="center",
            color=color,
            fontsize=size,
            transform=ax.transAxes,
            clip_on=True,
        )

    for index, header in enumerate(headers):
        cell(header, index, 0.88, GOLD)
    step = 0.62 / max(len(rows), 1)
    for row_index, row in enumerate(rows):
        y_pos = 0.62 - row_index * step
        for index, value in enumerate(row):
            color = colors[row_index] if index == 0 and row_index < len(colors) else WHITE
            cell(value, index, y_pos, color)


def _zone_result(row) -> str:
    if pd.isna(row["plate_x"]) or pd.isna(row["plate_z"]):
        return "—"
    if bool(row["in_heart"]):
        return "Heart"
    if bool(row["in_zone"]):
        return "Strike"
    return "Ball"


def _pitch_log(pdf, work, name, subtitle, kind: str):
    labeled = work.copy()
    labeled["pa_n"] = _pa_numbers(work)
    if kind == "bullpen":
        labeled["result_label"] = labeled.apply(_zone_result, axis=1)
    else:
        labeled["result_label"] = labeled.apply(_result_label, axis=1)
    rows = list(labeled.itertuples(index=False))
    chunks = [rows[i : i + 32] for i in range(0, max(len(rows), 1), 32)] or [[]]
    for page_rows in chunks:
        fig = plt.figure(figsize=(8.5, 11))
        fig.patch.set_facecolor(BG)
        fig.text(0.05, 0.96, f"{name.upper()}  ·  PITCH BY PITCH", color=WHITE, fontsize=13, fontweight="bold")
        fig.text(0.05, 0.935, subtitle, color=GOLD, fontsize=9)
        ax = fig.add_axes([0.04, 0.05, 0.92, 0.86])
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        header = (
            "#   PITCH   VELO   IVB    HB    SPIN   EXT   VAA   X     Z    LOC"
            if kind == "bullpen"
            else "#   INN  PA  PITCH   VELO   IVB    HB    SPIN   EXT   VAA   X     Z    RESULT"
        )
        ax.text(0.0, 0.98, header, color=GOLD, fontsize=8, family="monospace")
        for index, row in enumerate(page_rows):
            inning = "—" if pd.isna(getattr(row, "inning", np.nan)) else str(int(row.inning))
            raw_pitch = getattr(row, "pitch_type", "")
            pitch = "—" if pd.isna(raw_pitch) else _short(str(raw_pitch))
            metrics = (
                f"{_fmt(row.velocity):<7}{_fmt(row.ivb):<7}{_fmt(row.hb):<7}"
                f"{_fmt(row.spin_rate, 0):<7}{_fmt(row.extension, 2):<6}{_fmt(row.vaa):<6}"
                f"{_fmt(row.plate_x / 12 if pd.notna(row.plate_x) else np.nan, 2):<6}"
                f"{_fmt(row.plate_z / 12 if pd.notna(row.plate_z) else np.nan, 2):<6}{row.result_label}"
            )
            if kind == "bullpen":
                line = f"{index + 1:<4}{pitch:<7}{metrics}"
            else:
                line = f"{index + 1:<4}{inning:<5}{int(row.pa_n):<4}{pitch:<7}{metrics}"
            ax.text(0.0, 0.94 - index * 0.028, line, color=WHITE, fontsize=8, family="monospace")
        fig.text(0.05, 0.02, "Long Beach State Dirtbags  ·  Trackman", color=MUTED, fontsize=8)
        _logo(fig)
        pdf.savefig(fig)
        plt.close(fig)


def _location_page(pdf, work, name, subtitle, kind: str):
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor(BG)
    fig.text(0.05, 0.96, f"{name.upper()}  ·  PITCH LOCATIONS", color=WHITE, fontsize=13, fontweight="bold")
    caption = f"{subtitle}  ·  catcher's view"
    if kind != "bullpen":
        caption += "  ·  green ring = strikeout  ·  red ring = hit"
    fig.text(0.05, 0.935, caption, color=GOLD, fontsize=9)
    ax = fig.add_axes([0.12, 0.12, 0.76, 0.76])
    _scatter_locations(ax, work, mark_results=kind != "bullpen")
    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=get_pitch_color(pitch), label=f"{pitch} ({int((work['pitch_type'] == pitch).sum())})")
        for pitch in _pitch_order(work)
    ]
    if handles:
        ax.legend(handles=handles, frameon=False, fontsize=9, labelcolor=WHITE, loc="upper right")
    fig.text(0.05, 0.03, "Long Beach State Dirtbags  ·  Trackman", color=MUTED, fontsize=8)
    _logo(fig)
    pdf.savefig(fig)
    plt.close(fig)


def _side(work, hand: str) -> pd.DataFrame:
    side = work["batter_side"].str.lower()
    if hand == "L":
        return work[side.str.startswith("l")]
    return work[side.str.startswith("r")]


def generate_preview_profile(
    df: pd.DataFrame,
    output_path: str,
    *,
    name: str,
    throws: str,
    title: str,
    date_span: str,
    baseline,
) -> None:
    work = assign_plus(prepare_pitches(df), baseline) if df is not None and len(df) else prepare_pitches(df)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(path) as pdf:
        _profile_page_one(pdf, work, name, throws, title, date_span)
        _profile_page_two(pdf, work, name, throws)


def _profile_page_one(pdf, work, name, throws, title, date_span):
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor(BG)
    hand = "RHP" if str(throws).upper().startswith("R") else "LHP" if str(throws).upper().startswith("L") else (throws or "—")
    fig.text(0.04, 0.965, name, color=WHITE, fontsize=18, fontweight="bold")
    fig.text(0.04, 0.938, f"{hand}    {title}    {date_span}", color=MUTED, fontsize=9)
    counts = result_counts(work) if len(work) else {}
    order = _pitch_order(work)
    primary = order[0] if order else ""
    primary_group = work[work["pitch_type"] == primary] if primary else work
    pills = [
        ("PITCHES", str(len(work))),
        ("PA", str(counts.get("pa", 0))),
        (f"{_short(primary)} VELO" if primary else "VELO", _fmt(primary_group["velocity"].mean() if len(primary_group) else np.nan)),
        ("MAX", _fmt(work["velocity"].max() if len(work) else np.nan)),
        ("K%", _pct(100 * counts.get("k", 0) / counts["pa"] if counts.get("pa") else np.nan)),
        ("BB%", _pct(100 * counts.get("bb", 0) / counts["pa"] if counts.get("pa") else np.nan)),
        ("STR%", _pct(strike_pct(work) if len(work) else np.nan)),
        ("CSW%", _pct(csw_pct(work) if len(work) else np.nan)),
        ("WHIFF%", _pct(whiff_pct(work) if len(work) else np.nan)),
        ("XWOBA", _fmt(xwoba_value(work) if len(work) else np.nan, 3)),
        ("STUFF+", _fmt(mean_plus(work, "stuff_plus") if "stuff_plus" in work.columns else np.nan, 0)),
    ]
    width = 0.90 / len(pills)
    for index, (label, value) in enumerate(pills):
        ax = _panel(fig, [0.04 + index * width, 0.875, width - 0.006, 0.05])
        ax.text(0.5, 0.66, label, ha="center", color=MUTED, fontsize=6, transform=ax.transAxes)
        ax.text(0.5, 0.28, value, ha="center", color=WHITE, fontsize=8, fontweight="bold", transform=ax.transAxes)

    move = fig.add_axes([0.06, 0.61, 0.40, 0.24])
    _profile_movement(move, work)
    pies = _panel(fig, [0.52, 0.61, 0.44, 0.24])
    _usage_pies(fig, pies, work)

    table = _panel(fig, [0.04, 0.33, 0.92, 0.25])
    _profile_pitch_table(table, work, order)
    splits = _panel(fig, [0.04, 0.13, 0.92, 0.18])
    _split_table(splits, work)
    fig.text(
        0.04,
        0.078,
        textwrap.fill(
            "Stuff+ and Location+ use 100 as this Dirtbags group's average for that pitch type. "
            "xwOBA uses walk, hit-by-pitch, and strikeout weights, and a contact table based on the public barrel window. "
            "U3VAA is the average approach angle on pitches 34–42 inches high.",
            width=115,
        ),
        color=MUTED,
        fontsize=7.5,
        va="top",
    )
    fig.text(0.04, 0.015, "Long Beach State Dirtbags", color=GOLD, fontsize=8)
    _logo(fig)
    pdf.savefig(fig)
    plt.close(fig)


def _profile_movement(ax, work):
    ax.set_facecolor(CARD)
    for spine in ax.spines.values():
        spine.set_color(LINE)
    ax.axhline(0, color="#444444", linewidth=0.5)
    ax.axvline(0, color="#444444", linewidth=0.5)
    ax.set_title("Pitch movement", loc="left", color=GOLD, fontsize=9, fontweight="bold")
    for pitch in _pitch_order(work):
        sub = work[work["pitch_type"] == pitch].dropna(subset=["hb", "ivb"])
        if sub.empty:
            continue
        color = get_pitch_color(pitch)
        ax.scatter(sub["hb"], sub["ivb"], s=12 + 40 * len(sub) / max(len(work), 1), c=color, alpha=0.85, zorder=3)
        if len(sub) >= 3:
            ax.add_patch(Ellipse((sub["hb"].mean(), sub["ivb"].mean()), width=2 * sub["hb"].std(ddof=0) or 0.2, height=2 * sub["ivb"].std(ddof=0) or 0.2, fill=False, edgecolor=color, linewidth=0.8))
            ax.add_patch(Ellipse((sub["hb"].mean(), sub["ivb"].mean()), width=4 * sub["hb"].std(ddof=0) or 0.4, height=4 * sub["ivb"].std(ddof=0) or 0.4, fill=False, edgecolor=color, linewidth=0.5, alpha=0.7))
    ax.tick_params(colors=MUTED, labelsize=7.5)
    ax.set_xlabel("Horizontal break (in)", color=MUTED, fontsize=8)
    ax.set_ylabel("Induced vertical break (in)", color=MUTED, fontsize=8)


def _usage_pies(fig, host, work):
    host.axis("off")
    host.set_title("Usage vs batter handedness", loc="left", color=GOLD, fontsize=9, fontweight="bold")
    left = _side(work, "L")
    right = _side(work, "R")
    for rect, subset, label in (
        ([0.55, 0.63, 0.16, 0.16], left, f"vs LHB  {len(left)}"),
        ([0.76, 0.63, 0.16, 0.16], right, f"vs RHB  {len(right)}"),
    ):
        ax = fig.add_axes(rect)
        ax.set_facecolor(CARD)
        order = _pitch_order(subset) or _pitch_order(work)
        if subset.empty or not order:
            ax.text(0.5, 0.5, "No pitches", ha="center", color=MUTED, fontsize=8)
            ax.axis("off")
            continue
        pairs = [(pitch, int((subset["pitch_type"] == pitch).sum())) for pitch in order]
        pairs = [(pitch, count) for pitch, count in pairs if count > 0]
        if not pairs:
            ax.text(0.5, 0.5, "No pitches", ha="center", color=MUTED, fontsize=8)
            ax.axis("off")
            continue
        ax.pie([count for _, count in pairs], colors=[get_pitch_color(pitch) for pitch, _ in pairs], startangle=90)
        ax.set_title(label, color=WHITE, fontsize=8)


def _profile_pitch_table(ax, work, order):
    _title(ax, "Pitch metrics")
    ax.axis("off")
    headers = ["PITCH", "#", "USE%", "VELO", "MAX", "SPIN", "IVB", "HB", "VAA", "ZN%", "STR%", "CH%", "WHF%", "CSW%", "HH%", "XWOBA", "STF+", "LOC+"]
    rows = []
    colors = []
    for pitch in order[:6]:
        group = work[work["pitch_type"] == pitch]
        rows.append(
            [
                _short(pitch),
                str(len(group)),
                _pct(100 * len(group) / len(work) if len(work) else np.nan),
                _fmt(group["velocity"].mean()),
                _fmt(group["velocity"].max()),
                _fmt(group["spin_rate"].mean(), 0),
                _fmt(group["ivb"].mean()),
                _fmt(group["hb"].mean()),
                _fmt(group["vaa"].mean()),
                _pct(zone_pct(group)),
                _pct(strike_pct(group)),
                _pct(chase_pct(group)),
                _pct(whiff_pct(group)),
                _pct(csw_pct(group)),
                _pct(hard_hit_pct(group)),
                _fmt(xwoba_value(group), 3),
                _fmt(mean_plus(group, "stuff_plus"), 0),
                _fmt(mean_plus(group, "location_plus"), 0),
            ]
        )
        colors.append(get_pitch_color(pitch))
    _text_table(ax, headers, rows, colors)


def _split_table(ax, work):
    _title(ax, "Results by batter handedness")
    ax.axis("off")
    headers = ["SPLIT", "PITCH", "PA", "K%", "BB%", "AVG", "STR%", "ZONE%", "CH%", "WHF%", "CSW%", "HH%", "WOBA", "XWOBA"]
    rows = []
    colors = [WHITE, WHITE, GOLD]
    for label, subset in (("vs LHB", _side(work, "L")), ("vs RHB", _side(work, "R")), ("Total", work)):
        counts = result_counts(subset) if len(subset) else result_counts(subset.iloc[0:0] if len(work) == 0 else subset)
        ab = counts["ab"]
        rows.append(
            [
                label,
                str(len(subset)),
                str(counts["pa"]),
                _pct(100 * counts["k"] / counts["pa"] if counts["pa"] else np.nan),
                _pct(100 * counts["bb"] / counts["pa"] if counts["pa"] else np.nan),
                _fmt(counts["h"] / ab if ab else np.nan, 3),
                _pct(strike_pct(subset) if len(subset) else np.nan),
                _pct(zone_pct(subset) if len(subset) else np.nan),
                _pct(chase_pct(subset) if len(subset) else np.nan),
                _pct(whiff_pct(subset) if len(subset) else np.nan),
                _pct(csw_pct(subset) if len(subset) else np.nan),
                _pct(hard_hit_pct(subset) if len(subset) else np.nan),
                _fmt(woba_value(subset) if len(subset) else np.nan, 3),
                _fmt(xwoba_value(subset) if len(subset) else np.nan, 3),
            ]
        )
    _text_table(ax, headers, rows, colors)


def _profile_page_two(pdf, work, name, throws):
    fig = plt.figure(figsize=(8.5, 11))
    fig.patch.set_facecolor(BG)
    fig.text(0.04, 0.965, f"{name}  ·  locations, counts, and misses", color=WHITE, fontsize=12, fontweight="bold")
    order = _pitch_order(work)[:5]
    fig.text(0.04, 0.94, "Catcher's view. Dashed box is the strike zone. Heatmaps need 5 pitches and are scaled to that pitch.", color=MUTED, fontsize=8)
    for index, pitch in enumerate(order):
        group = work[work["pitch_type"] == pitch]
        x = 0.04 + index * 0.19
        fig.text(x, 0.915, pitch, color=get_pitch_color(pitch), fontsize=8, fontweight="bold")
        for row, (label, subset) in enumerate((("LHB", _side(group, "L")), ("RHB", _side(group, "R")))):
            ax = fig.add_axes([x, 0.78 - row * 0.13, 0.17, 0.12])
            _zone(ax)
            ax.scatter(subset["plate_x"], subset["plate_z"], s=8, c=get_pitch_color(pitch))
            ax.set_title(f"{label} {len(subset)}", color=MUTED, fontsize=7.5, loc="left")
        for row, (label, subset) in enumerate((("Heat L", _side(group, "L")), ("Heat R", _side(group, "R")))):
            ax = fig.add_axes([x, 0.50 - row * 0.13, 0.17, 0.12])
            _heatmap(ax, subset)
            ax.set_title(label, color=MUTED, fontsize=7.5, loc="left")
    counts = _panel(fig, [0.04, 0.16, 0.92, 0.18])
    _count_bars(counts, work, order)
    misses = _panel(fig, [0.04, 0.03, 0.92, 0.12])
    _miss_table(misses, work, throws)
    _logo(fig)
    pdf.savefig(fig)
    plt.close(fig)


def _heatmap(ax, subset):
    ax.set_facecolor(CARD)
    for spine in ax.spines.values():
        spine.set_color(LINE)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.add_patch(Rectangle((-8.5, 18), 17, 24, fill=False, edgecolor=WHITE, linewidth=0.6, linestyle="--"))
    ax.set_xlim(-24, 24)
    ax.set_ylim(6, 54)
    located = subset.dropna(subset=["plate_x", "plate_z"])
    if len(located) < 5:
        ax.text(0.5, 0.5, "n<5", transform=ax.transAxes, ha="center", color=MUTED, fontsize=8)
        return
    xs = located["plate_x"].to_numpy(dtype=float)
    zs = located["plate_z"].to_numpy(dtype=float)
    xx, zz = np.meshgrid(np.linspace(-24, 24, 80), np.linspace(6, 54, 80))
    bandwidth = 3.6
    density = np.zeros(xx.shape)
    for start in range(0, len(xs), 40):
        x = xs[start : start + 40][:, None, None]
        z = zs[start : start + 40][:, None, None]
        density += np.exp(-0.5 * (((xx - x) / bandwidth) ** 2 + ((zz - z) / bandwidth) ** 2)).sum(axis=0)
    floor = float(density.max()) * 0.12
    ax.contourf(xx, zz, np.ma.masked_less(density, floor), levels=8, cmap=HEAT, zorder=2)
    ax.set_xlim(-24, 24)
    ax.set_ylim(6, 54)
    ax.set_aspect("equal", adjustable="box")
    ax.add_patch(Rectangle((-8.5, 18), 17, 24, fill=False, edgecolor=WHITE, linewidth=0.6, linestyle="--", zorder=4))


def _count_bars(ax, work, order):
    _title(ax, "Usage by count")
    ax.axis("off")
    buckets = {
        "0-0": work[(work["balls"] == 0) & (work["strikes"] == 0)],
        "Ahead": work[work["strikes"] > work["balls"]],
        "Even": work[(work["balls"] == work["strikes"]) & ~((work["balls"] == 0) & (work["strikes"] == 0))],
        "Behind": work[work["balls"] > work["strikes"]],
        "2 strikes": work[work["strikes"] >= 2],
    }
    for index, (label, subset) in enumerate(buckets.items()):
        y = 0.78 - index * 0.16
        ax.text(0.01, y, f"{label} {len(subset)}", color=WHITE, fontsize=7.5, transform=ax.transAxes)
        if subset.empty or not order:
            continue
        start = 0.18
        for pitch in order:
            share = (subset["pitch_type"] == pitch).mean()
            if share <= 0:
                continue
            width = 0.75 * share
            ax.add_patch(Rectangle((start, y - 0.04), width, 0.08, transform=ax.transAxes, color=get_pitch_color(pitch), linewidth=0))
            if share >= 0.08:
                ax.text(start + width / 2, y, f"{share * 100:.0f}%", ha="center", va="center", color=BG, fontsize=6.5, transform=ax.transAxes)
            start += width


def _miss_table(ax, work, throws):
    _title(ax, "Miss tendency")
    ax.axis("off")
    headers = ["PITCH", "#", "ZONE%", "NON%", "ARM", "GLOVE", "UP", "DOWN", "MAIN"]
    rows = []
    colors = []
    groups = [(pitch, work[work["pitch_type"] == pitch]) for pitch in _pitch_order(work)[:5]]
    groups.append(("All", work))
    for pitch, group in groups:
        profile = _miss_profile(group, throws)
        if not profile:
            continue
        main = max(("Arm-Side", "Glove-Side", "Up", "Down"), key=lambda key: profile[key])
        rows.append(
            [
                _short(pitch) if pitch != "All" else "All",
                str(len(group)),
                _pct(profile["comp"]),
                _pct(profile["noncomp"]),
                _pct(profile["Arm-Side"]),
                _pct(profile["Glove-Side"]),
                _pct(profile["Up"]),
                _pct(profile["Down"]),
                main,
            ]
        )
        colors.append(get_pitch_color(pitch) if pitch != "All" else WHITE)
    _text_table(ax, headers, rows, colors)
