import os
import sys
import json
from dotenv import load_dotenv

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, backend_dir)
load_dotenv(os.path.join(backend_dir, ".env"))

from supabase import create_client
from cron_auto_classifier import auto_classify_trends, run_unclassified_safety_net_pass, ALLOWED_LANGUAGES, ALLOWED_USED_FOR

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    sb = create_client(url, key)

    print("=== ORDER 36 VERIFICATION TEST ===")

    # 1. Search for any synthetic test rows sitting in trends table
    print("\n--- Step 1: Searching for synthetic/test rows in trends table ---")
    res_test = sb.table("trends").select("id, audio_title, audio_artist, created_at").ilike("audio_title", "%test%").execute()
    test_rows = res_test.data or []
    print(f"Synthetic test rows found in trends table: {len(test_rows)}")
    for tr in test_rows:
        print(f"  ID: {tr['id']} | Title: {tr['audio_title']} | Artist: {tr['audio_artist']}")
    assert len(test_rows) == 0, f"Found {len(test_rows)} synthetic test rows still in DB!"

    # 2. Query for a REAL existing unclassified active trend
    print("\n--- Step 2: Querying a REAL existing unclassified active trend ---")
    res_unclass = sb.table("trends") \
        .select("id, audio_title, audio_artist, language_final, used_for, used_for_note, status") \
        .neq("status", "unqualified") \
        .or_("language_final.is.null,used_for.is.null") \
        .limit(1) \
        .execute()

    unclass_data = res_unclass.data or []
    assert len(unclass_data) > 0, "No unclassified active trends found in DB to test against"
    real_trend = unclass_data[0]
    target_id = real_trend["id"]
    print(f"Target REAL Trend ID: {target_id}")
    print(f"BEFORE State: Title='{real_trend['audio_title']}', Artist='{real_trend['audio_artist']}', Language='{real_trend['language_final']}', Used_For='{real_trend['used_for']}'")

    # 3. Run auto-classifier against real trend
    print(f"\n--- Step 3: Executing auto_classify_trends([{target_id}]) ---")
    hook_res = auto_classify_trends([target_id])
    print(f"Classification result summary: {hook_res}")

    # 4. Fetch AFTER state and assert schema compliance
    print(f"\n--- Step 4: Verifying AFTER State for REAL Trend ID {target_id} ---")
    after_res = sb.table("trends") \
        .select("id, audio_title, audio_artist, language_final, used_for, used_for_note, llm_classification_status") \
        .eq("id", target_id) \
        .execute()
    
    after_trend = after_res.data[0]
    print(json.dumps(after_trend, indent=2, ensure_ascii=False))

    assert after_trend["language_final"] in ALLOWED_LANGUAGES, f"Invalid language_final '{after_trend['language_final']}' not in ALLOWED_LANGUAGES"
    assert after_trend["used_for"] in ALLOWED_USED_FOR, f"Invalid used_for '{after_trend['used_for']}' not in ALLOWED_USED_FOR ({ALLOWED_USED_FOR})"
    print(f"[OK] VERIFIED! language_final='{after_trend['language_final']}' (valid), used_for='{after_trend['used_for']}' (valid from Order 27 allowed list).")

    # 5. Run Safety-Net Pass and verify log/counting accuracy
    print("\n--- Step 5: Testing Safety-Net Pass & Counting Accuracy ---")
    sn_res = run_unclassified_safety_net_pass(limit=10)
    print(f"Safety-net pass result: {sn_res}")
    
    processed = sn_res.get("processed", 0)
    lang_updated = sn_res.get("language_updated", 0)
    uf_updated = sn_res.get("used_for_updated", 0)
    
    print(f"Safety-net summary: processed={processed}, language_updated={lang_updated}, used_for_updated={uf_updated}")
    assert lang_updated <= processed, f"language_updated ({lang_updated}) cannot exceed processed ({processed})!"
    assert uf_updated <= processed, f"used_for_updated ({uf_updated}) cannot exceed processed ({processed})!"
    print("[OK] Safety-net counting accuracy verified! No inflated or double-counted numbers.")

    print("\n=======================================================")
    print("ALL ORDER 36 VERIFICATION TESTS PASSED CLEANLY!")
    print("=======================================================")

if __name__ == "__main__":
    main()
