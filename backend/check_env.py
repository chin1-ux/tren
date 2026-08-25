#!/usr/bin/env python3
"""
Check if Spotify credentials are loaded from .env
"""

import os
import sys
import io
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Load .env from the project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

print(f"Loading .env from: {env_path}")
print(f".env file exists: {os.path.exists(env_path)}")

client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

print(f"\nClient ID: {'Found' if client_id else 'Not found'}")
print(f"Client Secret: {'Found' if client_secret else 'Not found'}")

if client_id:
    print(f"Client ID value: {client_id}")
if client_secret:
    print(f"Client Secret value: {client_secret[:10]}... (truncated)")
