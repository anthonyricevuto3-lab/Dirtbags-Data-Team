"""
Centralized pitch-type color palette for reports, dashboards, and visuals.

Colors (user-requested):
- Fastball: vibrant red
- Changeup: bright green
- Slider: bright yellow
- Curveball: deep blue
- Sweeper: purple
- 2 seam: pink
- 4 seam: magenta
"""

from typing import Dict, Iterable

# Base palette keyed by normalized pitch type strings (alphanumeric, lowercase, no spaces/hyphens)
_BASE_PITCH_COLORS: Dict[str, str] = {
    "fastball": "#e53935",  # vibrant red
    "fb": "#e53935",
    "changeup": "#2ecc71",  # bright green
    "ch": "#2ecc71",
    "slider": "#fbc02d",  # bright yellow
    "sl": "#fbc02d",
    "curveball": "#1565c0",  # deep blue
    "curve": "#1565c0",
    "cb": "#1565c0",
    "knucklecurve": "#1565c0",
    "sweeper": "#8e24aa",  # purple
    "sweep": "#8e24aa",
    "2seam": "#ec407a",  # pink
    "2seamfastball": "#ec407a",
    "twoseamfastball": "#ec407a",
    "twoseam": "#ec407a",
    "sinker": "#ec407a",
    "4seam": "#d500f9",  # magenta
    "4seamfastball": "#d500f9",
    "fourseamfastball": "#d500f9",
    "fourseam": "#d500f9",
}

# Fallback color for unrecognized pitch types
DEFAULT_PITCH_COLOR = "#616161"  # neutral gray


def _normalize_pitch_type(pitch_type: str) -> str:
    """Normalize pitch type strings for lookup (lowercase, alphanumeric only)."""
    if not isinstance(pitch_type, str):
        return ""
    return "".join(ch for ch in pitch_type.lower() if ch.isalnum())


def get_pitch_color(pitch_type: str, default: str = DEFAULT_PITCH_COLOR) -> str:
    """
    Return the hex color for a given pitch type using the universal palette.
    """
    key = _normalize_pitch_type(pitch_type)
    return _BASE_PITCH_COLORS.get(key, default)


def get_pitch_color_map(
    pitch_types: Iterable[str], default: str = DEFAULT_PITCH_COLOR
) -> Dict[str, str]:
    """
    Build a Plotly/Matplotlib-friendly mapping from the provided pitch type labels
    to the universal palette colors.
    """
    return {
        pt: get_pitch_color(pt, default)
        for pt in pitch_types
        if isinstance(pt, str)
    }

