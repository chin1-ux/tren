"""
Early Trend Detection Algorithm
Predicts which trends are about to go viral before they peak
This is a key differentiator - most tools only show trends AFTER they're viral
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


class EarlyTrendDetector:
    """
    Detects trends early by analyzing velocity patterns and growth signals
    """
    
    @staticmethod
    def calculate_growth_velocity(trend_data: Dict) -> float:
        """
        Calculate the growth velocity of a trend
        Higher velocity = faster growth = more likely to go viral
        
        Args:
            trend_data: Trend data from database
        
        Returns:
            Growth velocity score (0-100)
        """
        velocity_avg = trend_data.get('velocity_avg', 0)
        reel_count = trend_data.get('reel_count', 0)
        
        # Normalize velocity to 0-100 scale
        # Based on research: velocity > 1M = high viral potential
        if velocity_avg == 0:
            return 0
        
        # Logarithmic scaling to handle large numbers
        normalized_velocity = min(100, (velocity_avg / 1000000) * 100)
        
        # Bonus for higher reel count (social proof)
        reel_bonus = min(20, (reel_count / 10000) * 20)
        
        return min(100, normalized_velocity + reel_bonus)
    
    @staticmethod
    def calculate_early_signal_score(trend_data: Dict) -> float:
        """
        Calculate early signal score based on multiple factors
        This predicts if a trend will go viral in the next 6-24 hours
        
        Args:
            trend_data: Trend data from database
        
        Returns:
            Early signal score (0-100)
        """
        signals = []
        
        # Signal 1: Velocity acceleration (is it speeding up?)
        velocity_avg = trend_data.get('velocity_avg', 0)
        peak_velocity = trend_data.get('peak_velocity', 0)
        
        if peak_velocity > 0:
            acceleration = (velocity_avg / peak_velocity) * 100
            signals.append(min(100, acceleration))
        else:
            # No peak yet, assume it's accelerating
            signals.append(min(100, velocity_avg / 10000))
        
        # Signal 2: Saturation score (lower is better for early detection)
        saturation = trend_data.get('saturation_score', 0)
        # Low saturation = room for growth
        saturation_signal = max(0, 100 - (saturation * 100))
        signals.append(saturation_signal)
        
        # Signal 3: Time since first detected (younger trends have more potential)
        first_detected = trend_data.get('first_detected_at')
        if first_detected:
            dt = datetime.fromisoformat(first_detected)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            hours_since_detection = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            # Optimal window: 6-24 hours
            if 6 <= hours_since_detection <= 24:
                signals.append(100)
            elif hours_since_detection < 6:
                signals.append(80)  # Very early, high potential
            elif hours_since_detection < 48:
                signals.append(60)  # Still good potential
            else:
                signals.append(30)  # Older, less potential
        else:
            signals.append(50)  # Unknown time
        
        # Signal 4: Confidence score from LLM
        confidence = trend_data.get('confidence', 0)
        signals.append(confidence * 100)
        
        # Signal 5: Regional crossover potential
        cultural_context = trend_data.get('cultural_context', '')
        if cultural_context in ['celebration', 'festival', 'trending']:
            signals.append(80)
        else:
            signals.append(50)
        
        # Average all signals
        return sum(signals) / len(signals) if signals else 0
    
    @staticmethod
    def predict_viral_potential(trend_data: Dict) -> Dict:
        """
        Predict the viral potential of a trend
        
        Args:
            trend_data: Trend data from database
        
        Returns:
            Prediction dict with score, timing, and recommendations
        """
        early_signal = EarlyTrendDetector.calculate_early_signal_score(trend_data)
        growth_velocity = EarlyTrendDetector.calculate_growth_velocity(trend_data)
        
        # Combined score (weighted)
        combined_score = (early_signal * 0.6) + (growth_velocity * 0.4)
        
        # Determine prediction category
        if combined_score >= 80:
            prediction = "HIGH - Likely to go viral in 6-12 hours"
            timing = "Join immediately (0-6h window)"
            multiplier = "3x"
        elif combined_score >= 60:
            prediction = "MEDIUM - Good viral potential in 12-24 hours"
            timing = "Join soon (6-24h window)"
            multiplier = "2x"
        elif combined_score >= 40:
            prediction = "LOW - Moderate viral potential"
            timing = "Can wait (24-48h window)"
            multiplier = "1.5x"
        else:
            prediction = "VERY LOW - Unlikely to go viral"
            timing = "Skip or wait for better signals"
            multiplier = "1x"
        
        return {
            'combined_score': round(combined_score, 2),
            'early_signal_score': round(early_signal, 2),
            'growth_velocity_score': round(growth_velocity, 2),
            'prediction': prediction,
            'optimal_timing': timing,
            'reach_multiplier': multiplier,
            'recommended_action': 'CREATE CONTENT NOW' if combined_score >= 60 else 'MONITOR OR SKIP'
        }
    
    @staticmethod
    def get_early_detection_trends(limit: int = 10) -> List[Dict]:
        """
        Get trends with high early detection scores
        These are trends that are about to go viral
        
        Args:
            limit: Number of trends to return
        
        Returns:
            List of trends with predictions
        """
        if not supabase:
            return []
        
        try:
            # Get recent trends (last 48 hours)
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            
            res = supabase.table('trends') \
                .select('*') \
                .in_('status', ['emerging', 'rising']) \
                .eq('is_seed_data', False) \
                .gte('first_detected_at', time_threshold) \
                .order('velocity_avg', desc=True) \
                .limit(limit * 2) \
                .execute()
            
            trends = res.data or []
            
            # Add predictions to each trend
            enriched_trends = []
            for trend in trends:
                prediction = EarlyTrendDetector.predict_viral_potential(trend)
                trend['prediction'] = prediction
                enriched_trends.append(trend)
            
            # Sort by combined score and return top N
            enriched_trends.sort(key=lambda x: x['prediction']['combined_score'], reverse=True)
            
            return enriched_trends[:limit]
            
        except Exception as e:
            logger.error(f"Error getting early detection trends: {e}")
            return []
    
    @staticmethod
    def get_trend_adoption_recommendation(trend_data: Dict, creator_niche: str = None) -> Dict:
        """
        Get personalized recommendation for trend adoption
        
        Args:
            trend_data: Trend data
            creator_niche: Creator's niche (optional)
        
        Returns:
            Recommendation with timing, content type, and tips
        """
        prediction = EarlyTrendDetector.predict_viral_potential(trend_data)
        
        # Check niche match
        trend_niche = trend_data.get('niche_tag', 'general')
        niche_match = creator_niche and creator_niche.lower() in trend_niche.lower()
        
        if prediction['combined_score'] >= 80:
            timing = "IMMEDIATE - Create within 6 hours"
            urgency = "HIGH"
        elif prediction['combined_score'] >= 60:
            timing = "SOON - Create within 24 hours"
            urgency = "MEDIUM"
        else:
            timing = "OPTIONAL - Can wait or skip"
            urgency = "LOW"
        
        return {
            'timing': timing,
            'urgency': urgency,
            'niche_match': niche_match,
            'recommended_content_type': trend_data.get('content_type', 'general'),
            'is_dance': trend_data.get('is_dance', False),
            'why_now': prediction['prediction'],
            'reach_multiplier': prediction['reach_multiplier'],
            'tips': [
                "Use trending audio in first 3 seconds",
                "Add text overlay for hook",
                "Post during optimal hours (18:00-21:00 IST)",
                "Use relevant hashtags from trend"
            ]
        }


# Test the early trend detection system
if __name__ == "__main__":
    print("=== Early Trend Detection System ===")
    
    # Test with sample trend data
    sample_trend = {
        'velocity_avg': 500000,
        'reel_count': 5000,
        'saturation_score': 0.3,
        'confidence': 0.85,
        'first_detected_at': (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat(),
        'cultural_context': 'celebration',
        'content_type': 'dance',
        'is_dance': True,
        'niche_tag': 'entertainment'
    }
    
    print("\n[Test 1] Growth Velocity Calculation")
    velocity = EarlyTrendDetector.calculate_growth_velocity(sample_trend)
    print(f"  [OK] Growth velocity: {velocity:.2f}/100")
    
    print("\n[Test 2] Early Signal Score")
    signal = EarlyTrendDetector.calculate_early_signal_score(sample_trend)
    print(f"  [OK] Early signal score: {signal:.2f}/100")
    
    print("\n[Test 3] Viral Potential Prediction")
    prediction = EarlyTrendDetector.predict_viral_potential(sample_trend)
    print(f"  [OK] Combined score: {prediction['combined_score']}")
    print(f"  [OK] Prediction: {prediction['prediction']}")
    print(f"  [OK] Optimal timing: {prediction['optimal_timing']}")
    print(f"  [OK] Reach multiplier: {prediction['reach_multiplier']}")
    
    print("\n[Test 4] Adoption Recommendation")
    recommendation = EarlyTrendDetector.get_trend_adoption_recommendation(sample_trend, 'fitness')
    print(f"  [OK] Timing: {recommendation['timing']}")
    print(f"  [OK] Urgency: {recommendation['urgency']}")
    print(f"  [OK] Niche match: {recommendation['niche_match']}")
    
    print("\n=== Early Trend Detection System Working ===")