#!/usr/bin/env python3
import urllib.request
import json
import time

url = "http://localhost:8000/api/admin/login"
data = {"email": "chinmay.feb03@gmail.com", "password": "wrongpassword"}

print("Testing 6 failed login attempts...")
for i in range(6):
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Attempt {i+1}: Status {response.status}")
            print(f"Response: {response.read().decode('utf-8')}")
    except urllib.error.HTTPError as e:
        print(f"Attempt {i+1}: Status {e.code}")
        print(f"Response: {e.read().decode('utf-8')}")
    time.sleep(0.5)
