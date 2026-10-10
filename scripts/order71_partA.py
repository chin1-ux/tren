import os
import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv("backend/.env")
from supabase import create_client
sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

# 1. Reset first_noticed to NULL for all rows
sb.table("ground_truth").update({"first_noticed": None}).neq("id", 0).execute()

# 2. Set only Khalouni Neich (2026-10-05) and Asaad Basha (2026-10-10)
rows = sb.table("ground_truth").select("*").execute().data or []
for r in rows:
    t = r.get("title") or ""
    if "Khalouni" in t:
        sb.table("ground_truth").update({"first_noticed": "2026-10-05"}).eq("id", r["id"]).execute()
    elif "امشي" in t:
        sb.table("ground_truth").update({"first_noticed": "2026-10-10"}).eq("id", r["id"]).execute()

# 3. Print the table
updated = sb.table("ground_truth").select("id, title, artist, first_noticed, source, note").order("id").execute().data or []
print("=" * 95)
print("PART A1: GROUND TRUTH TABLE (INVENTED DATES REMOVED)")
print("=" * 95)
print(f"{'ID':<4} | {'Title':<24} | {'Artist':<22} | {'First Noticed':<14} | {'Source':<10}")
print("-" * 95)
for u in updated:
    t_str = str(u.get("title") or "")[:22]
    a_str = str(u.get("artist") or "NULL")[:20]
    fn_str = str(u.get("first_noticed") or "NULL")
    s_str = str(u.get("source") or "NULL")
    print(f"{u['id']:<4} | {t_str:<24} | {a_str:<22} | {fn_str:<14} | {s_str:<10}")
print("=" * 95 + "\n")

# 4. Part A2: Recompute ground-truth metrics over rows with first_noticed NOT NULL only
print("PART A2: GROUND TRUTH RECOMPUTATION (NON-NULL first_noticed ONLY)")
print("=" * 95)
non_null_rows = [u for u in updated if u.get("first_noticed")]
n = len(non_null_rows)
print(f"Sample size n = {n} (Mark: TOO THIN TO QUOTE, n < 30)")
print("Since n < 5, omitting percentage summary and printing per-song audit rows:")
print("-" * 95)

# Fetch trends and proof_log for matching
pl_rows = sb.table("proof_log").select("flagged_at, audio_id, snapshot").execute().data or []
for song in non_null_rows:
    title = song.get("title") or ""
    artist = song.get("artist") or ""
    fn = song.get("first_noticed")
    q_token = title.split("/")[0].strip().split()[0]
    
    t_res = sb.table("trends").select("id, status, first_detected_at, audio_title").ilike("audio_title", f"%{q_token}%").execute().data or []
    t_info = f"Trend #{t_res[0]['id']} ({t_res[0].get('status')}, {t_res[0].get('first_detected_at')[:10]})" if t_res else "No Trend"
    
    # Compare first_detected_at vs first_noticed
    if t_res and t_res[0].get("first_detected_at"):
        t_date = t_res[0]["first_detected_at"][:10]
        if t_date < fn:
            rel = f"CAUGHT BEFORE (Trend {t_date} < Noticed {fn})"
        elif t_date == fn:
            rel = f"CAUGHT ON SAME DAY ({t_date})"
        else:
            rel = f"CAUGHT AFTER (Trend {t_date} > Noticed {fn})"
    else:
        rel = "MISSED (No trend)"
        
    print(f"Song: '{title}' by '{artist or 'NULL'}'")
    print(f"  first_noticed     : {fn}")
    print(f"  Trend Record      : {t_info}")
    print(f"  Detection Timing  : {rel}\n")
print("=" * 95)
