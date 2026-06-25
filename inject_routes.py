import json
import os

config_path = '.vercel/output/config.json'
if os.path.exists(config_path):
    print("Modifying .vercel/output/config.json to add custom API routes...")
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    routes = config.get('routes', [])
    
    # Prepend the API routing rule
    api_route = {
        "src": "/api/(.*)",
        "dest": "/api/[...path].py"
    }
    
    # Check if already present to avoid duplication
    if not any(r.get('src') == "/api/(.*)" for r in routes):
        routes.insert(0, api_route)
        
    config['routes'] = routes
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print("Successfully injected API routes!")
else:
    print(".vercel/output/config.json not found!")
