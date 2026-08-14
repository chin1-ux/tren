# Vercel entry‑point for the FastAPI app
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from backend.api import app

# Vercel Python function handler using starlette's ASGIAdapter
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.applications import Starlette

# Wrap FastAPI app for Vercel
asgi_app = app

def handler(request):
    """Vercel Python function handler."""
    from http.server import BaseHTTPRequestHandler
    import io
    import json
    
    # Parse Vercel request
    method = request.get("method", "GET")
    path = request.get("path", "/")
    headers = request.get("headers", {})
    body = request.get("body", "")
    
    # Convert to ASGI scope-like structure
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "server": ("vercel", 80),
        "scheme": "https",
    }
    
    # Simple response for testing
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok", "path": path, "method": method})
    }
