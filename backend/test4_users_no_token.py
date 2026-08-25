#!/usr/bin/env python3
import urllib.request

users_url = "http://localhost:8000/api/admin/users"
req = urllib.request.Request(users_url)
try:
    with urllib.request.urlopen(req) as response:
        print(f"Status Code: {response.status}")
        print(f"Response: {response.read().decode('utf-8')}")
except urllib.error.HTTPError as e:
    print(f"Status Code: {e.code}")
    print(f"Response: {e.read().decode('utf-8')}")
