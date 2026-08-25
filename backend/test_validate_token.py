#!/usr/bin/env python3
"""
Test admin token validation
"""

import urllib.request
import json

# First login to get token
login_url = "http://localhost:8000/api/admin/login"
login_data = {
    "email": "chinmay.feb03@gmail.com",
    "password": "nagaiah.rathna76"
}

print("=== Step 1: Login ===")
try:
    req = urllib.request.Request(
        login_url,
        data=json.dumps(login_data).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    
    with urllib.request.urlopen(req) as response:
        response_data = response.read()
        print(f"Status Code: {response.status}")
        print(f"Response: {response_data.decode('utf-8')}")
        
        login_result = json.loads(response_data.decode('utf-8'))
        token = login_result.get('access_token')
        
        if token:
            print(f"\n=== Step 2: Validate Token ===")
            validate_url = "http://localhost:8000/api/admin/validate-token"
            req = urllib.request.Request(
                validate_url,
                data=b'',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}'
                },
                method='POST'
            )
            
            with urllib.request.urlopen(req) as response:
                response_data = response.read()
                print(f"Status Code: {response.status}")
                print(f"Response: {response_data.decode('utf-8')}")
        else:
            print("No token received")
except urllib.error.HTTPError as e:
    print(f"\nHTTP Error: {e.code}")
    print(f"Response: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"\nError: {e}")
