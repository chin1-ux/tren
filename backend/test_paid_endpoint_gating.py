"""
Test Paid Endpoint Gating
Tests that free-tier users are rejected from paid endpoints
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
    from plan_enforcement import PlanEnforcement, require_feature
    from fastapi import HTTPException, status
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_feature_access_check():
    """Test that feature access check works correctly"""
    print("=== Testing Feature Access Check ===")
    
    # Test with free user trying to access paid feature
    free_user = "free@example.com"
    paid_feature = "unlimited_trends"
    
    try:
        PlanEnforcement.check_feature_access(free_user, paid_feature)
        print(f"  [FAIL] Free user {free_user} should not have access to {paid_feature}")
        return False
    except HTTPException as e:
        if e.status_code == 403:
            print(f"  [OK] Free user correctly rejected from {paid_feature} (403)")
            return True
        else:
            print(f"  [FAIL] Wrong status code: {e.status_code}")
            return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def test_require_feature_dependency():
    """Test that require_feature dependency works correctly"""
    print("\n=== Testing require_feature Dependency ===")
    
    # Test with guest user (should raise 401)
    try:
        from functools import partial
        from plan_enforcement import require_feature
        
        # Create a dependency function
        check_unlimited_trends = require_feature("unlimited_trends")
        
        # Test with guest user
        guest_user = "guest@trendrop.app"
        print(f"Testing with guest user: {guest_user}")
        
        # This should raise HTTPException 401
        try:
            check_unlimited_trends(guest_user)
            print("  [FAIL] Should have raised 401 for guest user")
            return False
        except HTTPException as e:
            if e.status_code == 401:
                print("  [OK] Correctly raised 401 for guest user")
                return True
            else:
                print(f"  [FAIL] Wrong status code: {e.status_code}")
                return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

def test_paid_features_mapping():
    """Test that PAID_FEATURES mapping is correct"""
    print("\n=== Testing PAID_FEATURES Mapping ===")
    
    from plan_enforcement import PlanEnforcement
    
    # Check that all expected features are in PAID_FEATURES
    expected_features = [
        'early_detection',
        'unlimited_trends',
        'ai_generation',
        'advanced_analytics',
        'india_features',
        'video_analysis',
        'team_features',
        'api_access',
        'priority_support'
    ]
    
    missing_features = []
    for feature in expected_features:
        if feature not in PlanEnforcement.PAID_FEATURES:
            missing_features.append(feature)
    
    if missing_features:
        print(f"  [FAIL] Missing features in PAID_FEATURES: {missing_features}")
        return False
    else:
        print(f"  [OK] All expected features are in PAID_FEATURES")
        return True

if __name__ == "__main__":
    test_feature_access_check()
    test_require_feature_dependency()
    test_paid_features_mapping()
    
    print("\n=== All Paid Endpoint Gating Tests Complete ===")
    print("\nNote: To fully test paid endpoint gating:")
    print("1. Create a free-tier user account")
    print("2. Attempt to access a paid endpoint (e.g., /api/trends/all-active)")
    print("3. Verify that request is rejected with 403 Forbidden")
    print("4. Upgrade user to paid plan")
    print("5. Verify that request succeeds with 200 OK")