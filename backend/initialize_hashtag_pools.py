#!/usr/bin/env python3
"""
Initialize micro-creator hashtag pools in the database
"""

from dynamic_hashtag_discovery import hashtag_discovery

print("Initializing micro-creator hashtag pools...")
result = hashtag_discovery.initialize_hashtag_pools()

if result.get('success'):
    print(f"[PASS] Hashtag pools initialized successfully!")
    print(f"Added: {result['added_count']} hashtags")
    print(f"Skipped: {result['skipped_count']} existing hashtags")
    print(f"Total: {result['total_hashtags']} hashtags")
else:
    print(f"[FAIL] Error initializing hashtag pools: {result.get('error')}")