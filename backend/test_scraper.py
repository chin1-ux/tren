#!/usr/bin/env python3
"""
Manual scraper test - test if scraper works locally
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Check required environment variables
required_vars = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'GROQ_API_KEY',
    'INSTAGRAM_USERNAME',
    'INSTAGRAM_PASSWORD'
]

print("=" * 60)
print("SCRAPER ENVIRONMENT CHECK")
print("=" * 60)

missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"[OK] {var}: SET")
    else:
        print(f"[MISSING] {var}: NOT SET")
        missing_vars.append(var)

if missing_vars:
    print(f"\nERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Scraper cannot run without these variables.")
    sys.exit(1)

print("\n" + "=" * 60)
print("TESTING INSTAGRAM SCRAPER")
print("=" * 60)

try:
    from instagram_scraper_browser import InstagramScraper
    print("\n1. Initializing Instagram scraper...")
    scraper = InstagramScraper()
    print("   [OK] Scraper initialized")

    print("\n2. Testing scrape (scraping 5 reels)...")
    result = scraper.scrape_trending_reels()
    print(f"   [OK] Scraped {result} reels")

    print("\n" + "=" * 60)
    print("SCRAPER TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)

except Exception as e:
    print(f"\n[ERROR] Scraper test failed: {e}")
    import traceback
    traceback.print_exc()
    print("\n" + "=" * 60)
    print("SCRAPER TEST FAILED")
    print("=" * 60)
    sys.exit(1)