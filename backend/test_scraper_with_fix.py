#!/usr/bin/env python3
"""
Test scraper with Camoufox fix applied
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("SCRAPER TEST WITH CAMOUFOX FIX")
print("=" * 80)

# Check required environment variables
required_vars = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'GROQ_API_KEY',
    'INSTAGRAM_USERNAME',
    'INSTAGRAM_PASSWORD'
]

print("\n1. Checking environment variables...")
missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        print(f"   [OK] {var}: SET")
    else:
        print(f"   [MISSING] {var}: NOT SET")
        missing_vars.append(var)

if missing_vars:
    print(f"\nERROR: Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

print("\n2. Testing scraper initialization...")
try:
    from instagram_scraper_browser import InstagramScraper
    print("   [OK] InstagramScraper imported")
    
    scraper = InstagramScraper()
    print("   [OK] Scraper initialized")
    
    print("\n3. Testing browser initialization...")
    # Test async browser init
    import asyncio
    
    async def test_browser():
        try:
            success = await scraper._init_browser_async()
            if success:
                print("   [OK] Browser initialized successfully")
                await scraper._close_browser_async()
                print("   [OK] Browser closed successfully")
                return True
            else:
                print("   [ERROR] Browser initialization failed")
                return False
        except Exception as e:
            print(f"   [ERROR] Browser test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    result = asyncio.run(test_browser())
    
    if result:
        print("\n" + "=" * 80)
        print("CONCLUSION: Scraper with Camoufox fix is working correctly")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("CONCLUSION: Scraper test failed - further investigation needed")
        print("=" * 80)
        sys.exit(1)
        
except Exception as e:
    print(f"\nERROR: Scraper test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)