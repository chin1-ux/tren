"""
One-time backfill: merge fragmented variant trends in the `trends` table.

Groups trends by (normalize_audio_title(audio_title), audio_artist). For each
group with >1 row, selects a survivor, repoints trend_snapshots FK rows,
merges key stats, and deletes non-survivors.

Usage:
    python backfill_merge_trends.py              # dry-run
    python backfill_merge_trends.py --apply       # execute
"""
import sys
import os
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

try:
    from audio_title_normalize import normalize_audio_title
except ImportError:
    print("ERROR: Cannot import audio_title_normalize.")
    sys.exit(1)

DRY_RUN = "--apply" not in sys.argv

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

STATUS_RANK = {"rising": 4, "emerging": 3, "peaked": 2, "expired": 1}


def fetch_all_trends():
    all_rows = []
    offset = 0
    page = 1000
    while True:
        res = sb.table("trends") \
            .select("id, audio_title, audio_artist, audio_id, velocity_avg, "
                    "peak_velocity, reel_count, status, first_detected_at, "
                    "audio_use_count, confidence, high_confidence") \
            .range(offset, offset + page - 1) \
            .execute()
        batch = res.data or []
        all_rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    return all_rows


def pick_survivor(group):
    """Pick survivor: highest status > highest velocity_avg > oldest first_detected_at."""
    def sort_key(t):
        return (
            -(STATUS_RANK.get(t.get("status"), 0)),
            -(t.get("velocity_avg") or 0),
            t.get("first_detected_at", "9999"),
        )
    return min(group, key=sort_key)


def main():
    rows = fetch_all_trends()
    print(f"Fetched {len(rows)} trends rows")

    # Group by normalized (title, artist)
    groups = defaultdict(list)
    for row in rows:
        norm_title = normalize_audio_title(row.get("audio_title", "") or "")
        artist = (row.get("audio_artist") or "").strip()
        key = (norm_title, artist)
        groups[key].append(row)

    merge_groups = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"Unique normalized groups: {len(groups)}")
    print(f"Groups needing merge: {len(merge_groups)}")

    total_non_survivors = sum(len(v) - 1 for v in merge_groups.values())
    print(f"Total rows to delete: {total_non_survivors}")
    print(f"Expected final count: {len(rows) - total_non_survivors}")

    if DRY_RUN:
        print("\n=== DRY RUN ===\n")
        for (norm_title, artist), group in sorted(merge_groups.items()):
            survivor = pick_survivor(group)
            losers = [t for t in group if t["id"] != survivor["id"]]
            print(f"MERGE '{norm_title}' by '{artist}':")
            print(f"  SURVIVOR: id={survivor['id']} status={survivor['status']} "
                  f"vel={survivor['velocity_avg']:.0f} reels={survivor['reel_count']} "
                  f"first={survivor['first_detected_at'][:10]}")
            for loser in losers:
                print(f"  DELETE:   id={loser['id']} status={loser['status']} "
                      f"vel={loser['velocity_avg']:.0f} reels={loser['reel_count']} "
                      f"first={loser['first_detected_at'][:10]}")
            print()
        return

    # Apply
    snapshots_repointed = 0
    trends_deleted = 0

    for (norm_title, artist), group in merge_groups.items():
        survivor = pick_survivor(group)
        losers = [t for t in group if t["id"] != survivor["id"]]
        loser_ids = [t["id"] for t in losers]

        # 1. Repoint trend_snapshots
        try:
            sb.table("trend_snapshots") \
                .update({"trend_id": survivor["id"]}) \
                .in_("trend_id", loser_ids) \
                .execute()
            snapshots_repointed += len(loser_ids)
        except Exception as e:
            print(f"  WARNING: snapshot repoint failed for survivor={survivor['id']}: {e}")

        # 2. Merge key stats onto survivor
        max_reel_count = max(t.get("reel_count", 0) for t in group)
        max_velocity = max(t.get("velocity_avg", 0) for t in group)
        max_peak = max(t.get("peak_velocity", 0) for t in group)
        max_use_count = max(t.get("audio_use_count", 0) for t in group)
        best_confidence = max(t.get("confidence", 0) for t in group)
        any_high_confidence = any(t.get("high_confidence", False) for t in group)

        sb.table("trends").update({
            "reel_count": max_reel_count,
            "velocity_avg": max_velocity,
            "peak_velocity": max_peak,
            "audio_use_count": max_use_count,
            "confidence": best_confidence,
            "high_confidence": any_high_confidence,
        }).eq("id", survivor["id"]).execute()

        # 3. Delete non-survivors
        sb.table("trends").delete().in_("id", loser_ids).execute()
        trends_deleted += len(losers)

    print(f"\n=== APPLY ===")
    print(f"Snapshots repointed: {snapshots_repointed}")
    print(f"Trends deleted: {trends_deleted}")
    print(f"Survivors updated: {len(merge_groups)}")


if __name__ == "__main__":
    main()
