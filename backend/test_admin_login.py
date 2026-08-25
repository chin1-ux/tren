from dotenv import load_dotenv
from supabase import create_client
import os
from auth import verify_password, get_admin_user_by_email

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

sb = create_client(url, key)

# Test the new password
test_password = 'TrendropAdmin@2024!'
user = get_admin_user_by_email('chinmay.feb03@gmail.com')
if user:
    stored_hash = user.get('password_hash')
    print('Testing new password verification...')
    result = verify_password(test_password, stored_hash)
    print(f'Password verification for {test_password}: {result}')
    
    # Check if user is locked
    print(f'Failed attempts: {user.get("failed_login_attempts")}')
    print(f'Locked until: {user.get("locked_until")}')
    
    # Test with request data
    print('\nSimulating login request...')
    print(f'Email: chinmay.feb03@gmail.com')
    print(f'Password: {test_password}')
    print(f'Verification result: {result}')
else:
    print('User not found')