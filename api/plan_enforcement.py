# Symlink/copy for Vercel deployment - points to backend/plan_enforcement.py
import os
import sys

# Ensure backend is in path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import the real module
from backend.plan_enforcement import *

# Re-export everything to make this module work as a drop-in replacement
__all__ = ['PlanEnforcement', 'require_feature', 'require_credits', 'log_endpoint_usage', 'require_phone_verified', 'CREDIT_COSTS']
