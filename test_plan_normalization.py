"""
Test: Credits-based plan enforcement
Verifies free/pro plans, credit deduction, and feature access.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))


def test_plan_values():
    """Plans are now just 'free' and 'pro'."""
    from plan_enforcement import PlanEnforcement

    # get_user_plan returns 'free' for guests
    assert PlanEnforcement.get_user_plan("guest@trendrop.app") == "free"
    print("  [OK] Guest plan is 'free'")


def test_paid_features_use_pro():
    """All PAID_FEATURES should list only 'pro'."""
    from plan_enforcement import PlanEnforcement

    for feature, plans in PlanEnforcement.PAID_FEATURES.items():
        assert plans == ['pro'], f"{feature} has unexpected plans: {plans}"
    print("  [OK] All PAID_FEATURES use ['pro']")


def test_brand_deals_config_keys():
    """BRAND_DEALS_CONFIG should have 'free' and 'pro' keys only."""
    from plan_enforcement import PlanEnforcement

    keys = set(PlanEnforcement.BRAND_DEALS_CONFIG.keys())
    assert keys == {'free', 'pro'}, f"Unexpected keys: {keys}"
    assert PlanEnforcement.BRAND_DEALS_CONFIG['free']['delay_hours'] == 48
    assert PlanEnforcement.BRAND_DEALS_CONFIG['pro']['delay_hours'] == 0
    print("  [OK] BRAND_DEALS_CONFIG has free/pro keys with correct delays")


def test_credit_costs():
    """CREDIT_COSTS should have the three expected entries."""
    from plan_enforcement import CREDIT_COSTS

    assert CREDIT_COSTS['ai_generation'] == 5
    assert CREDIT_COSTS['video_analysis'] == 10
    assert CREDIT_COSTS['export'] == 2
    print("  [OK] CREDIT_COSTS: ai=5, video=10, export=2")


def test_no_normalize_plan_name():
    """normalize_plan_name should not exist."""
    from plan_enforcement import PlanEnforcement

    assert not hasattr(PlanEnforcement, 'normalize_plan_name'), "normalize_plan_name should be removed"
    assert not hasattr(PlanEnforcement, 'to_display_plan_name'), "to_display_plan_name should be removed"
    print("  [OK] normalize_plan_name and to_display_plan_name removed")


if __name__ == "__main__":
    print("\n=== Credits Plan Enforcement Tests ===\n")
    test_plan_values()
    test_paid_features_use_pro()
    test_brand_deals_config_keys()
    test_credit_costs()
    test_no_normalize_plan_name()
    print("\nAll tests passed.")
