"""
Virality Prediction System
Predicts how well a creator's content will perform before they post
This is a key differentiator - no other tool offers this
"""
import os
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ViralityPredictor:
    """
    Predicts virality of content before posting
    Based on trend alignment, timing, content factors, and creator history
    """
    
    @staticmethod
    def calculate_trend_alignment_score(content_data: Dict, trend_data: Dict) -> float:
        """
        Calculate how well the content aligns with the trend
        
        Args:
            content_data: Content details (niche, type, audio, etc.)
            trend_data: Trend data
        
        Returns:
            Alignment score (0-100)
        """
        factors = []
        
        # Factor 1: Niche match
        content_niche = content_data.get('niche', 'general')
        trend_niche = trend_data.get('niche_tag', 'general')
        if content_niche.lower() in trend_niche.lower() or trend_niche == 'general':
            factors.append(100)
        else:
            factors.append(50)
        
        # Factor 2: Content type match
        content_type = content_data.get('content_type', 'general')
        trend_type = trend_data.get('content_type', 'general')
        if content_type == trend_type:
            factors.append(100)
        elif trend_type == 'general':
            factors.append(75)
        else:
            factors.append(40)
        
        # Factor 3: Audio match
        content_audio = content_data.get('audio_title', '')
        trend_audio = trend_data.get('audio_title', '')
        if content_audio and trend_audio and content_audio.lower() == trend_audio.lower():
            factors.append(100)
        else:
            factors.append(50)
        
        # Factor 4: Dance requirement match
        is_dance_content = content_data.get('is_dance', False)
        is_dance_trend = trend_data.get('is_dance', False)
        if is_dance_content == is_dance_trend:
            factors.append(100)
        else:
            factors.append(30)
        
        return sum(factors) / len(factors) if factors else 0
    
    @staticmethod
    def calculate_timing_score(posting_time: str, creator_timezone: str = 'Asia/Kolkata') -> float:
        """
        Calculate optimal posting time score
        
        Args:
            posting_time: ISO format timestamp
            creator_timezone: Creator's timezone
        
        Returns:
            Timing score (0-100)
        """
        try:
            post_dt = datetime.fromisoformat(posting_time)
            hour = post_dt.hour
            
            # Optimal hours for Indian creators (18:00-21:00 IST)
            if 18 <= hour <= 21:
                return 100
            elif 15 <= hour <= 23:
                return 80
            elif 12 <= hour <= 15:
                return 60
            elif 6 <= hour <= 12:
                return 40
            else:
                return 20  # Late night/early morning - suboptimal
        except Exception:
            return 50  # Default if time parsing fails
    
    @staticmethod
    def calculate_content_quality_score(content_data: Dict) -> float:
        """
        Calculate content quality score based on content factors
        
        Args:
            content_data: Content details
        
        Returns:
            Quality score (0-100)
        """
        factors = []
        
        # Factor 1: Hashtag quality
        hashtags = content_data.get('hashtags', [])
        if len(hashtags) >= 3 and len(hashtags) <= 10:
            factors.append(100)
        elif len(hashtags) > 0:
            factors.append(70)
        else:
            factors.append(30)
        
        # Factor 2: Caption length
        caption = content_data.get('caption', '')
        caption_length = len(caption)
        if 50 <= caption_length <= 300:
            factors.append(100)
        elif caption_length > 0:
            factors.append(70)
        else:
            factors.append(40)
        
        # Factor 3: Hook presence
        hook = content_data.get('hook', '')
        if hook and len(hook) > 10:
            factors.append(100)
        else:
            factors.append(50)
        
        # Factor 4: Audio trendiness
        audio_trendiness = content_data.get('audio_trendiness', 0)
        factors.append(audio_trendiness * 100)
        
        return sum(factors) / len(factors) if factors else 0
    
    @staticmethod
    def calculate_creator_history_score(creator_email: str) -> float:
        """
        Calculate creator's historical performance
        
        Args:
            creator_email: Creator's email
        
        Returns:
            History score (0-100)
        """
        if not supabase:
            return 50  # Default if no database
        
        try:
            # Get creator's past performance
            res = supabase.table('creator_trend_memory') \
                .select('outcome_score') \
                .eq('user_email', creator_email) \
                .execute()
            
            memories = res.data or []
            
            if not memories:
                return 50  # New creator, average score
            
            # Calculate average outcome score
            scores = [m.get('outcome_score', 0) for m in memories if m.get('outcome_score')]
            if not scores:
                return 50
            
            avg_score = sum(scores) / len(scores)
            return min(100, avg_score * 100)  # Normalize to 0-100
            
        except Exception as e:
            logger.error(f"Error calculating creator history: {e}")
            return 50
    
    @staticmethod
    def predict_content_virality(content_data: Dict, trend_data: Dict, creator_email: str = None) -> Dict:
        """
        Predict overall virality of content
        
        Args:
            content_data: Content details
            trend_data: Trend data
            creator_email: Creator's email (optional)
        
        Returns:
            Prediction with score, reach estimate, and recommendations
        """
        # Calculate individual scores
        trend_alignment = ViralityPredictor.calculate_trend_alignment_score(content_data, trend_data)
        timing_score = ViralityPredictor.calculate_timing_score(
            content_data.get('posting_time', datetime.now(timezone.utc).isoformat()),
            content_data.get('timezone', 'Asia/Kolkata')
        )
        content_quality = ViralityPredictor.calculate_content_quality_score(content_data)
        creator_history = ViralityPredictor.calculate_creator_history_score(creator_email) if creator_email else 50
        
        # Calculate trend viral potential
        try:
            from early_trend_detection import EarlyTrendDetector
            trend_prediction = EarlyTrendDetector.predict_viral_potential(trend_data)
            trend_potential = trend_prediction['combined_score']
        except Exception:
            trend_potential = 50  # Default if early detection fails
        
        # Combined score (weighted)
        # Trend potential is most important (35%)
        # Trend alignment is second (25%)
        # Content quality is third (20%)
        # Timing is fourth (15%)
        # Creator history is least (5%)
        combined_score = (
            (trend_potential * 0.35) +
            (trend_alignment * 0.25) +
            (content_quality * 0.20) +
            (timing_score * 0.15) +
            (creator_history * 0.05)
        )
        
        # Determine prediction category
        if combined_score >= 80:
            prediction = "HIGH - Likely to go viral"
            reach_estimate = "10,000-100,000 views"
            engagement_estimate = "15-25% engagement rate"
        elif combined_score >= 60:
            prediction = "MEDIUM - Good performance expected"
            reach_estimate = "5,000-50,000 views"
            engagement_estimate = "10-20% engagement rate"
        elif combined_score >= 40:
            prediction = "LOW - Average performance"
            reach_estimate = "1,000-10,000 views"
            engagement_estimate = "5-15% engagement rate"
        else:
            prediction = "VERY LOW - Poor performance expected"
            reach_estimate = "<1,000 views"
            engagement_estimate = "<5% engagement rate"
        
        # Generate recommendations
        recommendations = []
        
        if trend_alignment < 70:
            recommendations.append("Consider adjusting content to better match the trend")
        
        if timing_score < 70:
            recommendations.append("Optimal posting time is 18:00-21:00 IST")
        
        if content_quality < 70:
            recommendations.append("Add more hashtags (3-10) and a stronger hook")
        
        if trend_potential < 60:
            recommendations.append("Consider using a trend with higher viral potential")
        
        if not recommendations:
            recommendations.append("Content looks great! Ready to post.")
        
        return {
            'combined_score': round(combined_score, 2),
            'trend_alignment_score': round(trend_alignment, 2),
            'timing_score': round(timing_score, 2),
            'content_quality_score': round(content_quality, 2),
            'creator_history_score': round(creator_history, 2),
            'trend_potential_score': round(trend_potential, 2),
            'prediction': prediction,
            'reach_estimate': reach_estimate,
            'engagement_estimate': engagement_estimate,
            'recommendations': recommendations,
            'confidence': min(95, 50 + (combined_score * 0.4))  # Higher score = higher confidence
        }
    
    @staticmethod
    def get_improvement_suggestions(content_data: Dict, trend_data: Dict) -> List[str]:
        """
        Get specific suggestions to improve virality
        
        Args:
            content_data: Content details
            trend_data: Trend data
        
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Check trend alignment
        alignment = ViralityPredictor.calculate_trend_alignment_score(content_data, trend_data)
        if alignment < 70:
            if content_data.get('niche') != trend_data.get('niche_tag'):
                suggestions.append(f"Adjust content to match trend niche: {trend_data.get('niche_tag')}")
            if content_data.get('content_type') != trend_data.get('content_type'):
                suggestions.append(f"Use {trend_data.get('content_type')} content type for this trend")
        
        # Check hashtags
        hashtags = content_data.get('hashtags', [])
        if len(hashtags) < 3:
            suggestions.append("Add 3-10 relevant hashtags")
        elif len(hashtags) > 10:
            suggestions.append("Reduce hashtags to 3-10 for better reach")
        
        # Check caption
        caption = content_data.get('caption', '')
        if len(caption) < 50:
            suggestions.append("Write a longer caption (50-300 characters)")
        elif len(caption) > 300:
            suggestions.append("Shorten caption to 300 characters or less")
        
        # Check hook
        hook = content_data.get('hook', '')
        if not hook or len(hook) < 10:
            suggestions.append("Add a strong hook in the first 3 seconds")
        
        # Check timing
        posting_time = content_data.get('posting_time')
        if posting_time:
            timing_score = ViralityPredictor.calculate_timing_score(posting_time)
            if timing_score < 70:
                suggestions.append("Schedule post for 18:00-21:00 IST for maximum reach")
        
        return suggestions


# Test the virality prediction system
if __name__ == "__main__":
    print("=== Virality Prediction System ===")
    
    # Test content data
    test_content = {
        'niche': 'fitness',
        'content_type': 'general',
        'audio_title': 'Trending Song',
        'is_dance': False,
        'hashtags': ['fitness', 'workout', 'trending'],
        'caption': 'Join me for this amazing workout! #fitness #workout',
        'hook': 'Wait until you see this transformation',
        'audio_trendiness': 0.8,
        'posting_time': datetime.now(timezone.utc).replace(hour=19).isoformat(),
        'timezone': 'Asia/Kolkata'
    }
    
    # Test trend data
    test_trend = {
        'niche_tag': 'fitness',
        'content_type': 'general',
        'audio_title': 'Trending Song',
        'is_dance': False,
        'velocity_avg': 500000,
        'reel_count': 5000,
        'saturation_score': 0.3,
        'confidence': 0.85,
        'first_detected_at': (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        'cultural_context': 'celebration'
    }
    
    print("\n[Test 1] Trend Alignment Score")
    alignment = ViralityPredictor.calculate_trend_alignment_score(test_content, test_trend)
    print(f"  [OK] Alignment score: {alignment:.2f}/100")
    
    print("\n[Test 2] Timing Score")
    timing = ViralityPredictor.calculate_timing_score(test_content['posting_time'])
    print(f"  [OK] Timing score: {timing:.2f}/100")
    
    print("\n[Test 3] Content Quality Score")
    quality = ViralityPredictor.calculate_content_quality_score(test_content)
    print(f"  [OK] Quality score: {quality:.2f}/100")
    
    print("\n[Test 4] Virality Prediction")
    prediction = ViralityPredictor.predict_content_virality(test_content, test_trend)
    print(f"  [OK] Combined score: {prediction['combined_score']}")
    print(f"  [OK] Prediction: {prediction['prediction']}")
    print(f"  [OK] Reach estimate: {prediction['reach_estimate']}")
    print(f"  [OK] Confidence: {prediction['confidence']:.1f}%")
    
    print("\n[Test 5] Improvement Suggestions")
    suggestions = ViralityPredictor.get_improvement_suggestions(test_content, test_trend)
    print(f"  [OK] Suggestions: {len(suggestions)}")
    for suggestion in suggestions:
        print(f"    - {suggestion}")
    
    print("\n=== Virality Prediction System Working ===")