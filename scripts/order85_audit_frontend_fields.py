import os
import re
import json

frontend_src = "frontend/src"
fields_used = set()

# Pattern for t.field or trend.field or item.field
pattern1 = re.compile(r'\b(?:trend|t|item|trendItem)\.([a-zA-Z0-9_]+)\b')
# Pattern for destructuring: const { a, b, c } = trend
pattern2 = re.compile(r'(?:const|let)\s*\{([^}]+)\}\s*=\s*(?:trend|props\.trend|item)\b')

for root, _, files in os.walk(frontend_src):
    for f in files:
        if f.endswith(('.tsx', '.ts')):
            p = os.path.join(root, f)
            with open(p, encoding='utf-8', errors='replace') as fp:
                content = fp.read()
                
            for m in pattern1.finditer(content):
                field = m.group(1)
                # Filter out obvious JS methods
                if field not in ('map', 'filter', 'forEach', 'length', 'toString', 'includes', 'slice', 'reduce', 'some', 'find', 'trim'):
                    fields_used.add(field)
                    
            for m in pattern2.finditer(content):
                for subfield in m.group(1).split(','):
                    sub = subfield.split(':')[0].strip()
                    if sub and not sub.startswith(('//', '/*')):
                        fields_used.add(sub)

# Check ApiTrend in api.ts
api_ts_path = "frontend/src/lib/api.ts"
api_trend_fields = []
with open(api_ts_path, encoding='utf-8') as fp:
    content = fp.read()
    m = re.search(r'export interface ApiTrend \{([^}]+)\}', content)
    if m:
        for line in m.group(1).splitlines():
            line = line.strip()
            if line and not line.startswith('//'):
                fname = line.split('?')[0].split(':')[0].strip()
                if fname:
                    api_trend_fields.append(fname)

# Intersect fields_used with api_trend_fields to find genuinely read fields
genuinely_read = sorted(list(fields_used.intersection(set(api_trend_fields))))

print(f"Total ApiTrend fields in interface: {len(api_trend_fields)}")
print(f"Total fields actively referenced in frontend components: {len(genuinely_read)}")
print("\nActively read fields:")
print(json.dumps(genuinely_read, indent=2))

os.makedirs("evidence/order85", exist_ok=True)
with open("evidence/order85/frontend_fields_audit.json", "w", encoding="utf-8") as out:
    json.dump({
        "total_interface_fields": len(api_trend_fields),
        "total_actively_read_fields": len(genuinely_read),
        "actively_read_fields": genuinely_read
    }, out, indent=2)
