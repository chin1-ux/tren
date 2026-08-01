from __future__ import annotations


def calculate_opportunity_score(*, india_saturation_pct: float, window_hours_remaining: float, confidence: float) -> float:
    """
    Shared opportunity score calculation for trend rows.
    """
    sat_factor = max(0.0, (100.0 - float(india_saturation_pct or 0.0)) / 100.0)
    win_factor = max(0.0, float(window_hours_remaining or 0.0) / 24.0)
    conf = max(0.0, float(confidence or 0.0))
    return round(((sat_factor * 60.0) + (win_factor * 40.0)) * conf, 1)

