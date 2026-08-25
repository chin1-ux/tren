#!/usr/bin/env python3
"""
Check rising trends by classification status
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
print("RISING TRENDS BY CLASSIFICATION STATUS")
print("=" * 80)

# Get all rising trends
all_rising = sb.table('trends').select('*').eq('status', 'rising').execute()
print(f"\nTotal rising trends: {len(all_rising.data)}")

# Get rising trends with proper classification
proper_rising = sb.table('trends').select('*').eq('status', 'rising').in_('llm_classification_status', ['completed', 'not_needed']).execute()
print(f"Rising trends with proper classification: {len(proper_rising.data)}")

# Get rising trends with is_voiceover=False
non_voiceover = sb.table('trends').select('*').eq('status', 'rising').eq('is_voiceover', False).execute()
print(f"Rising trends that are not voiceovers: {len(non_voiceover.data)}")

# Get rising trends that match both conditions (what the API returns)
api_rising = sb.table('trends').select('*').eq('status', 'rising').eq('is_voiceover', False).in_('llm_classification_status', ['completed', 'not_needed']).execute()
print(f"Rising trends matching API criteria: {len(api_rising.data)}")

# Show classification status breakdown
print("\nClassification status breakdown:")
from collections import Counter
status_counts = Counter([t.get('llm_classification_status', 'unknown') for t in all_rising.data])
for status, count in status_counts.items():
    print(f"  {status}: {count}")

# Show voiceover breakdown
print("\nVoiceover breakdown:")
voiceover_counts = Counter([t.get('is_voiceover', False) for t in all_rising.data])
for is_vo, count in voiceover_counts.items():
    print(f"  is_voiceover={is_vo}: {count}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print(f"The API returns {len(api_rising.data)} rising trends because of filtering criteria:")
print("1. status = 'rising'")
print("2. is_voiceover = False")
print("3. llm_classification_status in ['completed', 'not_needed']")
print(f"\nWithout these filters, there are {len(all_rising.data)} rising trends total.")
print("=" * 80)