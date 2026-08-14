# Vercel entry‑point for the FastAPI app
import os
import sys

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from backend.api import app

# Vercel Python function handler using mangum
from mangum import Mangum
handler = Mangum(app)

