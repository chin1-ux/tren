import ast
import re
import os

with open('api.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Extract endpoints using AST for precise line numbers
tree = ast.parse("".join(lines))
endpoints = []
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        is_endpoint = False
        path = ""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == 'app':
                    is_endpoint = True
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        path = decorator.args[0].value
        if is_endpoint:
            endpoints.append({
                'name': node.name,
                'path': path,
                'start': node.lineno - len(node.decorator_list), # Rough, we'll refine
                'end': node.end_lineno
            })

# Refine start lines (include decorators)
for e in endpoints:
    while e['start'] > 1 and lines[e['start'] - 2].strip().startswith('@'):
        e['start'] -= 1

endpoints.sort(key=lambda x: x['start'])

# Group endpoints
groups = {
    'auth': ['/api/auth', '/api/phone', '/api/instagram'],
    'trends': ['/api/trends', '/api/algorithm', '/api/hashtags'],
    'ai': ['/api/ai', '/api/generate', '/api/repurpose', '/api/seo-caption', '/api/video', '/api/prepost-score', '/api/score-reel', '/api/calendar', '/api/daily-ideas'],
    'creator': ['/api/creator', '/api/marketplace', '/api/deals', '/api/brand-deals', '/api/collab-matches', '/api/user'],
    'admin': ['/api/admin', '/api/business', '/api/case-studies', '/api/pitch-deck'],
    'india': ['/api/india'],
    'system': ['/health', '/api/health', '/api/proof', '/api/cron', '/api/job-status', '/api/reel-status', '/api/run-scraper', '/api/feedback', '/api/analytics']
}

def get_group(path):
    for group, prefixes in groups.items():
        for prefix in prefixes:
            if path.startswith(prefix):
                return group
    return 'system'

grouped_endpoints = {g: [] for g in groups.keys()}
for e in endpoints:
    if not e['path']: continue
    g = get_group(e['path'])
    grouped_endpoints[g].append(e)

# Create routes directory
os.makedirs('routes', exist_ok=True)

# Standard imports for every route file to prevent NameErrors
standard_imports = """from fastapi import APIRouter, HTTPException, Depends, Request, Header, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import os, json, time, logging, traceback
from api_globals import *
from schemas import *

router = APIRouter()
"""

# We will create `api_globals.py` by extracting lines 1 to 508 of api.py
api_globals_lines = lines[0:508]
with open('api_globals.py', 'w', encoding='utf-8') as f:
    f.writelines(api_globals_lines)

# We will extract Pydantic models (lines 960-1070 roughly, let's just use exact lines)
# Let's find exactly where Pydantic models start and end.
pydantic_start = 0
for i, l in enumerate(lines):
    if 'Pydantic Models' in l:
        pydantic_start = i
        break
pydantic_end = 1070
for i in range(pydantic_start, len(lines)):
    if 'Health' in lines[i] or 'health_check' in lines[i]:
        pydantic_end = i - 1
        break

schemas_lines = ["from pydantic import BaseModel, EmailStr\nfrom typing import List, Optional\n\n"] + lines[pydantic_start:pydantic_end]
with open('schemas.py', 'w', encoding='utf-8') as f:
    f.writelines(schemas_lines)

# Write each route file
used_lines = set()
for g, eps in grouped_endpoints.items():
    if not eps: continue
    route_content = standard_imports + "\n"
    for e in eps:
        # get lines
        block = lines[e['start']-1 : e['end']]
        # replace @app with @router
        for i in range(len(block)):
            if block[i].strip().startswith('@app.'):
                block[i] = block[i].replace('@app.', '@router.')
            used_lines.add(e['start'] - 1 + i)
        route_content += "".join(block) + "\n\n"
    with open(f"routes/{g}.py", 'w', encoding='utf-8') as f:
        f.write(route_content)

# Now, recreate api.py
new_api_lines = []
new_api_lines.append("from api_globals import *\n")
new_api_lines.append("from schemas import *\n")
new_api_lines.append("from fastapi import FastAPI, Request\n")
new_api_lines.append("from fastapi.responses import JSONResponse\n")
new_api_lines.append("import traceback\n\n")

# Include routers
for g in grouped_endpoints.keys():
    if grouped_endpoints[g]:
        new_api_lines.append(f"from routes.{g} import router as {g}_router\n")
        new_api_lines.append(f"app.include_router({g}_router)\n")
new_api_lines.append("\n")

# Include the rest of the lines that were not models and not endpoints
for i, l in enumerate(lines):
    if i < 508:
        continue
    if pydantic_start <= i < pydantic_end:
        continue
    if i in used_lines:
        continue
    if l.strip().startswith('import '): continue # skip top level imports since we have them in globals
    # We add the remaining lines
    new_api_lines.append(l)

with open('api_new.py', 'w', encoding='utf-8') as f:
    f.writelines(new_api_lines)

print("Refactoring complete! Check api_new.py and routes/ folder.")
