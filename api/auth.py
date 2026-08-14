# Symlink/copy for Vercel deployment - points to backend/auth.py
import os
import sys

# Ensure backend is in path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import the real module
from backend.auth import *
