# Vercel entry‑point for the FastAPI app
# This file simply re‑exports the FastAPI instance defined in backend/api.py
from backend.api import app  # noqa: F401
