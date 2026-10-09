"""
backend/audio_probe.py - Order 61 Part D Audio Probe Engine

Probes Instagram hashtag explore API from inside a real browser session (Camoufox)
via page.evaluate to ingest dense reel signals for high-velocity candidates,
active watchlist songs, and rotating coverage chart titles.
"""

import os
import re
import sys
import json
import time
import random
import logging
import asyncio
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Set, Tuple
from dotenv import load_dotenv

# Ensure backend directory in path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from song_key import compute_song_key, normalize_title, normalize_artist
from supabase import create_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audio_probe")


def get_supabase():
    load_dotenv(os.path.join(backend_dir, ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials not configured.")
    return create_client(url, key)


def derive_tag_variants(title: str, artist: Optional[str]) -> List[str]:
    """
    Derive up to two tag variants:
    1. Title token (clean alphanumeric of normalized title)
    2. Title token + first artist token (if artist exists)
    """
    t_norm = normalize_title(title)
    if not t_norm:
        return []

    variants = [t_norm]
    a_norm = normalize_artist(artist)
    if a_norm:
        combo = f"{t_norm}{a_norm}"
        if combo != t_norm:
            variants.append(combo)

    return variants[:2]


def compute_candidates(sb, dry_run: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Computes candidates according to D1:
    (a) HOT: non-original audio, reel posted <=72h, with view_count or velocity_score >= 95th percentile
        of the 7-day distribution.
    (b) Active watchlist song_keys not probed in the last 12h.
    (c) COVERAGE: 10 rotating titles from seed_audios (dedup by song_key, not seen in reels in 14 days,
        not probed in 7 days).
    Exclude audios already in trends. Rank hot by velocity desc.
    """
    now_utc = datetime.now(timezone.utc)
    d7_ago = (now_utc - timedelta(days=7)).isoformat()
    h72_ago = (now_utc - timedelta(hours=72)).isoformat()
    h12_ago = (now_utc - timedelta(hours=12)).isoformat()
    d14_ago = (now_utc - timedelta(days=14)).isoformat()

    # 1. Fetch audios already in active trends
    trends_res = sb.table("trends").select("audio_id").neq("status", "unqualified").execute()
    trend_audio_ids = {str(r["audio_id"]) for r in (trends_res.data or []) if r.get("audio_id")}

    # 2. Fetch 7-day reels (paginated, columns only)
    logger.info("Computing 7-day reel distribution for percentile calculation...")
    offset = 0
    PAGE_SIZE = 1000
    reels_7d = []
    while True:
        res = sb.table("reels") \
            .select("reel_id, audio_id, audio_title, audio_artist, is_original_audio, view_count, velocity_score, created_at") \
            .gte("created_at", d7_ago) \
            .not_.is_("audio_id", "null") \
            .range(offset, offset + PAGE_SIZE - 1) \
            .execute()
        data = res.data or []
        for r in data:
            if not r.get("is_original_audio"):
                aid = str(r.get("audio_id") or "").strip()
                if aid and aid not in ("0", "Unknown") and aid not in trend_audio_ids:
                    reels_7d.append(r)
        if len(data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    # Calculate 95th percentiles over 7-day non-original reels
    views_list = sorted([float(r.get("view_count") or 0) for r in reels_7d])
    velo_list = sorted([float(r.get("velocity_score") or 0.0) for r in reels_7d])

    p95_views = 0.0
    p95_velo = 0.0
    if views_list:
        idx_v = int(len(views_list) * 0.95)
        p95_views = views_list[min(idx_v, len(views_list) - 1)]
    if velo_list:
        idx_vel = int(len(velo_list) * 0.95)
        p95_velo = velo_list[min(idx_vel, len(velo_list) - 1)]

    percentiles = {"p95_views": p95_views, "p95_velocity": p95_velo}
    logger.info(f"7-Day Non-Original Reels: {len(reels_7d)} | 95th Percentile Views: {p95_views:.1f} | 95th Percentile Velocity: {p95_velo:.2f}")

    # (a) HOT candidates (posted <=72h, views >= p95 OR velocity >= p95)
    hot_candidates_map: Dict[str, Dict[str, Any]] = {}
    for r in reels_7d:
        created_at = r.get("created_at") or ""
        if created_at >= h72_ago:
            v_cnt = float(r.get("view_count") or 0)
            v_score = float(r.get("velocity_score") or 0.0)
            if v_cnt >= p95_views or v_score >= p95_velo:
                sk = compute_song_key(r.get("audio_title"), r.get("audio_artist"))
                if sk:
                    if sk not in hot_candidates_map or v_score > hot_candidates_map[sk]["velocity"]:
                        hot_candidates_map[sk] = {
                            "song_key": sk,
                            "trigger": "hot",
                            "title": r.get("audio_title"),
                            "artist": r.get("audio_artist"),
                            "audio_id": str(r.get("audio_id")),
                            "velocity": v_score,
                            "views": v_cnt,
                        }

    # (b) Active watchlist song_keys not probed in the last 12h
    watchlist_candidates_map: Dict[str, Dict[str, Any]] = {}
    try:
        wl_res = sb.table("watchlist").select("song_key, audio_id, reasons, status").eq("status", "watching").execute()
        active_wl = wl_res.data or []
        wl_keys = [w["song_key"] for w in active_wl if w.get("song_key")]

        # Check recent probe_log for watchlist keys
        probed_recently: Set[str] = set()
        if wl_keys:
            pl_res = sb.table("probe_log").select("song_key").in_("song_key", wl_keys).gte("ts", h12_ago).execute()
            probed_recently = {p["song_key"] for p in (pl_res.data or []) if p.get("song_key")}

        for w in active_wl:
            sk = w.get("song_key")
            if sk and sk not in probed_recently and sk not in hot_candidates_map:
                watchlist_candidates_map[sk] = {
                    "song_key": sk,
                    "trigger": "watchlist",
                    "title": (w.get("reasons") or {}).get("title") or sk.split("|")[0],
                    "artist": (w.get("reasons") or {}).get("artist") or (sk.split("|")[1] if "|" in sk else None),
                    "audio_id": str(w.get("audio_id") or ""),
                    "velocity": 0.0,
                    "views": 0,
                }
    except Exception as wle:
        logger.warning(f"Error checking watchlist candidates: {wle}")

    # (c) COVERAGE: 10 rotating titles from seed_audios (dedup by song_key, not seen in reels in 14 days, not probed in 7 days)
    coverage_candidates_map: Dict[str, Dict[str, Any]] = {}
    try:
        # Build 14-day reels song_key set
        reels_14d_keys: Set[str] = set()
        r14_res = sb.table("reels").select("audio_title, audio_artist").gte("created_at", d14_ago).execute()
        for r in (r14_res.data or []):
            sk = compute_song_key(r.get("audio_title"), r.get("audio_artist"))
            if sk:
                reels_14d_keys.add(sk)

        # Build 7-day probed song_key set
        d7_probed_keys: Set[str] = set()
        pl7_res = sb.table("probe_log").select("song_key").gte("ts", (now_utc - timedelta(days=7)).isoformat()).execute()
        for p in (pl7_res.data or []):
            if p.get("song_key"):
                d7_probed_keys.add(p["song_key"])

        # Fetch seed_audios
        seeds_res = sb.table("seed_audios").select("title, artist").order("rank", desc=False).limit(200).execute()
        for s in (seeds_res.data or []):
            sk = compute_song_key(s.get("title"), s.get("artist"))
            if sk and sk not in reels_14d_keys and sk not in d7_probed_keys:
                if sk not in hot_candidates_map and sk not in watchlist_candidates_map and sk not in coverage_candidates_map:
                    coverage_candidates_map[sk] = {
                        "song_key": sk,
                        "trigger": "coverage",
                        "title": s.get("title"),
                        "artist": s.get("artist"),
                        "audio_id": None,
                        "velocity": 0.0,
                        "views": 0,
                    }
            if len(coverage_candidates_map) >= 10:
                break
    except Exception as ce:
        logger.warning(f"Error checking coverage candidates: {ce}")

    # Merge candidates: HOT (ranked by velocity desc) + Watchlist + Coverage (max 10)
    sorted_hot = sorted(hot_candidates_map.values(), key=lambda x: x["velocity"], reverse=True)
    all_candidates = sorted_hot + list(watchlist_candidates_map.values()) + list(coverage_candidates_map.values())

    # Map all known audio_ids in DB for each song_key to enable multi-ID matching
    all_keys = [c["song_key"] for c in all_candidates]
    audio_id_map: Dict[str, Set[str]] = {k: set() for k in all_keys}
    if all_keys:
        # Search reels for known audio IDs matching these song_keys
        for r in reels_7d:
            sk = compute_song_key(r.get("audio_title"), r.get("audio_artist"))
            if sk in audio_id_map and r.get("audio_id"):
                audio_id_map[sk].add(str(r["audio_id"]))

    for c in all_candidates:
        c["known_audio_ids"] = list(audio_id_map.get(c["song_key"], set()))
        if c.get("audio_id") and c["audio_id"] not in c["known_audio_ids"]:
            c["known_audio_ids"].append(c["audio_id"])

    logger.info(
        f"Candidate Breakdown: HOT={len(sorted_hot)}, Watchlist={len(watchlist_candidates_map)}, "
        f"Coverage={len(coverage_candidates_map)} (Total: {len(all_candidates)})"
    )
    return all_candidates, percentiles


async def run_probe_session(candidates: List[Dict[str, Any]], sb, dry_run: bool = False):
    """
    Runs Camoufox session with page.evaluate fetching https://www.instagram.com/api/v1/tags/web_info/
    Budget: max 30 probes/run, max 200/day. Jitter 3-8s. Stops on 429/401/challenge.
    """
    now_utc = datetime.now(timezone.utc)
    day_ago = (now_utc - timedelta(days=1)).isoformat()

    # 1. Budget check from probe_log
    daily_count = 0
    try:
        pl_cnt = sb.table("probe_log").select("id", count="exact").gte("ts", day_ago).execute()
        daily_count = pl_cnt.count or 0
    except Exception as de:
        logger.warning(f"Could not check daily probe_log count: {de}")

    DAILY_MAX = 200
    RUN_MAX = 30
    remaining_daily = max(0, DAILY_MAX - daily_count)
    run_budget = min(RUN_MAX, remaining_daily)

    if run_budget <= 0:
        logger.info(f"Daily probe budget exhausted ({daily_count}/{DAILY_MAX}). Skipping run.")
        return

    logger.info(f"Probe Session Budget: {run_budget} probes available (Today: {daily_count}/{DAILY_MAX})")

    # 2. Setup cookies
    cookies_path = os.path.join(backend_dir, "cookies.json")
    raw_c = []
    if os.path.exists(cookies_path):
        try:
            with open(cookies_path, "r", encoding="utf-8") as f:
                raw_c = json.load(f)
        except Exception as ce:
            logger.warning(f"Error reading {cookies_path}: {ce}")
    elif os.getenv("INSTAGRAM_COOKIES_B64"):
        try:
            import base64
            b64_val = os.getenv("INSTAGRAM_COOKIES_B64").strip()
            raw_c = json.loads(base64.b64decode(b64_val).decode("utf-8"))
        except Exception as b64e:
            logger.warning(f"Error decoding INSTAGRAM_COOKIES_B64: {b64e}")

    formatted_cookies = [
        {"name": c["name"], "value": c["value"], "domain": c.get("domain", ".instagram.com"), "path": c.get("path", "/")}
        for c in raw_c if isinstance(c, dict) and "name" in c and "value" in c
    ]

    from camoufox.async_api import AsyncCamoufox

    run_id = os.getenv("GITHUB_RUN_ID")
    probes_executed = 0
    total_matched_reels = 0
    total_probe_rows_written = 0

    async with AsyncCamoufox(headless=True) as browser:
        ctx = await browser.new_context(no_viewport=True)
        if formatted_cookies:
            await ctx.add_cookies(formatted_cookies)

        page = await ctx.new_page()

        # Warm-up once
        try:
            logger.info("Warming up browser session on https://www.instagram.com/ ...")
            t0 = time.time()
            await page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(3000)
            logger.info(f"Warm-up complete in {time.time()-t0:.2f}s, url: {page.url}")
        except Exception as we:
            logger.warning(f"Warm-up navigation warning: {we}")

        for cand in candidates:
            if probes_executed >= run_budget:
                logger.info(f"Run probe budget ({run_budget}) reached. Stopping session.")
                break

            title = cand.get("title") or ""
            artist = cand.get("artist")
            tag_variants = derive_tag_variants(title, artist)
            if not tag_variants:
                continue

            cand_norm_title = normalize_title(title)
            is_coverage = cand.get("trigger") == "coverage"

            for v_idx, tag in enumerate(tag_variants):
                if probes_executed >= run_budget:
                    break

                target_url = f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={tag}"
                t_call = time.time()

                eval_res = await page.evaluate("""
                    async (targetUrl) => {
                        const getCookie = (name) => {
                            const value = `; ${document.cookie}`;
                            const parts = value.split(`; ${name}=`);
                            if (parts.length === 2) return parts.pop().split(';').shift();
                            return '';
                        };
                        const csrf = getCookie('csrftoken');
                        try {
                            const res = await fetch(targetUrl, {
                                method: 'GET',
                                headers: {
                                    'Accept': '*/*',
                                    'X-IG-App-ID': '936619743392459',
                                    'X-CSRFToken': csrf,
                                    'X-Requested-With': 'XMLHttpRequest'
                                },
                                credentials: 'include'
                            });
                            const status = res.status;
                            let json = null;
                            let text = '';
                            try { json = await res.json(); } catch(e) { text = await res.text().catch(() => ''); }
                            return { status, json, text, redirected: res.redirected, url: res.url };
                        } catch(err) {
                            return { status: 0, error: err.toString() };
                        }
                    }
                """, target_url)

                call_duration = round(time.time() - t_call, 2)
                status = eval_res.get("status", 0)
                probes_executed += 1

                # Check abort conditions (429, 401, challenge, login redirect)
                if status in (429, 401) or "challenge" in eval_res.get("url", "") or "login" in eval_res.get("url", ""):
                    logger.error(f"ABORT TRIGGERED: status={status}, url={eval_res.get('url')}. Stopping probe session.")
                    return

                medias = []
                matched_rows = []
                creators = set()

                if status == 200 and eval_res.get("json"):
                    data = eval_res["json"].get("data", {})
                    sections = (data.get("top", {}).get("sections", []) + data.get("recent", {}).get("sections", []))
                    for sec in sections:
                        for mw in (sec.get("layout_content") or {}).get("medias", []):
                            m = mw.get("media")
                            if m:
                                medias.append(m)

                    for m in medias:
                        clips = m.get("clips_metadata") or {}
                        music = (clips.get("music_info") or {}).get("music_asset_info") or {}
                        orig = clips.get("original_sound_info") or {}
                        m_aids = [str(x) for x in [music.get("audio_cluster_id"), music.get("id"), orig.get("audio_asset_id"), orig.get("id")] if x]
                        m_title = (music.get("title") or orig.get("original_audio_title") or "").strip()
                        m_title_norm = normalize_title(m_title) or ""

                        is_match = False
                        if any(aid in cand["known_audio_ids"] for aid in m_aids):
                            is_match = True
                        elif is_coverage and cand_norm_title and (cand_norm_title == m_title_norm or cand_norm_title in m_title_norm):
                            is_match = True

                        if is_match:
                            code = m.get("code")
                            if code:
                                u = (m.get("user") or {}).get("username")
                                if u:
                                    creators.add(u)
                                t_at = m.get("taken_at")
                                dt_taken = datetime.fromtimestamp(t_at, tz=timezone.utc).isoformat() if t_at else None
                                matched_rows.append({
                                    "reel_code": code,
                                    "audio_id": cand.get("audio_id") or (m_aids[0] if m_aids else None),
                                    "song_key": cand["song_key"],
                                    "creator": u,
                                    "taken_at": dt_taken,
                                    "views": m.get("view_count") or m.get("play_count") or 0,
                                    "comments": m.get("comment_count") or 0,
                                    "source_tag": tag,
                                    "run_id": run_id
                                })

                # Persistence
                if not dry_run:
                    if matched_rows:
                        try:
                            # Upsert matched reels into probe_reels
                            sb.table("probe_reels").upsert(matched_rows, on_conflict="reel_code").execute()
                            total_probe_rows_written += len(matched_rows)
                        except Exception as pre:
                            logger.warning(f"Error upserting probe_reels: {pre}")

                    # Log to probe_log
                    try:
                        pl_entry = {
                            "tag": tag,
                            "trigger": cand.get("trigger"),
                            "candidate_audio_id": cand.get("audio_id"),
                            "song_key": cand["song_key"],
                            "http_status": status,
                            "medias": len(medias),
                            "matched": len(matched_rows),
                            "creators": len(creators),
                            "run_id": run_id
                        }
                        sb.table("probe_log").insert(pl_entry).execute()
                    except Exception as ple:
                        logger.warning(f"Error inserting probe_log: {ple}")

                total_matched_reels += len(matched_rows)
                logger.info(
                    f"Probe #{probes_executed}: tag=#{tag} [{cand.get('trigger')}] -> status={status}, "
                    f"medias={len(medias)}, matched={len(matched_rows)}, creators={len(creators)} ({call_duration}s)"
                )

                # If first variant matched or 200 with matches, do NOT try second variant
                if len(matched_rows) > 0 or status != 404 and len(medias) > 0:
                    break

                # Jitter before potential variant 2
                jitter = random.uniform(3.0, 8.0)
                await page.wait_for_timeout(int(jitter * 1000))

            # Jitter between candidates (3-8s)
            jitter = random.uniform(3.0, 8.0)
            await page.wait_for_timeout(int(jitter * 1000))

        await ctx.close()

    logger.info(
        f"Probe Session Finished: probes_executed={probes_executed}, "
        f"total_matched_reels={total_matched_reels}, rows_persisted={total_probe_rows_written}"
    )


def main():
    parser = argparse.ArgumentParser(description="Run Audio Probe Job (Order 61 Part D)")
    parser.add_argument("--no-write", action="store_true", help="Dry-run mode: do not write to production database")
    args = parser.parse_args()

    sb = get_supabase()
    candidates, percentiles = compute_candidates(sb, dry_run=args.no_write)
    asyncio.run(run_probe_session(candidates, sb, dry_run=args.no_write))


if __name__ == "__main__":
    main()
