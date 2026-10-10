import os
import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

TARGET_AID = "1108728035449207"

print("=" * 95)
print(f"PART D1: REELS AUDIT FOR ASAAD BASHA (AUDIO ID {TARGET_AID})")
print("=" * 95)

res = sb.table("reels").select("id, reel_id, owner_username, posted_at, scraped_at, created_at, source_tag, view_count, audio_title").eq("audio_id", TARGET_AID).execute()
reels = res.data or []

print(f"Total reels found for audio {TARGET_AID}: {len(reels)}")
print(f"{'Reel ID':<16} | {'Creator':<20} | {'Posted At':<22} | {'Scraped At':<22} | {'Source Tag':<15} | {'Views':<8}")
print("-" * 115)
for r in reels:
    rid = str(r.get("reel_id") or r.get("id"))
    creator = str(r.get("owner_username") or "Unknown")
    p_at = str(r.get("posted_at") or "NULL")[:19]
    s_at = str(r.get("scraped_at") or r.get("created_at") or "NULL")[:19]
    stag = str(r.get("source_tag") or "NULL")
    views = str(r.get("view_count") or 0)
    print(f"{rid:<16} | {creator:<20} | {p_at:<22} | {s_at:<22} | {stag:<15} | {views:<8}")

print("=" * 115)

# Trend details
t_res = sb.table("trends").select("id, status, created_at, first_detected_at").eq("audio_id", TARGET_AID).execute().data or []
print("\nTrend Table Records:")
for t in t_res:
    print(f"  Trend #{t['id']}: Status={t.get('status')} | created_at={t.get('created_at')} | first_detected_at={t.get('first_detected_at')}")
