# Vercel entry‑point for the FastAPI app
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app

# Vercel Python function handler
def handler(request):
    """Vercel Python function handler that wraps FastAPI ASGI app."""
    from mangum import Mangum
    
    # Mangum converts ASGI apps to AWS Lambda/Vercel compatible handlers
    asgi_handler = Mangum(app)
    return asgi_handler(request)
