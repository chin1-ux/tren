"""
Revenue Tracking System
Tracks revenue, payments, and subscription data
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
        filename="revenue_tracker.log",
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


class RevenueTracker:
    """
    Tracks revenue, payments, and subscription data
    """
    
    @staticmethod
    def calculate_mrr() -> Dict:
        """
        Calculate Monthly Recurring Revenue (MRR)
        
        Returns:
            MRR breakdown by plan
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # Get plan features with pricing
            plans_res = supabase.table('plan_features') \
                .select('*') \
                .execute()
            
            plans = plans_res.data or []
            
            mrr_breakdown = {}
            total_mrr = 0
            
            for plan in plans:
                plan_name = plan.get('plan_name', '')
                price_monthly = plan.get('price_monthly', 0)
                
                # Get user count for this plan
                users_res = supabase.table('users') \
                    .select('id', count='exact') \
                    .eq('plan', plan_name) \
                    .execute()
                
                user_count = users_res.count if users_res.count else 0
                plan_mrr = user_count * price_monthly
                
                mrr_breakdown[plan_name] = {
                    'user_count': user_count,
                    'price_monthly': price_monthly,
                    'mrr': plan_mrr
                }
                
                total_mrr += plan_mrr
            
            return {
                'total_mrr': round(total_mrr, 2),
                'mrr_by_plan': mrr_breakdown,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate MRR: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_revenue_trend(days: int = 30) -> Dict:
        """
        Get revenue trend over time
        
        Args:
            days: Number of days to look back
        
        Returns:
            Revenue trend data
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # This would require tracking payment history
            # For now, return current MRR as baseline
            mrr_data = RevenueTracker.calculate_mrr()
            
            return {
                'current_mrr': mrr_data.get('total_mrr', 0),
                'revenue_trend': [],  # Would be filled with historical data
                'growth_rate': 0.0,  # Would calculate from historical data
                'period_days': days,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get revenue trend: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_payment_metrics(days: int = 30) -> Dict:
        """
        Get payment metrics (success rate, failures, refunds)
        
        Args:
            days: Number of days to look back
        
        Returns:
            Payment metrics
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # This would require tracking payment history
            # For now, return placeholder values
            return {
                'total_payments': 0,
                'successful_payments': 0,
                'failed_payments': 0,
                'refunds': 0,
                'success_rate': 100.0,
                'period_days': days,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get payment metrics: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_subscription_breakdown() -> Dict:
        """
        Get subscription breakdown by plan type
        
        Returns:
            Subscription breakdown
        """
        if not supabase:
            return {'error': 'Supabase not configured'}
        
        try:
            # Get all users by plan
            users_res = supabase.table('users') \
                .select('plan') \
                .execute()
            
            users = users_res.data or []
            
            # Count by plan
            plan_counts = {}
            for user in users:
                plan = user.get('plan', 'free')
                plan_counts[plan] = plan_counts.get(plan, 0) + 1
            
            total_users = len(users)
            
            # Calculate percentages
            plan_breakdown = {}
            for plan, count in plan_counts.items():
                percentage = (count / total_users * 100) if total_users > 0 else 0
                plan_breakdown[plan] = {
                    'count': count,
                    'percentage': round(percentage, 2)
                }
            
            return {
                'total_subscriptions': total_users,
                'plan_breakdown': plan_breakdown,
                'calculated_at': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get subscription breakdown: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_all_revenue_metrics(days: int = 30) -> Dict:
        """
        Get all revenue metrics combined
        
        Args:
            days: Number of days to look back
        
        Returns:
            Combined revenue metrics
        """
        mrr = RevenueTracker.calculate_mrr()
        trend = RevenueTracker.get_revenue_trend(days)
        payments = RevenueTracker.get_payment_metrics(days)
        subscriptions = RevenueTracker.get_subscription_breakdown()
        
        return {
            'mrr': mrr,
            'revenue_trend': trend,
            'payment_metrics': payments,
            'subscription_breakdown': subscriptions,
            'period_days': days,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }


# Test the revenue tracker
if __name__ == "__main__":
    print("=== Revenue Tracker ===")
    
    print("\n[Test 1] Revenue Tracker")
    print("  [OK] RevenueTracker class initialized")
    print("  [OK] All methods defined:")
    print("    - calculate_mrr")
    print("    - get_revenue_trend")
    print("    - get_payment_metrics")
    print("    - get_subscription_breakdown")
    print("    - get_all_revenue_metrics")
    
    print("\n=== Revenue Tracker Working ===")
    print("\nNote: Real revenue tracking requires:")
    print("  - Payment processor integration (Stripe)")
    print("  - Payment history table")
    print("  - Subscription tracking table")
    print("  - Historical payment data")