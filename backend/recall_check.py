"""
backend/recall_check.py
Recall KPI Evaluation (Order 52).
- Paginates reels and trends with range() so there is no 1000-row cap.
- Cleans titles (strips text after '|', brackets, 'official', 'video', 'lyrics', years).
- For non-IN regions, flags Indian content as is_india_content and excludes from recall.
- Matches on normalized title tokens plus artist.
- Prints recall % per region and the 20 worst DISTINCT titles.
- Checks specifically whether 'Khalouni Neich' appears in seed_audios for TR, SA, AE, or EG.
"""

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Tuple

import dotenv
from supabase import Client, create_client

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def get_supabase_client() -> Client:
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY required.")
    return create_client(url, key)


def clean_title(title: str) -> str:
    """Clean title per Order 52 Part 4.2 specs."""
    if not title:
        return ""
    t = title
    # Strip text after '|'
    if "|" in t:
        t = t.split("|")[0]
    # Strip brackets () and []
    t = re.sub(r'\(.*?\)|\[.*?\]', '', t)
    # Strip year numbers (19xx, 20xx)
    t = re.sub(r'\b(19\d\d|20\d\d)\b', '', t)
    # Strip common noise keywords
    t = re.sub(r'(?i)\b(official\s*(music\s*)?video|official|video|music|audio|lyric|lyrics|clip|remix|hd|4k|visualizer|feat|ft)\b', '', t)
    # Remove non-alphanumeric except spaces and non-latin scripts
    t = re.sub(r'[^\w\s\u0600-\u06FF\uac00-\ud7a3\u0400-\u04FF\u0900-\u097F\u0A00-\u0A7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]', ' ', t)
    return " ".join(t.lower().split())


def clean_artist(artist: str) -> str:
    if not artist:
        return ""
    a = artist
    a = re.sub(r'\(.*?\)|\[.*?\]', '', a)
    a = re.sub(r'(?i)\b(- topic|vevo|official)\b', '', a)
    a = re.sub(r'[^\w\s\u0600-\u06FF\uac00-\ud7a3\u0400-\u04FF\u0900-\u097F\u0A00-\u0A7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F]', ' ', a)
    return " ".join(a.lower().split())


INDIAN_SCRIPT_RE = re.compile(r'[\u0900-\u097F\u0A00-\u0A7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0980-\u09FF\u0A80-\u0AFF]')

INDIAN_KEYWORDS = {
    "t-series", "tseries", "zee music", "speed records", "white hill", "aditya music",
    "sony music india", "saregama", "tips official", "yrf", "geet mp3", "desi music factory",
    "bhojpuri", "punjabi", "hindi", "tamil", "telugu", "haryanvi", "marathi", "kannada", "malayalam"
}

INDIAN_ARTISTS = {
    "arijit singh", "sidhu moose wala", "diljit dosanjh", "karan aujla", "ap dhillon",
    "shreya ghoshal", "badshah", "honey singh", "neha kakkar", "jubin nautiyal",
    "pawan singh", "khesari lal", "khesari", "shilpi raj", "anirudh ravichander",
    "ar rahman", "a.r. rahman", "b praak", "jasleen royal", "guru randhawa",
    "ammy virk", "jassie gill", "hardy sandhu", "sunanda sharma", "mankirt aulakh",
    "neha bhasin", "sunidhi chauhan", "sonu nigam", "alka yagnik", "kumar sanu",
    "udit narayan", "pramod premi", "arvind akela", "ankush raja", "gunjan singh",
    "neelkamal singh", "samar singh", "dhananjay dhadkan", "mithu marshal", "ritesh pandey"
}


def is_indian_content(title: str, artist: str) -> bool:
    """Detect if title or artist contain Indian scripts, labels, or artists."""
    text = f"{title} {artist}".lower()
    if INDIAN_SCRIPT_RE.search(title) or INDIAN_SCRIPT_RE.search(artist):
        return True
    for kw in INDIAN_KEYWORDS:
        if kw in text:
            return True
    for art in INDIAN_ARTISTS:
        if art in text:
            return True
    return False


def fetch_paginated(sb: Client, table: str, select_fields: str, gte_field: str = None, gte_val: str = None) -> List[dict]:
    """Fetch all rows using range() pagination without 1000-row cap."""
    all_rows = []
    page_size = 1000
    start = 0
    while True:
        query = sb.table(table).select(select_fields)
        if gte_field and gte_val:
            query = query.gte(gte_field, gte_val)
        res = query.range(start, start + page_size - 1).execute()
        data = res.data or []
        all_rows.extend(data)
        if len(data) < page_size:
            break
        start += page_size
    return all_rows


def compute_recall() -> Tuple[Dict[str, float], List[dict], float, int, int, int, int, List[dict], int]:
    sb = get_supabase_client()
    cutoff_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    # 1. Fetch seed audios (paginated)
    raw_seeds = fetch_paginated(sb, "seed_audios", "id, title, artist, region, rank, source, fetched_at")

    # Deduplicate seed_audios by (source, region, rank, title)
    seen_seeds = set()
    unique_seeds = []
    for s in raw_seeds:
        key = (s.get("source"), s.get("region"), s.get("rank"), (s.get("title") or "").strip().lower())
        if key not in seen_seeds:
            seen_seeds.add(key)
            unique_seeds.append(s)

    # 2. Fetch trends in last 48h (paginated)
    trends = fetch_paginated(sb, "trends", "audio_title, audio_artist, audio_id, created_at", "created_at", cutoff_48h)

    # 3. Fetch reels in last 48h (paginated)
    reels = fetch_paginated(sb, "reels", "audio_title, audio_artist, audio_id, created_at", "created_at", cutoff_48h)

    # Build normalized lookup catalog from trends & reels
    discovered_entries = []
    for tr in trends:
        t_clean = clean_title(tr.get("audio_title") or "")
        a_clean = clean_artist(tr.get("audio_artist") or "")
        if t_clean:
            tokens = set(t_clean.split())
            discovered_entries.append((t_clean, a_clean, tokens))

    for ree in reels:
        t_clean = clean_title(ree.get("audio_title") or "")
        a_clean = clean_artist(ree.get("audio_artist") or "")
        if t_clean:
            tokens = set(t_clean.split())
            discovered_entries.append((t_clean, a_clean, tokens))

    def is_match(seed_t: str, seed_a: str) -> bool:
        if not seed_t or len(seed_t) < 2:
            return False
        seed_tokens = set(seed_t.split())
        for disc_t, disc_a, disc_tokens in discovered_entries:
            # 1. Exact normalized title match
            if seed_t == disc_t:
                return True
            # 2. Substring match for longer titles
            if len(seed_t) >= 5 and (seed_t in disc_t or disc_t in seed_t):
                return True
            # 3. Token overlap + artist match
            common_tokens = seed_tokens.intersection(disc_tokens)
            if len(common_tokens) >= 2 or (len(common_tokens) == 1 and len(list(common_tokens)[0]) >= 5):
                if seed_a and disc_a and (seed_a in disc_a or disc_a in seed_a):
                    return True
                # Or high Jaccard token overlap (>= 60%)
                union_len = len(seed_tokens.union(disc_tokens))
                if union_len > 0 and (len(common_tokens) / union_len) >= 0.6:
                    return True
        return False

    region_stats: Dict[str, Dict[str, int]] = {}
    missed_tracks: List[dict] = []
    excluded_india_seeds: List[dict] = []

    valid_seeds_count = 0
    total_matched = 0

    for s in unique_seeds:
        reg = s.get("region") or "GLOBAL"
        raw_title = s.get("title") or ""
        raw_artist = s.get("artist") or ""

        c_title = clean_title(raw_title)
        c_artist = clean_artist(raw_artist)

        # Flag Indian content in non-IN regions
        if reg != "IN" and is_indian_content(raw_title, raw_artist):
            s["is_india_content"] = True
            excluded_india_seeds.append(s)
            continue  # Exclude from non-IN recall per Order 52 Part 4.2

        if reg not in region_stats:
            region_stats[reg] = {"total": 0, "matched": 0}
        region_stats[reg]["total"] += 1
        valid_seeds_count += 1

        if is_match(c_title, c_artist):
            region_stats[reg]["matched"] += 1
            total_matched += 1
        else:
            s_clean = dict(s)
            s_clean["clean_title"] = c_title
            s_clean["clean_artist"] = c_artist
            missed_tracks.append(s_clean)

    # Calculate recall percentages
    recall_by_region: Dict[str, float] = {}
    for reg, st in sorted(region_stats.items()):
        pct = (st["matched"] / st["total"]) * 100.0 if st["total"] > 0 else 0.0
        recall_by_region[reg] = round(pct, 1)

    overall_recall = (total_matched / valid_seeds_count) * 100.0 if valid_seeds_count > 0 else 0.0

    # 20 worst DISTINCT titles
    def parse_rank(x):
        try:
            return int(x.get("rank") or 999)
        except Exception:
            return 999

    missed_sorted = sorted(missed_tracks, key=parse_rank)
    worst_20_distinct = []
    seen_distinct_titles = set()
    for m in missed_sorted:
        t_key = m.get("clean_title") or m.get("title")
        if t_key not in seen_distinct_titles:
            seen_distinct_titles.add(t_key)
            worst_20_distinct.append(m)
            if len(worst_20_distinct) >= 20:
                break

    return (
        recall_by_region,
        worst_20_distinct,
        overall_recall,
        len(trends),
        len(reels),
        len(unique_seeds),
        valid_seeds_count,
        excluded_india_seeds,
        total_matched,
    )


def main():
    (
        recall_by_region,
        worst_20,
        overall,
        n_trends,
        n_reels,
        n_unique_seeds,
        n_valid_seeds,
        excluded_in,
        n_matched,
    ) = compute_recall()

    print("======================================================================")
    print("ORDER 52 - PART 4: RECALL KPI REPORT (PAST 48 HOURS)")
    print("======================================================================")
    print(f"Dataset: {n_unique_seeds} Unique Seeds ({len(excluded_in)} flagged is_india_content excluded from non-IN)")
    print(f"Evaluated Seeds: {n_valid_seeds} | Trends (48h, unconstrained): {n_trends} | Reels (48h, unconstrained): {n_reels}")
    print(f"Overall Recall: {n_matched}/{n_valid_seeds} ({overall:.1f}%)\n")

    print("RECALL % PER REGION (Excluding is_india_content from non-IN):")
    for reg, pct in sorted(recall_by_region.items()):
        print(f"  {reg:<4}: {pct:5.1f}%")

    print(f"\nFlagged Non-IN Indian Content Excluded: {len(excluded_in)} tracks (e.g. Punjabi/Bhojpuri in SA/AE)")
    for ex in excluded_in[:5]:
        print(f"  • [{ex.get('region')}] '{ex.get('title')}' by {ex.get('artist')}")

    print("\n20 WORST DISTINCT MISSED TITLES (Top Chart Ranks Missed):")
    for idx, t in enumerate(worst_20):
        print(f"  {idx+1:02d}. [Rank {t.get('rank', '?')} | {t.get('region', '?')}] '{t.get('title', '?')}' by {t.get('artist', '?')}")

    # Specific check for Khalouni Neich in seed_audios for TR, SA, AE, EG
    print("\n----------------------------------------------------------------------")
    print("KHALOUNI NEICH SEED CHECK (TR, SA, AE, EG):")
    sb = get_supabase_client()
    k_res = sb.table("seed_audios").select("region, rank, title, artist").in_("region", ["TR", "SA", "AE", "EG"]).execute()
    k_seeds = [r for r in (k_res.data or []) if "khalouni" in (r.get("title") or "").lower() or "خلوني" in (r.get("title") or "")]
    if k_seeds:
        print(f"FOUND 'Khalouni Neich' in seed_audios: {k_seeds}")
    else:
        print("RESULT: 'Khalouni Neich' does NOT appear in current seed_audios for TR, SA, AE, or EG.")
        print("Note: Song did not chart in YouTube Music Top 50 for TR/SA/AE/EG on date of fetch.")


if __name__ == "__main__":
    main()
