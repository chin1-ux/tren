import os
import re

out_lines = [
    "=" * 80,
    "ORDER 81: PHASE 3 INTERACTIVE ELEMENTS & BANNED STRINGS AUDIT",
    "=" * 80
]

# 1. Count interactive elements in DeckCard.tsx
card_file = "frontend/src/components/DeckCard.tsx"
interactive_elements = []
with open(card_file, "r", encoding="utf-8") as f:
    content = f.read()

# Match interactive elements on card face (before INFO SHEET)
card_face = content.split("{/* ── INFO SHEET")[0]
element_matches = re.findall(r'id="card-[^"]+"', card_face)

out_lines.append(f"\n1. INTERACTIVE ELEMENTS COUNT ON CARD FACE (Target <= 6):")
out_lines.append(f"Card face content: {card_file}")
for em in element_matches:
    out_lines.append(f"  • Found: {em}")
out_lines.append(f"Total Interactive Elements: {len(element_matches)}")
out_lines.append(f"Verdict: {'PASS (<= 6)' if len(element_matches) <= 6 else 'FAIL (> 6)'}")

# 2. Audit Banned Strings Across frontend/src and backend/
banned_strings = [
    'Act now',
    'First-mover advantage',
    'Tracking started',
    'Play Drop',
    'Drop/Growth',
    'Try as Trial Reel',
    'Optimal Post Window',
    'Hook Power',
    'Golden Hour Window'
]

matches = []
for scan_dir in ['frontend/src', 'backend']:
    for root, dirs, files in os.walk(scan_dir):
        dirs[:] = [d for d in dirs if not d.startswith('.') and 'venv' not in d and d != '__pycache__']
        for f in files:
            if f.endswith(('.tsx', '.ts', '.jsx', '.js', '.py')):
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    for line_no, line in enumerate(fp, 1):
                        for b in banned_strings:
                            if b.lower() in line.lower():
                                safe_line = line.strip().encode('ascii', 'replace').decode('ascii')
                                matches.append((path, line_no, b, safe_line))

out_lines.append(f"\n2. BANNED STRINGS SCAN ACROSS CODEBASE:")
for b in banned_strings:
    count_for_b = sum(1 for m in matches if m[2].lower() == b.lower())
    out_lines.append(f"  • '{b}': {count_for_b} occurrences")

out_lines.append(f"\nTotal Banned String Matches Found: {len(matches)}")
out_lines.append(f"Verdict: {'PASS (0 occurrences)' if len(matches) == 0 else 'FAIL'}")

output_report = "\n".join(out_lines)
print(output_report)

evidence_path = "evidence/order81/phase3_element_and_string_proof.txt"
with open(evidence_path, "w", encoding="utf-8") as f:
    f.write(output_report)
print(f"\nEvidence written to {evidence_path}")
