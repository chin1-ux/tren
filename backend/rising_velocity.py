import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client
import statistics

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

rising = sb.table("trends").select("velocity_avg, audio_title").eq("status", "rising").execute()
vels = [r.get("velocity_avg") or 0 for r in rising.data]
vels.sort()

print("=== RISING-BASELINE VELOCITY ===")
print(f"Count: {len(vels)}")
print(f"Values (sorted): {[round(v, 1) for v in vels]}")
print(f"Median: {round(statistics.median(vels), 1)}")
print(f"Mean: {round(statistics.mean(vels), 1)}")
print(f"Min: {round(min(vels), 1)}")
print(f"Max: {round(max(vels), 1)}")
print(f"Stdev: {round(statistics.stdev(vels), 1)}")
