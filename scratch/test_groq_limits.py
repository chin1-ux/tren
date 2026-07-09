import os, requests
from dotenv import load_dotenv

load_dotenv("backend/.env")
raw_keys = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
if not raw_keys:
    print("No Groq API keys found.")
    exit(1)

keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
print(f"Found {len(keys)} key(s). Testing first key...")
key = keys[0]

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {key}"
}
payload = {
    "model": os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "max_tokens": 10
}

try:
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=10
    )
    print(f"Status Code: {resp.status_code}")
    print("Response Headers:")
    for k, v in resp.headers.items():
        if "ratelimit" in k.lower():
            print(f"  {k}: {v}")
except Exception as e:
    print(f"Error testing key: {e}")
