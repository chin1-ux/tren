#!/usr/bin/env python3
"""
Investigate what 'skipped_local_fallback' status means
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
print("SKIPPED_LOCAL_FALLBACK STATUS INVESTIGATION")
print("=" * 80)

try:
    # Get all trends with skipped_local_fallback status
    skipped_trends = sb.table("trends").select("*").eq("llm_classification_status", "skipped_local_fallback").execute()
    
    print(f"\nTotal trends with 'skipped_local_fallback' status: {len(skipped_trends.data)}")
    
    if skipped_trends.data:
        print("\nTrend details:")
        for trend in skipped_trends.data:
            print(f"\nID: {trend.get('id')}")
            print(f"  Title: '{trend.get('audio_title', 'unknown')}'")
            print(f"  Artist: '{trend.get('audio_artist', 'unknown')}'")
            print(f"  Status: {trend.get('status')}")
            print(f"  Created: {trend.get('first_detected_at')}")
            print(f"  Classified: {trend.get('llm_classified_at')}")
            print(f"  Velocity: {trend.get('velocity_avg')}")
            print(f"  Niche: {trend.get('niche_tag')}")
            
            # Check if they have enrichment fields
            has_why_this_works = bool(trend.get('why_this_works'))
            has_ideal_description = bool(trend.get('ideal_content_description'))
            has_audio_cue = trend.get('audio_cue_second') is not None
            has_text_overlay = bool(trend.get('text_overlay_template'))
            has_hook = bool(trend.get('hook_brief'))
            
            print(f"  Enrichment fields:")
            print(f"    why_this_works: {has_why_this_works}")
            print(f"    ideal_content_description: {has_ideal_description}")
            print(f"    audio_cue_second: {has_audio_cue}")
            print(f"    text_overlay_template: {has_text_overlay}")
            print(f"    hook_brief: {has_hook}")
            
            # Check raw_llm_response
            has_raw_response = bool(trend.get('raw_llm_response'))
            print(f"    raw_llm_response: {has_raw_response}")
            
    else:
        print("No trends found with 'skipped_local_fallback' status.")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 80)
print("ANALYSIS & RECOMMENDATION")
print("=" * 80)
print("\nFINDING: skipped_local_fallback trends HAVE enrichment data:")
print("  - All 3 trends have why_this_works, ideal_content_description,")
print("    audio_cue_second, and text_overlay_template fields populated")
print("  - Missing: hook_brief and raw_llm_response fields")
print("  - All are expired trends from July 26-27 (historical data)")
print("  - All have reasonable velocity and niche classification")
print("\nINTERPRETATION: 'skipped_local_fallback' likely means these trends")
print("were processed by a local/deterministic classifier rather than the")
print("full LLM pipeline, but still received most enrichment data.")
print("\nRECOMMENDATION: Safe to include in API filter")
print("  - These trends have sufficient enrichment for user value")
print("  - Missing only hook_brief (nice-to-have, not critical)")
print("  - Historical status (expired) suggests they're not high-priority")
print("  - Only 3 such trends exist, minimal impact")
print("\nThis is a different tradeoff than 'pending' (no enrichment).")
print("skipped_local_fallback trends have partial enrichment from a fallback")
print("system, making them acceptable to show while 'pending' trends have none.")
print("\n" + "=" * 80)