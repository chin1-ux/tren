#!/usr/bin/env python3
"""
Encode cookies.json to base64 for GitHub Secrets
"""

import base64
import json

def encode_cookies_to_base64(json_file):
    """Read cookies.json and encode to base64"""
    with open(json_file, 'r', encoding='utf-8') as f:
        cookies_json = f.read()
    
    # Encode to base64
    base64_bytes = base64.b64encode(cookies_json.encode('utf-8'))
    base64_str = base64_bytes.decode('utf-8')
    
    print(f"Encoded cookies.json to base64")
    print(f"Base64 string length: {len(base64_str)} characters")
    print(f"\nBase64 string (first 100 chars):")
    print(base64_str[:100])
    print("...")
    print(f"\nBase64 string (last 100 chars):")
    print("...")
    print(base64_str[-100:])
    
    return base64_str

def main():
    json_file = "cookies.json"
    
    # Check if file exists
    try:
        with open(json_file, 'r') as f:
            cookies = json.load(f)
        print(f"Found {len(cookies)} cookies in {json_file}")
    except FileNotFoundError:
        print(f"Error: {json_file} not found")
        return
    
    # Encode to base64
    base64_str = encode_cookies_to_base64(json_file)
    
    # Save to file for reference
    with open("cookies_base64.txt", 'w') as f:
        f.write(base64_str)
    
    print(f"\nBase64 string saved to: cookies_base64.txt")
    print("\nInstructions:")
    print("1. Copy the base64 string from cookies_base64.txt")
    print("2. Go to: https://github.com/ch1n-may/trendrop/settings/secrets/actions")
    print("3. Add secret: INSTAGRAM_COOKIES_B64")
    print("4. Paste the base64 string")
    print("5. Click 'Add secret'")

if __name__ == '__main__':
    main()