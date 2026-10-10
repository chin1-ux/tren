import os
import sys
import json
import time
import random
import asyncio
from datetime import datetime, timezone, timedelta
from collections import Counter
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
from supabase import create_client
from camoufox.async_api import AsyncCamoufox

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
now = datetime.now(timezone.utc)
week_start = (now - timedelta(days=now.weekday())).date().isoformat()

print("=" * 95)
print("PART B2: OUT-OF-POOL COVERAGE (8 CAPTION-MINED TAGS)")
print("=" * 95)

# 1. Fetch registry and stoplist
reg_res = sb.table("tag_registry").select("tag").execute().data or []
registered = {r["tag"].lower().lstrip("#") for r in reg_res if r.get("tag")}
generic_stoplist = {
    "explore", "explorepage", "viral", "fyp", "reels", "trending", "foryou",
    "instagood", "instagram", "love", "like", "follow", "video", "reelsinstagram",
    "trend", "reel", "viralvideo", "viralreels", "trendingreels", "foryoupage"
}

# 2. Mine hashtags from reels over 14 days
cutoff_14d = (now - timedelta(days=14)).isoformat()
reels_res = sb.table("reels").select("hashtags").gte("created_at", cutoff_14d).limit(3000).execute().data or []
tag_counts = Counter()
total_reels = len(reels_res)

for r in reels_res:
    seen_in_reel = set()
    for h in (r.get("hashtags") or []):
        t = str(h).lower().strip().lstrip("#")
        if t and len(t) >= 4 and t not in registered and t not in generic_stoplist and t.isascii() and t.isalnum():
            seen_in_reel.add(t)
    for t in seen_in_reel:
        tag_counts[t] += 1

# Filter tags: candidate tags mined from captions
candidate_tags = [t for t, c in tag_counts.most_common(100) if c >= 5]
print(f"Total candidate caption-mined tags identified: {len(candidate_tags)}")

# Pick 8 tags with fixed seed
SEED = 71
random.seed(SEED)
chosen_tags = random.sample(candidate_tags, min(8, len(candidate_tags)))
print(f"Chosen 8 out-of-pool tags (seed={SEED}): {chosen_tags}")

# 3. Load cookies for Camoufox
cookies_path = "backend/cookies.json"
raw_cookies = []
if os.path.exists(cookies_path):
    with open(cookies_path, "r", encoding="utf-8") as f:
        raw_cookies = json.load(f)

formatted_cookies = [
    {"name": c["name"], "value": c["value"], "domain": c.get("domain", ".instagram.com"), "path": c.get("path", "/")}
    for c in raw_cookies if isinstance(c, dict) and "name" in c and "value" in c
]

all_qualifying_items = []
loaded_tags_count = 0

async def fetch_tags():
    global loaded_tags_count
    async with AsyncCamoufox(headless=True) as browser:
        ctx = await browser.new_context(no_viewport=True)
        if formatted_cookies:
            await ctx.add_cookies(formatted_cookies)
        page = await ctx.new_page()

        print("\nWarming up browser on https://www.instagram.com/ ...")
        try:
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(3000)
        except Exception:
            pass

        eval_script = """
        async (tagName) => {
            try {
                const url = `https://www.instagram.com/api/v1/tags/web_info/?tag_name=${encodeURIComponent(tagName)}`;
                const resp = await fetch(url, {
                    headers: {
                        'X-IG-App-ID': '936619743392459',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': '*/*'
                    }
                });
                const status = resp.status;
                const data = await resp.json().catch(() => null);
                return { status, data };
            } catch (err) {
                return { status: -1, error: err.toString() };
            }
        }
        """

        cutoff_72h = now - timedelta(hours=72)
        for idx, tag in enumerate(chosen_tags, start=1):
            jitter = random.uniform(3.0, 8.0)
            print(f"Loading tag #{tag} ({idx}/8, jitter {jitter:.1f}s)...")
            await asyncio.sleep(jitter)

            t0 = time.time()
            res = await page.evaluate(eval_script, tag)
            status = res.get("status")
            dur = time.time() - t0
            print(f"  HTTP status: {status} ({dur:.2f}s)")
            if status == 429:
                print("FAIL: Instagram returned 429 Rate Limited. Stopping per rule.")
                sys.exit(1)
            if status != 200:
                print(f"  Notice: Tag #{tag} returned non-200 status {status}")
                continue

            loaded_tags_count += 1
            data = res.get("data") or {}
            sections = (data.get("data") or {}).get("recent", {}).get("sections") or (data.get("data") or {}).get("top", {}).get("sections") or []
            medias = []
            for s in sections:
                for lay in s.get("layout_content", {}).get("medias", []):
                    m = lay.get("media")
                    if m:
                        medias.append(m)

            print(f"  Scanned {len(medias)} media items from #{tag}")
            for m in medias:
                taken_at = m.get("taken_at")
                if taken_at:
                    dt = datetime.fromtimestamp(taken_at, tz=timezone.utc)
                    if dt < cutoff_72h:
                        continue
                music = m.get("music_metadata") or {}
                aud = m.get("audio") or {}
                is_orig = music.get("is_original_sound", True) and not music.get("music_info")
                aid = str(music.get("music_canonical_id") or aud.get("audio_id") or "")
                play_count = m.get("play_count") or m.get("view_count") or 0
                if aid and not is_orig:
                    all_qualifying_items.append({
                        "audio_id": aid,
                        "tag": tag,
                        "views": play_count,
                        "taken_at": taken_at
                    })

asyncio.run(fetch_tags())

print(f"\nTotal qualifying fresh non-original media items: {len(all_qualifying_items)}")
distinct_aids = list({item["audio_id"] for item in all_qualifying_items})
n_distinct = len(distinct_aids)
print(f"Distinct fresh non-original audio_ids across 8 tags: n = {n_distinct}")

# Check presence in our reels table over last 7 days
cutoff_7d = (now - timedelta(days=7)).isoformat()
our_reels = sb.table("reels").select("audio_id").in_("audio_id", distinct_aids).gte("scraped_at", cutoff_7d).execute().data or [] if distinct_aids else []
our_aids = {str(r["audio_id"]) for r in our_reels}

present_count = sum(1 for aid in distinct_aids if aid in our_aids)
coverage_share = (present_count / n_distinct) if n_distinct > 0 else 0.0

# Top third by views
top_third_coverage_share = 0.0
n_top_third = 0
if all_qualifying_items:
    sorted_by_views = sorted(all_qualifying_items, key=lambda x: x["views"], reverse=True)
    top_third_items = sorted_by_views[:max(1, len(sorted_by_views) // 3)]
    top_third_aids = list({x["audio_id"] for x in top_third_items})
    n_top_third = len(top_third_aids)
    our_top_reels = sb.table("reels").select("audio_id").in_("audio_id", top_third_aids).gte("scraped_at", cutoff_7d).execute().data or [] if top_third_aids else []
    our_top_aids = {str(r["audio_id"]) for r in our_top_reels}
    top_present_count = sum(1 for aid in top_third_aids if aid in our_top_aids)
    top_third_coverage_share = (top_present_count / n_top_third) if n_top_third > 0 else 0.0

thin_str = "(TOO THIN TO QUOTE, n < 30)" if n_distinct < 30 else "(VALID, n >= 30)"
print("\n" + "=" * 95)
print("OUT-OF-POOL COVERAGE RESULTS:")
print(f"  All fresh non-original audios coverage: {coverage_share:.1%} ({present_count}/{n_distinct}) {thin_str}")
print(f"  Top-third by views coverage          : {top_third_coverage_share:.1%} ({top_present_count}/{n_top_third})")
print("=" * 95 + "\n")

# Store in coverage_report
report_rows = [
    {"week_start": week_start, "metric": "out_of_pool_coverage", "value": float(coverage_share), "n": n_distinct, "note": f"8 tags seed={SEED}"},
    {"week_start": week_start, "metric": "out_of_pool_top_third", "value": float(top_third_coverage_share), "n": n_top_third, "note": f"top third by views seed={SEED}"},
]
sb.table("coverage_report").insert(report_rows).execute()
print("Saved metrics to coverage_report table.")
