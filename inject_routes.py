import json
import os
import shutil

config_path = '.vercel/output/config.json'
func_dir = '.vercel/output/functions/api/[...path].func'

def clean_func_dir():
    if os.path.exists(func_dir):
        print("Cleaning existing function directory...")
        def remove_readonly(func, path, exc_info):
            import stat
            os.chmod(path, stat.S_IWRITE)
            func(path)
        try:
            shutil.rmtree(func_dir, onexc=remove_readonly)
        except TypeError:
            shutil.rmtree(func_dir, onerror=remove_readonly)

def bundle_python_function():
    os.makedirs(func_dir, exist_ok=True)

    os.makedirs(os.path.join(func_dir, 'api'), exist_ok=True)
    shutil.copy2('api/[...path].py', os.path.join(func_dir, 'api', '[...path].py'))

    dest_backend = os.path.join(func_dir, 'backend')
    shutil.copytree(
        'backend',
        dest_backend,
        ignore=shutil.ignore_patterns('venv', '.venv', '__pycache__', '*.pyc', '*.pyo', '.env', '*.log', 'uploads', 'outputs')
    )

    for filename in ['requirements.txt', 'pyproject.toml', '.python-version']:
        if os.path.exists(filename):
            shutil.copy2(filename, os.path.join(func_dir, filename))

    vc_config = {
        "runtime": "python3.12",
        "handler": "api/[...path].py",
        "launcherType": "Nodejs",
        "maxDuration": 30
    }
    with open(os.path.join(func_dir, '.vc-config.json'), 'w') as f:
        json.dump(vc_config, f, indent=2)
    print("Successfully packaged Python serverless function!")

api_route = {
    "src": "/api/(.*)",
    "dest": "/api/[...path]"
}

if os.path.exists(config_path):
    print("Modifying .vercel/output/config.json to add custom API routes...")
    with open(config_path, 'r') as f:
        config = json.load(f)
else:
    print("Creating .vercel/output/config.json from scratch...")
    config = {"version": 3}

routes = config.get('routes', [])

if not any(r.get('src') == "/api/(.*)" for r in routes):
    routes.insert(0, api_route)

config['routes'] = routes

os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print("Successfully injected API routes!")

clean_func_dir()
bundle_python_function()
