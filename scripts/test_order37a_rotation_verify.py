import os
import sys
import json
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_dir)
load_dotenv(os.path.join(backend_dir, ".env"))

from cron_auto_classifier import classify_used_for_batch

def main():
    print("=== ORDER 37a-verify: PROOF OF KEY ROTATION ON FAILURE ===")

    real_key1 = os.environ.get("GEMINI_API_KEY")
    print(f"\n1. Invalidation: Setting GEMINI_API_KEY (Key #1) to invalid/expired string...")
    os.environ["GEMINI_API_KEY"] = "INVALID_EXPIRED_KEY_123456789"

    test_trends = [{
        "id": 4252,
        "audio_title": "Nikle Currant",
        "audio_artist": "Jassi Gill, Neha Kakkar",
        "sample_captions": "Dance routine reel with friends #dance #trending"
    }]

    try:
        print("\n2. Executing classify_used_for_batch (calls call_gemini_only with production prompt & schema)...")
        results = classify_used_for_batch(test_trends)

        print("\n3. Raw Return Payload:")
        print(json.dumps(results, indent=2, ensure_ascii=False))

    finally:
        if real_key1:
            os.environ["GEMINI_API_KEY"] = real_key1
            print("\n4. Restoration: GEMINI_API_KEY (Key #1) restored to real value.")

if __name__ == "__main__":
    main()
