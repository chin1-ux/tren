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

    # Copy entrypoint as index.py (valid python module name)
    shutil.copy2('api/[...path].py', os.path.join(func_dir, 'index.py'))

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
        "handler": "index.py",
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
    print("Modifying .vercel/output/config.json to inject API route...")
    with open(config_path, 'r') as f:
        config = json.load(f)
else:
    print("Creating .vercel/output/config.json from scratch...")
    config = {"version": 3}

config['version'] = 3
existing_routes = config.get('routes', [])
# Ensure api_route is at the top
filtered_routes = [r for r in existing_routes if r.get('dest') != '/api/[...path]']
config['routes'] = [api_route] + filtered_routes

os.makedirs(os.path.dirname(config_path), exist_ok=True)
with open(config_path, 'w') as f:
    json.dump(config, f, indent=2)
print("Successfully injected API route into config.json!")

def copy_static_assets():
    static_dst = '.vercel/output/static'
    os.makedirs(static_dst, exist_ok=True)
    
    pub_dir = 'frontend/public'
    if os.path.exists(pub_dir):
        for f in os.listdir(pub_dir):
            s = os.path.join(pub_dir, f)
            d = os.path.join(static_dst, f)
            if os.path.isfile(s):
                shutil.copy2(s, d)
                print(f"Copied public asset {f} to {static_dst}")
                
    dist_dir = 'frontend/dist'
    if os.path.exists(dist_dir):
        for f in os.listdir(dist_dir):
            s = os.path.join(dist_dir, f)
            d = os.path.join(static_dst, f)
            if os.path.isfile(s):
                shutil.copy2(s, d)
                print(f"Copied dist asset {f} to {static_dst}")

clean_func_dir()
bundle_python_function()
copy_static_assets()

