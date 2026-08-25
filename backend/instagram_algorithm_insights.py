"""
Instagram Algorithm Insights Module
Provides creators with actionable insights about Instagram's algorithm and how to optimize content for virality.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

try:
    logging.basicConfig(
        filename="instagram_algorithm_insights.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

@dataclass
class ViralityFactor:
    """Represents a key virality factor on Instagram"""
    name: str
    weight: float  # Importance weight (0-1)
    current_score: float  # Creator's current performance (0-1)
    optimization_tips: List[str]
    algorithm_logic: str  # How Instagram uses this factor

@dataclass
class ContentRecommendation:
    """Actionable recommendation for content optimization"""
    category: str
    priority: str  # "high", "medium", "low"
    title: str
    description: str
    expected_impact: str
    implementation_difficulty: str  # "easy", "medium", "hard"

class InstagramAlgorithmInsights:
    """
    Instagram Algorithm Intelligence Engine
    Analyzes content and provides actionable insights for maximizing virality
    """
    
    def __init__(self):
        # Instagram 2024-2025 Algorithm Factors based on research
        self.virality_factors = {
            "watch_time": ViralityFactor(
                name="Watch Time",
                weight=0.25,
                current_score=0.0,
                optimization_tips=[
                    "Hook viewers in first 3 seconds with compelling visuals or questions",
                    "Use fast-paced editing to maintain engagement throughout",
                    "Create loops that encourage re-watching",
                    "Optimize video length: 15-30s for maximum completion rates"
                ],
                algorithm_logic="Instagram prioritizes content that keeps users on the platform longer. Higher watch time = more distribution"
            ),
            "engagement_rate": ViralityFactor(
                name="Engagement Rate",
                weight=0.20,
                current_score=0.0,
                optimization_tips=[
                    "Ask questions to encourage comments",
                    "Use trending audio to boost discoverability",
                    "Create shareable content (relatable, educational, entertaining)",
                    "Respond to comments quickly to boost engagement signals"
                ],
                algorithm_logic="High engagement (likes, comments, shares, saves) signals quality content and triggers wider distribution"
            ),
            "save_rate": ViralityFactor(
                name="Save Rate",
                weight=0.15,
                current_score=0.0,
                optimization_tips=[
                    "Include actionable tips, tutorials, or valuable information",
                    "Use text overlays with key takeaways",
                    "Create content worth revisiting (recipes, workouts, tutorials)",
                    "Add 'save for later' CTAs in captions"
                ],
                algorithm_logic="Saves indicate long-term value and are a strong signal for Explore page placement"
            ),
            "share_rate": ViralityFactor(
                name="Share Rate",
                weight=0.15,
                current_score=0.0,
                optimization_tips=[
                    "Create relatable content that resonates with viewers' experiences",
                    "Use humor or emotional storytelling",
                    "Make content easily shareable (clear message, universal appeal)",
                    "Tap into trends and challenges that encourage sharing"
                ],
                algorithm_logic="Shares expand your reach beyond followers and are key for viral distribution"
            ),
            "relevance_score": ViralityFactor(
                name="Relevance Score",
                weight=0.10,
                current_score=0.0,
                optimization_tips=[
                    "Use niche-specific hashtags and keywords",
                    "Create content for your target audience consistently",
                    "Analyze your top-performing content and double down on themes",
                    "Stay consistent with your content pillars and brand voice"
                ],
                algorithm_logic="Instagram matches content with users likely to engage based on interests and past behavior"
            ),
            "timeliness": ViralityFactor(
                name="Timeliness",
                weight=0.10,
                current_score=0.0,
                optimization_tips=[
                    "Post during peak hours for your audience",
                    "Jump on trends quickly (first 24-48 hours are critical)",
                    "Align content with current events, seasons, or cultural moments",
                    "Use trending audio and hashtags while they're hot"
                ],
                algorithm_logic="Fresh content gets initial boost, but engagement quality determines long-term success"
            ),
            "relationship": ViralityFactor(
                name="Relationship",
                weight=0.05,
                current_score=0.0,
                optimization_tips=[
                    "Engage with your followers consistently",
                    "Reply to comments and DMs to build community",
                    "Collaborate with other creators in your niche",
                    "Use Stories and Lives to strengthen follower connections"
                ],
                algorithm_logic="Strong follower relationships increase content priority in their feeds"
            )
        }
    
    def analyze_content_for_virality(self, content_data: Dict) -> Dict:
        """
        Analyze content data and provide virality insights
        
        Args:
            content_data: Dictionary containing content metrics and metadata
                - views: int
                - likes: int
                - comments: int
                - shares: int
                - saves: int
                - duration: int (seconds)
                - hook_quality: str (first 3 seconds analysis)
                - content_type: str
                - niche: str
                - posting_time: str
                - uses_trending_audio: bool
        
        Returns:
            Dictionary with virality analysis and recommendations
        """
        logger.info("Analyzing content for virality insights")
        
        views = content_data.get('views', 0)
        likes = content_data.get('likes', 0)
        comments = content_data.get('comments', 0)
        shares = content_data.get('shares', 0)
        saves = content_data.get('saves', 0)
        duration = content_data.get('duration', 0)
        
        # Calculate engagement metrics
        engagement_rate = (likes + comments + shares + saves) / max(views, 1)
        like_rate = likes / max(views, 1)
        comment_rate = comments / max(views, 1)
        share_rate = shares / max(views, 1)
        save_rate = saves / max(views, 1)
        
        # Score each virality factor
        factor_scores = {}
        
        # Watch time score (based on duration and completion assumption)
        optimal_duration = 20  # seconds
        duration_score = 1.0 - min(1.0, abs(duration - optimal_duration) / 30)
        factor_scores['watch_time'] = duration_score
        
        # Engagement rate score
        engagement_score = min(1.0, engagement_rate * 50)  # 2% engagement = perfect score
        factor_scores['engagement_rate'] = engagement_score
        
        # Save rate score
        save_score = min(1.0, save_rate * 200)  # 0.5% save rate = perfect score
        factor_scores['save_rate'] = save_score
        
        # Share rate score
        share_score = min(1.0, share_rate * 100)  # 1% share rate = perfect score
        factor_scores['share_rate'] = share_score
        
        # Relevance score (based on niche alignment)
        niche = content_data.get('niche', 'general')
        relevance_score = 0.7 if niche != 'general' else 0.5
        factor_scores['relevance_score'] = relevance_score
        
        # Timeliness score
        uses_trending_audio = content_data.get('uses_trending_audio', False)
        timeliness_score = 0.8 if uses_trending_audio else 0.5
        factor_scores['timeliness'] = timeliness_score
        
        # Relationship score (placeholder - would need follower data)
        factor_scores['relationship'] = 0.6
        
        # Calculate overall virality score
        overall_score = sum(
            factor_scores[factor] * self.virality_factors[factor].weight
            for factor in factor_scores
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(factor_scores, content_data)
        
        return {
            'overall_virality_score': round(overall_score * 100, 1),
            'factor_scores': factor_scores,
            'engagement_metrics': {
                'engagement_rate': round(engagement_rate * 100, 2),
                'like_rate': round(like_rate * 100, 2),
                'comment_rate': round(comment_rate * 100, 2),
                'share_rate': round(share_rate * 100, 2),
                'save_rate': round(save_rate * 100, 2)
            },
            'recommendations': recommendations,
            'algorithm_explanation': self._get_algorithm_explanation(),
            'viral_potential': self._assess_viral_potential(overall_score)
        }
    
    def _generate_recommendations(self, factor_scores: Dict, content_data: Dict) -> List[ContentRecommendation]:
        """Generate personalized recommendations based on factor analysis"""
        recommendations = []
        
        # Watch time recommendations
        if factor_scores.get('watch_time', 0) < 0.6:
            recommendations.append(ContentRecommendation(
                category="Watch Time",
                priority="high",
                title="Optimize Video Length and Hook",
                description="Your content may be too long or have a weak opening hook. Focus on the first 3 seconds to grab attention.",
                expected_impact="20-30% improvement in completion rates",
                implementation_difficulty="easy"
            ))
        
        # Engagement rate recommendations
        if factor_scores.get('engagement_rate', 0) < 0.5:
            recommendations.append(ContentRecommendation(
                category="Engagement",
                priority="high",
                title="Boost Engagement Signals",
                description="Add questions, CTAs, or interactive elements to encourage likes and comments.",
                expected_impact="15-25% increase in distribution",
                implementation_difficulty="easy"
            ))
        
        # Save rate recommendations
        if factor_scores.get('save_rate', 0) < 0.4:
            recommendations.append(ContentRecommendation(
                category="Save Rate",
                priority="medium",
                title="Create Save-Worthy Content",
                description="Add value through tips, tutorials, or actionable takeaways that viewers want to reference later.",
                expected_impact="Higher Explore page placement",
                implementation_difficulty="medium"
            ))
        
        # Share rate recommendations
        if factor_scores.get('share_rate', 0) < 0.3:
            recommendations.append(ContentRecommendation(
                category="Share Rate",
                priority="medium",
                title="Make Content Shareable",
                description="Create relatable, entertaining, or emotionally resonant content that viewers want to share with others.",
                expected_impact="Viral distribution potential",
                implementation_difficulty="medium"
            ))
        
        # Trending audio recommendations
        if not content_data.get('uses_trending_audio', False):
            recommendations.append(ContentRecommendation(
                category="Timeliness",
                priority="high",
                title="Use Trending Audio",
                description="Incorporate trending audio to boost discoverability and algorithmic preference.",
                expected_impact="10-20% boost in initial reach",
                implementation_difficulty="easy"
            ))
        
        return recommendations
    
    def _get_algorithm_explanation(self) -> str:
        """Return a concise explanation of how Instagram's algorithm works"""
        return """
Instagram's 2024-2025 algorithm prioritizes content that:
1. Keeps users watching (watch time is the #1 factor)
2. Generates meaningful engagement (comments > likes > shares)
3. Provides long-term value (saves trigger Explore placement)
4. Expands reach through sharing (shares are viral triggers)
5. Matches user interests (relevance score)
6. Capitalizes on trends (timeliness matters)
7. Builds community (relationships with followers)

The algorithm evaluates each piece of content against these factors and distributes it to users most likely to engage. Consistency and authenticity are key to long-term success.
        """
    
    def _assess_viral_potential(self, overall_score: float) -> str:
        """Assess the viral potential based on overall score"""
        if overall_score >= 0.8:
            return "HIGH - Strong viral potential"
        elif overall_score >= 0.6:
            return "MODERATE - Good potential with optimization"
        elif overall_score >= 0.4:
            return "LOW - Needs significant improvement"
        else:
            return "VERY LOW - Complete content strategy revision needed"
    
    def get_optimal_posting_times(self, niche: str, target_audience: str = "india") -> List[str]:
        """
        Get optimal posting times based on niche and target audience
        
        Args:
            niche: Content niche (fitness, food, comedy, etc.)
            target_audience: Geographic audience (default: india)
        
        Returns:
            List of optimal posting times in IST
        """
        # India-specific optimal times by niche
        india_times = {
            "fitness": ["6:00 AM IST", "7:00 AM IST", "6:00 PM IST", "7:00 PM IST"],
            "food": ["11:00 AM IST", "12:00 PM IST", "7:00 PM IST", "8:00 PM IST"],
            "comedy": ["8:00 PM IST", "9:00 PM IST", "10:00 PM IST"],
            "fashion": ["7:00 PM IST", "8:00 PM IST", "9:00 PM IST"],
            "travel": ["6:00 PM IST", "7:00 PM IST", "8:00 PM IST"],
            "motivation": ["6:00 AM IST", "7:00 AM IST", "9:00 PM IST"],
            "business": ["9:00 AM IST", "10:00 AM IST", "7:00 PM IST"],
            "general": ["7:00 AM IST", "12:00 PM IST", "7:00 PM IST", "9:00 PM IST"]
        }
        
        return india_times.get(niche.lower(), india_times["general"])
    
    def get_hashtag_strategy(self, niche: str, content_type: str) -> Dict[str, List[str]]:
        """
        Get hashtag strategy recommendations
        
        Args:
            niche: Content niche
            content_type: Type of content (reel, story, post)
        
        Returns:
            Dictionary with hashtag categories
        """
        hashtag_strategies = {
            "fitness": {
                "trending": ["#fitness", "#workout", "#gym", "#fitnessmotivation", "#gymlife"],
                "niche": ["#bodybuilding", "#cardio", "#weightloss", "#strengthtraining", "#fitfam"],
                "location": ["#fitnessindia", "#indiafitness", "#mumbaifitness", "#delhifitness"]
            },
            "food": {
                "trending": ["#food", "#foodie", "#foodporn", "#instafood", "#yummy"],
                "niche": ["#recipe", "#cooking", "#homecooking", "#foodblogger", "#foodstagram"],
                "location": ["#indianfood", "#streetfoodindia", "#mumbaifood", "#delhifood"]
            },
            "comedy": {
                "trending": ["#comedy", "#funny", "#humor", "#memes", "#viral"],
                "niche": ["#standupcomedy", "#comedyreels", "#funnyreels", "#comedyvideo"],
                "location": ["#indiancomedy", "#desicomedy", "#funnyindian"]
            },
            "fashion": {
                "trending": ["#fashion", "#style", "#ootd", "#fashionista", "#trending"],
                "niche": ["#fashionblogger", "#fashioninfluencer", "#styleinspo", "#outfitinspiration"],
                "location": ["#indianfashion", "#indianstyle", "#fashionindia"]
            },
            "general": {
                "trending": ["#reels", "#viral", "#trending", "#explore", "#fyp"],
                "niche": ["#instagood", "#instadaily", "#photooftheday", "#beautiful"],
                "location": ["#india", "#indian", "#desi"]
            }
        }
        
        return hashtag_strategies.get(niche.lower(), hashtag_strategies["general"])

# Example usage and testing
if __name__ == "__main__":
    insights = InstagramAlgorithmInsights()
    
    # Test content analysis
    test_content = {
        'views': 10000,
        'likes': 500,
        'comments': 50,
        'shares': 25,
        'saves': 30,
        'duration': 22,
        'niche': 'fitness',
        'uses_trending_audio': True
    }
    
    analysis = insights.analyze_content_for_virality(test_content)
    print("=== Instagram Algorithm Insights ===")
    print(f"Overall Virality Score: {analysis['overall_virality_score']}/100")
    print(f"Viral Potential: {analysis['viral_potential']}")
    print("\nFactor Scores:")
    for factor, score in analysis['factor_scores'].items():
        print(f"  {factor}: {score:.2f}")
    
    print("\nRecommendations:")
    for rec in analysis['recommendations']:
        print(f"  [{rec.priority.upper()}] {rec.title}: {rec.description}")
    
    print("\nOptimal Posting Times for Fitness:")
    for time in insights.get_optimal_posting_times('fitness'):
        print(f"  {time}")
    
    print("\nHashtag Strategy for Fitness:")
    strategy = insights.get_hashtag_strategy('fitness', 'reel')
    for category, tags in strategy.items():
        print(f"  {category}: {', '.join(tags[:3])}")