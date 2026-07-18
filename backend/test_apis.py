import os
import os
import sys
import requests
from dotenv import load_dotenv

try:
    from llm import _collect_env_keys
except ImportError:
    from backend.llm import _collect_env_keys

# Ensure we read environment variables
load_dotenv()

def test_supabase():
    print("\n--- Testing Supabase Connection ---")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("FAIL: SUPABASE_URL or SUPABASE_KEY missing.")
        return False
    try:
        from supabase import create_client
        supabase = create_client(url, key)
        # Quick query
        res = supabase.table("trends").select("id").limit(1).execute()
        print(f"SUCCESS: Supabase connected. Found trends: {len(res.data) if res.data else 0}")
        return True
    except Exception as e:
        print(f"FAIL: Supabase query failed: {e}")
        return False

def test_groq():
    print("\n--- Testing Groq API Keys ---")
    keys = _collect_env_keys(("GROQ_API_KEY", "LLM_API_KEY"))
    if not keys:
        print("FAIL: No Groq/LLM keys configured.")
        return False

    print(f"Found {len(keys)} Groq key(s) in configuration.")
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": "You are a health check assistant."},
            {"role": "user", "content": "Hello. Answer in one word: OK"}
        ],
        "max_tokens": 10
    }
    
    all_ok = True
    for idx, key in enumerate(keys, start=1):
        print(f"Testing Groq key #{idx}...")
        try:
            res = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
                json=payload,
                timeout=10
            )
            res.raise_for_status()
            text = res.json()["choices"][0]["message"]["content"].strip()
            print(f"  SUCCESS: Response: {text}")
        except Exception as e:
            print(f"  FAIL: Key #{idx} failed: {e}")
            all_ok = False
            
    return all_ok

def test_gemini():
    print("\n--- Testing Gemini API Keys ---")
    keys = _collect_env_keys(("GEMINI_API_KEY",))
    if not keys:
        print("FAIL: No Gemini keys configured.")
        return False

    print(f"Found {len(keys)} Gemini key(s) in configuration.")
    payload = {
        "contents": [{"parts": [{"text": "Hello. Answer in one word: OK"}]}],
        "systemInstruction": {"parts": [{"text": "You are a health check assistant."}]},
        "generationConfig": {"responseMimeType": "application/json"}
    }
    all_ok = True
    for idx, key in enumerate(keys, start=1):
        print(f"Testing Gemini key #{idx}...")
        try:
            res = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                params={"key": key},
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            res.raise_for_status()
            print("  SUCCESS: Gemini request completed.")
        except Exception as e:
            print(f"  FAIL: Gemini key #{idx} failed: {e}")
            all_ok = False
    return all_ok

def test_apify():
    print("\n--- Testing Apify API Tokens ---")
    raw_tokens = os.getenv("APIFY_API_TOKEN")
    if not raw_tokens:
        print("FAIL: APIFY_API_TOKEN not configured.")
        return False
    
    tokens = [t.strip() for t in raw_tokens.split(",") if t.strip()]
    print(f"Found {len(tokens)} Apify token(s) in configuration.")
    
    all_ok = True
    for idx, token in enumerate(tokens, start=1):
        masked = token[:10] + "..." + token[-4:] if len(token) > 14 else "invalid"
        print(f"Testing token #{idx} ({masked})...")
        try:
            # Query Apify API to fetch user info or list actor runs
            res = requests.get(
                "https://api.apify.com/v2/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            if res.status_code == 200:
                user_data = res.json().get("data", {})
                username = user_data.get("username", "Unknown")
                print(f"  SUCCESS: Token #{idx} is valid. User: {username}")
            elif res.status_code == 401:
                print(f"  FAIL: Token #{idx} is unauthorized (invalid key).")
                all_ok = False
            elif res.status_code == 403:
                # Could be forbidden/rate limit
                print(f"  FAIL: Token #{idx} forbidden: {res.text}")
                all_ok = False
            else:
                res.raise_for_status()
        except Exception as e:
            print(f"  FAIL: Token #{idx} request error: {e}")
            all_ok = False
            
    return all_ok

if __name__ == "__main__":
    sb = test_supabase()
    gq = test_groq()
    gm = test_gemini()
    ap = test_apify()
    
    print("\n--- Diagnostic Summary ---")
    print(f"Supabase Status: {'PASS' if sb else 'FAIL'}")
    print(f"Groq API Status: {'PASS' if gq else 'SOME/ALL KEYS FAILED'}")
    print(f"Gemini API Status: {'PASS' if gm else 'SOME/ALL KEYS FAILED'}")
    print(f"Apify API Status: {'PASS' if ap else 'SOME/ALL TOKENS FAILED'}")
    
    if not (sb and gq and gm and ap):
        sys.exit(1)
    sys.exit(0)
