"""
User Management Backend
Handles user CRUD operations, plan changes, and anti-abuse
Combines device fingerprinting and usage tracking
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except Exception:
        pass

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

try:
    from device_fingerprint import DeviceFingerprint
except Exception as e:
    print(f"DeviceFingerprint import failed: {e}")
    DeviceFingerprint = None

try:
    from usage_tracker import UsageTracker
except Exception as e:
    print(f"UsageTracker import failed: {e}")
    UsageTracker = None


class UserManager:
    """
    User management with anti-abuse features
    """
    
    @staticmethod
    def create_user(email: str, niche: str = None, language_preference: str = None) -> Dict:
        """
        Create a new user with default free plan
        
        Args:
            email: User's email
            niche: User's content niche
            language_preference: User's language preference
        
        Returns:
            Created user data
        """
        if not supabase:
            return {}
        
        try:
            # Check if user already exists
            existing = supabase.table('users') \
                .select('*') \
                .eq('email', email) \
                .execute()
            
            if existing.data:
                return existing.data[0]
            
            # Create new user
            import random
            user_id = f"#{random.randint(1000, 9999)}"
            
            user_data = {
                'email': email,
                'user_id': user_id,  # Short ID for watermarking (e.g., "#1234")
                'niche': niche,
                'language_preference': language_preference,
                'plan': 'free',
                'email_verified': False,
                'status': 'active',
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            res = supabase.table('users') \
                .insert(user_data) \
                .execute()
            
            return res.data[0] if res.data else {}
            
        except Exception as e:
            print(f"Error creating user: {e}")
            return {}
    
    @staticmethod
    def get_user(email: str) -> Optional[Dict]:
        """
        Get user by email
        
        Args:
            email: User's email
        
        Returns:
            User data or None
        """
        if not supabase:
            return None
        
        try:
            res = supabase.table('users') \
                .select('*') \
                .eq('email', email) \
                .single() \
                .execute()
            
            return res.data if res.data else None
            
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    @staticmethod
    def get_all_users(limit: int = 100, offset: int = 0, search: str = None, plan_filter: str = None) -> List[Dict]:
        """
        Get all users with pagination and filtering
        
        Args:
            limit: Number of users to return
            offset: Offset for pagination
            search: Search by email
            plan_filter: Filter by plan
        
        Returns:
            List of user data
        """
        if not supabase:
            return []
        
        try:
            query = supabase.table('users') \
                .select('*') \
                .order('created_at', desc=True)
            
            if search:
                query = query.ilike('email', f'%{search}%')
            
            if plan_filter:
                query = query.eq('plan', plan_filter)
            
            query = query.range(offset, offset + limit - 1)
            
            res = query.execute()
            return res.data or []
            
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    @staticmethod
    def update_user_plan(email: str, new_plan: str, admin_email: str, reason: str = None) -> bool:
        """
        Update user's plan
        
        Args:
            email: User's email
            new_plan: New plan (free, pro, business)
            admin_email: Admin making the change
            reason: Reason for change
        
        Returns:
            Success status
        """
        if not supabase:
            return False
        
        try:
            # Update user plan
            supabase.table('users') \
                .update({
                    'plan': new_plan
                }) \
                .eq('email', email) \
                .execute()
            
            # Log admin action
            supabase.table('admin_audit_log') \
                .insert({
                    'admin_email': admin_email,
                    'action': 'plan_change',
                    'target_user_email': email,
                    'details': {
                        'old_plan': 'unknown',  # Could fetch current plan first
                        'new_plan': new_plan,
                        'reason': reason
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }) \
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error updating user plan: {e}")
            return False
    
    @staticmethod
    def lock_user_account(email: str, admin_email: str, reason: str = None) -> bool:
        """
        Lock user account due to suspicious activity
        
        Args:
            email: User's email
            admin_email: Admin making the change
            reason: Reason for locking
        
        Returns:
            Success status
        """
        if not supabase:
            return False
        
        try:
            supabase.table('users') \
                .update({
                    'status': 'locked'
                }) \
                .eq('email', email) \
                .execute()
            
            supabase.table('admin_audit_log') \
                .insert({
                    'admin_email': admin_email,
                    'action': 'account_lock',
                    'target_user_email': email,
                    'details': {'reason': reason},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }) \
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error locking user account: {e}")
            return False
    
    @staticmethod
    def unlock_user_account(email: str, admin_email: str, reason: str = None) -> bool:
        """
        Unlock user account
        
        Args:
            email: User's email
            admin_email: Admin making the change
            reason: Reason for unlocking
        
        Returns:
            Success status
        """
        if not supabase:
            return False
        
        try:
            supabase.table('users') \
                .update({
                    'status': 'active'
                }) \
                .eq('email', email) \
                .execute()
            
            supabase.table('admin_audit_log') \
                .insert({
                    'admin_email': admin_email,
                    'action': 'account_unlock',
                    'target_user_email': email,
                    'details': {'reason': reason},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }) \
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error unlocking user account: {e}")
            return False
    
    @staticmethod
    def get_user_devices(email: str) -> List[Dict]:
        """
        Get all devices for a user
        
        Args:
            email: User's email
        
        Returns:
            List of device records
        """
        if not DeviceFingerprint:
            return []
        
        return DeviceFingerprint.get_user_devices(email)
    
    @staticmethod
    def get_user_usage_stats(email: str, days: int = 30) -> Dict:
        """
        Get usage statistics for a user
        
        Args:
            email: User's email
            days: Number of days to look back
        
        Returns:
            Usage statistics
        """
        if not UsageTracker:
            return {}
        
        return UsageTracker.get_user_usage_stats(email, days)
    
    @staticmethod
    def get_suspicious_activity(days: int = 7) -> List[Dict]:
        """
        Get recent suspicious activity
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of suspicious activity records
        """
        if not supabase:
            return []
        
        try:
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            res = supabase.table('suspicious_activity') \
                .select('*') \
                .gte('created_at', time_threshold) \
                .eq('is_resolved', False) \
                .order('created_at', desc=True) \
                .execute()
            
            return res.data or []
            
        except Exception as e:
            print(f"Error getting suspicious activity: {e}")
            return []
    
    @staticmethod
    def resolve_suspicious_activity(activity_id: int, admin_email: str, resolution: str = None) -> bool:
        """
        Mark suspicious activity as resolved
        
        Args:
            activity_id: Activity ID
            admin_email: Admin resolving
            resolution: Resolution notes
        
        Returns:
            Success status
        """
        if not supabase:
            return False
        
        try:
            supabase.table('suspicious_activity') \
                .update({
                    'is_resolved': True,
                    'resolved_at': datetime.now(timezone.utc).isoformat()
                }) \
                .eq('id', activity_id) \
                .execute()
            
            if resolution:
                # Get current description
                current_res = supabase.table('suspicious_activity') \
                    .select('description') \
                    .eq('id', activity_id) \
                    .single() \
                    .execute()
                
                current_desc = current_res.data.get('description', '') if current_res.data else ''
                new_desc = f"{current_desc} (Resolved: {resolution})"
                
                supabase.table('suspicious_activity') \
                    .update({'description': new_desc}) \
                    .eq('id', activity_id) \
                    .execute()
            
            supabase.table('admin_audit_log') \
                .insert({
                    'admin_email': admin_email,
                    'action': 'resolve_suspicious_activity',
                    'details': {'activity_id': activity_id, 'resolution': resolution},
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }) \
                .execute()
            
            return True
            
        except Exception as e:
            print(f"Error resolving suspicious activity: {e}")
            return False
    
    @staticmethod
    def get_business_metrics(days: int = 30) -> Dict:
        """
        Get business metrics for admin dashboard
        
        Args:
            days: Number of days to look back
        
        Returns:
            Business metrics
        """
        if not supabase:
            return {}
        
        try:
            # Total users
            users_res = supabase.table('users') \
                .select('plan', 'created_at') \
                .execute()
            
            users = users_res.data or []
            
            # Plan distribution
            plan_counts = {'free': 0, 'pro': 0}
            new_users_7d = 0
            new_users_30d = []
            
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
            
            for user in users:
                plan = user.get('plan', 'free')
                plan_counts[plan] = plan_counts.get(plan, 0) + 1
                
                created_at = user.get('created_at', '')
                if created_at > week_ago:
                    new_users_7d += 1
                if created_at > month_ago:
                    new_users_30d.append(created_at)
            
            # Usage stats
            usage_stats = UsageTracker.get_all_users_usage(days) if UsageTracker else {}
            
            # Suspicious activity
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            suspicious_res = supabase.table('suspicious_activity') \
                .select('*') \
                .gte('created_at', time_threshold) \
                .execute()
            
            suspicious = suspicious_res.data or []
            unresolved_suspicious = [s for s in suspicious if not s.get('is_resolved', False)]
            
            return {
                'total_users': len(users),
                'plan_distribution': plan_counts,
                'new_users_7d': new_users_7d,
                'new_users_30d': len(new_users_30d),
                'total_usage': usage_stats.get('total_usage', 0),
                'plan_usage': usage_stats.get('plan_usage', {}),
                'feature_usage': usage_stats.get('feature_usage', {}),
                'suspicious_activity_count': len(suspicious),
                'unresolved_suspicious': len(unresolved_suspicious),
                'days_analyzed': days
            }
            
        except Exception as e:
            print(f"Error getting business metrics: {e}")
            return {}


# Test the user management system
if __name__ == "__main__":
    print("=== User Management System ===")
    
    # Test user creation
    user = UserManager.create_user("test@example.com", "fitness", "English")
    print(f"\nCreated user: {user.get('email')}")
    print(f"Plan: {user.get('plan')}")
    print(f"Status: {user.get('status')}")
    
    # Test plan update
    success = UserManager.update_user_plan("test@example.com", "pro", "admin@trendrop.ai", "Test upgrade")
    print(f"\nPlan update: {success}")
    
    # Test business metrics
    metrics = UserManager.get_business_metrics(30)
    print(f"\nBusiness metrics:")
    print(f"  Total users: {metrics.get('total_users')}")
    print(f"  Plan distribution: {metrics.get('plan_distribution')}")
    
    print("\n=== User Management System Working ===")