import os
import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

TARGET_AID = "1108728035449207"
TARGET_TID = 7583

print("=" * 95)
print(f"PART C1: READINGS AUDIT FOR TREND #{TARGET_TID} / AUDIO {TARGET_AID} ('امشي بثقه')")
print("=" * 95)

# 1. audio_count_history readings
ach_res = sb.table("audio_count_history").select("id, audio_id, use_count, raw_text, captured_at, run_id").eq("audio_id", TARGET_AID).execute()
readings = ach_res.data or []
print(f"\n1. audio_count_history readings: {len(readings)} found")
if readings:
    for r in readings:
        print(f"   ID: {r.get('id')} | Count: {r.get('use_count')} | Raw: '{r.get('raw_text')}' | Captured: {r.get('captured_at')} | Run ID: {r.get('run_id')}")
else:
    print("   No readings found in audio_count_history.")

# 2. watchlist rows
wl_res = sb.table("watchlist").select("*").eq("audio_id", TARGET_AID).execute()
wl_rows = wl_res.data or []
print(f"\n2. watchlist rows: {len(wl_rows)} found")
for w in wl_rows:
    print(f"   Song Key: {w.get('song_key')} | Score: {w.get('score')} | Status: {w.get('status')} | Flagged: {w.get('flagged_at')}")

# 3. probe_log rows
pl_res = sb.table("probe_log").select("*").or_(f"candidate_audio_id.eq.{TARGET_AID},tag.ilike.%امشي%").execute()
pl_rows = pl_res.data or []
print(f"\n3. probe_log rows: {len(pl_rows)} found")
for p in pl_rows:
    print(f"   Tag: #{p.get('tag')} | HTTP: {p.get('http_status')} | Medias: {p.get('medias')} | Matched: {p.get('matched')} | TS: {p.get('ts')}")

# 4. Check why capture did not select it
print("\n4. Capture job selection analysis:")
# Check audio_capture.py selection criteria
print("   Checking capture job candidate selection in backend/audio_capture.py...")
