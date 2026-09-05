"""
One-time backfill: normalize existing trend_lifecycle.trend_id values.

This script updates trend_lifecycle rows that were keyed on raw audio_title
(e.g., "Espresso (Sped Up)") to use the normalized form (e.g., "Espresso").

It also merges rows that collide after normalization (multiple variants of
the same song) by combining their spread_timeline and saturation_by_region.

Usage:
    python backfill_normalize_trend_lifecycle.py          # dry-run
    python backfill_normalize_trend_lifecycle.py --apply  # execute
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
    print("ERROR: Cannot import audio_title_normalize. Run from backend/ directory.")
    sys.exit(1)

DRY_RUN = "--apply" not in sys.argv

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def main():
    # Paginate through all rows (Supabase defaults to 1000)
    all_rows = []
    offset = 0
    page_size = 1000
    while True:
        res = sb.table("trend_lifecycle") \
            .select("trend_id, first_seen_at, spread_timeline, saturation_by_region") \
            .range(offset, offset + page_size - 1) \
            .execute()
        batch = res.data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    rows = all_rows
    print(f"Fetched {len(rows)} trend_lifecycle rows")

    # Group by normalized trend_id
    groups = defaultdict(list)
    already_normalized = 0
    needs_update = 0

    for row in rows:
        raw_id = row.get("trend_id", "")
        norm_id = normalize_audio_title(raw_id)
        if norm_id == raw_id:
            already_normalized += 1
            groups[norm_id].append(row)
        else:
            needs_update += 1
            groups[norm_id].append(row)

    print(f"Already normalized: {already_normalized}")
    print(f"Need normalization: {needs_update}")
    print(f"Unique normalized groups: {len(groups)}")

    # Find groups with >1 row (variants that need merging)
    merges = {k: v for k, v in groups.items() if len(v) > 1}
    print(f"Groups needing merge (variants): {len(merges)}")

    if DRY_RUN:
        print("\n=== DRY RUN — no changes will be written ===\n")
        for norm_id, group in merges.items():
            print(f"  MERGE '{norm_id}': {len(group)} rows")
            for row in group:
                print(f"    - trend_id={row['trend_id']} first_seen={row.get('first_seen_at','?')}")
        # Also show renames
        renames = [(g[0]["trend_id"], norm_id) for norm_id, g in groups.items()
                   if len(g) == 1 and g[0]["trend_id"] != norm_id]
        if renames:
            print(f"\n  RENAMES ({len(renames)}):")
            for old, new in renames:
                print(f"    '{old}' -> '{new}'")
        return

    # Apply changes
    updated = 0
    merged = 0
    deleted = 0

    for norm_id, group in groups.items():
        if len(group) == 1:
            row = group[0]
            if row["trend_id"] != norm_id:
                # Check if normalized key already exists (would cause collision)
                existing = sb.table("trend_lifecycle").select("trend_id").eq("trend_id", norm_id).execute()
                if existing.data:
                    # Collision — need to merge into existing row instead of rename
                    existing_row = sb.table("trend_lifecycle").select("*").eq("trend_id", norm_id).execute()
                    if existing_row.data:
                        er = existing_row.data[0]
                        combined_timeline = list(er.get("spread_timeline") or [])
                        combined_timeline.extend(row.get("spread_timeline") or [])
                        combined_saturation = dict(er.get("saturation_by_region") or {})
                        for country, count in (row.get("saturation_by_region") or {}).items():
                            combined_saturation[country] = combined_saturation.get(country, 0) + count
                        sb.table("trend_lifecycle").update({
                            "spread_timeline": combined_timeline,
                            "saturation_by_region": combined_saturation,
                        }).eq("trend_id", norm_id).execute()
                        sb.table("trend_lifecycle").delete().eq("trend_id", row["trend_id"]).execute()
                        merged += 1
                    else:
                        sb.table("trend_lifecycle").update({"trend_id": norm_id}).eq("trend_id", row["trend_id"]).execute()
                        updated += 1
                else:
                    sb.table("trend_lifecycle").update({"trend_id": norm_id}).eq("trend_id", row["trend_id"]).execute()
                    updated += 1
        else:
            # Merge: pick survivor (oldest first_seen_at), combine timelines
            survivor = min(group, key=lambda r: r.get("first_seen_at", "9999"))
            other_rows = [r for r in group if r["trend_id"] != survivor["trend_id"]]

            combined_timeline = list(survivor.get("spread_timeline") or [])
            combined_saturation = dict(survivor.get("saturation_by_region") or {})

            for other in other_rows:
                combined_timeline.extend(other.get("spread_timeline") or [])
                for country, count in (other.get("saturation_by_region") or {}).items():
                    combined_saturation[country] = combined_saturation.get(country, 0) + count

            # Update survivor with merged data (keep survivor's raw trend_id)
            sb.table("trend_lifecycle").update({
                "spread_timeline": combined_timeline,
                "saturation_by_region": combined_saturation,
            }).eq("trend_id", survivor["trend_id"]).execute()
            merged += 1

            # Delete non-survivors
            for other in other_rows:
                sb.table("trend_lifecycle").delete().eq("trend_id", other["trend_id"]).execute()
                deleted += 1

    print(f"\n=== APPLY ===")
    print(f"Updated (renamed): {updated}")
    print(f"Merged: {merged}")
    print(f"Deleted: {deleted}")


if __name__ == "__main__":
    main()
