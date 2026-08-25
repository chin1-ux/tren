#!/usr/bin/env python3
"""
Check scraper configuration and diagnose why it returns 0 reels
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("="*80)
print("SCRAPER CONFIGURATION CHECK")
print("="*80)

# Check required environment variables
print("\n1. Checking required environment variables...")
required_vars = [
    'SUPABASE_URL',
    'SUPABASE_KEY',
    'GROQ_API_KEY',
    'INSTAGRAM_USERNAME',
    'INSTAGRAM_PASSWORD',
    'INSTAGRAM_COOKIES_B64'
]

missing_vars = []
for var in required_vars:
    value = os.getenv(var)
    if value:
        # Show partial value for security
        if 'PASSWORD' in var or 'KEY' in var or 'COOKIES' in var:
            print(f"   [OK] {var}: SET (length: {len(value)})")
        else:
            print(f"   [OK] {var}: {value}")
    else:
        print(f"   [MISSING] {var}: NOT SET")
        missing_vars.append(var)

if missing_vars:
    print(f"\n   ERROR: Missing required environment variables: {', '.join(missing_vars)}")
else:
    print("\n   All required environment variables are set")

# Check scraper mode
print("\n2. Checking scraper mode...")
scraper_mode = os.getenv("SCRAPER_MODE", "india")
print(f"   Current mode: {scraper_mode}")

# Check hashtag override
print("\n3. Checking hashtag override...")
hashtag_override = os.getenv("SCRAPER_HASHTAGS", "")
if hashtag_override:
    print(f"   Custom hashtags: {hashtag_override}")
else:
    print("   Using default hashtag pools")

# Check LLM keys
print("\n4. Checking LLM keys...")
groq_keys = sum(1 for key in ["GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"] if os.getenv(key))
gemini_keys = sum(1 for key in ["GEMINI_API_KEY", "GEMINI_API_KEY_2"] if os.getenv(key))
print(f"   GROQ keys: {groq_keys}")
print(f"   Gemini keys: {gemini_keys}")

# Check cookies file
print("\n5. Checking Instagram cookies file...")
cookies_file = "backend/cookies.json"
if os.path.exists(cookies_file):
    file_size = os.path.getsize(cookies_file)
    print(f"   [OK] Cookies file exists (size: {file_size} bytes)")
else:
    print(f"   [MISSING] Cookies file does not exist: {cookies_file}")

# Check Camoufox installation
print("\n6. Checking Camoufox installation...")
try:
    import camoufox
    print("   [OK] Camoufox is installed")
except ImportError:
    print("   [MISSING] Camoufox is not installed")

print("\n" + "="*80)
print("CONFIGURATION CHECK COMPLETE")
print("="*80)

print("\nDIAGNOSIS:")
print("-" * 80)

if missing_vars:
    print("1. Missing environment variables - scraper cannot run")
elif not os.path.exists(cookies_file):
    print("1. Cookies file missing - scraper cannot authenticate with Instagram")
elif groq_keys == 0 and gemini_keys == 0:
    print("1. No LLM keys - scraper may fail at classification step")
else:
    print("1. Configuration looks OK")
    print("2. Issue may be with Instagram authentication or blocking")
    print("3. Try manually running the scraper to see specific errors")
    print("4. Check Instagram cookies are valid and not expired")
    print("5. Check if Instagram is blocking the scraper IP")

print("\nNEXT STEPS:")
print("-" * 80)
print("1. Add missing environment variables")
print("2. Ensure Instagram cookies are valid")
print("3. Test scraper manually: python backend/test_scraper.py")
print("4. Check scraper logs for specific errors")
print("5. Consider using fresh Instagram cookies")