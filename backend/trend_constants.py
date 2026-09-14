"""
Shared constants for trend detection, scoring, and lifecycle management.
"""

RISING_USE_THRESHOLD = 500000
EMERGING_USE_THRESHOLD = 150000
GLOBAL_SATURATION_THRESHOLD_REELS = 1000000

# Vintage audio & resurgence thresholds (configurable heuristics)
VINTAGE_CATALOG_AGE_DAYS = 365
VINTAGE_CATALOG_AGE_YEARS_FALLBACK = 2
RESURGENCE_VELOCITY_THRESHOLD = 3000

# Creator Outlier Virality constants (pending calibration against live watchlist data)
CREATOR_OUTLIER_VIEW_MULTIPLIER = 3.0  # 3.0x personal median views = early outlier virality signal
CREATOR_OUTLIER_MIN_VIEWS = 1000        # Minimum view floor to prevent false flags on low-view accounts

