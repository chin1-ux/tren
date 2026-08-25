#!/usr/bin/env python3
"""
Test password verification
"""

import bcrypt

# The hash from the database
stored_hash = "$2b$12$Q7yDXG726Osu5tLYqAbgxumbnYBa.35MnD/RExoh2zOcoc0xcrcVy"
password = "nagaiah.rathna76"

print("=== Password Verification Test ===\n")
print(f"Password: {password}")
print(f"Stored hash: {stored_hash}")

# Test verification
result = bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
print(f"\nVerification result: {result}")

# Test with wrong password
wrong_password = "wrongpassword"
wrong_result = bcrypt.checkpw(wrong_password.encode('utf-8'), stored_hash.encode('utf-8'))
print(f"Wrong password verification: {wrong_result}")
