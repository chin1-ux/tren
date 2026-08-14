import os
import sys

# Ensure project root is on PYTHONPATH so backend modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.api import app

class LoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            print(f"DEBUG ASGI SCOPE PATH: {scope.get('path')} | RAW PATH: {scope.get('raw_path')}")
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            print(f"ERROR in ASGI middleware: {e}")
            import traceback
            traceback.print_exc()
            raise

# Export the wrapped app
app = LoggingMiddleware(app)
