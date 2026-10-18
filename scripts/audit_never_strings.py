import os
import re
import json

PROHIBITED_PATTERNS = [
    r"golden\s*hour",
    r"act\s*now",
    r"film\s*now",
    r"first-mover\s*advantage",
    r"tracking\s*started",
    r"classifying",
    r"play\s*drop",
    r"\bgrowth\b",
    r"early\s*signal",
    r"try\s*as\s*trial\s*reel",
    r"optimal\s*post\s*window",
    r"why\s*this\s*works",
    r"run\s*a/b\s*batches",
    r"1\s*reels\s*tracked"
]

TARGET_FILES = [
    r"frontend\src\routes\deck.tsx",
    r"frontend\src\components\deck\DeckCard.tsx",
    r"frontend\src\components\deck\DeckInfoSheet.tsx",
    r"frontend\src\components\deck\DeckWatchSheet.tsx",
    r"frontend\src\components\deck\DeckExplore.tsx",
    r"frontend\src\components\deck\DeckPicks.tsx",
    r"frontend\src\components\deck\DeckOnboarding.tsx",
    r"frontend\src\lib\deck-ranking.ts",
    r"frontend\src\lib\deck-tokens.ts",
    r"backend\routes\deck.py"
]

findings = []
for rel_path in TARGET_FILES:
    abs_path = os.path.join(r"c:\Users\Chinmay\OneDrive\Desktop\trendrop", rel_path)
    if not os.path.exists(abs_path):
        print(f"Warning: {abs_path} does not exist")
        continue
    with open(abs_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    for pattern in PROHIBITED_PATTERNS:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for m in matches:
            line_no = content[:m.start()].count("\n") + 1
            findings.append({
                "file": rel_path,
                "line": line_no,
                "pattern": pattern,
                "match": m.group(0)
            })

os.makedirs("evidence/order100", exist_ok=True)
with open("evidence/order100/grep_proof_never_strings.json", "w", encoding="utf-8") as f:
    json.dump({
        "status": "PASS" if len(findings) == 0 else "FAIL",
        "violations_count": len(findings),
        "violations": findings
    }, f, indent=2)

print(f"Never-strings audit complete. Violations found: {len(findings)}")
if findings:
    print(json.dumps(findings, indent=2))
else:
    print("ALL TARGET FILES ARE 100% CLEAN OF PROHIBITED STRINGS! PASS.")
