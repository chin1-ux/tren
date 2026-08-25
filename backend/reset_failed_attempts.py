#!/usr/bin/env python3
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Reset failed attempts for admin user
supabase.table("admin_users").update({
    "failed_login_attempts": 0,
    "locked_until": None
}).eq("email", "chinmay.feb03@gmail.com").execute()

print("Reset failed login attempts")
