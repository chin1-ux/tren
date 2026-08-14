# Symlink/copy for Vercel deployment - points to backend/auth.py
import os
import sys

# Ensure backend is in path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Import the real module
from backend.auth import *

# Re-export everything to make this module work as a drop-in replacement
__all__ = ['get_current_user', 'hash_password', 'verify_password', 'create_access_token',
           'verify_token', 'get_admin_user_by_email', 'require_admin', 'log_admin_login_attempt',
           'check_and_update_login_attempts', 'record_failed_login_attempt', 'reset_login_attempts']
