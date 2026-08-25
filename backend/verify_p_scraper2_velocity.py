"""
P-SCRAPER-2 evidence harness (read-only).

Question: does resolving follower counts from creator_baselines (when the IG
hashtag endpoint omits them) actually differentiate velocity scoring on REAL
production rows, versus the current universal 2500-follower fallback?

Method:
 1. Sample recent reels with owner_follower_count = 0 whose owner has a
    creator_baselines row with follower_count > 0.
 2. Recompute each reel's velocity twice with the EXACT production formula
    (instagram_scraper_browser.py:1278-1281):
        engagement = views + likes*3 + comments*5
        eff_followers = followers if followers > 0 else 2500
        velocity = engagement / hours_live / log(eff_followers + 10) * 100
    OLD path: followers treated as 0 (today's behavior for these rows)
    NEW path: followers = creator_baselines.follower_count (the fix)
 3. Report differentiation stats + threshold-gate effects.
 4. Control group: reels that already have owner_follower_count > 0 must be
    byte-identical under both paths (the fix must not touch them).
"""
import urllib.request, json, math, ssl, time

env = {}
for line in open(r"C:\Users\Chinmay\OneDrive\Desktop\trendrop\backend\.env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"')
ctx = ssl.create_default_context()
SB = env["SUPABASE_URL"].rstrip("/")
KEY = env["SUPABASE_SERVICE_ROLE_KEY"]

def rest(path):
    r = urllib.request.Request(SB + path)
    r.add_header("apikey", KEY)
    r.add_header("Authorization", "Bearer " + KEY)
    return json.load(urllib.request.urlopen(r, timeout=30, context=ctx))

def velocity(views, likes, comments, hours_live, followers):
    engagement = views * 1.0 + likes * 3.0 + comments * 5.0
    eff = followers if followers > 0 else 2500
    return (engagement / hours_live / math.log(eff + 10)) * 100

# --- sample: zero-follower reels with a usable baseline ---
reels = rest("/rest/v1/reels?select=reel_id,owner_username,view_count,like_count,comment_count,owner_follower_count,posted_at&owner_follower_count=eq.0&order=created_at.desc&limit=400")
baselines = {}
owners = list({r["owner_username"] for r in reels if r.get("owner_username")})
for i in range(0, len(owners), 500):
    chunk = owners[i:i + 500]
    q = ",".join(chunk)
    for row in rest(f"/rest/v1/creator_baselines?select=username,follower_count&username=in.({q})&follower_count=gt.0"):
        baselines[row["username"]] = row["follower_count"]

matched = [r for r in reels if baselines.get(r.get("owner_username"))]
print(f"recent zero-follower reels scanned: {len(reels)}")
print(f"  with creator_baseline follower_count > 0: {len(matched)}")
print(f"  distinct creators covered: {len(set(r['owner_username'] for r in matched))}")

changed = same = crossed_up = crossed_down = 0
ratios = []
examples = []
for r in matched:
    views = r.get("view_count") or 0
    likes = r.get("like_count") or 0
    comments = r.get("comment_count") or 0
    ts = r.get("posted_at")
    if not ts:
        continue
    try:
        from datetime import datetime, timezone
        s = str(ts).replace("Z", "+00:00")
        posted = datetime.fromisoformat(s)
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)  # DB stores naive timestamps (UTC by convention)
        hours_live = max((datetime.now(timezone.utc) - posted).total_seconds() / 3600.0, 0.5)
    except Exception:
        continue
    bl = baselines[r["owner_username"]]
    v_old = velocity(views, likes, comments, hours_live, 0)   # today's path (fallback)
    v_new = velocity(views, likes, comments, hours_live, bl)  # fixed path
    if abs(v_new - v_old) < 1e-9:
        same += 1
    else:
        changed += 1
        ratios.append(v_new / v_old if v_old else float("inf"))
    old_gate = v_old > 0.3 or (views > 15000 and hours_live < 6)
    new_gate = v_new > 0.3 or (views > 15000 and hours_live < 6)
    if new_gate and not old_gate: crossed_up += 1
    if old_gate and not new_gate: crossed_down += 1
    if len(examples) < 8 and changed and v_old:
        examples.append((r["owner_username"], bl, round(v_old, 3), round(v_new, 3)))

print(f"\nvelocity CHANGED for {changed}/{len(matched)} matched reels ({100*changed/max(len(matched),1):.1f}%)")
if ratios:
    ratios.sort()
    print(f"  new/old ratio: min={ratios[0]:.3f} median={ratios[len(ratios)//2]:.3f} max={ratios[-1]:.3f}")
print(f"velocity-gate flips caused by the fix: {crossed_up} enter, {crossed_down} exit")

print("\nsample (creator, baseline_followers, velocity_old->new):")
for e in examples:
    print(f"  @{e[0]:<24} {e[1]:>9,}  {e[2]:>10} -> {e[3]}")

# --- control: reels with real follower data must be untouched ---
ctrl = rest("/rest/v1/reels?select=view_count,like_count,comment_count,owner_follower_count&owner_follower_count=gt.0&limit=50")
diffs = sum(1 for c in ctrl if velocity(c["view_count"] or 0, c["like_count"] or 0, c["comment_count"] or 0, 24, c["owner_follower_count"]) != velocity(c["view_count"] or 0, c["like_count"] or 0, c["comment_count"] or 0, 24, c["owner_follower_count"]))
identical = all(
    velocity(c["view_count"] or 0, c["like_count"] or 0, c["comment_count"] or 0, 24, c["owner_follower_count"]) ==
    velocity(c["view_count"] or 0, c["like_count"] or 0, c["comment_count"] or 0, 24, max(c["owner_follower_count"], 0))
    for c in ctrl
)
print(f"\nCONTROL ({len(ctrl)} reels with followers>0): identity preserved = {identical}, anomalies={diffs}")
