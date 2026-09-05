import ast
import re
import os

with open('api.py', 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

endpoints = []
models = []

for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef):
        is_endpoint = False
        path = ""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == 'app':
                    is_endpoint = True
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value
            elif isinstance(decorator, ast.Attribute): # @app.get without call? unlikely
                pass
        if is_endpoint:
            endpoints.append({
                'name': node.name,
                'path': path,
                'start': node.lineno - len(node.decorator_list), # rough estimate
                'end': node.end_lineno
            })
    elif isinstance(node, ast.ClassDef):
        is_model = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == 'BaseModel':
                is_model = True
        if is_model:
            models.append({
                'name': node.name,
                'start': node.lineno,
                'end': node.end_lineno
            })

print(f"Found {len(endpoints)} endpoints and {len(models)} models.")
endpoints.sort(key=lambda x: x['start'])
for e in endpoints[:5]:
    print(e)
