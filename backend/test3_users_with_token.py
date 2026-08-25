#!/usr/bin/env python3
import urllib.request
import json

# Get token from login
login_url = "http://localhost:8000/api/admin/login"
login_data = {"email": "chinmay.feb03@gmail.com", "password": "nagaiah.rathna76"}

req = urllib.request.Request(login_url, data=json.dumps(login_data).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as response:
    response_data = response.read()
    login_result = json.loads(response_data.decode('utf-8'))
    token = login_result.get('access_token')

# Test /api/admin/users with token
users_url = "http://localhost:8000/api/admin/users"
req = urllib.request.Request(users_url, headers={'Authorization': f'Bearer {token}'})
with urllib.request.urlopen(req) as response:
    print(f"Status Code: {response.status}")
    print(f"Response: {response.read().decode('utf-8')}")
