#!/usr/bin/env python3
"""
Test Camoufox browser initialization with addons disabled
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

print("=" * 80)
print("CAMOUFOX BROWSER INITIALIZATION TEST")
print("=" * 80)

try:
    from camoufox.async_api import AsyncCamoufox as CamoufoxBrowser
    print("\n[OK] Camoufox imported successfully")
except ImportError as e:
    print(f"\n[ERROR] Camoufox not installed: {e}")
    exit(1)

async def test_browser_init():
    print("\nTesting browser initialization with addons=None...")
    try:
        cm = CamoufoxBrowser(headless=True, geoip=False, addons=None)
        browser = await cm.__aenter__()
        print("[OK] Browser initialized successfully with addons=None")
        
        # Test creating a context
        ctx = await browser.new_context(no_viewport=True)
        print("[OK] Browser context created successfully")
        
        # Clean up
        await ctx.close()
        await cm.__aexit__(None, None, None)
        print("[OK] Browser closed successfully")
        
        return True
    except Exception as e:
        print(f"[ERROR] Browser initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run the test
result = asyncio.run(test_browser_init())

print("\n" + "=" * 80)
if result:
    print("CONCLUSION: Camoufox fix is working correctly")
else:
    print("CONCLUSION: Camoufox fix needs further investigation")
print("=" * 80)