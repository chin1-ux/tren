"""Backfill format detection fields for existing trends."""
import socket, json, sys, os
sys.stdout.reconfigure(encoding='utf-8')
_orig = socket.getaddrinfo
def _ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4
import urllib.request, urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from format_detector import detect_dominant_format, is_format_trend, get_format_trend_score

SUPABASE_URL = "https://gxxpvstrvphwhlqbvymv.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4eHB2c3RydnBod2hscWJ2eW12Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDg4NzczNywiZXhwIjoyMTAwNDYzNzM3fQ.DhoBpfPSmXWBHKnk5oa0H_a6LsaEm--WPjSVSMab-aU"
hdrs = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}", "Content-Type": "application/json"}

def supa_get(path):
    req = urllib.request.Request(f"{SUPABASE_URL}{path}", headers={"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

def supa_patch(table, data, trend_id):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{trend_id}", data=body, headers=hdrs, method="PATCH")
    return urllib.request.urlopen(req, timeout=15).status

# Get all active trends
print("Fetching active trends...")
trends = supa_get("/rest/v1/trends?select=id,audio_title,audio_artist,status&status=in.(rising,emerging)&limit=50")
print(f"Found {len(trends)} active trends")

updated = 0
for trend in trends:
    tid = trend["id"]
    title = trend.get("audio_title", "?")
    artist = trend.get("audio_artist", "?")
    
    # URL-encode the filter values
    encoded_title = urllib.parse.quote(title, safe="")
    encoded_artist = urllib.parse.quote(artist, safe="")
    
    reels = supa_get(f"/rest/v1/reels?select=caption,hashtags,owner_username,view_count,like_count,velocity_score&audio_title=eq.{encoded_title}&audio_artist=eq.{encoded_artist}&limit=50")
    
    if not reels:
        print(f"  [{tid}] {title[:35]}: 0 reels, skip")
        continue
    
    analysis = detect_dominant_format(reels)
    fmt_trend = is_format_trend(analysis)
    fmt_score = get_format_trend_score(analysis) if fmt_trend else 0.0
    
    update_data = {
        "dominant_format": analysis["dominant_format"],
        "format_replication_rate": analysis["format_replication_rate"],
        "format_concepts": json.dumps(analysis["format_concepts"]),
        "creator_diversity": analysis["creator_diversity"],
        "is_format_trend": fmt_trend,
        "format_trend_score": fmt_score,
    }
    
    status = supa_patch("trends", update_data, tid)
    updated += 1
    print(f"  [{tid}] {title[:35]:35} | {len(reels)} reels | fmt={analysis['dominant_format']:20} | repl={analysis['format_replication_rate']:.2f} | div={analysis['creator_diversity']:.2f} | trend={fmt_trend}")

print(f"\nDone: {updated}/{len(trends)} updated")
