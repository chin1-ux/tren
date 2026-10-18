import os
import json
import gzip

assets_dir = r".vercel\output\static\assets"

files = os.listdir(assets_dir)
measurements = {}

for f in sorted(files):
    if f.endswith(".js") or f.endswith(".css"):
        fp = os.path.join(assets_dir, f)
        raw_size = os.path.getsize(fp)
        with open(fp, "rb") as fl:
            gz_size = len(gzip.compress(fl.read()))
        measurements[f] = {
            "raw_kb": round(raw_size / 1024, 2),
            "gzip_kb": round(gz_size / 1024, 2)
        }

deck_chunk = next((k for k in measurements if k.startswith("deck-")), None)
print("Deck chunk:", deck_chunk, measurements.get(deck_chunk))

os.makedirs("evidence/order100", exist_ok=True)
with open("evidence/order100/bundle_measurements.json", "w", encoding="utf-8") as f:
    json.dump({
        "deck_route_chunk": deck_chunk,
        "deck_route_metrics": measurements.get(deck_chunk),
        "target_max_gzip_kb": 60,
        "pass": measurements.get(deck_chunk, {}).get("gzip_kb", 0) <= 60,
        "all_assets": measurements
    }, f, indent=2)

print("Saved bundle measurements to evidence/order100/bundle_measurements.json")
