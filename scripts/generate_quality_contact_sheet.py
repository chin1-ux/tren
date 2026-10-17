import os
import sys
import json
from datetime import datetime, timezone
from collections import Counter
from dotenv import load_dotenv

load_dotenv("backend/.env")
load_dotenv(".env")

sys.path.append(".")
from supabase import create_client
from backend.quality_engine import evaluate_quality

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY"))

print("1. Fetching user saved trend IDs...")
saved_res = sb.table("trend_actions").select("trend_id").eq("action_type", "target").execute()
saved_trend_ids = set(r["trend_id"] for r in saved_res.data or [])
print(f"Total user saved trends: {len(saved_trend_ids)}")

print("2. Fetching audio_first_seen creators map...")
# audio_first_seen has creators_seen
afs_map = {}
offset = 0
while True:
    res_afs = sb.table("audio_first_seen").select("audio_id, creators_seen, reels_seen").range(offset, offset + 999).execute()
    data = res_afs.data or []
    for r in data:
        afs_map[r["audio_id"]] = r.get("creators_seen") or 1
    if len(data) < 1000:
        break
    offset += 1000
print(f"Loaded {len(afs_map)} audio provenance records.")

print("3. Fetching trends with slim columns...")
trends = []
offset = 0
while True:
    res_t = sb.table("trends").select(
        "id, audio_id, audio_title, audio_artist, language_final, language, status, stage, velocity_avg, reel_count, is_original_audio_resolved, shazam_id, why_this_works, used_for_note"
    ).range(offset, offset + 999).execute()
    data = res_t.data or []
    trends.extend(data)
    if len(data) < 1000:
        break
    offset += 1000
print(f"Loaded {len(trends)} trends.")

print("4. Evaluating quality tiers...")
evaluations = []
tier_counts = Counter()
reason_counts = Counter()

# HARD TEST: count how many never_hide trends end up in Tier C
hard_test_failures = []

for t in trends:
    aid = t.get("audio_id") or ""
    # Distinct creators: audio_first_seen.creators_seen > trend.reel_count
    distinct_creators = afs_map.get(aid) or t.get("reel_count") or 1
    is_saved = t["id"] in saved_trend_ids
    
    # We evaluate both in India mode (primary)
    ev = evaluate_quality(t, distinct_creators=distinct_creators, is_saved_by_user=is_saved, mode="india")
    evaluations.append((t, ev))
    tier = ev["tier"]
    tier_counts[tier] += 1
    for r in ev["reasons"]:
        reason_counts[r] += 1
        
    # Check NEVER-HIDE violation
    if "never_hide_saved_by_user" in ev["reasons"] or "never_hide_market_fit_multi_creator" in ev["reasons"]:
        if tier == "C":
            hard_test_failures.append((t["id"], t["audio_title"], ev["reasons"]))

print("\nQuality Evaluation Summary:")
print(f"Total Evaluated: {len(evaluations)}")
print(f"Tier A: {tier_counts['A']}")
print(f"Tier B: {tier_counts['B']}")
print(f"Tier C (Quarantine): {tier_counts['C']}")
print(f"\nHARD TEST NEVER-HIDE Failures in Tier C: {len(hard_test_failures)}")

# Select 50 would-be-hidden (Tier C) and 50 would-be-shown (Tier A/B)
hidden_50 = [item for item in evaluations if item[1]["tier"] == "C"][:50]
shown_50 = [item for item in evaluations if item[1]["tier"] in ["A", "B"]][:50]

# Write Raw Evidence Report
out_lines = [
    "=" * 80,
    "ORDER 81: PHASE 2 QUALITY GATE (SHADOW MODE) AUDIT REPORT",
    f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
    "=" * 80,
    f"\nTOTAL TRENDS EVALUATED: {len(evaluations)}",
    f"Tier A (High Confidence Music): {tier_counts['A']} ({round(tier_counts['A']/len(evaluations)*100, 1)}%)",
    f"Tier B (Eligible Adoption/Emerging): {tier_counts['B']} ({round(tier_counts['B']/len(evaluations)*100, 1)}%)",
    f"Tier C (Quarantined/Hidden): {tier_counts['C']} ({round(tier_counts['C']/len(evaluations)*100, 1)}%)",
    f"\nHARD TEST RESULT: {len(hard_test_failures)} Never-Hide trends in Tier C (PASS = 0). Status: {'PASS' if len(hard_test_failures) == 0 else 'FAIL'}",
    "\nBREAKDOWN BY REASON:",
    "-" * 60
]
for r, c in reason_counts.most_common():
    out_lines.append(f"{r:<50} : {c}")

out_lines.append("\nSAMPLE 10 WOULD-BE-HIDDEN (TIER C):")
out_lines.append(f"{'ID':<6} | {'Lang':<5} | {'Creators':<8} | {'Title':<25} | {'Primary Reason':<30}")
out_lines.append("-" * 80)
for t, ev in hidden_50[:10]:
    title = (t.get("audio_title") or "")[:25].encode("ascii", "replace").decode("ascii")
    out_lines.append(f"{t['id']:<6} | {ev['signals']['language_final']:<5} | {ev['signals']['distinct_creators']:<8} | {title:<25} | {ev['reasons'][0]:<30}")

out_lines.append("\nSAMPLE 10 WOULD-BE-SHOWN (TIER A/B):")
out_lines.append(f"{'ID':<6} | {'Tier':<4} | {'Lang':<5} | {'Creators':<8} | {'Title':<25} | {'Reason':<30}")
out_lines.append("-" * 80)
for t, ev in shown_50[:10]:
    title = (t.get("audio_title") or "")[:25].encode("ascii", "replace").decode("ascii")
    out_lines.append(f"{t['id']:<6} | {ev['tier']:<4} | {ev['signals']['language_final']:<5} | {ev['signals']['distinct_creators']:<8} | {title:<25} | {ev['reasons'][0]:<30}")

evidence_path = "evidence/order81/phase2_quality_gate.txt"
with open(evidence_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines))
print(f"\nSaved raw evidence to {evidence_path}")

# Generate Modern HTML Contact Sheet
html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trendrop - Quality Gate Contact Sheet (Shadow Mode)</title>
<style>
  :root {{
    --bg: #0b0f19;
    --card: #151d2f;
    --border: #232f48;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --tier-a: #10b981;
    --tier-b: #3b82f6;
    --tier-c: #ef4444;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
  body {{ background: var(--bg); color: var(--text); padding: 32px 20px; line-height: 1.5; }}
  .container {{ max-width: 1200px; margin: 0 auto; }}
  header {{ margin-bottom: 32px; border-bottom: 1px solid var(--border); padding-bottom: 24px; }}
  h1 {{ font-size: 26px; font-weight: 800; display: flex; align-items: center; gap: 10px; }}
  .badge-shadow {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.4); padding: 3px 10px; border-radius: 9999px; font-size: 13px; }}
  .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-top: 20px; }}
  .stat-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }}
  .stat-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; }}
  .stat-value {{ font-size: 28px; font-weight: 800; margin-top: 6px; }}
  .section {{ margin-top: 40px; }}
  h2 {{ font-size: 18px; font-weight: 700; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }}
  .table-wrapper {{ overflow-x: auto; background: var(--card); border: 1px solid var(--border); border-radius: 12px; }}
  table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
  th {{ background: rgba(0, 0, 0, 0.25); padding: 12px 16px; font-weight: 700; color: var(--text-muted); border-bottom: 1px solid var(--border); }}
  td {{ padding: 12px 16px; border-bottom: 1px solid var(--border); }}
  tr:last-child td {{ border-bottom: none; }}
  .chip {{ display: inline-block; padding: 3px 8px; border-radius: 6px; font-weight: 700; font-size: 11px; }}
  .chip-a {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
  .chip-b {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
  .chip-c {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
  .chip-lang {{ background: rgba(255, 255, 255, 0.08); color: var(--text); border: 1px solid rgba(255, 255, 255, 0.15); }}
  .reason {{ color: #cbd5e1; font-family: monospace; font-size: 12px; }}
</style>
</head>
<body>
<div class="container">
  <header>
    <h1>Trendrop Quality Gate Contact Sheet <span class="badge-shadow">Shadow Mode</span></h1>
    <p style="color: var(--text-muted); margin-top: 6px; font-size: 14px;">Evaluated {len(evaluations)} live database trends. Shadow mode: zero feed filters applied, zero data deleted.</p>
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">Tier A (High Confidence Music)</div>
        <div class="stat-value" style="color: var(--tier-a);">{tier_counts['A']}</div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">{round(tier_counts['A']/len(evaluations)*100, 1)}% of catalog</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tier B (Eligible / Emerging)</div>
        <div class="stat-value" style="color: var(--tier-b);">{tier_counts['B']}</div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">{round(tier_counts['B']/len(evaluations)*100, 1)}% of catalog</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Tier C (Quarantined / Hidden)</div>
        <div class="stat-value" style="color: var(--tier-c);">{tier_counts['C']}</div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">{round(tier_counts['C']/len(evaluations)*100, 1)}% of catalog</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Hard Test (Never-Hide in Tier C)</div>
        <div class="stat-value" style="color: {'#10b981' if len(hard_test_failures) == 0 else '#ef4444'};">{'PASS (0)' if len(hard_test_failures) == 0 else f'FAIL ({len(hard_test_failures)})'}</div>
        <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Guaranteed user saves & >=3 creators</div>
      </div>
    </div>
  </header>

  <!-- Section 1: 50 Would-be-hidden (Tier C) -->
  <div class="section">
    <h2><span class="chip chip-c">Tier C</span> 50 Would-be-hidden Audios (Quarantined)</h2>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Artist</th>
            <th>Lang</th>
            <th>Creators</th>
            <th>Quarantine Reason</th>
          </tr>
        </thead>
        <tbody>
"""

for t, ev in hidden_50:
    title = (t.get("audio_title") or "Unknown").replace("<", "&lt;").replace(">", "&gt;")
    artist = (t.get("audio_artist") or "Unknown").replace("<", "&lt;").replace(">", "&gt;")
    lang = ev["signals"]["language_final"].upper()
    creators = ev["signals"]["distinct_creators"]
    reasons_str = "<br>".join(ev["reasons"][:2])
    html_content += f"""          <tr>
            <td style="color: var(--text-muted); font-weight: 600;">#{t['id']}</td>
            <td style="font-weight: 700;">{title}</td>
            <td style="color: var(--text-muted);">{artist}</td>
            <td><span class="chip chip-lang">{lang}</span></td>
            <td style="font-weight: 600;">{creators}</td>
            <td class="reason">{reasons_str}</td>
          </tr>
"""

html_content += """        </tbody>
      </table>
    </div>
  </div>

  <!-- Section 2: 50 Would-be-shown (Tier A / Tier B) -->
  <div class="section">
    <h2><span class="chip chip-a">Tier A/B</span> 50 Would-be-shown Audios (Feed Eligible)</h2>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Tier</th>
            <th>Title</th>
            <th>Artist</th>
            <th>Lang</th>
            <th>Creators</th>
            <th>Eligibility Reason</th>
          </tr>
        </thead>
        <tbody>
"""

for t, ev in shown_50:
    title = (t.get("audio_title") or "Unknown").replace("<", "&lt;").replace(">", "&gt;")
    artist = (t.get("audio_artist") or "Unknown").replace("<", "&lt;").replace(">", "&gt;")
    lang = ev["signals"]["language_final"].upper()
    creators = ev["signals"]["distinct_creators"]
    tier_class = "chip-a" if ev["tier"] == "A" else "chip-b"
    reasons_str = "<br>".join(ev["reasons"][:2])
    html_content += f"""          <tr>
            <td style="color: var(--text-muted); font-weight: 600;">#{t['id']}</td>
            <td><span class="chip {tier_class}">Tier {ev['tier']}</span></td>
            <td style="font-weight: 700;">{title}</td>
            <td style="color: var(--text-muted);">{artist}</td>
            <td><span class="chip chip-lang">{lang}</span></td>
            <td style="font-weight: 600;">{creators}</td>
            <td class="reason">{reasons_str}</td>
          </tr>
"""

html_content += """        </tbody>
      </table>
    </div>
  </div>
</div>
</body>
</html>
"""

html_path = "evidence/order81/quality_contact_sheet.html"
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Saved HTML contact sheet to {html_path}")
