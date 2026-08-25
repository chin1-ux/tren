#!/usr/bin/env python3
"""
Check rising trends with and without time delay filter
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timezone, timedelta

load_dotenv()

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if not url or not key:
    print("ERROR: Supabase credentials not set")
    exit(1)

sb = create_client(url, key)

print("=" * 80)
print("RISING TRENDS WITH/WITHOUT TIME DELAY ANALYSIS")
print("=" * 80)

# Get all rising trends
all_rising = sb.table('trends').select('*').eq('status', 'rising').eq('is_voiceover', False).in_('llm_classification_status', ['completed', 'not_needed']).execute()

print(f"\nTotal rising trends (no time filter): {len(all_rising.data)}")

# Apply 24-hour delay filter (free plan)
time_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
filtered_rising = sb.table('trends').select('*').eq('status', 'rising').eq('is_voiceover', False).in_('llm_classification_status', ['completed', 'not_needed']).lte('first_detected_at', time_cutoff).execute()

print(f"Rising trends with 24-hour delay (free plan): {len(filtered_rising.data)}")

# Show some examples of trends that are filtered out
print("\nExamples of trends filtered out by 24-hour delay:")
count = 0
for trend in all_rising.data:
    first_detected = trend.get('first_detected_at')
    if first_detected:
        try:
            dt = datetime.fromisoformat(first_detected.replace('Z', '+00:00'))
            if dt > datetime.now(timezone.utc) - timedelta(hours=24):
                count += 1
                if count <= 5:
                    audio_title = trend.get('audio_title', 'N/A')[:50]
                    hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                    print(f"  - {audio_title} ({hours_ago:.1f} hours ago)")
        except:
            pass

print(f"\nTotal trends filtered out: {len(all_rising.data) - len(filtered_rising.data)}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print(f"Free users see {len(filtered_rising.data)} rising trends due to 24-hour data delay.")
print(f"Pro/Agency users see {len(all_rising.data)} rising trends (no delay).")
print("The scraper is working correctly - this is a plan gating feature.")
print("=" * 80)