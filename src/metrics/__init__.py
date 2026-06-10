"""
Shared metrics library for Dirtbags Data Team.

This module provides transparent, reproducible, and explainable metrics
for pitch analysis, plate discipline, contact outcomes, and more.
"""

from .pitch_metrics import (
    calculate_usage_rate,
    calculate_strike_rate,
    calculate_whiff_rate,
    calculate_zone_rate,
    calculate_chase_rate,
    calculate_swing_rate,
    calculate_putaway_proxy,
)

from .movement_metrics import (
    calculate_ivb_avg,
    calculate_hb_avg,
    calculate_spin_avg,
    calculate_extension_avg,
    calculate_velocity_avg,
    calculate_velocity_max,
    calculate_release_height_avg,
    calculate_release_side_avg,
)

from .contact_metrics import (
    calculate_contact_outcomes,
    calculate_spray_distribution,
    calculate_launch_angle_avg,
    calculate_exit_velocity_avg,
)

from .arsenal_summary import (
    generate_arsenal_summary,
    generate_plate_discipline_summary,
    generate_contact_summary,
)

from .inning_success_metrics import (
    compute_inning_success_metrics,
    compute_pa_win_pct_by_inning,
    compute_whiff_pct_by_inning,
    compute_weak_contact_pct_by_inning,
    compute_run_prevention_pct_by_inning,
    compute_dominance_pct_by_inning,
    compute_inning_success_pct,
)

__all__ = [
    # Pitch metrics
    'calculate_usage_rate',
    'calculate_strike_rate',
    'calculate_whiff_rate',
    'calculate_zone_rate',
    'calculate_chase_rate',
    'calculate_swing_rate',
    'calculate_putaway_proxy',
    # Movement metrics
    'calculate_ivb_avg',
    'calculate_hb_avg',
    'calculate_spin_avg',
    'calculate_extension_avg',
    'calculate_velocity_avg',
    'calculate_velocity_max',
    'calculate_release_height_avg',
    'calculate_release_side_avg',
    # Contact metrics
    'calculate_contact_outcomes',
    'calculate_spray_distribution',
    'calculate_launch_angle_avg',
    'calculate_exit_velocity_avg',
    # Summary generators
    'generate_arsenal_summary',
    'generate_plate_discipline_summary',
    'generate_contact_summary',
    # Inning success metrics
    'compute_inning_success_metrics',
    'compute_pa_win_pct_by_inning',
    'compute_whiff_pct_by_inning',
    'compute_weak_contact_pct_by_inning',
    'compute_run_prevention_pct_by_inning',
    'compute_dominance_pct_by_inning',
    'compute_inning_success_pct',
]

