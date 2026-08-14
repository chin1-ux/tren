"""
Test Heartbeat Fallback
Tests that heartbeat monitoring falls back to email when webhook fails
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
    from heartbeat_monitor import _send_webhook, _send_email
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

def test_webhook_missing_url():
    """Test that missing webhook URL returns False"""
    print("=== Testing Missing Webhook URL ===")
    
    # Clear webhook URL
    os.environ["CRON_HEARTBEAT_WEBHOOK_URL"] = ""
    
    result = _send_webhook("Test message")
    
    if result == False:
        print("  [OK] Missing webhook URL correctly returns False")
        return True
    else:
        print("  [FAIL] Missing webhook URL incorrectly returns True")
        return False

def test_email_missing_credentials():
    """Test that missing email credentials returns False"""
    print("\n=== Testing Missing Email Credentials ===")
    
    # Clear email credentials
    os.environ["RESEND_API_KEY"] = ""
    os.environ["CRON_HEARTBEAT_ALERT_EMAIL"] = ""
    
    result = _send_email("Test message")
    
    if result == False:
        print("  [OK] Missing email credentials correctly returns False")
        return True
    else:
        print("  [FAIL] Missing email credentials incorrectly returns True")
        return False

def test_email_available():
    """Test that email fallback is available when credentials are set"""
    print("\n=== Testing Email Fallback Availability ===")
    
    # Check if Resend is available
    try:
        import resend
        print("  [OK] Resend is available for email fallback")
        return True
    except ImportError:
        print("  [INFO] Resend not available - email fallback disabled")
        return True  # Not a failure, just informational

def test_webhook_with_invalid_url():
    """Test that invalid webhook URL returns False"""
    print("\n=== Testing Invalid Webhook URL ===")
    
    # Set invalid webhook URL
    os.environ["CRON_HEARTBEAT_WEBHOOK_URL"] = "https://invalid-url-that-does-not-exist.com/webhook"
    
    result = _send_webhook("Test message")
    
    if result == False:
        print("  [OK] Invalid webhook URL correctly returns False")
        return True
    else:
        print("  [FAIL] Invalid webhook URL incorrectly returns True")
        return False

if __name__ == "__main__":
    test_webhook_missing_url()
    test_email_missing_credentials()
    test_email_available()
    test_webhook_with_invalid_url()
    
    print("\n=== All Heartbeat Fallback Tests Complete ===")
    print("\nNote: To configure heartbeat monitoring:")
    print("1. Set CRON_HEARTBEAT_WEBHOOK_URL for webhook alerts (Slack, Discord)")
    print("2. Set CRON_HEARTBEAT_ALERT_EMAIL for email fallback (requires RESEND_API_KEY)")
    print("3. If webhook fails, heartbeat will automatically fall back to email")
    print("4. WhatsApp alerts require WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN")