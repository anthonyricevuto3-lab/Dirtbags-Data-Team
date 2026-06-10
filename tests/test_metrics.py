"""
Unit tests for metrics library.
"""

import pytest
import pandas as pd
import numpy as np
from src.metrics import (
    calculate_usage_rate,
    calculate_strike_rate,
    calculate_whiff_rate,
    calculate_zone_rate,
    calculate_ivb_avg,
    calculate_hb_avg,
    generate_arsenal_summary,
)


@pytest.fixture
def sample_trackman_data():
    """Create sample Trackman DataFrame for testing."""
    data = {
        'pitch_type': ['Fastball', 'Fastball', 'Slider', 'Slider', 'Fastball'],
        'pitch_number': [1, 2, 3, 4, 5],
        'pitcher_id': ['P1', 'P1', 'P1', 'P1', 'P1'],
        'batter_id': ['B1', 'B1', 'B1', 'B1', 'B1'],
        'inning': [1, 1, 1, 1, 1],
        'balls': [0, 1, 1, 2, 2],
        'strikes': [0, 0, 1, 1, 2],
        'outs': [0, 0, 0, 0, 0],
        'pitch_call': ['StrikeCalled', 'BallCalled', 'InPlay', 'StrikeSwinging', 'BallCalled'],
        'strike': [True, False, True, True, False],
        'swing': [False, False, True, True, False],
        'whiff': [False, False, False, True, False],
        'velocity': [92.5, 91.8, 82.3, 81.5, 90.2],
        'spin_rate': [2200, 2150, 2400, 2350, 2180],
        'ivb': [12.5, 11.8, -5.2, -4.8, 12.1],
        'hb': [8.2, 7.9, 12.5, 13.1, 8.0],
        'extension': [6.2, 6.1, 5.8, 5.9, 6.0],
        'release_height': [5.8, 5.7, 5.6, 5.5, 5.7],
        'release_side': [-2.1, -2.0, -2.2, -2.1, -2.0],
        'plate_x': [0.5, -1.2, 0.8, 1.1, -0.9],
        'plate_z': [2.1, 1.8, 1.5, 1.9, 2.0],
        'zone': [5, 0, 4, 6, 0],
        'launch_angle': [np.nan, np.nan, 8.5, np.nan, np.nan],
        'exit_velocity': [np.nan, np.nan, 95.2, np.nan, np.nan],
        'hit_type': [np.nan, np.nan, 'GroundBall', np.nan, np.nan],
        'spray_angle': [np.nan, np.nan, -25.0, np.nan, np.nan],
        'distance': [np.nan, np.nan, 120.0, np.nan, np.nan],
    }
    return pd.DataFrame(data)


def test_usage_rate(sample_trackman_data):
    """Test usage rate calculation."""
    # Fastball: 3/5 = 60%
    assert calculate_usage_rate(sample_trackman_data, 'Fastball') == pytest.approx(60.0)
    # Slider: 2/5 = 40%
    assert calculate_usage_rate(sample_trackman_data, 'Slider') == pytest.approx(40.0)


def test_strike_rate(sample_trackman_data):
    """Test strike rate calculation."""
    # Fastball: 2 strikes / 3 pitches = 66.7%
    fastball_strike_rate = calculate_strike_rate(sample_trackman_data, 'Fastball')
    assert fastball_strike_rate == pytest.approx(66.67, abs=0.1)
    
    # Slider: 2 strikes / 2 pitches = 100%
    slider_strike_rate = calculate_strike_rate(sample_trackman_data, 'Slider')
    assert slider_strike_rate == pytest.approx(100.0)


def test_whiff_rate(sample_trackman_data):
    """Test whiff rate calculation."""
    # Fastball: 0 whiffs / 0 swings = NaN
    fastball_whiff = calculate_whiff_rate(sample_trackman_data, 'Fastball')
    assert pd.isna(fastball_whiff)
    
    # Slider: 1 whiff / 2 swings = 50%
    slider_whiff = calculate_whiff_rate(sample_trackman_data, 'Slider')
    assert slider_whiff == pytest.approx(50.0)


def test_zone_rate(sample_trackman_data):
    """Test zone rate calculation."""
    # Fastball: 1 zone pitch / 3 pitches = 33.3%
    fastball_zone = calculate_zone_rate(sample_trackman_data, 'Fastball')
    assert fastball_zone == pytest.approx(33.33, abs=0.1)


def test_movement_metrics(sample_trackman_data):
    """Test movement metric calculations."""
    # Fastball IVB average
    fastball_ivb = calculate_ivb_avg(sample_trackman_data, 'Fastball')
    assert fastball_ivb == pytest.approx(12.13, abs=0.1)
    
    # Fastball HB average
    fastball_hb = calculate_hb_avg(sample_trackman_data, 'Fastball')
    assert fastball_hb == pytest.approx(8.03, abs=0.1)


def test_arsenal_summary(sample_trackman_data):
    """Test arsenal summary generation."""
    summary = generate_arsenal_summary(sample_trackman_data)
    
    assert len(summary) == 2  # Fastball and Slider
    assert 'Pitch Type' in summary.columns
    assert 'Usage%' in summary.columns
    assert 'Velocity AVG' in summary.columns

