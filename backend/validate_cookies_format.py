#!/usr/bin/env python3
"""
Validate Instagram cookies JSON format
"""

import json
import os

def validate_cookies_format(json_file):
    """Validate cookies.json format"""
    print("="*60)
    print("COOKIE VALIDATION")
    print("="*60)
    
    # Handle relative paths
    if not os.path.isabs(json_file):
        json_file = os.path.join(os.path.dirname(__file__), json_file)
    
    # Check if file exists
    if not os.path.exists(json_file):
        print(f"[FAIL] {json_file} does not exist")
        return False
    
    print(f"[OK] {json_file} exists")
    
    # Try to parse JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[FAIL] Invalid JSON format: {e}")
        return False
    
    print(f"[OK] Valid JSON format")
    print(f"[OK] Found {len(cookies)} cookies")
    
    # Check required fields
    required_fields = ['name', 'value', 'domain', 'path']
    missing_fields = []
    
    for i, cookie in enumerate(cookies):
        for field in required_fields:
            if field not in cookie:
                missing_fields.append(f"Cookie {i}: missing '{field}'")
    
    if missing_fields:
        print(f"[FAIL] Missing required fields:")
        for field in missing_fields:
            print(f"  - {field}")
        return False
    
    print(f"[OK] All cookies have required fields")
    
    # Check for sessionid
    sessionid_present = any(c['name'] == 'sessionid' for c in cookies)
    if sessionid_present:
        print(f"[OK] sessionid cookie is present")
    else:
        print(f"[FAIL] sessionid cookie is missing (critical for authentication)")
        return False
    
    # Check for csrftoken
    csrftoken_present = any(c['name'] == 'csrftoken' for c in cookies)
    if csrftoken_present:
        print(f"[OK] csrftoken cookie is present")
    else:
        print(f"[WARN] csrftoken cookie is missing (recommended)")
    
    # Check for mid
    mid_present = any(c['name'] == 'mid' for c in cookies)
    if mid_present:
        print(f"[OK] mid cookie is present")
    else:
        print(f"[WARN] mid cookie is missing (recommended)")
    
    # Check for datr
    datr_present = any(c['name'] == 'datr' for c in cookies)
    if datr_present:
        print(f"[OK] datr cookie is present")
    else:
        print(f"[WARN] datr cookie is missing (recommended)")
    
    # Check for ig_did
    ig_did_present = any(c['name'] == 'ig_did' for c in cookies)
    if ig_did_present:
        print(f"[OK] ig_did cookie is present")
    else:
        print(f"[WARN] ig_did cookie is missing (recommended)")
    
    # Show sample cookie
    if cookies:
        print("\nSample cookie:")
        print(json.dumps(cookies[0], indent=2))
    
    print("\n" + "="*60)
    print("VALIDATION COMPLETE")
    print("="*60)
    
    return True

def main():
    json_file = "cookies.json"
    success = validate_cookies_format(json_file)
    
    if success:
        print("\n[SUCCESS] Cookies are valid and ready for use")
    else:
        print("\n[FAILED] Cookies have validation errors")
    
    return success

if __name__ == '__main__':
    main()