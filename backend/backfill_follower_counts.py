"""
P-SCRAPER-2 backfill: populate owner_follower_count in reels from creator_baselines.

Read-only on creator_baselines, write-only on reels.owner_follower_count.
No schema changes. Idempotent — safe to re-run (skips rows already > 0).
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.environ["SUPABASE_URL"]
key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
sb = create_client(url, key)


def main():
    # 1. Load all baselines with real follower_count
    baselines = {}
    offset = 0
    while True:
        batch = (
            sb.table("creator_baselines")
            .select("username, follower_count")
            .range(offset, offset + 999)
            .execute()
        )
        if not batch.data:
            break
        for row in batch.data:
            if row["follower_count"] and row["follower_count"] > 0:
                baselines[row["username"]] = row["follower_count"]
        if len(batch.data) < 1000:
            break
        offset += 1000

    print(f"Loaded {len(baselines)} baselines with real follower_count")
    if not baselines:
        print("No baselines with data — nothing to backfill.")
        return

    # 2. Find reels with owner_follower_count = 0 that have a matching baseline
    updated = 0
    skipped_no_match = 0
    skipped_already_set = 0
    offset = 0

    while True:
        batch = (
            sb.table("reels")
            .select("id, owner_username, owner_follower_count")
            .range(offset, offset + 999)
            .execute()
        )
        if not batch.data:
            break

        updates = []
        for row in batch.data:
            username = row.get("owner_username")
            current = row.get("owner_follower_count") or 0

            if current > 0:
                skipped_already_set += 1
                continue

            if username and username in baselines:
                updates.append({"id": row["id"], "owner_follower_count": baselines[username]})
            else:
                skipped_no_match += 1

        # Batch update (Supabase upsert-style: update one at a time with PK)
        for u in updates:
            try:
                sb.table("reels").update({"owner_follower_count": u["owner_follower_count"]}).eq("id", u["id"]).execute()
                updated += 1
            except Exception as e:
                print(f"  Error updating id={u['id']}: {e}")

        if updates:
            print(f"  Batch offset {offset}: updated {len(updates)}/{len(batch.data)} rows")

        if len(batch.data) < 1000:
            break
        offset += 1000

    print(f"\nBackfill complete:")
    print(f"  Updated: {updated}")
    print(f"  Skipped (no matching baseline): {skipped_no_match}")
    print(f"  Skipped (already > 0): {skipped_already_set}")

    # 3. Verify distribution
    print("\n=== Verification ===")
    verify = (
        sb.table("reels")
        .select("owner_follower_count")
        .not_.is_("owner_follower_count", "null")
        .limit(5000)
        .execute()
    )
    if verify.data:
        values = [r["owner_follower_count"] for r in verify.data if r.get("owner_follower_count")]
        positive = [v for v in values if v > 0]
        zero = [v for v in values if v == 0]
        if positive:
            print(f"  Sampled {len(values)} rows")
            print(f"  owner_follower_count > 0: {len(positive)}")
            print(f"  owner_follower_count = 0: {len(zero)}")
            print(f"  Min: {min(positive)}, Max: {max(positive)}, Median: {sorted(positive)[len(positive)//2]}")
        else:
            print(f"  WARNING: Still 0 for all {len(values)} sampled rows")


if __name__ == "__main__":
    main()
