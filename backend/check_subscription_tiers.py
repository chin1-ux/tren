#!/usr/bin/env python3
"""
Check subscription tiers configuration
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
print("SUBSCRIPTION TIERS CHECK")
print("=" * 80)

res = sb.table('subscription_tiers').select('*').execute()
tiers = res.data

print(f"\nTotal subscription tiers: {len(tiers)}")

for tier in tiers:
    name = tier.get('name', 'N/A')
    delay_hours = tier.get('data_delay_hours', 0)
    print(f"\n{name}:")
    print(f"  Data delay hours: {delay_hours}")
    print(f"  Description: {tier.get('description', 'N/A')}")

print("\n" + "=" * 80)