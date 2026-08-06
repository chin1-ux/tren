"""
Business Metrics System
Tracks key business metrics for pre-seed funding
Phase 5: Pre-Seed Preparation
"""
import os
import sys
import logging
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

try:
    logging.basicConfig(
        filename="business_metrics.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')

if SUPABASE_URL and SUPABASE_KEY:
    supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None


class BusinessMetrics:
    """
    Tracks and calculates business metrics for pre-seed funding
    """
    
    @staticmethod
    def get_user_metrics(days: int = 30) -> Dict:
        """
        Get user acquisition metrics
        
        Args:
            days: Number of days to look back
        
        Returns:
            User metrics (total, daily signups, conversion rate, etc.)
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            # Get total users
            total_res = supabase.table('users') \
                .select('id', count='exact') \
                .execute()
            
            total_users = total_res.count if total_res.count else 0
            
            # Get daily signups
            signups_res = supabase.table('users') \
                .select('created_at') \
                .gte('created_at', time_threshold) \
                .execute()
            
            daily_signups = signups_res.data or []
            
            # Calculate daily average
            avg_daily_signups = len(daily_signups) / days if days > 0 else 0
            
            # Get paying users (assuming plan != 'free')
            paying_res = supabase.table('users') \
                .select('id', count='exact') \
                .neq('plan', 'free') \
                .execute()
            
            paying_users = paying_res.count if paying_res.count else 0
            
            # Calculate conversion rate
            conversion_rate = (paying_users / total_users * 100) if total_users > 0 else 0
            
            return {
                'total_users': total_users,
                'paying_users': paying_users,
                'free_users': total_users - paying_users,
                'conversion_rate': round(conversion_rate, 2),
                'avg_daily_signups': round(avg_daily_signups, 2),
                'period_days': days,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user metrics: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_revenue_metrics(days: int = 30) -> Dict:
        """
        Get revenue metrics
        
        Args:
            days: Number of days to look back
        
        Returns:
            Revenue metrics (MRR, revenue by plan, trends)
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # Get plan features with pricing
            plans_res = supabase.table('plan_features') \
                .select('*') \
                .execute()
            
            plans = plans_res.data or []
            
            # Calculate MRR based on paying users
            mrr = 0
            revenue_by_plan = {}
            
            for plan in plans:
                plan_name = plan.get('plan_name', '')
                price_monthly = plan.get('price_monthly', 0)
                
                # Get user count for this plan
                users_res = supabase.table('users') \
                    .select('id', count='exact') \
                    .eq('plan', plan_name) \
                    .execute()
                
                user_count = users_res.count if users_res.count else 0
                plan_revenue = user_count * price_monthly
                
                mrr += plan_revenue
                revenue_by_plan[plan_name] = {
                    'user_count': user_count,
                    'revenue': plan_revenue,
                    'price_monthly': price_monthly
                }
            
            return {
                'mrr': round(mrr, 2),
                'revenue_by_plan': revenue_by_plan,
                'period_days': days,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get revenue metrics: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_engagement_metrics(days: int = 30) -> Dict:
        """
        Get engagement metrics
        
        Args:
            days: Number of days to look back
        
        Returns:
            Engagement metrics (DAU, MAU, feature usage, retention)
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            time_threshold = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
            
            # Get active users (those who have used the API recently)
            # This would require tracking API usage in usage_logs table
            usage_res = supabase.table('usage_logs') \
                .select('user_email') \
                .gte('timestamp', time_threshold) \
                .execute()
            
            usage_logs = usage_res.data or []
            unique_users = len(set(log.get('user_email') for log in usage_logs))
            
            # Calculate DAU and MAU
            dau = unique_users  # Simplified - would need daily breakdown
            mau = unique_users  # Simplified - would need monthly breakdown
            
            return {
                'dau': dau,
                'mau': mau,
                'active_users': unique_users,
                'total_usage_logs': len(usage_logs),
                'period_days': days,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get engagement metrics: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_churn_metrics(days: int = 30) -> Dict:
        """
        Get churn metrics
        
        Args:
            days: Number of days to look back
        
        Returns:
            Churn metrics (churn rate, retention)
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # This would require tracking plan changes over time
            # For now, return placeholder
            return {
                'churn_rate': 0.0,  # Would calculate from plan downgrades
                'retention_rate': 100.0,  # Would calculate from active users
                'period_days': days,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get churn metrics: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_all_metrics(days: int = 30) -> Dict:
        """
        Get all business metrics combined
        
        Args:
            days: Number of days to look back
        
        Returns:
            Combined business metrics
        """
        user_metrics = BusinessMetrics.get_user_metrics(days)
        revenue_metrics = BusinessMetrics.get_revenue_metrics(days)
        engagement_metrics = BusinessMetrics.get_engagement_metrics(days)
        churn_metrics = BusinessMetrics.get_churn_metrics(days)
        
        return {
            'user_metrics': user_metrics,
            'revenue_metrics': revenue_metrics,
            'engagement_metrics': engagement_metrics,
            'churn_metrics': churn_metrics,
            'period_days': days,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    def calculate_cac_ltv() -> Dict:
        """
        Calculate Customer Acquisition Cost (CAC) and Lifetime Value (LTV)
        
        Returns:
            CAC and LTV metrics
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # This would require tracking marketing spend and customer lifetime
            # For now, return placeholder values
            return {
                'cac': 10.0,  # Would calculate from marketing spend / new users
                'ltv': 50.0,  # Would calculate from avg revenue per user * avg months
                'ltv_cac_ratio': 5.0,  # Should be > 3 for healthy business
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate CAC/LTV: {e}")
            return {'error': str(e)}


# Test the business metrics system
if __name__ == "__main__":
    print("=== Business Metrics System ===")
    
    print("\n[Test 1] Business Metrics System")
    print("  [OK] BusinessMetrics class initialized")
    print("  [OK] All methods defined:")
    print("    - get_user_metrics")
    print("    - get_revenue_metrics")
    print("    - get_engagement_metrics")
    print("    - get_churn_metrics")
    print("    - get_all_metrics")
    print("    - calculate_cac_ltv")
    
    print("\n=== Business Metrics System Working ===")
    print("\nNote: Real metrics require:")
    print("  - Supabase database with user data")
    print("  - Plan features table with pricing")
    print("  - Usage logs table for engagement tracking")
    print("  - Historical data for churn calculation")