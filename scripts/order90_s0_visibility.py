import os

targets = [
    "backend/routes",
    "backend/api_globals.py",
    "backend/trend_refresher.py",
    "frontend/src"
]

results = []

def scan_file(filepath):
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            for idx, line in enumerate(f, 1):
                if "llm_classification_status" in line or "VERIFIED_STATUSES" in line:
                    results.append(f"{filepath}:{idx}: {line.strip()}")
    except Exception:
        pass

for t in targets:
    if os.path.isfile(t):
        scan_file(t)
    elif os.path.isdir(t):
        for root, dirs, files in os.walk(t):
            for file in files:
                if file.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                    scan_file(os.path.join(root, file))

with open("evidence/order90/s0_visibility_audit.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))

print(f"Found {len(results)} references to llm_classification_status / VERIFIED_STATUSES:")
for r in results:
    print(" ", r)
