import os
import sys
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv("backend/.env")
load_dotenv(".env")

sys.path.append(".")
from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"))

print("Fetching 100 real audios from database...")
res = sb.table("trends").select("id, audio_title, audio_artist").order("id", desc=True).limit(100).execute()
audios = res.data or []
print(f"Fetched {len(audios)} audios.")

itunes_hits = 0
deezer_hits = 0
either_hits = 0
details = []

for idx, a in enumerate(audios):
    title = a.get("audio_title") or ""
    artist = a.get("audio_artist") or ""
    
    # Clean title
    clean_title = title
    if "::" in clean_title:
        clean_title = clean_title.split("::")[-1]
    # Remove special brackets
    clean_title = clean_title.split("(")[0].split("-")[0].strip()
    
    query = f"{clean_title} {artist}".strip()
    encoded = urllib.parse.quote(query)
    
    has_itunes = False
    itunes_url = None
    try:
        itunes_api = f"https://itunes.apple.com/search?term={encoded}&entity=song&limit=1"
        req = urllib.request.Request(itunes_api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data.get("resultCount", 0) > 0 and data["results"][0].get("previewUrl"):
                has_itunes = True
                itunes_url = data["results"][0]["previewUrl"]
    except Exception:
        pass

    has_deezer = False
    deezer_url = None
    try:
        deezer_api = f"https://api.deezer.com/search?q={encoded}&limit=1"
        req = urllib.request.Request(deezer_api, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data.get("total", 0) > 0 and data["data"][0].get("preview"):
                has_deezer = True
                deezer_url = data["data"][0]["preview"]
    except Exception:
        pass

    if has_itunes:
        itunes_hits += 1
    if has_deezer:
        deezer_hits += 1
    if has_itunes or has_deezer:
        either_hits += 1

    details.append({
        "id": a["id"],
        "title": title[:30],
        "artist": artist[:20],
        "itunes": has_itunes,
        "deezer": has_deezer,
        "matched": has_itunes or has_deezer
    })
    
    if (idx + 1) % 25 == 0:
        print(f"Processed {idx + 1}/100... Current coverage: {round(either_hits / (idx + 1) * 100, 1)}%")

total = len(audios)
itunes_pct = round(itunes_hits / total * 100, 1)
deezer_pct = round(deezer_hits / total * 100, 1)
combined_pct = round(either_hits / total * 100, 1)

print("\n=== AUDIO PREVIEW COVERAGE TEST RESULTS ===")
print(f"Total Audios Tested: {total}")
print(f"iTunes Search Hits: {itunes_hits}/{total} ({itunes_pct}%)")
print(f"Deezer Search Hits: {deezer_hits}/{total} ({deezer_pct}%)")
print(f"Combined Coverage (Either Source): {either_hits}/{total} ({combined_pct}%)")
print(f"Requirement: >= 60% coverage -> Keep global player, Else -> Delete audio-only player.")
print(f"Verdict: {'KEEP GLOBAL PLAYER' if combined_pct >= 60.0 else 'DELETE AUDIO-ONLY PLAYER'}")

# Save evidence file
out_lines = [
    "=" * 80,
    "ORDER 81 PHASE 3: AUDIO PREVIEW SOURCE COVERAGE TEST REPORT",
    f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
    "=" * 80,
    f"\nTotal Audios Tested: {total}",
    f"iTunes Search Hits: {itunes_hits} ({itunes_pct}%)",
    f"Deezer Search Hits: {deezer_hits} ({deezer_pct}%)",
    f"Combined Coverage: {either_hits} ({combined_pct}%)",
    f"Coverage Requirement: >= 60%",
    f"VERDICT: {'KEEP GLOBAL PLAYER (>= 60%)' if combined_pct >= 60.0 else 'DELETE AUDIO-ONLY PLAYER (< 60%)'}",
    "\nSAMPLE 20 RESULTS:",
    f"{'ID':<6} | {'Matched':<7} | {'iTunes':<6} | {'Deezer':<6} | {'Title':<30} | {'Artist':<20}",
    "-" * 80
]
for d in details[:20]:
    out_lines.append(f"{d['id']:<6} | {str(d['matched']):<7} | {str(d['itunes']):<6} | {str(d['deezer']):<6} | {d['title']:<30} | {d['artist']:<20}")

os.makedirs("evidence/order81", exist_ok=True)
report_path = "evidence/order81/phase3_audio_preview_test.txt"
with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
print(f"\nSaved raw evidence to {report_path}")
