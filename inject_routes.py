import json
import os
import shutil

config_path = '.vercel/output/config.json'
if os.path.exists(config_path):
    print("Modifying .vercel/output/config.json to add custom API routes...")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    routes = config.get('routes', [])
    
    # Prepend the API routing rule
    api_route = {
        "src": "/api/(.*)",
        "dest": "/api/[...path]"
    }
    
    # Check if already present to avoid duplication
    if not any(r.get('src') == "/api/(.*)" for r in routes):
        routes.insert(0, api_route)
        
    config['routes'] = routes
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print("Successfully injected API routes!")
    
    # Bundle the python serverless function into the build output
    func_dir = '.vercel/output/functions/api/[...path].func'
    print(f"Bundling python serverless function into: {func_dir}")
    
    # Remove previous bundle if it exists to ensure a clean state
    if os.path.exists(func_dir):
        print(f"Cleaning existing function directory...")
        # Handle potential read-only file removal issues on Windows
        def onerror(func, path, exc_info):
            import stat
            os.chmod(path, stat.S_IWRITE)
            func(path)
        shutil.rmtree(func_dir, onexc=onerror)
        
    os.makedirs(func_dir, exist_ok=True)
    
    # Copy API handler script preserving directory structure
    os.makedirs(os.path.join(func_dir, 'api'), exist_ok=True)
    shutil.copy2('api/[...path].py', os.path.join(func_dir, 'api', '[...path].py'))
    
    # Copy backend modules, ignoring virtual environment, cache, logs, and temp uploads/outputs
    dest_backend = os.path.join(func_dir, 'backend')
    shutil.copytree(
        'backend', 
        dest_backend, 
        ignore=shutil.ignore_patterns('venv', '.venv', '__pycache__', '*.pyc', '*.pyo', '.env', '*.log', 'uploads', 'outputs')
    )


    
    # Copy config files
    for filename in ['requirements.txt', 'pyproject.toml', '.python-version']:
        if os.path.exists(filename):
            shutil.copy2(filename, os.path.join(func_dir, filename))
            
    # Write .vc-config.json
    vc_config = {
        "runtime": "python3.12",
        "handler": "api/[...path].py",
        "launcherType": "Nodejs"
    }
    with open(os.path.join(func_dir, '.vc-config.json'), 'w') as f:
        json.dump(vc_config, f, indent=2)
    print("Successfully packaged Python serverless function!")
else:
    print(".vercel/output/config.json not found!")

