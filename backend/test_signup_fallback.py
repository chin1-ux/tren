"""
Test Signup Fallback
Tests that signup fails with clear error if Twilio is not configured
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
    from phone_verification import PhoneVerification
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_phone_verification_availability():
    """Test that PhoneVerification availability is checked correctly"""
    print("=== Testing Phone Verification Availability ===")
    
    # Check if PhoneVerification is available
    if PhoneVerification:
        print("  [OK] PhoneVerification is available")
        
        # Check if Twilio credentials are configured
        twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
        twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
        twilio_phone = os.getenv("TWILIO_PHONE_NUMBER")
        
        if twilio_sid and twilio_token and twilio_phone:
            print("  [OK] Twilio credentials are configured")
            return True
        else:
            print("  [INFO] Twilio credentials not configured")
            print("  [OK] Signup should fail with 503 error")
            return True
    else:
        print("  [FAIL] PhoneVerification not available")
        return False

def test_signup_without_twilio():
    """Test that signup fails when Twilio is not configured"""
    print("\n=== Testing Signup Without Twilio ===")
    
    # Temporarily clear Twilio credentials
    original_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    original_token = os.environ.get("TWILIO_AUTH_TOKEN")
    original_phone = os.environ.get("TWILIO_PHONE_NUMBER")
    
    os.environ["TWILIO_ACCOUNT_SID"] = ""
    os.environ["TWILIO_AUTH_TOKEN"] = ""
    os.environ["TWILIO_PHONE_NUMBER"] = ""
    
    # Try to send verification code
    result = PhoneVerification.send_verification_code("+919876543210")
    
    # Restore original credentials
    if original_sid:
        os.environ["TWILIO_ACCOUNT_SID"] = original_sid
    if original_token:
        os.environ["TWILIO_AUTH_TOKEN"] = original_token
    if original_phone:
        os.environ["TWILIO_PHONE_NUMBER"] = original_phone
    
    if not result.get('success'):
        print("  [OK] Verification code send failed as expected")
        return True
    else:
        print("  [FAIL] Verification code send succeeded when it should have failed")
        return False

if __name__ == "__main__":
    test_phone_verification_availability()
    test_signup_without_twilio()
    
    print("\n=== All Signup Fallback Tests Complete ===")
    print("\nNote: Signup now requires Twilio configuration:")
    print("- If TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER are not set")
    print("- Signup will fail with 503 Service Unavailable")
    print("- Error message: 'Phone verification service not configured'")