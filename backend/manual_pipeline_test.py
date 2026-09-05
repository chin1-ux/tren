#!/usr/bin/env python3
"""
Manual pipeline run - run the full pipeline locally
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("MANUAL PIPELINE RUN")
print("=" * 60)

print("\n1. Running full pipeline...")
try:
    from cron_job import run_full_pipeline
    run_full_pipeline()
    print("   [OK] Pipeline completed")
except Exception as e:
    print(f"   [ERROR] Pipeline failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n2. Running audio count check...")
try:
    from cron_job import run_audio_count_check
    run_audio_count_check()
    print("   [OK] Audio count check completed")
except Exception as e:
    print(f"   [ERROR] Audio count check failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("MANUAL PIPELINE RUN COMPLETED")
print("=" * 60)