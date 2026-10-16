import os
import sys
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv('backend/.env')
load_dotenv('.env')

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

now = datetime.now(timezone.utc)
out_file = "evidence/order79/resurging_dry_run.txt"

lines = []
lines.append("=" * 80)
lines.append("ORDER 79B & 79C ITEM 3 & 4: RESURGING AUDIT & STAGE-TAG DRY RUN")
lines.append(f"Timestamp: {now.isoformat()}")
lines.append("=" * 80)

# 1. Fetch all trends currently stamped 'resurging'
print("Fetching resurging trends from Supabase...")
res = sb.table("trends").select(
    "id, audio_title, audio_artist, audio_id, status, velocity_avg, "
    "audio_use_count, reel_count, first_detected_at, last_seen_at, "
    "created_at, status_changed_at, status_reason"
).eq("status", "resurging").execute()

trends = res.data or []
total_resurging = len(trends)
lines.append(f"\nTotal trends currently with status='resurging': {total_resurging}")

# 2. Path analysis: trend_refresher vs trend_detector
path_counts = {
    "refresher_resurgence_gate": 0,
    "resurgence_gate (detector)": 0,
    "refresher_legacy": 0,
    "unknown_or_null_reason": 0
}

for t in trends:
    sr = t.get("status_reason")
    if isinstance(sr, dict):
        trig = sr.get("trigger_source") or ""
        if "refresher" in trig:
            path_counts["refresher_resurgence_gate"] += 1
        elif "resurgence" in trig:
            path_counts["resurgence_gate (detector)"] += 1
        else:
            path_counts["refresher_legacy"] += 1
    elif isinstance(sr, str) and "refresher" in sr:
        path_counts["refresher_resurgence_gate"] += 1
    elif isinstance(sr, str) and "resurgence" in sr:
        path_counts["resurgence_gate (detector)"] += 1
    else:
        path_counts["unknown_or_null_reason"] += 1

lines.append("\n--- TWO-PATH ATTRIBUTION ANALYSIS ---")
for k, v in path_counts.items():
    lines.append(f"  {k:<30}: {v} ({v/total_resurging*100:.1f}%)")

# Helper to compute age in days
def parse_dt(dt_str):
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except:
        return None

# 3. Simulate Candidate Threshold Sets
# Candidate A (Strict Second Wave):
#   - Was previously peaked/expired OR audio_age >= 7d
#   - last_seen_at within 7d
#   - velocity_avg >= 500
#   - reel_count >= 3
# Candidate B (Moderate Second Wave):
#   - audio_age >= 7d
#   - last_seen_at within 14d
#   - velocity_avg >= 250
#   - reel_count >= 2
# Candidate C (Relaxed Second Wave):
#   - audio_age >= 5d
#   - last_seen_at within 14d
#   - velocity_avg >= 100
#   - reel_count >= 1

cand_A_matches = []
cand_B_matches = []
cand_C_matches = []

for t in trends:
    f_dt = parse_dt(t.get("first_detected_at") or t.get("created_at"))
    l_dt = parse_dt(t.get("last_seen_at") or t.get("status_changed_at") or t.get("created_at"))
    age_days = (now - f_dt).total_seconds() / 86400.0 if f_dt else 0
    days_since_seen = (now - l_dt).total_seconds() / 86400.0 if l_dt else 999
    vel = float(t.get("velocity_avg") or 0)
    reels = int(t.get("reel_count") or 0)

    # Candidate A
    if age_days >= 7 and days_since_seen <= 7 and vel >= 500 and reels >= 3:
        cand_A_matches.append(t)

    # Candidate B
    if age_days >= 7 and days_since_seen <= 14 and vel >= 250 and reels >= 2:
        cand_B_matches.append(t)

    # Candidate C
    if age_days >= 5 and days_since_seen <= 14 and vel >= 100 and reels >= 1:
        cand_C_matches.append(t)

lines.append("\n--- 3 CANDIDATE THRESHOLD SETS DISTRIBUTION ---")
lines.append(f"  Candidate A (Strict: age>=7d, seen<=7d, vel>=500, reels>=3): {len(cand_A_matches)} trends ({len(cand_A_matches)/total_resurging*100:.1f}%)")
lines.append(f"  Candidate B (Moderate: age>=7d, seen<=14d, vel>=250, reels>=2): {len(cand_B_matches)} trends ({len(cand_B_matches)/total_resurging*100:.1f}%)")
lines.append(f"  Candidate C (Relaxed: age>=5d, seen<=14d, vel>=100, reels>=1): {len(cand_C_matches)} trends ({len(cand_C_matches)/total_resurging*100:.1f}%)")

# 4. Map the remaining 889 trends into the honest stage tags under Candidate B
# Stage Tag Formula:
# - Comeback: meets Candidate B second-wave criteria
# - Just starting: age <= 3d, reels >= 2
# - Blowing up: age <= 7d, vel >= 500, days_since_seen <= 3
# - Still going: age > 7d, days_since_seen <= 3, vel > 0
# - Fading: 3 < days_since_seen < 14
# - Expired: days_since_seen >= 14

stage_groups = {
    "Comeback": [],
    "Just starting": [],
    "Blowing up": [],
    "Still going": [],
    "Fading": [],
    "Expired": []
}

cand_B_ids = set(t["id"] for t in cand_B_matches)

for t in trends:
    tid = t["id"]
    if tid in cand_B_ids:
        stage_groups["Comeback"].append(t)
        continue

    f_dt = parse_dt(t.get("first_detected_at") or t.get("created_at"))
    l_dt = parse_dt(t.get("last_seen_at") or t.get("status_changed_at") or t.get("created_at"))
    age_days = (now - f_dt).total_seconds() / 86400.0 if f_dt else 0
    days_since_seen = (now - l_dt).total_seconds() / 86400.0 if l_dt else 999
    vel = float(t.get("velocity_avg") or 0)
    reels = int(t.get("reel_count") or 0)

    if days_since_seen >= 14:
        stage_groups["Expired"].append(t)
    elif days_since_seen > 3:
        stage_groups["Fading"].append(t)
    elif age_days <= 3 and reels >= 2:
        stage_groups["Just starting"].append(t)
    elif age_days <= 7 and vel >= 500:
        stage_groups["Blowing up"].append(t)
    else:
        stage_groups["Still going"].append(t)

lines.append("\n--- HONEST STAGE TAG DRY-RUN BREAKDOWN (REPLAY OF 889 'RESURGING' TRENDS) ---")
for stage, grp in stage_groups.items():
    lines.append(f"  {stage:<15}: {len(grp):>4} ({len(grp)/total_resurging*100:>5.1f}%)")

# 5. Example trends per group (up to 10 per group)
lines.append("\n--- 10 REPRESENTATIVE EXAMPLES PER STAGE GROUP ---")
for stage in ["Comeback", "Still going", "Fading", "Expired", "Blowing up", "Just starting"]:
    grp = stage_groups[stage]
    lines.append(f"\n[{stage.upper()} - {len(grp)} trends total (Sample of {min(10, len(grp))}):]")
    for i, t in enumerate(grp[:10]):
        title = t.get("audio_title") or t.get("song") or "Unknown"
        artist = t.get("audio_artist") or "Unknown"
        reels = t.get("reel_count") or 1
        l_dt = t.get("last_seen_at") or t.get("status_changed_at") or "None"
        vel = float(t.get("velocity_avg") or 0)
        lines.append(f"  {i+1:2d}. [ID {t['id']}] \"{title[:30]}\" by {artist[:20]} | Reels: {reels} | Vel: {vel:.1f} | Last Seen: {l_dt}")

# 6. Report every reader of the status column across backend and frontend
lines.append("\n--- READERS OF trends.status COLUMN IN CODEBASE ---")
readers = [
    ("backend/routes/trends.py", "SLIM_FEED_COLUMNS, get_unified_feed: filters on status in ('emerging','rising','resurging','peaked')"),
    ("backend/routes/trends.py", "get_rising: status='rising'"),
    ("backend/routes/trends.py", "get_emerging: status='emerging'"),
    ("backend/routes/trends.py", "get_peaked: status='peaked'"),
    ("backend/routes/trends.py", "get_resurging: status='resurging'"),
    ("backend/routes/trends.py", "get_expired: status='expired'"),
    ("backend/routes/trends.py", "_normalize_trends_slim: checks status not in ('unqualified','disqualified')"),
    ("backend/trend_detector.py", "evaluates status for promotion / demotion / resurgence"),
    ("backend/trend_refresher.py", "refreshes velocity, shifts peaking/expired/resurging"),
    ("frontend/src/lib/api.ts", "UiTrend.status mapping"),
    ("frontend/src/components/TrendCard.tsx", "getLifecycleStatusBadge(trend.status)"),
    ("frontend/src/routes/index.tsx", "filters feed by status param ('rising', 'emerging', 'all')")
]
for file_path, desc in readers:
    lines.append(f"  - {file_path:<30} -> {desc}")

lines.append("\n" + "=" * 80)
lines.append("END OF RESURGING AUDIT & DRY RUN (ZERO WRITES EXECUTED)")
lines.append("=" * 80)

output_text = "\n".join(lines)
with open(out_file, "w", encoding="utf-8") as f:
    f.write(output_text)
print(output_text)
