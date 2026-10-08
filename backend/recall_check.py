"""
backend/recall_check.py
Recall KPI Evaluation (Order 51).
Matches seed_audios titles against trends/reels created in the last 48 hours.
Prints recall % per region and the 20 worst-missed titles (highest chart ranks).
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


def normalize_title(title: str) -> str:
    """Normalize song title for robust matching."""
    if not title:
        return ""
    t = title.lower()
    # Remove common video / audio suffixes
    t = re.sub(r'\(.*?\)|\[.*?\]', '', t)
    t = re.sub(r'\b(official|video|music|audio|lyric|lyrics|clip|remix|hd|4k)\b', '', t)
    # Remove non-alphanumeric except spaces
    t = re.sub(r'[^\w\s\u0600-\u06FF\uac00-\ud7a3\u0400-\u04FF]', ' ', t)
    return " ".join(t.split())


def compute_recall() -> Tuple[Dict[str, float], List[dict]]:
    sb = get_supabase_client()
    cutoff_48h = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    # 1. Fetch seed audios
    res_seeds = sb.table("seed_audios").select("title, artist, region, rank, source").execute()
    seeds = res_seeds.data or []

    # 2. Fetch trends in last 48h
    res_trends = sb.table("trends").select("audio_title, audio_artist, audio_id, created_at").gte("created_at", cutoff_48h).execute()
    trends = res_trends.data or []

    # 3. Fetch reels in last 48h
    res_reels = sb.table("reels").select("audio_title, audio_artist, audio_id, created_at").gte("created_at", cutoff_48h).execute()
    reels = res_reels.data or []

    # Build normalized lookup sets from trends & reels
    discovered_titles: Set[str] = set()
    for tr in trends:
        raw_t = tr.get("audio_title") or ""
        norm_t = normalize_title(raw_t)
        if norm_t:
            discovered_titles.add(norm_t)

    for ree in reels:
        raw_s = ree.get("audio_title") or ""
        norm_s = normalize_title(raw_s)
        if norm_s:
            discovered_titles.add(norm_s)

    def is_match(seed_title: str) -> bool:
        norm_seed = normalize_title(seed_title)
        if not norm_seed or len(norm_seed) < 3:
            return False
        if norm_seed in discovered_titles:
            return True
        for disc in discovered_titles:
            if len(norm_seed) >= 5 and (norm_seed in disc or disc in norm_seed):
                return True
        return False

    region_stats: Dict[str, Dict[str, int]] = {}
    missed_tracks: List[dict] = []

    for s in seeds:
        reg = s.get("region") or "GLOBAL"
        if reg not in region_stats:
            region_stats[reg] = {"total": 0, "matched": 0}
        region_stats[reg]["total"] += 1

        title = s.get("title") or ""
        if is_match(title):
            region_stats[reg]["matched"] += 1
        else:
            missed_tracks.append(s)

    # Calculate percentages
    recall_by_region: Dict[str, float] = {}
    total_seeds = len(seeds)
    total_matched = sum(st["matched"] for st in region_stats.values())

    for reg, st in sorted(region_stats.items()):
        pct = (st["matched"] / st["total"]) * 100.0 if st["total"] > 0 else 0.0
        recall_by_region[reg] = round(pct, 1)

    overall_recall = (total_matched / total_seeds) * 100.0 if total_seeds > 0 else 0.0

    # Sort missed tracks by rank (rank 1 is highest priority missed)
    def parse_rank(x):
        try:
            return int(x.get("rank") or 999)
        except Exception:
            return 999

    missed_sorted = sorted(missed_tracks, key=parse_rank)
    worst_20_missed = missed_sorted[:20]

    return recall_by_region, worst_20_missed, overall_recall, len(trends), len(reels), total_seeds, total_matched


def main():
    recall_by_region, worst_20, overall, n_trends, n_reels, n_seeds, n_matched = compute_recall()

    print("======================================================================")
    print("ORDER 51 - PART 5: RECALL KPI REPORT (PAST 48 HOURS)")
    print("======================================================================")
    print(f"Dataset: {n_seeds} Seed Audios | {n_trends} Trends (48h) | {n_reels} Reels (48h)")
    print(f"Overall Recall: {n_matched}/{n_seeds} ({overall:.1f}%)\n")
    print("RECALL % PER REGION:")
    for reg, pct in recall_by_region.items():
        print(f"  {reg}: {pct:5.1f}%")

    print("\n20 WORST-MISSED TITLES (Top Chart Ranks Missed):")
    for idx, t in enumerate(worst_20):
        print(f"  {idx+1:02d}. [Rank {t.get('rank', '?')} | {t.get('region', '?')}] '{t.get('title', '?')}' by {t.get('artist', '?')}")


if __name__ == "__main__":
    main()
