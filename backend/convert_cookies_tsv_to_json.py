#!/usr/bin/env python3
"""
Convert Instagram cookies from TSV format to JSON format

This script converts raw browser cookie exports (TSV format) to the JSON format
expected by the Instagram scraper.
"""

import json
import os
from datetime import datetime

def parse_expiration_timestamp(expiration_str):
    """Parse ISO 8601 timestamp to Unix timestamp"""
    try:
        # Handle special case for session cookies
        if expiration_str.lower() == 'session':
            return None  # Session cookies don't have expiration
        dt = datetime.fromisoformat(expiration_str.replace('Z', '+00:00'))
        return dt.timestamp()
    except Exception as e:
        print(f"Warning: Could not parse expiration '{expiration_str}': {e}")
        return None

def parse_boolean(value):
    """Parse boolean field (✓ → true, empty → false)"""
    if value == '✓':
        return True
    elif value == '' or value is None:
        return False
    else:
        # Try to parse as string
        return str(value).lower() in ['true', 'yes', '1']

def convert_tsv_to_json(tsv_file, json_file):
    """Convert TSV format cookies to JSON format"""
    cookies = []
    
    with open(tsv_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse TSV line (tab-separated)
            parts = line.split('\t')
            
            if len(parts) < 10:
                print(f"Warning: Skipping malformed line (only {len(parts)} fields): {line[:50]}")
                continue
            
            # Extract fields
            name = parts[0].strip()
            value = parts[1].strip()
            domain = parts[2].strip()
            path = parts[3].strip()
            expiration_str = parts[4].strip()
            size = parts[5].strip()
            httpOnly = parse_boolean(parts[6].strip())
            secure = parse_boolean(parts[7].strip())
            sameSite = parts[8].strip()
            category = parts[9].strip() if len(parts) > 9 else ''
            
            # Convert expiration to Unix timestamp
            expiration = parse_expiration_timestamp(expiration_str)
            
            # Create cookie object
            cookie = {
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
            }
            
            # Add optional fields
            if expiration is not None:
                cookie["expiration"] = expiration
            if httpOnly:
                cookie["httpOnly"] = httpOnly
            if secure:
                cookie["secure"] = secure
            if sameSite:
                cookie["sameSite"] = sameSite
            
            cookies.append(cookie)
    
    # Write JSON output
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(cookies, f, indent=2)
    
    print(f"Converted {len(cookies)} cookies from TSV to JSON")
    print(f"Output file: {json_file}")
    
    # Print sample
    if cookies:
        print("\nSample cookie:")
        print(json.dumps(cookies[0], indent=2))
    
    return cookies

def main():
    # Use the Instagram cookies file we created earlier
    tsv_file = "instagram_cookies.tsv"
    json_file = "cookies.json"
    
    # Create TSV file from your provided data
    tsv_data = """csrftoken	9f0ldh740ttDQQpDzn1dOi6TaKeuKJeB	.instagram.com	/	2027-09-11T07:42:37.019Z	41		✓		Medium
datr	EjQ4am5LH5Htsn4KtnED4Wnk	.instagram.com	/	2027-07-26T18:57:22.805Z	28	✓	✓	None			Medium
dpr	1.25	.instagram.com	/	2026-08-14T07:42:33.000Z	7		✓	None			Medium
ds_user_id	44450961500	.instagram.com	/	2026-11-05T07:42:37.019Z	21		✓	None			Medium
ig_did	7F31DD16-AF05-4A0D-BD65-FFAF73372DDB	.instagram.com	/	2027-06-21T18:57:22.057Z	42	✓✓	None			Medium
ig_nrcb	1	.instagram.com	/	2027-06-21T18:57:24.782Z	8	✓				Medium
mid	ajg0FAALAAHVsTBvhZHXGDuugQ6_	.instagram.com	/	2027-07-26T18:57:24.782Z	31	✓				Medium
ps_l	1	.instagram.com	/	2027-07-26T19:22:03.012Z	5	✓✓	Lax			Medium
ps_n	1	.instagram.com	/	2027-07-26T19:22:03.012Z	5	✓✓	None			Medium
rur	PRN%2C17841444445006370%2C1787300836%3A01ffc182ebbc33ee36c01459d262f9c22ab5d776d387b700867714f12a9bc82ed7ab56f7	.instagram.com	/	2027-08-07T07:43:37.000Z	114	✓	✓	Lax			Medium
sessionid	44450961500%3A9XFUNbSNWDUBlx%3A27%3AAYg__TWsItjmf29BYYDI4aFU3dKucTYlgsset6M4Pxs	.instagram.com	/	2027-08-07T07:42:37.020Z	88	✓✓				Medium
wd	982x730	.instagram.com	/	2026-08-14T07:43:36.000Z	9		✓	Lax			Medium"""
    
    with open(tsv_file, 'w', encoding='utf-8') as f:
        f.write(tsv_data)
    
    print(f"Created TSV file: {tsv_file}")
    
    # Convert to JSON
    cookies = convert_tsv_to_json(tsv_file, json_file)
    
    # Verify sessionid is present
    sessionid_present = any(c['name'] == 'sessionid' for c in cookies)
    if sessionid_present:
        print("\n[OK] sessionid cookie is present (required for authentication)")
    else:
        print("\n[FAIL] sessionid cookie is missing (authentication will fail)")
    
    print("\nConversion complete!")

if __name__ == '__main__':
    main()