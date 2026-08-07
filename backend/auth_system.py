#!/usr/bin/env python3
"""
Real authentication system
Implements: login, signup, session management, auth verification
"""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# Initialize Supabase client (lazy initialization for GitHub Actions compatibility)
sb = None

def get_supabase_client():
    """Get Supabase client with lazy initialization"""
    global sb
    if sb is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        if not url or not key:
            raise RuntimeError('Supabase credentials not set in environment')
        sb = create_client(url, key)
    return sb

# Session duration (in hours)
SESSION_DURATION_HOURS = 24

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

def create_user(email: str, password: str, niche: str = "all", language: str = "en") -> dict:
    """
    Create a new user with hashed password
    """
    client = get_supabase_client()
    # Check if user already exists
    existing = client.table('users').select('*').eq('email', email).execute()
    if existing.data:
        return {'success': False, 'error': 'User already exists'}

    # Hash password
    password_hash = hash_password(password)

    # Create user
    user_data = {
        'email': email,
        'password_hash': password_hash,
        'niche': niche,
        'language_preference': language,
        'created_at': datetime.now().isoformat()
    }

    result = client.table('users').insert(user_data).execute()

    if result.data:
        return {'success': True, 'user': result.data[0]}
    else:
        return {'success': False, 'error': 'Failed to create user'}

def login_user(email: str, password: str) -> dict:
    """
    Login user with email and password
    Returns session token if successful
    """
    client = get_supabase_client()
    # Get user by email
    result = client.table('users').select('*').eq('email', email).execute()

    if not result.data:
        return {'success': False, 'error': 'User not found'}

    user = result.data[0]
    password_hash = hash_password(password)

    # Verify password
    if user.get('password_hash') != password_hash:
        return {'success': False, 'error': 'Invalid password'}

    # Generate session token
    session_token = generate_session_token()
    expires_at = datetime.now() + timedelta(hours=SESSION_DURATION_HOURS)

    # Store session
    session_data = {
        'user_email': email,
        'session_token': session_token,
        'expires_at': expires_at.isoformat(),
        'created_at': datetime.now().isoformat()
    }

    client.table('user_sessions').insert(session_data).execute()

    return {
        'success': True,
        'session_token': session_token,
        'expires_at': expires_at.isoformat(),
        'user': {
            'email': user['email'],
            'niche': user.get('niche', 'all'),
            'language': user.get('language_preference', 'en')
        }
    }

def verify_session(session_token: str) -> dict:
    """
    Verify session token and return user info if valid
    """
    client = get_supabase_client()
    # Get session
    result = client.table('user_sessions').select('*').eq('session_token', session_token).execute()

    if not result.data:
        return {'valid': False, 'error': 'Session not found'}

    session = result.data[0]
    expires_at = datetime.fromisoformat(session['expires_at'])

    # Check if session is expired
    if datetime.now() > expires_at:
        # Delete expired session
        client.table('user_sessions').delete().eq('session_token', session_token).execute()
        return {'valid': False, 'error': 'Session expired'}

    # Get user info
    user_result = client.table('users').select('*').eq('email', session['user_email']).execute()

    if not user_result.data:
        return {'valid': False, 'error': 'User not found'}

    user = user_result.data[0]

    return {
        'valid': True,
        'user': {
            'email': user['email'],
            'niche': user.get('niche', 'all'),
            'language': user.get('language_preference', 'en')
        }
    }

def logout_user(session_token: str) -> dict:
    """
    Logout user by deleting session
    """
    client = get_supabase_client()
    result = client.table('user_sessions').delete().eq('session_token', session_token).execute()

    return {'success': True}

def cleanup_expired_sessions():
    """
    Clean up expired sessions
    """
    client = get_supabase_client()
    client.table('user_sessions').delete().lt('expires_at', datetime.now().isoformat()).execute()
    return {'success': True}

# Initialize auth tables
def init_auth_tables():
    """
    Create required tables for authentication
    """
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv()
    db_url = os.getenv('SUPABASE_DB_URL')

    if not db_url:
        raise RuntimeError('SUPABASE_DB_URL not set')

    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cursor = conn.cursor()

    # Add password_hash column to users table
    print("Adding password_hash column to users table...")
    try:
        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS password_hash TEXT;
        """)
    except Exception as e:
        print(f"Password hash column already exists or error: {e}")

    # Create user_sessions table
    print("Creating user_sessions table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            user_email TEXT NOT NULL,
            session_token TEXT NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
    """)

    # Create index on session_token
    print("Creating index on session_token...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
    """)

    # Create index on user_email
    print("Creating index on user_email...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_sessions_email ON user_sessions(user_email);
    """)

    cursor.close()
    conn.close()

    print("[PASS] Auth tables initialized")

if __name__ == "__main__":
    try:
        # Initialize tables
        init_auth_tables()

        # Test auth system (only if credentials are available)
        print("\nTesting auth system...")

        # Create test user
        print("\n1. Creating test user...")
        result = create_user("test@example.com", "password123", "dance", "hi")
        print(f"   Result: {result}")

        # Login user
        print("\n2. Logging in user...")
        result = login_user("test@example.com", "password123")
        print(f"   Result: {result}")
    except RuntimeError as e:
        if "Supabase credentials not set" in str(e):
            print("[INFO] Supabase credentials not set - skipping auth system test")
            print("[INFO] Auth system initialization requires SUPABASE_URL and SUPABASE_KEY")
        else:
            raise

    if result.get('success'):
        session_token = result['session_token']

        # Verify session
        print("\n3. Verifying session...")
        result = verify_session(session_token)
        print(f"   Result: {result}")

        # Logout user
        print("\n4. Logging out user...")
        result = logout_user(session_token)
        print(f"   Result: {result}")
