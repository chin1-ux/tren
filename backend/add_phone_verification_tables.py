"""
Add Phone Verification Tables to Supabase
Creates tables for phone verification system
"""
import os
import sys
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

load_dotenv()

print("=== Add Phone Verification Tables ===")

# SQL to create tables
sql_statements = [
    # Phone verifications table
    """
    CREATE TABLE IF NOT EXISTS phone_verifications (
        id BIGSERIAL PRIMARY KEY,
        phone_number TEXT UNIQUE NOT NULL,
        verification_code TEXT NOT NULL,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        verified BOOLEAN DEFAULT FALSE,
        verified_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """,
    
    # Index for faster lookups
    """
    CREATE INDEX IF NOT EXISTS idx_phone_verifications_phone ON phone_verifications(phone_number);
    """,
    
    """
    CREATE INDEX IF NOT EXISTS idx_phone_verifications_expires ON phone_verifications(expires_at);
    """
]

print("\n=== SQL Statements for Manual Execution ===")
print("\nPlease run these SQL statements in Supabase SQL Editor:")

for i, sql in enumerate(sql_statements, 1):
    print(f"\n-- Table/Index {i}")
    print(sql)

print("\n=== Phone Verification Tables Setup Complete ===")
print("\nNote: These tables are required for the phone verification system.")
print("After creating the tables, you can use the phone_verification.py module.")