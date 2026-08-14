# Vercel entry‑point for the FastAPI app
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.api import app

# Vercel Python function handler
from mangum import Mangum
handler = Mangum(app)
