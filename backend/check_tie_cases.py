import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
sb = create_client(url, key)

tie_cases = [
    ("Sad Flute Music", 899, 900),
    ("Vellake", 914, 913),
    ("Tera Mera Rishta - New", 491, 844),
    ("Tera Mera Rishta - Orig", 836, 892),
    ("Majanua Ha Mafiya", 907, 908),
]

all_ids = [id for _, s, d in tie_cases for id in (s, d)]
res = sb.table("trends").select("id, audio_title, velocity_avg, status, created_at").in_("id", all_ids).execute()
rows = {r["id"]: r for r in res.data}

for name, survivor_id, delete_id in tie_cases:
    s = rows[survivor_id]
    d = rows[delete_id]
    s_vel = s.get("velocity_avg") or 0
    d_vel = d.get("velocity_avg") or 0
    s_created = str(s.get("created_at", ""))[:10]
    d_created = str(d.get("created_at", ""))[:10]
    if s_vel >= d_vel:
        verdict = "OK - survivor has higher or equal velocity"
    else:
        verdict = "BROKEN - deleted row has higher velocity"
    print(f"{name}:")
    print(f"  SURVIVOR id={survivor_id}  vel={s_vel}  status={s.get('status')}  created={s_created}")
    print(f"  DELETE   id={delete_id}  vel={d_vel}  status={d.get('status')}  created={d_created}")
    print(f"  Verdict: {verdict}")
    print()
