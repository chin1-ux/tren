import pytest
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from trend_scoring import calculate_trend_state, TrendLifecycle
from trend_constants import RISING_USE_THRESHOLD, EMERGING_USE_THRESHOLD


def test_lifecycle_expired_by_time():
    """Trend with window_hours_remaining <= 0 must transition to EXPIRED."""
    state = calculate_trend_state(
        velocity_avg=5000.0,
        global_saturation_pct=10.0,
        india_saturation_pct=5.0,
        window_hours_remaining=0,
        audio_use_count=100000,
        confidence=0.9,
        max_velocity=6000.0,
        discovery_source="regional",
        unique_creators=5,
    )
    assert state.lifecycle == TrendLifecycle.EXPIRED


def test_lifecycle_expired_by_saturation():
    """Trend with global_saturation_pct >= 90 must transition to EXPIRED."""
    state = calculate_trend_state(
        velocity_avg=5000.0,
        global_saturation_pct=92.0,
        india_saturation_pct=85.0,
        window_hours_remaining=24,
        audio_use_count=1000000,
        confidence=0.9,
        max_velocity=6000.0,
        discovery_source="regional",
        unique_creators=5,
    )
    assert state.lifecycle == TrendLifecycle.EXPIRED


def test_lifecycle_peaked():
    """High saturation/use_count with declining velocity must transition to PEAKED."""
    state = calculate_trend_state(
        velocity_avg=100.0,
        global_saturation_pct=70.0,
        india_saturation_pct=60.0,
        window_hours_remaining=12,
        audio_use_count=6000000,
        confidence=0.85,
        max_velocity=200.0,
        discovery_source="regional",
        unique_creators=10,
    )
    assert state.lifecycle == TrendLifecycle.PEAKED


def test_lifecycle_rising_by_creator_adoption():
    """Accelerating/stable velocity with >= 3 creators must transition to RISING."""
    state = calculate_trend_state(
        velocity_avg=4000.0,
        global_saturation_pct=15.0,
        india_saturation_pct=10.0,
        window_hours_remaining=36,
        audio_use_count=50000,
        confidence=0.9,
        max_velocity=4500.0,
        discovery_source="regional",
        unique_creators=3,
    )
    assert state.lifecycle == TrendLifecycle.RISING


def test_lifecycle_rising_by_volume_threshold():
    """Use count >= RISING_USE_THRESHOLD with stable velocity must transition to RISING."""
    state = calculate_trend_state(
        velocity_avg=3500.0,
        global_saturation_pct=25.0,
        india_saturation_pct=20.0,
        window_hours_remaining=36,
        audio_use_count=RISING_USE_THRESHOLD + 1000,
        confidence=0.9,
        max_velocity=4000.0,
        discovery_source="regional",
        unique_creators=1,
    )
    assert state.lifecycle == TrendLifecycle.RISING


def test_lifecycle_emerging():
    """Early stage trend with >= 2 creators and low saturation must transition to EMERGING."""
    state = calculate_trend_state(
        velocity_avg=600.0,
        global_saturation_pct=5.0,
        india_saturation_pct=3.0,
        window_hours_remaining=48,
        audio_use_count=20000,
        confidence=0.8,
        max_velocity=800.0,
        discovery_source="regional",
        unique_creators=2,
    )
    assert state.lifecycle == TrendLifecycle.EMERGING


def test_lifecycle_unqualified():
    """Single creator with low velocity and low use count must transition to UNQUALIFIED."""
    state = calculate_trend_state(
        velocity_avg=50.0,
        global_saturation_pct=2.0,
        india_saturation_pct=1.0,
        window_hours_remaining=48,
        audio_use_count=1000,
        confidence=0.5,
        max_velocity=80.0,
        discovery_source="regional",
        unique_creators=1,
    )
    assert state.lifecycle == TrendLifecycle.UNQUALIFIED
