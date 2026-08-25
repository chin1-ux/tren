#!/usr/bin/env python3
import urllib.request
import json

url = "http://localhost:8000/api/admin/login"
data = {"email": "chinmay.feb03@gmail.com", "password": "nagaiah.rathna76"}

req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
with urllib.request.urlopen(req) as response:
    print(f"Status Code: {response.status}")
    print(f"Response: {response.read().decode('utf-8')}")
