#!/usr/bin/env python3
"""
Phase 1: Restore admin schema
This script executes the restore_admin_schema.sql to recreate the admin tables.
"""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")

if not SUPABASE_URL or not SUPABASE_DB_URL:
    print("Missing SUPABASE_URL or SUPABASE_DB_URL")
    exit(1)

print("=== Phase 1: Restore Admin Schema ===")
print(f"Supabase URL: {SUPABASE_URL}")
print(f"Database URL: {SUPABASE_DB_URL[:50]}...\n")

# Read the SQL file
with open('backend/restore_admin_schema.sql', 'r') as f:
    sql_content = f.read()

print("SQL content to execute:")
print(sql_content)
print("\n" + "="*60)
print("INSTRUCTIONS:")
print("1. Copy the SQL content above")
print("2. Open Supabase SQL Editor in your browser")
print("3. Paste and execute the SQL")
print("4. Run: python generate_admin_password_hash.py")
print("5. Use the generated hash to insert your admin user")
print("="*60)
