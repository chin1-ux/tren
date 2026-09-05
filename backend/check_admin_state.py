from dotenv import load_dotenv
from supabase import create_client
import os

load_dotenv()
url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

sb = create_client(url, key)

# Check current admin user state
result = sb.table('admin_users').select('*').eq('email', 'chinmay.feb03@gmail.com').execute()
if result.data:
    user = result.data[0]
    print('Current admin user state:')
    print('Email:', user.get('email'))
    print('Password hash:', user.get('password_hash')[:30] + '...')
    print('Role:', user.get('role'))
    print('Failed attempts:', user.get('failed_login_attempts'))
    print('Locked until:', user.get('locked_until'))
    print('Last login:', user.get('last_login'))
else:
    print('User not found')