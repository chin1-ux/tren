"""
Test Plan Name Normalization
Tests that plan name normalization works correctly for both display and internal names
"""
import os
import sys
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

load_dotenv()

try:
    from plan_enforcement import PlanEnforcement
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_normalize_plan_name():
    """Test that plan names are normalized correctly"""
    print("=== Testing Plan Name Normalization ===")
    
    test_cases = [
        ("pro", "pro"),  # Internal name stays as-is
        ("business", "business"),  # Internal name stays as-is
        ("creator", "pro"),  # Display name converts to internal
        ("agency", "business"),  # Display name converts to internal
        ("free", "free"),  # Free stays as-is
        ("CREATOR", "pro"),  # Case-insensitive
        ("Agency", "business"),  # Case-insensitive
        ("invalid", "free"),  # Invalid name defaults to free
        (None, "free"),  # None defaults to free
        ("", "free"),  # Empty defaults to free
    ]
    
    all_passed = True
    for input_plan, expected_output in test_cases:
        result = PlanEnforcement.normalize_plan_name(input_plan)
        if result == expected_output:
            print(f"  [OK] {input_plan} → {result}")
        else:
            print(f"  [FAIL] {input_plan} → {result} (expected {expected_output})")
            all_passed = False
    
    return all_passed

def test_to_display_plan_name():
    """Test that internal names convert to display names correctly"""
    print("\n=== Testing Display Plan Name Conversion ===")
    
    test_cases = [
        ("pro", "creator"),  # Internal → display
        ("business", "agency"),  # Internal → display
        ("free", "free"),  # Free stays as-is
        ("creator", "creator"),  # Display name stays as-is
        ("agency", "agency"),  # Display name stays as-is
        ("PRO", "creator"),  # Case-insensitive
        ("invalid", "invalid"),  # Invalid name passes through
    ]
    
    all_passed = True
    for input_plan, expected_output in test_cases:
        result = PlanEnforcement.to_display_plan_name(input_plan)
        if result == expected_output:
            print(f"  [OK] {input_plan} → {result}")
        else:
            print(f"  [FAIL] {input_plan} → {result} (expected {expected_output})")
            all_passed = False
    
    return all_passed

def test_paid_features_uses_internal_names():
    """Test that PAID_FEATURES uses internal names"""
    print("\n=== Testing PAID_FEATURES Uses Internal Names ===")
    
    from plan_enforcement import PlanEnforcement
    
    # Check that PAID_FEATURES uses internal names (pro, business)
    all_features_use_internal = True
    for feature, allowed_plans in PlanEnforcement.PAID_FEATURES.items():
        for plan in allowed_plans:
            if plan not in ['pro', 'business']:
                print(f"  [FAIL] Feature {feature} has non-internal plan: {plan}")
                all_features_use_internal = False
    
    if all_features_use_internal:
        print("  [OK] All PAID_FEATURES use internal plan names (pro, business)")
    
    return all_features_use_internal

if __name__ == "__main__":
    test_normalize_plan_name()
    test_to_display_plan_name()
    test_paid_features_uses_internal_names()
    
    print("\n=== All Plan Normalization Tests Complete ===")
    print("\nNote: Plan name normalization allows:")
    print("- Database to store either internal (pro/business) or display (creator/agency) names")
    print("- Razorpay integration to use either naming convention")
    print("- User-facing displays to use creator/agency naming")
    print("- Internal logic to use pro/business naming for consistency")