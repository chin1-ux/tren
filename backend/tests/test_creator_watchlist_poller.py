import pytest
from creator_watchlist_poller import (
    classify_creator_tier,
    evaluate_creator_outlier_virality,
    poll_creator_watchlist,
    CREATOR_OUTLIER_VIEW_MULTIPLIER,
    CREATOR_OUTLIER_MIN_VIEWS
)


def test_classify_creator_tier_boundaries():
    """Verify strict inclusive/exclusive follower boundary tier classifications."""
    # Tier 1 (Mid-Tier): 10,000 <= fc < 100,000
    assert classify_creator_tier(10000) == "tier_1_mid"
    assert classify_creator_tier(99999) == "tier_1_mid"

    # Tier 3a (Macro/Mega): fc >= 100,000
    assert classify_creator_tier(100000) == "tier_3a_macro"
    assert classify_creator_tier(500000) == "tier_3a_macro"

    # Tier 2 (Micro): 1,000 <= fc < 10,000
    assert classify_creator_tier(1000) == "tier_2_micro"
    assert classify_creator_tier(9999) == "tier_2_micro"

    # Tier 3b (Nano): fc < 1,000 or None/0
    assert classify_creator_tier(999) == "tier_3b_nano"
    assert classify_creator_tier(0) == "tier_3b_nano"
    assert classify_creator_tier(None) == "tier_3b_nano"


def test_outlier_virality_evaluation_exact_multiplier_boundary():
    """Exact 3.0x multiplier boundary check: 3,000 views on 1,000 median passes; 2,999 fails."""
    baseline = {"median_views": 1000.0}

    # Exact 3.0x boundary passes
    reel_exact = {"view_count": 3000}
    assert evaluate_creator_outlier_virality(reel_exact, baseline) is True

    # 2.999x boundary fails
    reel_below = {"view_count": 2999}
    assert evaluate_creator_outlier_virality(reel_below, baseline) is False


def test_outlier_virality_evaluation_exact_floor_boundary():
    """Exact 1,000 view floor boundary check: 1,000 views passes; 999 views fails even if ratio >= 3x."""
    baseline = {"median_views": 200.0}  # 3.0x median = 600 views

    # Ratio is 5.0x (1,000 / 200), views = 1,000 (meets floor) -> passes
    reel_floor_exact = {"view_count": 1000}
    assert evaluate_creator_outlier_virality(reel_floor_exact, baseline) is True

    # Ratio is 4.995x (999 / 200), views = 999 (fails 1,000 floor) -> fails
    reel_floor_below = {"view_count": 999}
    assert evaluate_creator_outlier_virality(reel_floor_below, baseline) is False


def test_outlier_virality_evaluation_zero_median_views():
    """Creators with median_views <= 0 (insufficient baseline data) MUST return False."""
    baseline_zero = {"median_views": 0.0}
    baseline_none = {"median_views": None}

    reel_high_views = {"view_count": 50000}

    # Must return False (insufficient baseline data to compute multiplier)
    assert evaluate_creator_outlier_virality(reel_high_views, baseline_zero) is False
    assert evaluate_creator_outlier_virality(reel_high_views, baseline_none) is False


def test_watchlist_slot_allocation_with_spillover_tier1_shortfall():
    """
    Slot Spillover Test 1: Tier 1 has 3 creators due, Tier 2 has 20 creators due.
    Target limit = 15. Tier 1 gets 3 slots, Tier 2 gets 12 slots via spillover (total 15).
    """
    class MockSupabase:
        def table(self, name):
            return MockQueryBuilder(name)

    class MockQueryBuilder:
        def __init__(self, name):
            self.name = name
            self.tier = None

        def select(self, *args, **kwargs):
            return self

        def eq(self, col, val):
            if col == "watchlist_tier":
                self.tier = val
            return self

        def limit(self, val):
            return self

        def execute(self):
            if self.tier == "tier_1_mid":
                data = [{"username": f"t1_user_{i}"} for i in range(3)]
            elif self.tier == "tier_2_micro":
                data = [{"username": f"t2_user_{i}"} for i in range(20)]
            else:
                data = []
            return MockResult(data)

    class MockResult:
        def __init__(self, data):
            self.data = data

    mock_sb = MockSupabase()
    selected = poll_creator_watchlist(mock_sb, limit=15)

    assert len(selected) == 15
    t1_selected = [c for c in selected if c["username"].startswith("t1_")]
    t2_selected = [c for c in selected if c["username"].startswith("t2_")]

    assert len(t1_selected) == 3
    assert len(t2_selected) == 12


def test_watchlist_slot_allocation_with_spillover_tier2_shortfall():
    """
    Slot Spillover Test 2: Tier 1 has 15 creators due, Tier 2 has 2 creators due.
    Target limit = 15. Tier 2 gets 2 slots, Tier 1 gets 13 slots via spillover (total 15).
    """
    class MockSupabase:
        def table(self, name):
            return MockQueryBuilder(name)

    class MockQueryBuilder:
        def __init__(self, name):
            self.name = name
            self.tier = None

        def select(self, *args, **kwargs):
            return self

        def eq(self, col, val):
            if col == "watchlist_tier":
                self.tier = val
            return self

        def limit(self, val):
            return self

        def execute(self):
            if self.tier == "tier_1_mid":
                data = [{"username": f"t1_user_{i}"} for i in range(15)]
            elif self.tier == "tier_2_micro":
                data = [{"username": f"t2_user_{i}"} for i in range(2)]
            else:
                data = []
            return MockResult(data)

    class MockResult:
        def __init__(self, data):
            self.data = data

    mock_sb = MockSupabase()
    selected = poll_creator_watchlist(mock_sb, limit=15)

    assert len(selected) == 15
    t1_selected = [c for c in selected if c["username"].startswith("t1_")]
    t2_selected = [c for c in selected if c["username"].startswith("t2_")]

    assert len(t1_selected) == 13
    assert len(t2_selected) == 2
