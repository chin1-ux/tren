#!/usr/bin/env python3
"""
Test admin endpoints with JWT token
"""

import urllib.request
import json

# Login to get token
login_url = "http://localhost:8000/api/admin/login"
login_data = {
    "email": "chinmay.feb03@gmail.com",
    "password": "nagaiah.rathna76"
}

print("=== Login ===")
req = urllib.request.Request(
    login_url,
    data=json.dumps(login_data).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

with urllib.request.urlopen(req) as response:
    response_data = response.read()
    login_result = json.loads(response_data.decode('utf-8'))
    token = login_result.get('access_token')
    print(f"Token received: {token[:50]}...")

def make_request(url, method='GET', data=None):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode('utf-8') if data else None,
        headers=headers,
        method=method
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')

# Test admin endpoints
print("\n=== Test /api/admin/users ===")
status, response = make_request("http://localhost:8000/api/admin/users")
print(f"Status: {status}")
print(f"Response: {response[:200]}...")

print("\n=== Test /api/admin/plan-features ===")
status, response = make_request("http://localhost:8000/api/admin/plan-features")
print(f"Status: {status}")
print(f"Response: {response[:200]}...")

print("\n=== All tests completed ===")
