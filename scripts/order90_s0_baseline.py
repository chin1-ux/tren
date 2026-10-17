import os
import sys
import json
import re
from dotenv import load_dotenv
from supabase import create_client

backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
load_dotenv(os.path.join(backend_dir, ".env"))

sb_url = os.getenv("SUPABASE_URL")
sb_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

sb = create_client(sb_url, sb_key)

print("=== S0.1 SQL COUNT AUDIT ===")

# Total rows in trends table using exact count
total_res = sb.table("trends").select("id", count="exact").limit(1).execute()
total_trends_db = total_res.count
print(f"Total trends in DB (via count='exact'): {total_trends_db}")

# Distinct llm_classification_status values and their exact counts
# Since distinct aggregate is best done via iterating known statuses or paging,
# let's test all candidate statuses:
known_statuses = [
    "completed", "skipped_local_fallback", "verified", "pending", 
    "not_needed", "failed", "classification_failed", "llm_unavailable"
]

status_counts = {}
for st in known_statuses:
    c_res = sb.table("trends").select("id", count="exact").eq("llm_classification_status", st).limit(1).execute()
    if c_res.count > 0:
        status_counts[st] = c_res.count

# Also check for null status
null_res = sb.table("trends").select("id", count="exact").is_("llm_classification_status", "null").limit(1).execute()
if null_res.count > 0:
    status_counts["null"] = null_res.count

sum_statuses = sum(status_counts.values())
print(f"Sum of status counts: {sum_statuses} / Total DB: {total_trends_db}")
for st, cnt in status_counts.items():
    print(f"  {st}: {cnt}")

# Now for each status, count fallback vs real text
# Fallback criteria:
# why_this_works like 'The track %' OR used_for_note = 'Automated fallback classification.' OR why_this_works is null
text_breakdown = {}
for st in status_counts.keys():
    q_base = sb.table("trends").select("id", count="exact").limit(1)
    if st == "null":
        q_base = q_base.is_("llm_classification_status", "null")
    else:
        q_base = q_base.eq("llm_classification_status", st)
    
    # Template text count
    # PostgREST ilike/like
    q_template = sb.table("trends").select("id", count="exact").limit(1)
    if st == "null":
        q_template = q_template.is_("llm_classification_status", "null")
    else:
        q_template = q_template.eq("llm_classification_status", st)
    q_template = q_template.like("why_this_works", "The track %is currently driving high engagement%")
    t_cnt = q_template.execute().count or 0

    # Note fallback count
    q_note = sb.table("trends").select("id", count="exact").limit(1)
    if st == "null":
        q_note = q_note.is_("llm_classification_status", "null")
    else:
        q_note = q_note.eq("llm_classification_status", st)
    q_note = q_note.eq("used_for_note", "Automated fallback classification.")
    n_cnt = q_note.execute().count or 0

    # Null why_this_works
    q_null_why = sb.table("trends").select("id", count="exact").limit(1)
    if st == "null":
        q_null_why = q_null_why.is_("llm_classification_status", "null")
    else:
        q_null_why = q_null_why.eq("llm_classification_status", st)
    q_null_why = q_null_why.is_("why_this_works", "null")
    null_why_cnt = q_null_why.execute().count or 0

    # Combined fallback or empty
    # In PostgREST: or_(why_this_works.like.The track %is currently driving high engagement%,used_for_note.eq.Automated fallback classification.,why_this_works.is.null)
    q_fb_comb = sb.table("trends").select("id", count="exact").limit(1)
    if st == "null":
        q_fb_comb = q_fb_comb.is_("llm_classification_status", "null")
    else:
        q_fb_comb = q_fb_comb.eq("llm_classification_status", st)
    q_fb_comb = q_fb_comb.or_("why_this_works.like.The track %is currently driving high engagement%,used_for_note.eq.Automated fallback classification.,why_this_works.is.null")
    fb_total = q_fb_comb.execute().count or 0

    st_total = status_counts[st]
    real_text_total = st_total - fb_total
    text_breakdown[st] = {
        "total": st_total,
        "fallback_or_empty": fb_total,
        "real_text": real_text_total,
        "breakdown": {
            "template_why_this_works": t_cnt,
            "automated_fallback_note": n_cnt,
            "null_why_this_works": null_why_cnt
        }
    }

print("\nExact Status x Text Breakdown:")
print(json.dumps(text_breakdown, indent=2))

# Find API's exact feed-eligible WHERE clause
print("\n=== FEED-ELIGIBLE AUDIT (API's exact WHERE) ===")
# In routes/trends.py:
# Emerging: status in ('emerging', 'rising') and is_seed_data = false and llm_classification_status in ('completed', 'not_needed', 'skipped_local_fallback', 'verified')
# Let's inspect active trends in DB:
# We query total feed-eligible trends by status in ('emerging', 'rising', 'resurging')
q_feed_all = sb.table("trends").select("id", count="exact").in_("status", ["emerging", "rising", "resurging"]).gt("window_hours_remaining", 0).limit(1).execute()
total_feed_eligible = q_feed_all.count
print(f"Total feed-eligible trends (status in emerging/rising/resurging, window_hours_remaining > 0): {total_feed_eligible}")

# Feed eligible with fallback text
q_feed_fb = sb.table("trends").select("id", count="exact") \
    .in_("status", ["emerging", "rising", "resurging"]) \
    .gt("window_hours_remaining", 0) \
    .or_("why_this_works.like.The track %is currently driving high engagement%,used_for_note.eq.Automated fallback classification.,why_this_works.is.null") \
    .limit(1).execute()
feed_eligible_fallback = q_feed_fb.count
feed_eligible_real = total_feed_eligible - feed_eligible_fallback
print(f"Feed-eligible WITH fallback text: {feed_eligible_fallback}")
print(f"Feed-eligible WITH real text: {feed_eligible_real}")
print(f"Real text percentage in live feed: {feed_eligible_real / total_feed_eligible * 100:.2f}%")

out_data = {
    "total_trends_db": total_trends_db,
    "status_counts": status_counts,
    "text_breakdown": text_breakdown,
    "total_feed_eligible": total_feed_eligible,
    "feed_eligible_fallback": feed_eligible_fallback,
    "feed_eligible_real": feed_eligible_real
}

os.makedirs("evidence/order90", exist_ok=True)
with open("evidence/order90/s0_baseline_counts.json", "w") as f:
    json.dump(out_data, f, indent=2)
print("Saved baseline counts to evidence/order90/s0_baseline_counts.json")
