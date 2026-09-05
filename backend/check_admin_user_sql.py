#!/usr/bin/env python3
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Query admin_users table
res = supabase.table("admin_users").select("email, role").execute()
print("SELECT email, role FROM admin_users;")
for row in res.data:
    print(f"{row['email']}, {row['role']}")
