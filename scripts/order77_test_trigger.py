import os
import sys
from dotenv import load_dotenv
load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

print("=" * 80)
print("ORDER 77 ITEM 3: FIRST_DETECTED_AT IMMUTABILITY TRIGGER TEST")
print("=" * 80)

test_audio_id = "test_order77_immutability_dummy"
t0 = "2026-09-01T12:00:00+00:00"
t_attempt = "2026-10-15T18:00:00+00:00"

try:
    # 0. Clean any prior test row
    sb.table('trends').delete().eq('audio_id', test_audio_id).execute()

    # 1. Insert test row
    print(f"1. Inserting test trend with first_detected_at = {t0}...")
    ins_res = sb.table('trends').insert({
        'audio_id': test_audio_id,
        'audio_title': 'Trigger Test Audio',
        'audio_artist': 'Trigger Test Artist',
        'status': 'emerging',
        'first_detected_at': t0,
    }).execute()
    print("   Inserted:", ins_res.data[0]['first_detected_at'])

    # 2. Attempt to UPDATE first_detected_at to a newer timestamp
    print(f"\n2. Attempting UPDATE to first_detected_at = {t_attempt}...")
    upd_res = sb.table('trends').update({
        'first_detected_at': t_attempt,
        'audio_title': 'Trigger Test Audio (Updated Title)'
    }).eq('audio_id', test_audio_id).execute()

    # 3. Read back from database
    read_res = sb.table('trends').select('id, audio_id, first_detected_at, last_seen_at, audio_title').eq('audio_id', test_audio_id).execute()
    actual_t = read_res.data[0]['first_detected_at']
    last_seen = read_res.data[0]['last_seen_at']
    print("\n3. Read-back values from DB:")
    print(f"   first_detected_at = {actual_t}")
    print(f"   last_seen_at      = {last_seen}")
    print(f"   audio_title       = {read_res.data[0]['audio_title']}")

    # 4. Verify trigger protected it
    if actual_t.startswith("2026-09-01T12:00:00"):
        print("\n[PASS] Trigger successfully BLOCKED the overwrite! first_detected_at is immutable.")
    else:
        print(f"\n[FAIL] Trigger did NOT protect first_detected_at! Overwritten to {actual_t}")
        sys.exit(1)

    # 5. Cleanup
    sb.table('trends').delete().eq('audio_id', test_audio_id).execute()
    print("\n4. Cleaned up test row.")

except Exception as e:
    print(f"\n[ERROR] during trigger test: {e}")
    # Always attempt cleanup
    try:
        sb.table('trends').delete().eq('audio_id', test_audio_id).execute()
    except Exception:
        pass
    sys.exit(1)

print("=" * 80)
print("TRIGGER VERIFICATION COMPLETE")
print("=" * 80)
