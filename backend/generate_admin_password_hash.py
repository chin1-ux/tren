#!/usr/bin/env python3
"""
Generate bcrypt hash for admin password.
Usage: python generate_admin_password_hash.py <password>
"""

import bcrypt
import sys

def generate_bcrypt_hash(password: str) -> str:
    """Generate bcrypt hash for the given password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_admin_password_hash.py <password>")
        print("Example: python generate_admin_password_hash.py MySecurePassword123")
        exit(1)
    
    password = sys.argv[1]
    if not password:
        print("Error: Password cannot be empty")
        exit(1)
    
    hash_result = generate_bcrypt_hash(password)
    print(f"\n=== BCRYPT HASH ===")
    print(hash_result)
    print("\nUse this hash in the SQL INSERT statement:")
    print(f"INSERT INTO admin_users (email, password_hash, role)")
    print(f"VALUES ('chinmay.feb03@gmail.com', '{hash_result}', 'super_admin');")
