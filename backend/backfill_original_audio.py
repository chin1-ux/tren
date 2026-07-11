import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv("backend/.env")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
if not url or not key:
    print("Error: Supabase URL or Key not found in environment.")
    sys.exit(1)

sb = create_client(url, key)

print("Starting original audio backfill...")
try:
    # Use case-insensitive ilike query to match any title containing 'original'
    res = sb.table("reels") \
        .update({"is_original_audio": True}) \
        .ilike("audio_title", "%original%") \
        .eq("is_original_audio", False) \
        .execute()
        
    print(f"Successfully backfilled {len(res.data or [])} mismatched original audio reels.")
except Exception as e:
    print(f"Error executing backfill: {e}")
    sys.exit(1)
