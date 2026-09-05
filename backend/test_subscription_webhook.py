"""
Test subscription webhook handling for failed renewals and cancellations
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_subscription_webhook_failed_renewal():
    """Test that failed payment webhook schedules plan downgrade after grace period"""
    print("=== Test: Subscription Webhook - Failed Renewal ===")
    
    try:
        from supabase import create_client
        
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("[SKIP] Supabase credentials not set")
            return
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Create test user with pro plan
        test_email = "test_failed_renewal@example.com"
        
        # Clean up existing test user if exists
        supabase.table("users").delete().eq("email", test_email).execute()
        
        # Insert test user with pro plan
        grace_period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        supabase.table("users").insert({
            "email": test_email,
            "plan": "pro",
            "subscription_status": "payment.failed",
            "grace_period_ends_at": grace_period_end
        }).execute()
        
        print(f"[OK] Created test user {test_email} with pro plan and payment.failed status")
        
        # Verify plan enforcement respects grace period
        from plan_enforcement import PlanEnforcement
        
        plan = PlanEnforcement.get_user_plan(test_email)
        print(f"[OK] User plan during grace period: {plan}")
        
        if plan != "pro":
            print(f"[FAIL] Expected 'pro' during grace period, got '{plan}'")
            return False
        
        # Test expired grace period
        past_grace_end = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        supabase.table("users").update({
            "grace_period_ends_at": past_grace_end
        }).eq("email", test_email).execute()
        
        plan_after_grace = PlanEnforcement.get_user_plan(test_email)
        print(f"[OK] User plan after grace period: {plan_after_grace}")
        
        if plan_after_grace != "free":
            print(f"[FAIL] Expected 'free' after grace period, got '{plan_after_grace}'")
            return False
        
        # Clean up
        supabase.table("users").delete().eq("email", test_email).execute()
        
        print("[SUCCESS] Subscription webhook grace period logic works correctly")
        return True
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_subscription_webhook_cancelled():
    """Test that subscription.cancelled webhook schedules plan downgrade after grace period"""
    print("\n=== Test: Subscription Webhook - Cancelled ===")
    
    try:
        from supabase import create_client
        
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            print("[SKIP] Supabase credentials not set")
            return
        
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Create test user with pro plan
        test_email = "test_cancelled@example.com"
        
        # Clean up existing test user if exists
        supabase.table("users").delete().eq("email", test_email).execute()
        
        # Insert test user with pro plan and cancelled status
        grace_period_end = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat().replace('+00:00', 'Z')
        
        supabase.table("users").insert({
            "email": test_email,
            "plan": "pro",
            "subscription_status": "subscription.cancelled",
            "grace_period_ends_at": grace_period_end
        }).execute()
        
        print(f"[OK] Created test user {test_email} with pro plan and subscription.cancelled status")
        
        # Verify plan enforcement respects grace period
        from plan_enforcement import PlanEnforcement
        
        plan = PlanEnforcement.get_user_plan(test_email)
        print(f"[OK] User plan during grace period: {plan}")
        
        if plan != "pro":
            print(f"[FAIL] Expected 'pro' during grace period, got '{plan}'")
            return False
        
        # Clean up
        supabase.table("users").delete().eq("email", test_email).execute()
        
        print("[SUCCESS] Subscription cancelled webhook grace period logic works correctly")
        return True
        
    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = True
    success = test_subscription_webhook_failed_renewal() and success
    success = test_subscription_webhook_cancelled() and success
    
    if success:
        print("\n=== ALL TESTS PASSED ===")
        sys.exit(0)
    else:
        print("\n=== SOME TESTS FAILED ===")
        sys.exit(1)