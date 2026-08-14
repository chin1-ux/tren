# Vercel entry‑point for the FastAPI app
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from backend.api import app

# Vercel Python function handler
async def handler(request):
    """Vercel Python function handler for FastAPI."""
    from fastapi import Response
    from fastapi.testclient import TestClient
    import json
    
    client = TestClient(app)
    
    # Parse Vercel request
    method = request.get("method", "GET")
    path = request.get("path", "/")
    headers = request.get("headers", {})
    body = request.get("body", "")
    
    # Make request to FastAPI app
    try:
        if method == "GET":
            response = client.get(path, headers=headers)
        elif method == "POST":
            response = client.post(path, headers=headers, content=body)
        elif method == "PUT":
            response = client.put(path, headers=headers, content=body)
        elif method == "DELETE":
            response = client.delete(path, headers=headers)
        else:
            response = client.request(method, path, headers=headers, content=body)
        
        return {
            "statusCode": response.status_code,
            "headers": dict(response.headers),
            "body": response.text
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }
