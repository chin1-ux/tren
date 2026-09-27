import os
import sys
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_dir)
load_dotenv(os.path.join(backend_dir, ".env"))

from supabase import create_client
from cron_auto_classifier import auto_classify_trends, run_unclassified_safety_net_pass

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    sb = create_client(url, key)

    print("=== STEP 1: Creating a temporary test trend ===")
    ts_suffix = int(datetime.now(timezone.utc).timestamp())
    test_payload = {
        "audio_title": "Chuttamalle Test Track",
        "audio_artist": "Anirudh Ravichander",
        "audio_id": f"test_audio_order35_{ts_suffix}",
        "status": "rising",
        "is_seed_data": False,
        "is_voiceover": False,
        "window_hours_remaining": 48,
        "language": None,
        "language_final": None,
        "used_for": None,
        "used_for_note": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    res_insert = sb.table("trends").insert(test_payload).execute()
    created_rows = res_insert.data or []
    assert len(created_rows) > 0, "Failed to insert test trend"
    test_id = created_rows[0]["id"]
    print(f"[OK] Created test trend ID: {test_id}")

    print("\n=== STEP 2: RAW BEFORE STATE (language_final=NULL, used_for=NULL) ===")
    before_row = sb.table("trends").select("id, audio_title, audio_artist, language_final, language, used_for, used_for_note, llm_classification_status").eq("id", test_id).execute().data[0]
    print(json.dumps(before_row, indent=2, ensure_ascii=False))

    assert before_row["language_final"] is None, "Expected language_final to be NULL before hook"
    assert before_row["used_for"] is None, "Expected used_for to be NULL before hook"

    print("\n=== STEP 3: Executing auto_classify_trends([test_id]) hook ===")
    result = auto_classify_trends([test_id])
    print(f"Hook execution summary: {result}")

    print("\n=== STEP 4: RAW AFTER STATE (language_final & used_for populated) ===")
    after_row = sb.table("trends").select("id, audio_title, audio_artist, language_final, language, used_for, used_for_note, llm_classification_status").eq("id", test_id).execute().data[0]
    print(json.dumps(after_row, indent=2, ensure_ascii=False))

    assert after_row["language_final"] is not None, "Expected language_final to be populated after hook"
    assert after_row["used_for"] is not None, "Expected used_for to be populated after hook"
    print(f"[OK] BEFORE -> AFTER verification passed! language_final='{after_row['language_final']}', used_for='{after_row['used_for']}'")

    print("\n=== STEP 5: Cleaning up test trend ===")
    sb.table("trends").delete().eq("id", test_id).execute()
    print("[OK] Test trend deleted successfully.")

    print("\n=== STEP 6: Testing Safety-Net Pass ===")
    safety_net_res = run_unclassified_safety_net_pass(limit=10)
    print(f"[OK] Safety-net pass completed: {safety_net_res}")

    print("\n==========================================")
    print("ALL ORDER 35 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==========================================")

if __name__ == "__main__":
    main()
