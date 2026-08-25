#!/usr/bin/env python3
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check chinbinchin03@gmail.co current plan
res = supabase.table("users").select("email, plan, tier_id").eq("email", "chinbinchin03@gmail.co").execute()
if res.data:
    user = res.data[0]
    print(f"Database plan: {user.get('plan')}, tier_id: {user.get('tier_id')}")
else:
    print("User not found")
