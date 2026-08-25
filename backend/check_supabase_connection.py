#!/usr/bin/env python3
"""
Check Supabase connection and diagnose issues
"""

import os
import sys
import io
from dotenv import load_dotenv
from supabase import create_client
import time

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load .env
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)
load_dotenv()  # Fallback

def check_supabase_connection():
    """Check Supabase connection and diagnose issues"""
    
    print("=== Supabase Connection Diagnostic ===\n")
    
    # Check credentials
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY')
    service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    db_url = os.getenv('SUPABASE_DB_URL')
    
    print("Credentials Status:")
    print(f"  SUPABASE_URL: {'✅ Found' if url else '❌ Missing'}")
    print(f"  SUPABASE_KEY: {'✅ Found' if key else '❌ Missing'}")
    print(f"  SUPABASE_SERVICE_ROLE_KEY: {'✅ Found' if service_role_key else '❌ Missing'}")
    print(f"  SUPABASE_DB_URL: {'✅ Found' if db_url else '❌ Missing'}")
    
    if url:
        print(f"  URL: {url[:30]}... (truncated)")
    
    # Test REST API connection
    print("\nTesting Supabase REST API connection...")
    
    try:
        # Try with regular key first
        api_key = service_role_key or key
        if not api_key:
            print("❌ No API key available for testing")
            return False
            
        client = create_client(url, api_key)
        
        start_time = time.time()
        result = client.table('reels').select('id', count='exact').limit(1).execute()
        elapsed = time.time() - start_time
        
        print(f"✅ REST API connection successful")
        print(f"   Response time: {elapsed:.2f} seconds")
        print(f"   Reels count: {result.count if hasattr(result, 'count') else 'unknown'}")
        
    except Exception as e:
        print(f"❌ REST API connection failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        
        # Check for specific error patterns
        error_str = str(e).lower()
        if 'timeout' in error_str or 'deadline' in error_str:
            print("   🔍 Diagnosis: Connection timeout - possible network or Supabase issue")
        elif 'rate limit' in error_str or '429' in error_str:
            print("   🔍 Diagnosis: Rate limit exceeded - possible free tier limit")
        elif 'auth' in error_str or 'unauthorized' in error_str:
            print("   🔍 Diagnosis: Authentication issue - check API keys")
        
        return False
    
    # Test database URL connection if available
    if db_url:
        print("\nTesting direct PostgreSQL connection...")
        
        try:
            import psycopg2
            from psycopg2 import OperationalError
            
            start_time = time.time()
            conn = psycopg2.connect(db_url, connect_timeout=10)
            elapsed = time.time() - start_time
            
            print(f"✅ Direct PostgreSQL connection successful")
            print(f"   Connection time: {elapsed:.2f} seconds")
            
            # Check connection info
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"   PostgreSQL version: {version[0][:50]}...")
            
            cursor.close()
            conn.close()
            
        except ImportError:
            print("⚠️  psycopg2 not available - skipping direct connection test")
        except OperationalError as e:
            print(f"❌ Direct PostgreSQL connection failed: {e}")
            
            error_str = str(e).lower()
            if 'timeout' in error_str or 'deadline' in error_str:
                print("   🔍 Diagnosis: Connection timeout - possible Supabase free tier limit")
            elif 'connection refused' in error_str:
                print("   🔍 Diagnosis: Connection refused - database may be down")
            elif 'authentication' in error_str:
                print("   🔍 Diagnosis: Authentication failed - check DB credentials")
                
        except Exception as e:
            print(f"❌ Direct connection test failed: {e}")
    
    # Check Supabase project status (if possible)
    print("\n=== Recommendations ===")
    
    print("If you're seeing connection timeouts:")
    print("1. Check Supabase dashboard for project status")
    print("2. Verify you're not on Supabase free tier limits:")
    print("   - Database size: 500MB limit")
    print("   - Bandwidth: 2GB/month limit")
    print("   - API requests: 50,000/month limit")
    print("3. Check if your project is paused or suspended")
    print("4. Try accessing Supabase dashboard directly")
    print("5. Consider upgrading to Pro tier if limits are hit")
    
    print("\nQuick fix attempts:")
    print("1. Restart your local network connection")
    print("2. Check if VPN/firewall is blocking connections")
    print("3. Try a different network (if on mobile network)")
    print("4. Check Supabase status page: https://status.supabase.com")
    
    return True

if __name__ == '__main__':
    check_supabase_connection()
