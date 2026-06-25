import os
import sys

# Ensure backend modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.api import app

def handler(request):
    """Vercel serverless entrypoint that forwards the request to the FastAPI app.
    Uses serverless_wsgi to translate the Vercel request dict into an ASGI call.
    """
    import serverless_wsgi
    return serverless_wsgi.handle_request(app, request)
