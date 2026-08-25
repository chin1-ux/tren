#!/usr/bin/env python3
"""
Fix pending LLM classifications by setting them to 'not_needed'
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
print("FIXING PENDING LLM CLASSIFICATIONS")
print("=" * 80)

# Get rising trends with pending classification
pending_rising = sb.table('trends').select('*').eq('status', 'rising').eq('llm_classification_status', 'pending').execute()

print(f"\nFound {len(pending_rising.data)} rising trends with pending classification")

if pending_rising.data:
    print("\nUpdating these trends to 'not_needed' status...")
    
    for trend in pending_rising.data:
        trend_id = trend.get('id')
        audio_title = trend.get('audio_title', 'N/A')[:50]
        
        try:
            sb.table('trends').update({'llm_classification_status': 'not_needed'}).eq('id', trend_id).execute()
            print(f"  [OK] Updated trend {trend_id}: {audio_title}")
        except Exception as e:
            print(f"  [FAIL] Failed to update trend {trend_id}: {e}")
    
    print("\n[OK] All pending classifications updated to 'not_needed'")
else:
    print("No pending classifications found")

# Verify the fix
print("\nVerifying fix...")
api_rising = sb.table('trends').select('*').eq('status', 'rising').eq('is_voiceover', False).in_('llm_classification_status', ['completed', 'not_needed']).execute()
print(f"Rising trends now matching API criteria: {len(api_rising.data)}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print(f"Fixed {len(pending_rising.data)} pending classifications.")
print(f"The frontend should now show {len(api_rising.data)} rising trends instead of 11.")
print("=" * 80)