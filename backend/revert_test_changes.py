import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

# Revert test-induced status changes
reverts = [
    (20, "expired"),
    (6, "peaked"),
]

for tid, original_status in reverts:
    sb.table("trends").update({"status": original_status}).eq("id", tid).execute()
    # Verify
    r = sb.table("trends").select("id, audio_title, status").eq("id", tid).execute()
    row = r.data[0]
    ok = row["status"] == original_status
    print(f"Reverted id={tid} '{row['audio_title']}' -> {row['status']}: {'PASS' if ok else 'FAIL'}")

print("\nProduction data restored.")
