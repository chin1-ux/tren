"""
Usage Tracking System
Enforces plan limits and tracks feature usage for analytics
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
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


class UsageTracker:
    """
    Usage tracking and plan limit enforcement
    """
    
    @staticmethod
    def get_user_plan(user_email: str) -> str:
        """
        Get the user's current plan
        
        Args:
            user_email: User's email
        
        Returns:
            Plan name (free, pro, business)
        """
        if not supabase:
            return 'free'
        
        try:
            res = supabase.table('users') \
                .select('plan') \
                .eq('email', user_email) \
                .single() \
                .execute()
            
            if res.data:
                return res.data.get('plan', 'free')
            return 'free'
            
        except Exception as e:
            print(f"Error getting user plan: {e}")
            return 'free'
    
    @staticmethod
    def get_plan_limits(plan_name: str) -> Dict:
        """
        Get usage limits for a plan
        
        Args:
            plan_name: Plan name
        
        Returns:
            Dict with api_limit_per_day, trend_views_per_day, features
        """
        if not supabase:
            return {
                'api_limit_per_day': 5,
                'trend_views_per_day': 10,
                'features': ['basic_trends']
            }
        
        try:
            res = supabase.table('plan_features') \
                .select('*') \
                .eq('plan_name', plan_name) \
                .single() \
                .execute()
            
            if res.data:
                return {
                    'api_limit_per_day': res.data.get('api_limit_per_day', 5),
                    'trend_views_per_day': res.data.get('trend_views_per_day', 10),
                    'features': res.data.get('features', [])
                }
            
            # Default limits if plan not found
            return {
                'api_limit_per_day': 5,
                'trend_views_per_day': 10,
                'features': ['basic_trends']
            }
            
        except Exception as e:
            print(f"Error getting plan limits: {e}")
            return {
                'api_limit_per_day': 5,
                'trend_views_per_day': 10,
                'features': ['basic_trends']
            }
    
    @staticmethod
    def check_usage_limit(user_email: str, feature: str) -> Tuple[bool, str]:
        """
        Check if user has exceeded their usage limit for a feature
        
        Args:
            user_email: User's email
            feature: Feature being used (e.g., 'api_call', 'trend_view', 'ai_generation')
        
        Returns:
            (is_allowed, reason)
        """
        if not supabase:
            return True, ""
        
        try:
            plan = UsageTracker.get_user_plan(user_email)
            limits = UsageTracker.get_plan_limits(plan)
            
            # Check if feature is in plan
            if feature not in limits['features'] and feature != 'api_call':
                return False, f"'{feature}' not available in {plan} plan"
            
            # Get today's usage
            today = datetime.now(timezone.utc).date().isoformat()
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            
            res = supabase.table('usage_logs') \
                .select('*') \
                .eq('user_email', user_email) \
                .gte('timestamp', time_threshold) \
                .execute()
            
            usage_logs = res.data or []
            
            # Count feature usage
            feature_count = sum(1 for log in usage_logs if log['feature_used'] == feature)
            
            # Check limits
            if feature == 'api_call':
                limit = limits['api_limit_per_day']
                if limit != -1 and feature_count >= limit:
                    return False, f"API limit reached: {limit} calls/day"
            
            elif feature == 'trend_view':
                limit = limits['trend_views_per_day']
                if limit != -1 and feature_count >= limit:
                    return False, f"Trend view limit reached: {limit} views/day"
            
            # No limit or not exceeded
            return True, ""
            
        except Exception as e:
            print(f"Error checking usage limit: {e}")
            return True, ""  # Allow on error
    
    @staticmethod
    def log_usage(user_email: str, feature: str, metadata: Optional[Dict] = None):
        """
        Log feature usage for analytics
        
        Args:
            user_email: User's email
            feature: Feature being used
            metadata: Additional metadata about the usage
        """
        if not supabase:
            return
        
        try:
            plan = UsageTracker.get_user_plan(user_email)
            
            supabase.table('usage_logs') \
                .insert({
                    'user_email': user_email,
                    'feature_used': feature,
                    'plan_at_time': plan,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'metadata': metadata or {}
                }) \
                .execute()
            
            # Update user's usage count
            user_res = supabase.table('users') \
                .select('usage_count') \
                .eq('email', user_email) \
                .single() \
                .execute()
            
            current_count = user_res.data.get('usage_count', 0) if user_res.data else 0
            
            supabase.table('users') \
                .update({
                    'usage_count': current_count + 1,
                    'last_active': datetime.now(timezone.utc).isoformat()
                }) \
                .eq('email', user_email) \
                .execute()
            
        except Exception as e:
            print(f"Error logging usage: {e}")
    
    @staticmethod
    def get_user_usage_stats(user_email: str, days: int = 30) -> Dict:
        """
        Get usage statistics for a user
        
        Args:
            user_email: User's email
            days: Number of days to look back
        
        Returns:
            Dict with usage statistics
        """
        if not supabase:
            return {}
        
        try:
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            res = supabase.table('usage_logs') \
                .select('*') \
                .eq('user_email', user_email) \
                .gte('timestamp', time_threshold) \
                .execute()
            
            logs = res.data or []
            
            # Calculate stats
            feature_usage = {}
            daily_usage = {}
            
            for log in logs:
                feature = log['feature_used']
                date = log['timestamp'][:10]  # YYYY-MM-DD
                
                feature_usage[feature] = feature_usage.get(feature, 0) + 1
                daily_usage[date] = daily_usage.get(date, 0) + 1
            
            return {
                'total_usage': len(logs),
                'feature_usage': feature_usage,
                'daily_usage': daily_usage,
                'days_analyzed': days
            }
            
        except Exception as e:
            print(f"Error getting usage stats: {e}")
            return {}
    
    @staticmethod
    def get_all_users_usage(days: int = 30) -> Dict:
        """
        Get usage statistics for all users (admin only)
        
        Args:
            days: Number of days to look back
        
        Returns:
            Dict with aggregated usage statistics
        """
        if not supabase:
            return {}
        
        try:
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            res = supabase.table('usage_logs') \
                .select('*') \
                .gte('timestamp', time_threshold) \
                .execute()
            
            logs = res.data or []
            
            # Calculate stats
            plan_usage = {}
            feature_usage = {}
            user_usage = {}
            
            for log in logs:
                plan = log.get('plan_at_time', 'free')
                feature = log['feature_used']
                user = log['user_email']
                
                plan_usage[plan] = plan_usage.get(plan, 0) + 1
                feature_usage[feature] = feature_usage.get(feature, 0) + 1
                user_usage[user] = user_usage.get(user, 0) + 1
            
            return {
                'total_usage': len(logs),
                'plan_usage': plan_usage,
                'feature_usage': feature_usage,
                'unique_users': len(user_usage),
                'days_analyzed': days
            }
            
        except Exception as e:
            print(f"Error getting all users usage: {e}")
            return {}


# Test the usage tracking system
if __name__ == "__main__":
    print("=== Usage Tracking System ===")
    
    # Test plan limits
    limits = UsageTracker.get_plan_limits('free')
    print(f"\nFree plan limits:")
    print(f"  API calls/day: {limits['api_limit_per_day']}")
    print(f"  Trend views/day: {limits['trend_views_per_day']}")
    print(f"  Features: {limits['features']}")
    
    limits = UsageTracker.get_plan_limits('pro')
    print(f"\nPro plan limits:")
    print(f"  API calls/day: {limits['api_limit_per_day']}")
    print(f"  Trend views/day: {limits['trend_views_per_day']}")
    print(f"  Features: {limits['features']}")
    
    # Test usage limit check
    is_allowed, reason = UsageTracker.check_usage_limit("test@example.com", "api_call")
    print(f"\nUsage limit check: {is_allowed}")
    if reason:
        print(f"Reason: {reason}")
    
    print("\n=== Usage Tracking System Working ===")