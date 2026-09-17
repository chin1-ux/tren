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

# View-Velocity Outlier constants (3-Tier Detector)
VIEW_VELOCITY_UNTRACKED_MIN_VIEWS = 50000     # Tier 3 floor: 50,000 views for untracked / micro-creators (<1k followers)
VIEW_VELOCITY_HEURISTIC_MIN_VIEWS = 20000     # Tier 2 floor: 20,000 view floor for heuristic baselines (1k-10k followers)
VIEW_VELOCITY_HEURISTIC_REACH_MULT = 15.0     # Tier 2 reach multiplier: 15x follower count


