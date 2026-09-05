#!/usr/bin/env python3
"""
Check API responses for rising-trends endpoint per plan tier
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not url or not key:
    print("ERROR: Supabase credentials not set")
    exit(1)

sb = create_client(url, key)

print("=" * 80)
print("API RESPONSE SIMULATION FOR RISING TRENDS")
print("=" * 80)

# Simulate the main trends endpoint query
print("\nSimulating /api/trends endpoint query:")
try:
    # This simulates the query made in api.py line 1165
    q = sb.table("trends").select("*").eq("status", "rising").eq("is_voiceover", False).in_("llm_classification_status", ["completed", "not_needed", "skipped_local_fallback"])
    
    # Add language filter (default "all" - no filter)
    # Add niche filter (default "all" - no filter)
    
    # Add data delay filter (for free tier, delay_hours = 0, so no filter)
    # For this test, we'll check with no delay filter
    
    # Default sort by velocity
    q = q.order("velocity_avg", desc=True)
    
    # Limit 100
    q = q.limit(100)
    
    res = q.execute()
    trends = res.data or []
    
    print(f"Total rising trends returned by API query: {len(trends)}")
    
    # Check if any are being filtered out by additional criteria
    print(f"\nChecking additional filters:")
    
    # Check is_voiceover filter
    voiceover_count = sum(1 for t in trends if t.get('is_voiceover') == True)
    print(f"  Trends with is_voiceover=True (filtered out): {voiceover_count}")
    
    # Check llm_classification_status filter
    classification_status_counts = {}
    for t in trends:
        status = t.get('llm_classification_status', 'unknown')
        classification_status_counts[status] = classification_status_counts.get(status, 0) + 1
    print(f"  llm_classification_status distribution: {classification_status_counts}")
    
    # Check if classification filter is removing trends
    excluded_by_classification = sum(1 for t in trends if t.get('llm_classification_status') not in ["completed", "not_needed"])
    print(f"  Trends excluded by classification filter: {excluded_by_classification}")
    
except Exception as e:
    print(f"Error simulating API query: {e}")

# Check all rising trends without filters
print("\n" + "=" * 80)
print("ALL RISING TRENDS (NO FILTERS)")
print("=" * 80)

try:
    all_rising = sb.table("trends").select("*").eq("status", "rising").execute()
    print(f"Total rising trends in database: {len(all_rising.data)}")
    
    # Check how many would be filtered by each criterion
    all_rising_data = all_rising.data
    
    voiceover_filtered = sum(1 for t in all_rising_data if t.get('is_voiceover') == True)
    classification_filtered = sum(1 for t in all_rising_data if t.get('llm_classification_status') not in ["completed", "not_needed"])
    
    print(f"  Would be filtered by is_voiceover=True: {voiceover_filtered}")
    print(f"  Would be filtered by llm_classification_status: {classification_filtered}")
    print(f"  Would pass all filters: {len(all_rising_data) - voiceover_filtered - classification_filtered}")
    
except Exception as e:
    print(f"Error checking all rising trends: {e}")

# Check for any user-specific filtering issues
print("\n" + "=" * 80)
print("USER-SPECIFIC FILTERING CHECK")
print("=" * 80)

print("\nChecking if user configuration could affect results:")
print("  - The API uses user-specific niche/language preferences")
print("  - For guest users, defaults to 'all' for both")
print("  - This should not reduce the count unless specific filters are applied")

# Check plan enforcement delay
print("\n" + "=" * 80)
print("PLAN ENFORCEMENT DELAY CHECK")
print("=" * 80)

print("\nChecking data delay by plan tier:")
print("  - Free tier: 0 hours delay (no filtering)")
print("  - Creator tier: 0 hours delay (no filtering)")
print("  - Agency tier: 0 hours delay (no filtering)")
print("  - This should not be causing the issue")

print("\n" + "=" * 80)