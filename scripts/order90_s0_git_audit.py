import subprocess
import json
import os

files_to_check = [
    "backend/llm.py",
    "backend/cron_auto_classifier.py",
    "backend/nightly_llm_batch.py",
    "backend/check_pending_count.py",
    "backend/pending_timeout_fallback.py",
    ".github/workflows/nightly-llm-classification.yml",
    ".github/workflows/emergency-llm-classification.yml",
    ".github/workflows/pending-trends-fallback.yml"
]

res = {"trendrop": {}, "trendrop_tren": {}, "allam_log": "", "earliest_429": None}

# 1. git log between Oct 9 and Oct 14 in trendrop
for f in files_to_check:
    cmd = ["git", "log", "--since=2026-10-09", "--until=2026-10-14", "--format=%h %ad %an: %s", "--date=short", "--", f]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=".")
    if p.stdout.strip():
        res["trendrop"][f] = p.stdout.strip().splitlines()

# 2. git log between Oct 9 and Oct 14 in trendrop_tren
tren_path = os.path.abspath(os.path.join("..", "trendrop_tren"))
if os.path.exists(tren_path):
    for f in files_to_check:
        cmd = ["git", "log", "--since=2026-10-09", "--until=2026-10-14", "--format=%h %ad %an: %s", "--date=short", "--", f]
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=tren_path)
        if p.stdout.strip():
            res["trendrop_tren"][f] = p.stdout.strip().splitlines()

# 3. git log -S"allam-2-7b"
p_allam = subprocess.run(["git", "log", "-Sallam-2-7b", "--format=%h %ad %an: %s", "--date=iso"], capture_output=True, text=True)
res["allam_log"] = p_allam.stdout.strip().splitlines()

# 4. Search actions logs on or before Oct 12 in chin1-ux/tren
cmd_runs = ["gh", "run", "list", "--repo", "chin1-ux/tren", "--created", "<=2026-10-12", "--limit", "20", "--json", "databaseId,createdAt,workflowName"]
p_runs = subprocess.run(cmd_runs, capture_output=True, text=True)
if p_runs.returncode == 0 and p_runs.stdout.strip():
    runs = json.loads(p_runs.stdout)
    for r in runs:
        rid = r["databaseId"]
        p_log = subprocess.run(["gh", "run", "view", "--repo", "chin1-ux/tren", str(rid), "--log"], capture_output=True, text=True, errors="ignore")
        for line in p_log.stdout.splitlines():
            if "429" in line or "All Groq API keys failed" in line:
                res["earliest_429"] = {
                    "run_id": rid,
                    "created_at": r["createdAt"],
                    "workflow": r["workflowName"],
                    "line": line.strip()
                }
                break
        if res["earliest_429"]:
            break

out_path = "evidence/order90/s0_git_audit.json"
with open(out_path, "w") as f:
    json.dump(res, f, indent=2)

print("Saved git audit to", out_path)
print("Trendrop changes Oct 9-14:", json.dumps(res["trendrop"], indent=2))
print("Trendrop_tren changes Oct 9-14:", json.dumps(res["trendrop_tren"], indent=2))
print("Allam-2-7b history:", json.dumps(res["allam_log"], indent=2))
print("Earliest 429 on/before Oct 12:", res["earliest_429"])
