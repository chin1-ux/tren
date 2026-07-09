import os, sys
sys.path.insert(0, "backend")
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("backend/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

print("=== CRON RUNS ===")
try:
    runs = sb.table("cron_runs").select("*").order("run_at", desc=True).limit(10).execute()
    for r in runs.data:
        print(f"Run at: {r.get('run_at')} | Status: {r.get('status')} | New trends found: {r.get('new_trends_found')} | Trend IDs: {r.get('trend_ids')}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== TRENDS ===")
try:
    trends = sb.table("trends").select("id", "first_detected_at", "audio_title", "audio_artist", "status", "composite_score").order("first_detected_at", desc=True).limit(20).execute()
    for t in trends.data:
        print(f"ID: {t.get('id')} | Created at: {t.get('first_detected_at')} | Title: {t.get('audio_title')} | Status: {t.get('status')} | Score: {t.get('composite_score')}")
except Exception as e:
    print(f"Error: {e}")
