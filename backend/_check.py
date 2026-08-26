import socket, os, sys
os.environ["PYTHONIOENCODING"] = "utf-8"
_orig = socket.getaddrinfo
def _ipv4(host, port, family=0, type=0, proto=0, flags=0):
    return _orig(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4
import urllib.request, json
sys.stdout.reconfigure(encoding='utf-8')

SUPABASE_URL = "https://gxxpvstrvphwhlqbvymv.supabase.co"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd4eHB2c3RydnBod2hscWJ2eW12Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NDg4NzczNywiZXhwIjoyMTAwNDYzNzM3fQ.DhoBpfPSmXWBHKnk5oa0H_a6LsaEm--WPjSVSMab-aU"
hdrs = {"apikey": SERVICE_KEY, "Authorization": f"Bearer {SERVICE_KEY}"}

# Check if format columns exist
print("=== FORMAT COLUMNS CHECK ===")
try:
    r = urllib.request.urlopen(urllib.request.Request(
        f"{SUPABASE_URL}/rest/v1/trends?select=dominant_format,format_replication_rate,format_concepts,creator_diversity,is_format_trend,format_trend_score&limit=2&order=id.desc",
        headers=hdrs), timeout=15)
    data = json.loads(r.read().decode())
    if data:
        print("COLUMNS EXIST!")
        for row in data:
            print(f"  {json.dumps(row, default=str)[:300]}")
    else:
        print("No data but columns exist")
except Exception as e:
    err = str(e)
    try: err = e.read().decode()[:300]
    except: pass
    print(f"COLUMNS MISSING: {err}")
    print("\nNEED TO RUN SQL MIGRATION!")
