"""
Validate that trend state is internally consistent.
BLOCKS deployment on failure (user requirement).
"""

def validate_trend_state(trend: dict) -> list[str]:
    """Return list of consistency errors."""
    errors = []
    
    # Check: MEGA and UNDER_RADAR should be mutually exclusive
    if trend.get("is_mega") and trend.get("is_under_radar"):
        errors.append("Trend cannot be both MEGA and UNDER_RADAR")
    
    # Check: Urgency should align with velocity tier
    if trend.get("velocity_tier") == "accelerating" and trend.get("urgency") == "low":
        errors.append("Accelerating velocity should not have LOW urgency")
    
    # Check: Saturated trends should have LOW or MODERATE urgency
    if trend.get("saturation_tier") == "saturated" and trend.get("urgency") == "critical":
        errors.append("Saturated trend should not have CRITICAL urgency")
    
    # Check: Expired lifecycle should have LOW urgency
    if trend.get("lifecycle") == "expired" and trend.get("urgency") not in ["low", None]:
        errors.append("Expired trend should have LOW urgency")
    
    # Check: Expired lifecycle with early saturation is implausible
    if trend.get("lifecycle") == "expired" and trend.get("saturation_tier") == "early":
        errors.append("Expired trend cannot have early saturation (implausible combination)")
    
    return errors

def validate_all_trends() -> tuple[bool, int]:
    """Validate all trends in database. Returns (success, error_count)."""
    from supabase import create_client
    import os
    from dotenv import load_dotenv
    import sys
    
    load_dotenv()
    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
    
    res = sb.table("trends").select("*").execute()
    trends = res.data or []
    
    total_errors = 0
    for trend in trends:
        errors = validate_trend_state(trend)
        if errors:
            total_errors += len(errors)
            print(f"Trend {trend.get('id')} ({trend.get('audio_title')}): {errors}")
    
    print(f"\nTotal errors: {total_errors} / {len(trends)} trends")
    
    # BLOCK deployment if errors found
    if total_errors > 0:
        print("❌ VALIDATION FAILED - Deployment blocked")
        sys.exit(1)
    else:
        print("✅ VALIDATION PASSED")
        return True, 0

if __name__ == "__main__":
    validate_all_trends()
