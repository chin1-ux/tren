import os
import sys

# Ensure project root is on PYTHONPATH so backend modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.api import app
import serverless_wsgi

def handler(request):
    """Vercel serverless entrypoint for any path under `/api/*`.
    Uses `serverless_wsgi` to translate Vercel's request dict into an ASGI call.
    """
    return serverless_wsgi.handle_request(app, request)
