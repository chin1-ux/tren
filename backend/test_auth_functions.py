#!/usr/bin/env python3
"""
Test auth functions directly
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.auth import get_admin_user_by_email, verify_password

print("=== Test Auth Functions ===\n")

# Test get_admin_user_by_email
email = "chinmay.feb03@gmail.com"
print(f"Testing get_admin_user_by_email for {email}...")
admin_user = get_admin_user_by_email(email)
print(f"Result: {admin_user}")

if admin_user:
    print(f"\n✅ Admin user found:")
    print(f"   Email: {admin_user.get('email')}")
    print(f"   Role: {admin_user.get('role')}")
    print(f"   Password hash: {admin_user.get('password_hash')[:50]}...")
    
    # Test password verification
    password = "nagaiah.rathna76"
    print(f"\nTesting password verification for '{password}'...")
    result = verify_password(password, admin_user["password_hash"])
    print(f"Verification result: {result}")
else:
    print("❌ Admin user not found")
