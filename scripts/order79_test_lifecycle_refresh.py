import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv('backend/.env')
load_dotenv('.env')

from supabase import create_client
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

now = datetime.now(timezone.utc)
lines = []
lines.append("=" * 80)
lines.append("ORDER 79B/C ITEM 3: LIFECYCLE REFRESH AUDIT & PROOF")
lines.append(f"Timestamp: {now.isoformat()}")
lines.append("=" * 80)

# Check last 5 runs of Trend Refresh in chin1-ux/tren
lines.append("\n--- LAST 5 RUNS OF 'Trend Refresh (Main Account - 8h)' (ID 342411741) ---")
import subprocess
res = subprocess.run("gh run list --workflow 342411741 --repo chin1-ux/tren --limit 5", shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
lines.append(res.stdout.strip())

# Sample 20 active trends to inspect status, window_hours_remaining, and last_seen_at
lines.append("\n--- SAMPLE OF 20 ACTIVE TRENDS AUDITED FOR LIFECYCLE HEALTH ---")
res_trends = sb.table("trends").select("id, audio_title, audio_artist, status, window_hours_remaining, created_at, status_changed_at, last_seen_at").in_("status", ["rising", "emerging"]).order("id", desc=True).limit(20).execute()

for i, t in enumerate(res_trends.data or []):
    title = (t.get("audio_title") or "")[:25]
    artist = (t.get("audio_artist") or "")[:15]
    win = t.get("window_hours_remaining")
    st = t.get("status")
    sc = t.get("status_changed_at") or "None"
    ls = t.get("last_seen_at") or "None"
    lines.append(f"  {i+1:2d}. [ID {t['id']}] \"{title}\" by {artist} | Status={st:<8} | Window={win:>2}h | LastSeen={ls} | StatusChanged={sc}")

lines.append("\n" + "=" * 80)
lines.append("LIFECYCLE PROOF COMPLETE")
lines.append("=" * 80)

output_text = "\n".join(lines)
with open("evidence/order79/lifecycle_refresh_proof.txt", "w", encoding="utf-8") as f:
    f.write(output_text)
print(output_text)
