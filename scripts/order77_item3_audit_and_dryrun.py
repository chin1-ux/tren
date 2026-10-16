import os
import sys
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv('backend/.env')
from supabase import create_client

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
sb = create_client(url, key)

print("=" * 80)
print("ORDER 77 ITEM 3: FIRST_DETECTED_AT AUDIT & BACKFILL DRY RUN")
print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
print("=" * 80)

now = datetime.now(timezone.utc)
seven_days_ago = now - timedelta(days=7)

def parse_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace('Z', '+00:00'))

# 1. Focus on all active trends (emerging, rising, resurging) + recent 200 trends
print("Querying active & recent trends from database...")
trends_res = sb.table('trends').select('id, audio_id, audio_title, status, first_detected_at, created_at').in_('status', ['emerging', 'rising', 'resurging']).execute()
active_trends = trends_res.data or []
print(f"Active trends found: {len(active_trends)}")

# Also fetch all emerging trends specifically
em_res = sb.table('trends').select('id, audio_id, audio_title, status, first_detected_at, created_at').eq('status', 'emerging').execute()
em_trends = em_res.data or []
print(f"Total emerging trends: {len(em_trends)}")

shifts = []
emerging_leaving_7d = []

# Analyze each active trend
for i, t in enumerate(active_trends):
    tid = t['id']
    aid = t.get('audio_id')
    f_det_str = t.get('first_detected_at') or t.get('created_at')
    if not aid or not f_det_str:
        continue
    
    # Query earliest reel for this audio_id
    reels_res = sb.table('reels').select('scraped_at, created_at').eq('audio_id', aid).order('created_at', desc=False).limit(1).execute()
    reels = reels_res.data or []
    if not reels:
        continue
    
    reel_time_str = reels[0].get('scraped_at') or reels[0].get('created_at')
    if not reel_time_str:
        continue
        
    dt_f_det = parse_dt(f_det_str)
    dt_reel = parse_dt(reel_time_str)
    
    # Check if reel was sighted earlier than recorded first_detected_at (by >= 10 minutes)
    if (dt_f_det - dt_reel).total_seconds() > 600:
        shift_hrs = (dt_f_det - dt_reel).total_seconds() / 3600.0
        shifts.append({
            'id': tid,
            'title': t.get('audio_title'),
            'status': t.get('status'),
            'current_first_detected': f_det_str,
            'earliest_reel_time': reel_time_str,
            'shift_hours': shift_hrs
        })
        
        # Check if currently emerging and inside 7d, but will leave 7d
        if t.get('status') == 'emerging' and dt_f_det >= seven_days_ago and dt_reel < seven_days_ago:
            emerging_leaving_7d.append({
                'id': tid,
                'title': t.get('audio_title'),
                'current_first_detected': f_det_str,
                'earliest_reel_time': reel_time_str,
                'age_days_true': (now - dt_reel).total_seconds() / 86400.0
            })

print("\nAUDIT RESULTS FOR ACTIVE TRENDS:")
print(f"Active trends checked: {len(active_trends)}")
print(f"Trends where earliest reel is earlier than first_detected_at: {len(shifts)} ({len(shifts)/max(1, len(active_trends))*100:.1f}%)")
print(f"Currently-emerging trends that will leave the 7-day window upon backfill: {len(emerging_leaving_7d)}")

if shifts:
    print("\nSAMPLE OF 5 SHIFTING TRENDS:")
    print("-" * 80)
    for s in shifts[:5]:
        print(f"Trend ID {s['id']} ('{s['title']}', status: {s['status']}):")
        print(f"  Current first_detected : {s['current_first_detected']}")
        print(f"  Earliest reel sighting : {s['earliest_reel_time']} (shift: {s['shift_hours']:.1f} hours earlier)")
    print("-" * 80)

if emerging_leaving_7d:
    print("\nEMERGING TRENDS LEAVING 7-DAY WINDOW (HONEST DISCLOSURE):")
    print("-" * 80)
    for e in emerging_leaving_7d:
        print(f"Trend ID {e['id']} ('{e['title']}'):")
        print(f"  Current: {e['current_first_detected']} -> True Earliest: {e['earliest_reel_time']} ({e['age_days_true']:.1f} days old)")
    print("-" * 80)
else:
    print("\nHonest check: 0 currently-emerging trends will leave the 7-day window.")

print("=" * 80)
