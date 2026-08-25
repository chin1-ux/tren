"""
Test Demo Allowlist
Tests that demo allowlist works correctly and prevents look-alike attacks
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

try:
    from plan_enforcement import PlanEnforcement
    from fastapi import HTTPException, status
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_demo_allowlist_empty():
    """Test that empty allowlist rejects all users"""
    print("=== Testing Empty Demo Allowlist ===")
    
    # Set empty allowlist
    os.environ["DEMO_ALLOWLIST"] = ""
    
    # Test with any user
    test_user = "anyone@example.com"
    result = PlanEnforcement.is_demo_allowlisted(test_user)
    
    if result == False:
        print(f"  [OK] Empty allowlist correctly rejects {test_user}")
        return True
    else:
        print(f"  [FAIL] Empty allowlist incorrectly allows {test_user}")
        return False

def test_demo_allowlist_exact_match():
    """Test that allowlist requires exact email match"""
    print("\n=== Testing Exact Email Match ===")
    
    # Set allowlist with specific email
    os.environ["DEMO_ALLOWLIST"] = "demo@trendrop.app"
    
    # Test with exact match
    exact_match = "demo@trendrop.app"
    result = PlanEnforcement.is_demo_allowlisted(exact_match)
    
    if result == True:
        print(f"  [OK] Exact match correctly allows {exact_match}")
    else:
        print(f"  [FAIL] Exact match incorrectly rejects {exact_match}")
        return False
    
    # Test with look-alike (should be rejected)
    look_alike = "demo1@trendrop.app"
    result = PlanEnforcement.is_demo_allowlisted(look_alike)
    
    if result == False:
        print(f"  [OK] Look-alike correctly rejected: {look_alike}")
        return True
    else:
        print(f"  [FAIL] Look-alike incorrectly allowed: {look_alike}")
        return False

def test_demo_allowlist_case_insensitive():
    """Test that allowlist is case-insensitive"""
    print("\n=== Testing Case Insensitive Matching ===")
    
    # Set allowlist with lowercase email
    os.environ["DEMO_ALLOWLIST"] = "demo@trendrop.app"
    
    # Test with uppercase
    uppercase = "DEMO@TRENDROP.APP"
    result = PlanEnforcement.is_demo_allowlisted(uppercase)
    
    if result == True:
        print(f"  [OK] Case-insensitive match correctly allows {uppercase}")
        return True
    else:
        print(f"  [FAIL] Case-insensitive match incorrectly rejects {uppercase}")
        return False

def test_demo_allowlist_multiple_emails():
    """Test that allowlist supports multiple emails"""
    print("\n=== Testing Multiple Emails in Allowlist ===")
    
    # Set allowlist with multiple emails
    os.environ["DEMO_ALLOWLIST"] = "demo@trendrop.app,test@example.com,admin@trendrop.app"
    
    # Test with each email
    test_emails = [
        "demo@trendrop.app",
        "test@example.com",
        "admin@trendrop.app"
    ]
    
    all_allowed = True
    for email in test_emails:
        result = PlanEnforcement.is_demo_allowlisted(email)
        if result == True:
            print(f"  [OK] {email} correctly allowed")
        else:
            print(f"  [FAIL] {email} incorrectly rejected")
            all_allowed = False
    
    # Test with email not in list
    not_in_list = "notallowed@example.com"
    result = PlanEnforcement.is_demo_allowlisted(not_in_list)
    if result == False:
        print(f"  [OK] {not_in_list} correctly rejected")
    else:
        print(f"  [FAIL] {not_in_list} incorrectly allowed")
        all_allowed = False
    
    return all_allowed

def test_old_hardcoded_bypasses_removed():
    """Test that old hardcoded bypasses no longer work"""
    print("\n=== Testing Old Hardcoded Bypasses Removed ===")
    
    # Set empty allowlist
    os.environ["DEMO_ALLOWLIST"] = ""
    
    # Test with old hardcoded emails
    old_bypasses = [
        "agency-demo@trendrop.app",
        "creator-demo@trendrop.app"
    ]
    
    all_rejected = True
    for email in old_bypasses:
        result = PlanEnforcement.is_demo_allowlisted(email)
        if result == False:
            print(f"  [OK] Old bypass {email} correctly rejected")
        else:
            print(f"  [FAIL] Old bypass {email} still works")
            all_rejected = False
    
    return all_rejected

if __name__ == "__main__":
    test_demo_allowlist_empty()
    test_demo_allowlist_exact_match()
    test_demo_allowlist_case_insensitive()
    test_demo_allowlist_multiple_emails()
    test_old_hardcoded_bypasses_removed()
    
    print("\n=== All Demo Allowlist Tests Complete ===")
    print("\nNote: To configure demo allowlist:")
    print("1. Set DEMO_ALLOWLIST environment variable (comma-separated emails)")
    print("2. Example: DEMO_ALLOWLIST=demo@trendrop.app,test@example.com")
    print("3. Look-alike emails will be rejected (exact match required)")
    print("4. Matching is case-insensitive")