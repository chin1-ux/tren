import os
import sys
import statistics
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
from supabase import create_client

def parse_dt(s):
    if not s:
        return None
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
now = datetime.now(timezone.utc)

print("=" * 95)
print("PART B1: BREAKOUT MEASUREMENT (STRICT 3x IN 72h & INITIAL >= 1000)")
print("=" * 95)

# Fetch audio_count_history
ach_res = sb.table("audio_count_history").select("audio_id, use_count, captured_at").order("captured_at", desc=False).limit(3000).execute()
rows = ach_res.data or []
by_aid = {}
for r in rows:
    aid = str(r["audio_id"])
    by_aid.setdefault(aid, []).append(r)

print(f"Total readings fetched: {len(rows)} across {len(by_aid)} distinct audios.")

# Fetch proof_log and trends for detection lead times
pl_res = sb.table("proof_log").select("audio_id, flagged_at").execute().data or []
pl_by_aid = {}
for p in pl_res:
    aid = str(p.get("audio_id") or "")
    if aid and p.get("flagged_at"):
        pl_by_aid.setdefault(aid, []).append(parse_dt(p["flagged_at"]))

trends_res = sb.table("trends").select("audio_id, first_detected_at, audio_title").execute().data or []
tr_by_aid = {}
for tr in trends_res:
    aid = str(tr.get("audio_id") or "")
    if aid and tr.get("first_detected_at"):
        tr_by_aid.setdefault(aid, []).append(parse_dt(tr["first_detected_at"]))

breakouts = []
# Find breakouts
for aid, hist in by_aid.items():
    if len(hist) < 2:
        continue
    # sort by time
    hist_sorted = sorted(hist, key=lambda x: parse_dt(x["captured_at"]))
    first_dt = parse_dt(hist_sorted[0]["captured_at"])
    first_cnt = hist_sorted[0].get("use_count") or 0
    
    if first_cnt < 1000:
        continue  # Requirement: earlier reading >= 1000
        
    for r in hist_sorted[1:]:
        cur_dt = parse_dt(r["captured_at"])
        cur_cnt = r.get("use_count") or 0
        diff_h = (cur_dt - first_dt).total_seconds() / 3600.0
        if diff_h <= 72.0 and cur_cnt >= 3 * first_cnt:
            breakouts.append({
                "audio_id": aid,
                "first_time": first_dt,
                "first_count": first_cnt,
                "breakout_time": cur_dt,
                "breakout_count": cur_cnt,
                "ratio": cur_cnt / first_cnt,
                "growth_hours": diff_h
            })
            break

n_breakouts = len(breakouts)
print(f"\nTotal qualifying breakouts found: n = {n_breakouts}")

leads = []
for b in breakouts:
    aid = b["audio_id"]
    det_candidates = pl_by_aid.get(aid, []) + tr_by_aid.get(aid, [])
    if det_candidates:
        earliest_det = min(det_candidates)
        lead_h = (b["breakout_time"] - earliest_det).total_seconds() / 3600.0
        max_possible_lead = (now - b["first_time"]).total_seconds() / 3600.0
        
        # Assertion: lead <= (now - first reading time)
        if lead_h > max_possible_lead + 0.1:  # small epsilon for clock precision
            print(f"FAIL: Lead violation for audio {aid}! lead ({lead_h:.1f}h) > now-first_time ({max_possible_lead:.1f}h)")
            sys.exit(1)
            
        b["earliest_detection"] = earliest_det
        b["lead_hours"] = lead_h
        leads.append(b)
    else:
        b["earliest_detection"] = None
        b["lead_hours"] = None

print(f"Breakouts with early system detection: {len(leads)} / {n_breakouts}")
if leads:
    med_lead = statistics.median([l["lead_hours"] for l in leads])
    print(f"Median detection lead: {med_lead:+.1f} hours (positive = system flagged before breakout)")
    
    # Sort by lead_hours desc
    leads_sorted = sorted(leads, key=lambda x: x["lead_hours"], reverse=True)
    print("\nTop 10 Breakouts by Lead Time:")
    print(f"{'Audio ID':<18} | {'First Reading':<20} | {'Breakout Time':<20} | {'Growth':<12} | {'Lead Hours':<10}")
    print("-" * 95)
    for l in leads_sorted[:10]:
        first_str = f"{l['first_count']} @ {l['first_time'].isoformat()[:16]}"
        bo_str = f"{l['breakout_count']} @ {l['breakout_time'].isoformat()[:16]}"
        growth_str = f"{l['ratio']:.1f}x ({l['growth_hours']:.1f}h)"
        lead_str = f"{l['lead_hours']:+.1f}h"
        print(f"{l['audio_id']:<18} | {first_str:<20} | {bo_str:<20} | {growth_str:<12} | {lead_str:<10}")
else:
    print("No breakouts with system detection yet.")
print("=" * 95)
