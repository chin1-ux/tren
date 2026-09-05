import ast
import re

with open('api.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

tree = ast.parse("".join(lines))
models = []
for node in tree.body:
    if isinstance(node, ast.ClassDef):
        is_model = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                is_model = True
        if is_model:
            models.append({
                'name': node.name,
                'start': node.lineno - 1,
                'end': node.end_lineno
            })

models.sort(key=lambda x: x['start'], reverse=True)

schema_lines = []
for m in models:
    block = lines[m['start']:m['end']]
    schema_lines = block + ["\n"] + schema_lines
    # delete from lines
    del lines[m['start']:m['end']]

with open('schemas.py', 'a', encoding='utf-8') as f:
    f.writelines(schema_lines)

with open('api.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Moved", len(models), "models to schemas.py")
