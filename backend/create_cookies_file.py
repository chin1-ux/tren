import os
import base64
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base64 string from .env
base64_str = os.getenv("INSTAGRAM_COOKIES_B64", "")

if base64_str:
    # Decode base64 to bytes
    cookies_bytes = base64.b64decode(base64_str)
    
    # Convert bytes to string
    cookies_json = cookies_bytes.decode('utf-8')
    
    # Parse JSON
    cookies_data = json.loads(cookies_json)
    
    # Write to cookies.json
    cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.json")
    with open(cookies_path, 'w') as f:
        json.dump(cookies_data, f, indent=2)
    
    print(f"Created cookies.json at {cookies_path}")
    print(f"Total cookies: {len(cookies_data)}")
else:
    print("ERROR: INSTAGRAM_COOKIES_B64 not found in environment")