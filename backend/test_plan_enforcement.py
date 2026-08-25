"""
Test script to verify plan enforcement is working correctly
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")

def test_endpoint_with_bearer_token(endpoint, token, expected_status):
    """Test an endpoint with a bearer token"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{API_BASE}{endpoint}", headers=headers)
        print(f"Testing {endpoint}")
        print(f"  Expected status: {expected_status}")
        print(f"  Actual status: {response.status_code}")
        print(f"  Response: {response.text[:200]}")
        print()
        return response.status_code == expected_status
    except Exception as e:
        print(f"  Error: {e}")
        print()
        return False

def main():
    print("=== PLAN ENFORCEMENT VERIFICATION TESTS ===\n")
    
    # Test with free tier user (should be blocked on paid features)
    free_token = "free-test-token"  # Replace with actual free user token
    pro_token = "pro-test-token"    # Replace with actual pro user token
    
    # Test emerging trends (paid feature)
    print("1. Testing /api/trends/emerging (early_detection - Pro/Agency only)")
    test_endpoint_with_bearer_token("/api/trends/emerging", free_token, 403)
    test_endpoint_with_bearer_token("/api/trends/emerging", pro_token, 200)
    
    # Test audio scores (paid feature)
    print("2. Testing /api/trends/audio-scores (advanced_analytics - Pro/Agency only)")
    test_endpoint_with_bearer_token("/api/trends/audio-scores", free_token, 403)
    test_endpoint_with_bearer_token("/api/trends/audio-scores", pro_token, 200)
    
    # Test all-active trends (paid feature)
    print("3. Testing /api/trends/all-active (unlimited_trends - Pro/Agency only)")
    test_endpoint_with_bearer_token("/api/trends/all-active", free_token, 403)
    test_endpoint_with_bearer_token("/api/trends/all-active", pro_token, 200)
    
    # Test basic trends (should work for free tier)
    print("4. Testing /api/trends (basic_trends - Free tier)")
    test_endpoint_with_bearer_token("/api/trends", free_token, 200)
    test_endpoint_with_bearer_token("/api/trends", pro_token, 200)
    
    print("=== TESTS COMPLETE ===")

if __name__ == "__main__":
    main()
