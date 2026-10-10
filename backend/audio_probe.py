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


INDIC_THAI_RANGES = [
    (0x0900, 0x0DFF),  # Devanagari, Bengali, Gurmukhi, Gujarati, Oriya, Tamil, Telugu, Kannada, Malayalam
    (0x0E00, 0x0E7F),  # Thai
]


def has_indic_or_thai(text: str) -> bool:
    for c in text:
        cp = ord(c)
        for start, end in INDIC_THAI_RANGES:
            if start <= cp <= end:
                return True
    return False


def is_latin_string(text: str) -> bool:
    return all(ord(c) < 128 for c in text)


def derive_tag_variants(title: str, artist: Optional[str]) -> Tuple[List[Tuple[str, str]], Optional[str]]:
    """
    Order 68 Part 4.3:
    For titles with >=2 words derive up to 2 tags:
    - Underscore-joined (first for non-Latin scripts) and concatenated.
    - Stop at the first that returns >=1 media matched by audio_id or song_key.
    - Record tag_variant in probe_log (additive column).
    """
    if has_indic_or_thai(title):
        latin_words = re.findall(r'[a-zA-Z0-9]+', title)
        latin_clean = "".join(w.lower() for w in latin_words if len(w) >= 2)
        if latin_clean and len(latin_clean) >= 4 and not latin_clean.startswith("mix"):
            return [(latin_clean, "latin_translit")], None
        return [], "indic_script_no_latin_tag"

    # Check words in title
    clean_title = re.sub(r'[^\w\s]', '', title.strip())
    words = [w for w in re.split(r'[\s_]+', clean_title) if w]
    is_latin = is_latin_string(title)

    if len(words) >= 2:
        tag_underscore = '_'.join(w.lower() for w in words)
        tag_concat = ''.join(w.lower() for w in words)
        if not is_latin:
            # Underscore-joined first for non-Latin scripts (e.g. Arabic #امشي_بثقه)
            return [(tag_underscore, "underscore"), (tag_concat, "concatenated")], None
        else:
            # Concatenated first for Latin scripts
            return [(tag_concat, "concatenated"), (tag_underscore, "underscore")], None

    t_norm = normalize_title(title)
    if not t_norm:
        return [], "invalid_title"

    variants = [(t_norm, "single")]
    a_norm = normalize_artist(artist)
    if a_norm:
        combo = f"{t_norm}{a_norm}"
        if combo != t_norm:
            variants.append((combo, "artist_combo"))

    return variants[:2], None


def compute_candidates(sb, dry_run: bool = False) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """
    Order 64 Part A2 Quota Allocation (total <= 30 per run):
    - 12 EARLY: song_key with 2-5 distinct creators in own reels over 72h, ranked by watchlist score.
    - 8 HOT-UNKNOWN: hot p95 reel, song not in trends, own creators < 6, ranked by velocity desc.
    - 6 COVERAGE: seed titles (dedup by song_key, not in reels 14d, not probed 7d, creators < 6).
    - 4 RE-PROBE: top watchlist songs for growth, >=6h since last probe, creators < 6.
    Skip song_keys with >=6 own creators (they go to Part D promotion instead).
    12h cooldown on EARLY/HOT-UNKNOWN, 200/day cap unchanged.
    Unused quota flows to the next bucket (waterfall overflow).
    """
    now_utc = datetime.now(timezone.utc)
    d7_ago = (now_utc - timedelta(days=7)).isoformat()
    h72_ago = (now_utc - timedelta(hours=72)).isoformat()
    h12_ago = (now_utc - timedelta(hours=12)).isoformat()
    h6_ago = (now_utc - timedelta(hours=6)).isoformat()
    d14_ago = (now_utc - timedelta(days=14)).isoformat()

    # 1. Fetch audios and song_keys already in active trends
    trends_res = sb.table("trends").select("audio_id, audio_title, audio_artist").neq("status", "unqualified").execute()
    trend_audio_ids = {str(r["audio_id"]) for r in (trends_res.data or []) if r.get("audio_id")}
    trend_keys = {
        compute_song_key(r.get("audio_title"), r.get("audio_artist"))
        for r in (trends_res.data or [])
        if compute_song_key(r.get("audio_title"), r.get("audio_artist"))
    }

    # 2. Fetch 7-day reels for percentile calculation
    logger.info("Computing 7-day reel distribution for percentile calculation...")
    offset = 0
    PAGE_SIZE = 1000
    reels_7d = []
    while True:
        res = sb.table("reels") \
            .select("id, reel_id, audio_id, audio_title, audio_artist, is_original_audio, view_count, velocity_score, created_at") \
            .gte("created_at", d7_ago) \
            .not_.is_("audio_id", "null") \
            .order("id", desc=False) \
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

    # 3. Pull 72h reels from Supabase and group by song_key
    reels_72h = []
    offset = 0
    while True:
        res = sb.table("reels") \
            .select("id, reel_id, audio_id, audio_title, audio_artist, owner_username, is_original_audio, view_count, velocity_score, created_at") \
            .gte("created_at", h72_ago) \
            .order("id", desc=False) \
            .range(offset, offset + PAGE_SIZE - 1) \
            .execute()
        data = res.data or []
        for r in data:
            if not r.get("is_original_audio"):
                reels_72h.append(r)
        if len(data) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    song_stats: Dict[str, Dict[str, Any]] = {}
    for r in reels_72h:
        sk = compute_song_key(r.get("audio_title"), r.get("audio_artist"))
        if not sk or sk in trend_keys:
            continue
        aid = str(r.get("audio_id") or "").strip()
        if aid and aid in trend_audio_ids:
            continue

        if sk not in song_stats:
            song_stats[sk] = {
                "song_key": sk,
                "title": r.get("audio_title"),
                "artist": r.get("audio_artist"),
                "audio_id": aid if aid and aid not in ("0", "Unknown") else None,
                "creators": set(),
                "reels": 0,
                "max_views": 0,
                "max_velocity": 0.0,
                "hot_reels": 0,
                "newest_posted_at": None,
            }
        st = song_stats[sk]
        u = r.get("owner_username")
        if u:
            st["creators"].add(u)
        st["reels"] += 1
        p_at = r.get("posted_at") or r.get("created_at")
        if p_at and (st.get("newest_posted_at") is None or p_at > st.get("newest_posted_at")):
            st["newest_posted_at"] = p_at
        v_cnt = int(r.get("view_count") or 0)
        v_score = float(r.get("velocity_score") or 0.0)
        if v_cnt > st["max_views"]:
            st["max_views"] = v_cnt
        if v_score > st["max_velocity"]:
            st["max_velocity"] = v_score
        if v_cnt >= p95_views or v_score >= p95_velo:
            st["hot_reels"] += 1

    # 4. Check probe history for cooldowns
    probed_12h: Set[str] = set()
    probed_6h: Set[str] = set()
    probed_7d: Set[str] = set()
    try:
        pl_res = sb.table("probe_log").select("song_key, ts").gte("ts", (now_utc - timedelta(days=7)).isoformat()).execute()
        for p in (pl_res.data or []):
            sk = p.get("song_key")
            ts = p.get("ts") or ""
            if sk:
                probed_7d.add(sk)
                if ts >= h12_ago:
                    probed_12h.add(sk)
                if ts >= h6_ago:
                    probed_6h.add(sk)
    except Exception as ple:
        logger.warning(f"Error checking probe_log history: {ple}")

    # Import watchlist score calculator
    from watchlist import calculate_v3_score

    # (a) EARLY candidates: 2-5 distinct creators in own reels over 72h, ranked by (creators desc, recency desc, score desc)
    early_pool: List[Dict[str, Any]] = []
    for sk, st in song_stats.items():
        n_creators = len(st["creators"])
        if 2 <= n_creators <= 5:
            if sk in probed_12h:
                continue
            tags, skip = derive_tag_variants(st["title"], st["artist"])
            if skip and skip != "indic_script":
                continue
            score, _ = calculate_v3_score(st["max_views"], n_creators, st["reels"], st["max_velocity"], 0.0)
            early_pool.append({
                "song_key": sk,
                "trigger": "early",
                "title": st["title"],
                "artist": st["artist"],
                "audio_id": st["audio_id"],
                "velocity": st["max_velocity"],
                "views": st["max_views"],
                "creators_count": n_creators,
                "newest_posted_at": str(st.get("newest_posted_at") or ""),
                "score": score,
            })
    early_pool.sort(key=lambda x: (x["creators_count"], str(x["newest_posted_at"]), x["score"]), reverse=True)

    # (b) HOT-UNKNOWN candidates: hot p95 reel, song not in trends, own creators < 6, ranked by velocity desc
    hot_unknown_pool: List[Dict[str, Any]] = []
    for sk, st in song_stats.items():
        n_creators = len(st["creators"])
        if n_creators < 6 and st["hot_reels"] > 0:
            if sk in probed_12h:
                continue
            tags, skip = derive_tag_variants(st["title"], st["artist"])
            if skip and skip != "indic_script":
                continue
            hot_unknown_pool.append({
                "song_key": sk,
                "trigger": "hot_unknown",
                "title": st["title"],
                "artist": st["artist"],
                "audio_id": st["audio_id"],
                "velocity": st["max_velocity"],
                "views": st["max_views"],
                "creators_count": n_creators,
                "score": st["max_velocity"],
            })
    hot_unknown_pool.sort(key=lambda x: x["velocity"], reverse=True)

    # (c) COVERAGE candidates: seed titles (dedup by song_key, not in reels 14d, not probed 7d, creators < 6)
    coverage_pool: List[Dict[str, Any]] = []
    try:
        reels_14d_keys: Set[str] = set()
        r14_res = sb.table("reels").select("audio_title, audio_artist").gte("created_at", d14_ago).execute()
        for r in (r14_res.data or []):
            sk = compute_song_key(r.get("audio_title"), r.get("audio_artist"))
            if sk:
                reels_14d_keys.add(sk)

        seeds_res = sb.table("seed_audios").select("title, artist, rank").order("rank", desc=False).limit(200).execute()
        seen_cov_keys: Set[str] = set()
        for s in (seeds_res.data or []):
            sk = compute_song_key(s.get("title"), s.get("artist"))
            if sk and sk not in reels_14d_keys and sk not in probed_7d and sk not in trend_keys and sk not in seen_cov_keys:
                tags, skip = derive_tag_variants(s.get("title"), s.get("artist"))
                if skip and skip != "indic_script":
                    continue
                seen_cov_keys.add(sk)
                coverage_pool.append({
                    "song_key": sk,
                    "trigger": "coverage",
                    "title": s.get("title"),
                    "artist": s.get("artist"),
                    "audio_id": None,
                    "velocity": 0.0,
                    "views": 0,
                    "creators_count": 0,
                    "score": 0.0,
                })
            if len(coverage_pool) >= 15:
                break
    except Exception as ce:
        logger.warning(f"Error checking coverage pool: {ce}")

    # (d) RE-PROBE candidates: top active watchlist songs for growth, >=6h since last probe, creators < 6
    reprobe_pool: List[Dict[str, Any]] = []
    try:
        wl_res = sb.table("watchlist").select("song_key, audio_id, score, reasons, status").eq("status", "watching").order("score", desc=True).execute()
        for w in (wl_res.data or []):
            sk = w.get("song_key")
            if not sk or sk in trend_keys or sk in probed_6h:
                continue
            # Check own creators in song_stats
            st = song_stats.get(sk, {})
            n_creators = len(st.get("creators", set()))
            if n_creators >= 6:
                continue
            tags, skip = derive_tag_variants((w.get("reasons") or {}).get("title") or sk.split("|")[0], (w.get("reasons") or {}).get("artist") or (sk.split("|")[1] if "|" in sk else None))
            if skip and skip != "indic_script":
                continue
            reprobe_pool.append({
                "song_key": sk,
                "trigger": "re_probe",
                "title": (w.get("reasons") or {}).get("title") or sk.split("|")[0],
                "artist": (w.get("reasons") or {}).get("artist") or (sk.split("|")[1] if "|" in sk else None),
                "audio_id": str(w.get("audio_id") or ""),
                "velocity": st.get("max_velocity", 0.0),
                "views": st.get("max_views", 0),
                "creators_count": n_creators,
                "score": float(w.get("score") or 0.0),
            })
    except Exception as wle:
        logger.warning(f"Error checking reprobe pool: {wle}")

    # Quotas: 12 EARLY, 8 HOT-UNKNOWN, 6 COVERAGE, 4 RE-PROBE (Total <= 30)
    QUOTAS = {"early": 12, "hot_unknown": 8, "coverage": 6, "re_probe": 4}
    selected: List[Dict[str, Any]] = []
    selected_keys: Set[str] = set()
    allocated_counts = {"early": 0, "hot_unknown": 0, "coverage": 0, "re_probe": 0}

    pools = {
        "early": early_pool,
        "hot_unknown": hot_unknown_pool,
        "coverage": coverage_pool,
        "re_probe": reprobe_pool,
    }

    # Pass 1: standard quota allocation
    for bucket in ["early", "hot_unknown", "coverage", "re_probe"]:
        q = QUOTAS[bucket]
        for c in pools[bucket]:
            if allocated_counts[bucket] >= q:
                break
            if c["song_key"] not in selected_keys:
                selected_keys.add(c["song_key"])
                c["trigger"] = bucket
                selected.append(c)
                allocated_counts[bucket] += 1

    # Pass 2: waterfall overflow (unused slots flow to next buckets up to 30)
    if len(selected) < 30:
        for bucket in ["early", "hot_unknown", "coverage", "re_probe"]:
            for c in pools[bucket]:
                if len(selected) >= 30:
                    break
                if c["song_key"] not in selected_keys:
                    selected_keys.add(c["song_key"])
                    c["trigger"] = bucket
                    selected.append(c)
                    allocated_counts[bucket] += 1

    # Log allocation per run
    logger.info(
        f"Probe Allocation Log: early={allocated_counts['early']}, "
        f"hot_unknown={allocated_counts['hot_unknown']}, "
        f"coverage={allocated_counts['coverage']}, "
        f"re_probe={allocated_counts['re_probe']} (Total: {len(selected)})"
    )

    # Map all known audio_ids in DB for each song_key to enable multi-ID matching
    all_keys = [c["song_key"] for c in selected]
    audio_id_map: Dict[str, Set[str]] = {k: set() for k in all_keys}
    if all_keys:
        for r in reels_72h:
            sk = compute_song_key(r.get("audio_title"), r.get("audio_artist"))
            if sk in audio_id_map and r.get("audio_id"):
                audio_id_map[sk].add(str(r["audio_id"]))

    for c in selected:
        c["known_audio_ids"] = list(audio_id_map.get(c["song_key"], set()))
        if c.get("audio_id") and c["audio_id"] not in c["known_audio_ids"]:
            c["known_audio_ids"].append(c["audio_id"])

    return selected, percentiles


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
            tag_variants, skip_reason = derive_tag_variants(title, artist)
            if skip_reason:
                logger.info(f"Skipping candidate '{title}' by '{artist}' (reason: {skip_reason})")
                if not dry_run:
                    try:
                        pl_entry = {
                            "tag": f"SKIP:{skip_reason}",
                            "trigger": cand.get("trigger"),
                            "candidate_audio_id": cand.get("audio_id"),
                            "song_key": cand["song_key"],
                            "skip_reason": skip_reason,
                            "http_status": 0,
                            "medias": 0,
                            "matched": 0,
                            "creators": 0,
                            "run_id": run_id,
                        }
                        sb.table("probe_log").insert(pl_entry).execute()
                    except Exception as ple:
                        logger.warning(f"Error inserting skipped probe_log: {ple}")
                continue

            if not tag_variants:
                continue

            cand_norm_title = normalize_title(title)
            is_coverage = cand.get("trigger") == "coverage"

            for v_idx, tag_item in enumerate(tag_variants):
                tag, var_name = tag_item if isinstance(tag_item, tuple) else (tag_item, "default")
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

                        m_artist = (music.get("artist_name") or orig.get("artist_name") or "").strip()
                        m_sk = compute_song_key(m_title, m_artist)

                        is_match = False
                        if any(aid in cand["known_audio_ids"] for aid in m_aids):
                            is_match = True
                        elif m_sk and m_sk == cand["song_key"]:
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
                            "tag_variant": var_name,
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
                    f"Probe #{probes_executed}: tag=#{tag} [{var_name}] [{cand.get('trigger')}] -> status={status}, "
                    f"medias={len(medias)}, matched={len(matched_rows)}, creators={len(creators)} ({call_duration}s)"
                )

                # Stop at the first that returns >=1 media matched BY audio_id or song_key
                if len(matched_rows) > 0:
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
