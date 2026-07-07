import os
import requests
import json
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("backend/.env")

# 1. Check Apify API Token & Limits
apify_token = os.getenv("APIFY_API_TOKEN")
print("--- Checking Apify API ---")
if not apify_token:
    print("Apify API Token not found in .env")
else:
    try:
        url = f"https://api.apify.com/v2/users/me?token={apify_token}"
        res = requests.get(url)
        print(f"Apify User Profile Response Code: {res.status_code}")
        if res.status_code == 200:
            profile = res.json().get("data", {})
            print(f"Username: {profile.get('username')}")
            print(f"Email: {profile.get('email')}")
            # Get usage/limits if available
            limits_url = f"https://api.apify.com/v2/subscription?token={apify_token}"
            limits_res = requests.get(limits_url)
            if limits_res.status_code == 200:
                sub = limits_res.json().get("data", {})
                print(f"Subscription plan: {sub.get('plan', {}).get('name', 'N/A')}")
                print(f"Status: {sub.get('status')}")
                print(f"Usage this billing cycle: {sub.get('currentUsageUsd', 'N/A')} USD")
                print(f"Limit: {sub.get('monthlyUsageLimitUsd', 'N/A')} USD")
            else:
                print(f"Could not retrieve subscription/usage details: {limits_res.status_code}")
        else:
            print(f"Error fetching profile: {res.text}")
    except Exception as e:
        print(f"Apify check failed: {e}")

# 2. Check Supabase DB
print("\n--- Checking Supabase Database ---")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Supabase URL or Key not found in .env")
else:
    try:
        sb = create_client(url, key)
        
        # Check total trends
        trends_res = sb.table("trends").select("id", count="exact").limit(1).execute()
        total_trends = trends_res.count
        print(f"Total trends in DB: {total_trends}")
        
        # Check trends by status
        status_res = sb.table("trends").select("status").execute()
        statuses = [t["status"] for t in status_res.data]
        from collections import Counter
        print(f"Trends by status: {dict(Counter(statuses))}")
        
        # Check latest trend timestamp
        latest_res = sb.table("trends").select("created_at").order("created_at", desc=True).limit(5).execute()
        print("Latest 5 trends created_at timestamps:")
        for t in latest_res.data:
            print(f"  - {t.get('created_at')}")
            
        # Check logs/scans
        print("\nChecking scraper logs/history...")
        logs_res = sb.table("scraper_logs").select("*").order("timestamp", desc=True).limit(5).execute()
        print(f"Scraper logs found: {len(logs_res.data)}")
        for l in logs_res.data:
            print(f"  - Time: {l.get('timestamp')}, Status: {l.get('status')}, Platform: {l.get('platform')}, Details: {l.get('message') or l.get('error_message') or l.get('details')}")
            
    except Exception as e:
        print(f"Supabase check failed: {e}")
