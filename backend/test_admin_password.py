from dotenv import load_dotenv
from supabase import create_client
import os
from auth import verify_password, get_admin_user_by_email

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

sb = create_client(url, key)

# Test password verification
test_passwords = ['admin123', 'password', 'admin', '123456', '']
user = get_admin_user_by_email('chinmay.feb03@gmail.com')
if user:
    stored_hash = user.get('password_hash')
    print('Testing password verification...')
    print('Stored hash:', stored_hash[:20] + '...')
    
    for test_pwd in test_passwords:
        result = verify_password(test_pwd, stored_hash)
        print(f'Password verification for "{test_pwd}": {result}')
else:
    print('User not found')