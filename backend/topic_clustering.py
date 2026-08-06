"""
Topic/Conversation Clustering Engine
Analyzes captions and content to identify trending topics and conversations
that go beyond simple hashtag tracking. Uses semantic analysis to group similar content.
"""
import os
import sys
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
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

try:
    logging.basicConfig(
        filename="topic_clustering.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

@dataclass
class TopicCluster:
    """Represents a cluster of similar content around a topic"""
    topic_id: str
    topic_name: str
    topic_keywords: List[str]
    topic_category: str  # "entertainment", "lifestyle", "education", "news", etc.
    content_samples: List[str]  # Sample captions/content
    creator_count: int
    total_engagement: int
    avg_velocity: float
    viral_potential: float
    trending_since: datetime
    estimated_lifespan_hours: int
    related_topics: List[str]
    target_audiences: List[str]
    content_opportunities: List[str]

@dataclass
class Conversation:
    """Represents a trending conversation or meme format"""
    conversation_id: str
    conversation_name: str
    conversation_type: str  # "meme", "challenge", "trend", "news", "cultural"
    template_structure: str  # Description of the format
    participation_count: int
    velocity_score: float
    engagement_rate: float
    viral_potential: float
    platform_performance: Dict[str, float]
    optimal_content_types: List[str]
    example_captions: List[str]
    creator_opportunities: List[str]

class TopicClusteringEngine:
    """
    Topic/Conversation Clustering Engine
    Analyzes content to identify trending topics and conversations beyond hashtags
    """
    
    def __init__(self):
        load_dotenv()
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_KEY')
        self.supabase: Optional[Client] = None
        
        if self.supabase_url and self.supabase_key:
            try:
                self.supabase = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client: {e}")
        
        # Predefined topic categories with keywords
        self.topic_categories = {
            'entertainment': ['movie', 'film', 'actor', 'actress', 'web series', 'webseries', 'netflix', 'prime', 'show', 'celebrity', 'bollywood', 'hollywood'],
            'lifestyle': ['routine', 'day in the life', 'morning', 'night', 'daily', 'vlog', 'lifestyle', 'routine', 'habits'],
            'education': ['learn', 'tutorial', 'tips', 'how to', 'guide', 'educational', 'knowledge', 'skill', 'course'],
            'motivation': ['motivation', 'inspire', 'success', 'goals', 'mindset', 'positive', 'grind', 'hustle', 'growth'],
            'relationships': ['relationship', 'love', 'dating', 'friendship', 'family', 'partner', 'couple', 'married'],
            'comedy': ['funny', 'comedy', 'humor', 'laugh', 'joke', 'memes', 'hilarious', 'skit', 'comedian'],
            'fitness': ['workout', 'gym', 'fitness', 'exercise', 'health', 'muscle', 'cardio', 'transformation'],
            'food': ['food', 'recipe', 'cooking', 'eat', 'restaurant', 'foodie', 'tasty', 'delicious', 'meal'],
            'travel': ['travel', 'trip', 'vacation', 'destination', 'explore', 'adventure', 'hotel', 'beach'],
            'fashion': ['fashion', 'style', 'outfit', 'dress', 'look', 'brand', 'trend', 'designer'],
            'beauty': ['makeup', 'beauty', 'skincare', 'hair', 'cosmetics', 'routine', 'glow', 'tutorial'],
            'music': ['music', 'song', 'singer', 'artist', 'audio', 'cover', 'remix', 'album', 'track'],
            'sports': ['cricket', 'football', 'sports', 'game', 'match', 'player', 'team', 'tournament', 'score'],
            'technology': ['tech', 'gadget', 'phone', 'app', 'software', 'AI', 'digital', 'review', 'unboxing'],
            'social_issues': ['social', 'cause', 'awareness', 'movement', 'change', 'rights', 'justice', 'community']
        }
        
        # Common conversation/meme formats
        self.conversation_formats = {
            'before_after': ['before', 'after', 'transformation', 'then vs now', 'vs'],
            'storytime': ['storytime', 'story time', 'true story', 'listen to this', 'you wont believe'],
            'reaction': ['reaction', 'reacting to', 'my reaction', 'thoughts on', 'honest reaction'],
            'tutorial': ['tutorial', 'how to', 'step by step', 'guide', 'learn', 'tips'],
            'challenge': ['challenge', 'try this', 'i tried', 'attempt', '24 hour challenge'],
            'review': ['review', 'honest review', 'my thoughts', 'rating', 'opinion'],
            'day_in_life': ['day in the life', 'daily routine', 'with me', 'follow me around', 'routine'],
            'pov': ['pov', 'point of view', 'imagine', 'when you', 'if you'],
            'relatable': ['relatable', 'when your', 'why does', 'me too', 'same'],
            'trend': ['trending', 'viral', 'fyp', 'foryou', 'trend', 'trending now']
        }
    
    def extract_keywords_from_caption(self, caption: str, max_keywords: int = 10) -> List[str]:
        """
        Extract meaningful keywords from a caption
        """
        if not caption:
            return []
        
        # Convert to lowercase
        caption = caption.lower()
        
        # Remove special characters and URLs
        caption = re.sub(r'http\S+|www\S+', '', caption)
        caption = re.sub(r'[^\w\s]', ' ', caption)
        
        # Remove common stop words
        stop_words = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', 'in', 'to', 'for', 'of', 'with', 'by', 'it', 'this', 'that', 'as', 'be', 'are', 'was', 'were', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'to', 'not', 'no', 'yes', 'or', 'but', 'if', 'then', 'else', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'from', 'up', 'down', 'out', 'off', 'over', 'under', 'again', 'further', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just'}
        
        words = caption.split()
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Count word frequency
        word_counts = Counter(keywords)
        
        # Return top keywords
        return [word for word, count in word_counts.most_common(max_keywords)]
    
    def cluster_topics(self, hours_window: int = 48, min_cluster_size: int = 5) -> List[TopicCluster]:
        """
        Cluster similar content into topics based on captions and keywords
        """
        if not self.supabase:
            logger.warning("Supabase not available for topic clustering")
            return []
        
        try:
            # Get recent reels with captions
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours_window)).isoformat()
            
            reels_res = self.supabase.table('reels') \
                .select('caption, owner_username, view_count, like_count, velocity_score, created_at') \
                .gte('created_at', time_threshold) \
                .not_.is_('caption', 'null') \
                .limit(500) \
                .execute()
            
            reels = reels_res.data or []
            
            # Extract keywords from each caption
            caption_keywords = []
            for reel in reels:
                caption = reel.get('caption', '')
                keywords = self.extract_keywords_from_caption(caption)
                if keywords:
                    caption_keywords.append({
                        'keywords': keywords,
                        'caption': caption[:200],  # Store short snippet
                        'creator': reel.get('owner_username', ''),
                        'engagement': reel.get('view_count', 0) + reel.get('like_count', 0),
                        'velocity': reel.get('velocity_score', 0),
                        'created_at': reel.get('created_at')
                    })
            
            # Cluster keywords into topics
            keyword_cooccurrence = defaultdict(lambda: {'count': 0, 'creators': set(), 'engagement': 0, 'velocities': [], 'captions': []})
            
            for item in caption_keywords:
                keywords = item['keywords']
                creator = item['creator']
                engagement = item['engagement']
                velocity = item['velocity']
                caption = item['caption']
                
                # Add to each keyword's co-occurrence data
                for keyword in keywords:
                    keyword_cooccurrence[keyword]['count'] += 1
                    keyword_cooccurrence[keyword]['creators'].add(creator)
                    keyword_cooccurrence[keyword]['engagement'] += engagement
                    keyword_cooccurrence[keyword]['velocities'].append(velocity)
                    if len(keyword_cooccurrence[keyword]['captions']) < 3:
                        keyword_cooccurrence[keyword]['captions'].append(caption)
            
            # Filter for significant keywords
            significant_keywords = {
                k: v for k, v in keyword_cooccurrence.items()
                if v['count'] >= min_cluster_size
            }
            
            # Group related keywords into topic clusters
            topic_clusters = []
            processed_keywords = set()
            
            for keyword, data in sorted(significant_keywords.items(), key=lambda x: x[1]['count'], reverse=True):
                if keyword in processed_keywords:
                    continue
                
                # Find related keywords (keywords that often appear together)
                related_keywords = [keyword]
                for other_keyword, other_data in significant_keywords.items():
                    if other_keyword != keyword and other_keyword not in processed_keywords:
                        # Check if they have overlapping creators (simplified similarity)
                        overlap = len(data['creators'] & other_data['creators'])
                        if overlap >= min(2, len(data['creators']) // 2):
                            related_keywords.append(other_keyword)
                            processed_keywords.add(other_keyword)
                
                processed_keywords.add(keyword)
                
                # Determine topic category
                topic_category = self._determine_topic_category(related_keywords)
                
                # Create topic cluster
                topic_id = f"topic_{len(topic_clusters)}_{keyword[:10]}"
                topic_name = f"{keyword} {' '.join(related_keywords[1:3]) if len(related_keywords) > 1 else ''}"
                
                # Aggregate data for the cluster
                total_creators = sum(significant_keywords[k]['creators'].__len__() for k in related_keywords)
                total_engagement = sum(significant_keywords[k]['engagement'] for k in related_keywords)
                all_velocities = []
                all_captions = []
                
                for k in related_keywords:
                    all_velocities.extend(significant_keywords[k]['velocities'])
                    all_captions.extend(significant_keywords[k]['captions'])
                
                avg_velocity = sum(all_velocities) / len(all_velocities) if all_velocities else 0
                viral_potential = min(100, avg_velocity * 2)
                
                # Content samples
                content_samples = all_captions[:5]
                
                # Related topics (simplified)
                related_topics = []
                for other_keyword in list(significant_keywords.keys())[:5]:
                    if other_keyword not in related_keywords:
                        related_topics.append(other_keyword)
                
                # Target audiences based on category
                target_audiences = self._get_target_audiences_for_category(topic_category)
                
                # Content opportunities
                content_opportunities = self._get_content_opportunities_for_category(topic_category)
                
                topic_clusters.append(TopicCluster(
                    topic_id=topic_id,
                    topic_name=topic_name.strip(),
                    topic_keywords=related_keywords,
                    topic_category=topic_category,
                    content_samples=content_samples,
                    creator_count=total_creators,
                    total_engagement=total_engagement,
                    avg_velocity=avg_velocity,
                    viral_potential=viral_potential,
                    trending_since=datetime.now(timezone.utc) - timedelta(hours=hours_window),
                    estimated_lifespan_hours=self._estimate_topic_lifespan(avg_velocity, total_creators),
                    related_topics=related_topics[:3],
                    target_audiences=target_audiences,
                    content_opportunities=content_opportunities
                ))
            
            # Sort by viral potential
            topic_clusters.sort(key=lambda t: t.viral_potential, reverse=True)
            
            return topic_clusters[:20]  # Return top 20 topics
            
        except Exception as e:
            logger.error(f"Error clustering topics: {e}")
            return []
    
    def detect_conversations(self, hours_window: int = 48) -> List[Conversation]:
        """
        Detect trending conversation formats and meme structures
        """
        if not self.supabase:
            logger.warning("Supabase not available for conversation detection")
            return []
        
        try:
            # Get recent reels with captions
            time_threshold = (datetime.now(timezone.utc) - timedelta(hours=hours_window)).isoformat()
            
            reels_res = self.supabase.table('reels') \
                .select('caption, owner_username, view_count, like_count, velocity_score, created_at') \
                .gte('created_at', time_threshold) \
                .not_.is_('caption', 'null') \
                .limit(500) \
                .execute()
            
            reels = reels_res.data or []
            
            # Detect conversation formats in captions
            format_counts = defaultdict(lambda: {
                'count': 0,
                'creators': set(),
                'engagement': 0,
                'velocities': [],
                'captions': []
            })
            
            for reel in reels:
                caption = reel.get('caption', '').lower()
                creator = reel.get('owner_username', '')
                engagement = reel.get('view_count', 0) + reel.get('like_count', 0)
                velocity = reel.get('velocity_score', 0)
                
                # Check for conversation format keywords
                for format_name, keywords in self.conversation_formats.items():
                    if any(keyword in caption for keyword in keywords):
                        format_counts[format_name]['count'] += 1
                        format_counts[format_name]['creators'].add(creator)
                        format_counts[format_name]['engagement'] += engagement
                        format_counts[format_name]['velocities'].append(velocity)
                        if len(format_counts[format_name]['captions']) < 5:
                            format_counts[format_name]['captions'].append(reel.get('caption', '')[:200])
            
            # Create conversation objects
            conversations = []
            
            for format_name, data in format_counts.items():
                if data['count'] < 3:  # Skip formats with low participation
                    continue
                
                avg_velocity = sum(data['velocities']) / len(data['velocities']) if data['velocities'] else 0
                engagement_rate = data['engagement'] / data['count'] if data['count'] > 0 else 0
                viral_potential = min(100, avg_velocity * 2 + engagement_rate / 1000)
                
                # Determine conversation type
                conversation_type = self._determine_conversation_type(format_name)
                
                # Platform performance (simplified)
                platform_performance = {
                    'instagram': min(1.0, viral_potential / 100),
                    'youtube_shorts': min(1.0, viral_potential / 120),
                    'tiktok': min(1.0, viral_potential / 150)
                }
                
                # Optimal content types
                optimal_content_types = self._get_optimal_content_types_for_format(format_name)
                
                # Creator opportunities
                creator_opportunities = self._get_creator_opportunities_for_format(format_name)
                
                conversations.append(Conversation(
                    conversation_id=f"conv_{format_name}",
                    conversation_name=format_name.replace('_', ' ').title(),
                    conversation_type=conversation_type,
                    template_structure=self._get_template_structure(format_name),
                    participation_count=len(data['creators']),
                    velocity_score=avg_velocity,
                    engagement_rate=engagement_rate,
                    viral_potential=viral_potential,
                    platform_performance=platform_performance,
                    optimal_content_types=optimal_content_types,
                    example_captions=data['captions'],
                    creator_opportunities=creator_opportunities
                ))
            
            # Sort by viral potential
            conversations.sort(key=lambda c: c.viral_potential, reverse=True)
            
            return conversations[:10]  # Return top 10 conversations
            
        except Exception as e:
            logger.error(f"Error detecting conversations: {e}")
            return []
    
    def _determine_topic_category(self, keywords: List[str]) -> str:
        """Determine which category a topic belongs to"""
        keyword_text = ' '.join(keywords).lower()
        
        for category, category_keywords in self.topic_categories.items():
            if any(keyword in keyword_text for keyword in category_keywords):
                return category
        
        return 'general'
    
    def _get_target_audiences_for_category(self, category: str) -> List[str]:
        """Get target audiences for a topic category"""
        audiences = {
            'entertainment': ['movie buffs', 'celebrity followers', 'entertainment seekers', 'pop culture enthusiasts'],
            'lifestyle': ['lifestyle enthusiasts', 'daily routine viewers', 'self-improvement seekers', 'vlog consumers'],
            'education': ['learners', 'students', 'skill seekers', 'knowledge enthusiasts'],
            'motivation': ['self-improvement seekers', 'entrepreneurs', 'career-focused individuals', 'personal growth enthusiasts'],
            'relationships': ['relationship advice seekers', 'couples', 'single individuals', 'family-oriented users'],
            'comedy': ['entertainment seekers', 'gen z', 'millennials', 'viral content consumers'],
            'fitness': ['fitness enthusiasts', 'gym-goers', 'health-conscious individuals', 'beginners'],
            'food': ['home cooks', 'foodies', 'restaurant-goers', 'cooking enthusiasts'],
            'travel': ['travel enthusiasts', 'adventure seekers', 'vacation planners', 'digital nomads'],
            'fashion': ['fashion enthusiasts', 'style-conscious individuals', 'brand followers', 'trend adopters'],
            'beauty': ['beauty enthusiasts', 'skincare conscious', 'makeup lovers', 'transformation seekers'],
            'music': ['music lovers', 'artists', 'music enthusiasts', 'cover artists'],
            'sports': ['sports fans', 'athletes', 'fitness enthusiasts', 'team supporters'],
            'technology': ['tech enthusiasts', 'gadget lovers', 'early adopters', 'digital natives'],
            'social_issues': ['socially conscious users', 'activists', 'community builders', 'awareness seekers'],
            'general': ['general audience', 'viral content consumers', 'entertainment seekers', 'social media users']
        }
        
        return audiences.get(category, audiences['general'])
    
    def _get_content_opportunities_for_category(self, category: str) -> List[str]:
        """Get content creation opportunities for a category"""
        opportunities = {
            'entertainment': ['movie reviews', 'celebrity reactions', 'web series discussions', 'entertainment news'],
            'lifestyle': ['daily routines', 'morning/night routines', 'lifestyle tips', 'habit sharing'],
            'education': ['tutorial videos', 'how-to guides', 'tips and tricks', 'educational content'],
            'motivation': ['motivational speeches', 'success stories', 'mindset advice', 'goal setting'],
            'relationships': ['relationship advice', 'couple content', 'friendship dynamics', 'family content'],
            'comedy': ['skits', 'relatable humor', 'viral trends', 'memes'],
            'fitness': ['workout routines', 'exercise tutorials', 'fitness challenges', 'transformation content'],
            'food': ['recipe tutorials', 'cooking tips', 'food reviews', 'meal prep'],
            'travel': ['destination guides', 'travel tips', 'vlog content', 'adventure content'],
            'fashion': ['outfit showcases', 'styling tips', 'brand reviews', 'lookbook creation'],
            'beauty': ['makeup tutorials', 'skincare routines', 'product reviews', 'transformations'],
            'music': ['music covers', 'audio recommendations', 'artist features', 'music challenges'],
            'sports': ['sports analysis', 'match reactions', 'athlete features', 'team support'],
            'technology': ['tech reviews', 'unboxing videos', 'app tutorials', 'gadget comparisons'],
            'social_issues': ['awareness content', 'educational videos', 'community building', 'discussion starters'],
            'general': ['viral trend participation', 'storytelling', 'behind-the-scenes', 'entertainment']
        }
        
        return opportunities.get(category, opportunities['general'])
    
    def _determine_conversation_type(self, format_name: str) -> str:
        """Determine conversation type based on format"""
        if format_name in ['before_after', 'challenge']:
            return 'challenge'
        elif format_name in ['storytime', 'reaction', 'review']:
            return 'narrative'
        elif format_name in ['tutorial']:
            return 'educational'
        elif format_name in ['day_in_life', 'pov', 'relatable']:
            return 'lifestyle'
        elif format_name in ['trend']:
            return 'trend'
        else:
            return 'general'
    
    def _get_template_structure(self, format_name: str) -> str:
        """Get template structure description for a format"""
        structures = {
            'before_after': 'Show transformation from one state to another with clear before/after shots',
            'storytime': 'Share a personal story or experience with narrative structure',
            'reaction': 'React to content with genuine emotional response and commentary',
            'tutorial': 'Step-by-step guide teaching a skill or process',
            'challenge': 'Attempt a specific challenge with clear start and end points',
            'review': 'Honest assessment and opinion on a product, service, or content',
            'day_in_life': 'Document daily activities and routine in vlog format',
            'pov': 'Create content from a specific perspective or point of view',
            'relatable': 'Share relatable situations that resonate with audience experiences',
            'trend': 'Participate in or comment on current viral trends'
        }
        
        return structures.get(format_name, 'General content format')
    
    def _get_optimal_content_types_for_format(self, format_name: str) -> List[str]:
        """Get optimal content types for a conversation format"""
        types = {
            'before_after': ['transformation videos', 'progress content', 'comparison content'],
            'storytime': ['narrative videos', 'storytelling', 'personal experiences'],
            'reaction': ['reaction videos', 'commentary', 'thoughts on content'],
            'tutorial': ['tutorial videos', 'how-to guides', 'educational content'],
            'challenge': ['challenge videos', 'attempt content', '24-hour challenges'],
            'review': ['review videos', 'opinion content', 'honest assessments'],
            'day_in_life': ['vlog content', 'routine videos', 'daily documentation'],
            'pov': ['perspective content', 'scenario videos', 'imagine content'],
            'relatable': ['relatable content', 'humor', 'viral scenarios'],
            'trend': ['trend participation', 'viral content', 'trend commentary']
        }
        
        return types.get(format_name, ['general content'])
    
    def _get_creator_opportunities_for_format(self, format_name: str) -> List[str]:
        """Get creator opportunities for a conversation format"""
        opportunities = {
            'before_after': ['fitness transformations', 'home makeovers', 'skill progress', 'style evolution'],
            'storytime': ['personal stories', 'experiences', 'lessons learned', 'funny anecdotes'],
            'reaction': ['react to trending content', 'review products', 'comment on news', 'share opinions'],
            'tutorial': ['teach skills', 'share knowledge', 'create guides', 'help others learn'],
            'challenge': ['attempt viral challenges', 'create original challenges', 'document attempts', 'share results'],
            'review': ['review products', 'share opinions', 'rate services', 'provide feedback'],
            'day_in_life': ['document routines', 'share lifestyle', 'behind-the-scenes', 'daily vlogs'],
            'pov': ['create scenarios', 'share perspectives', 'imagine situations', 'roleplay content'],
            'relatable': ['share relatable moments', 'create humor', 'comment on common experiences', 'viral situations'],
            'trend': ['participate in trends', 'comment on trends', 'create trend variations', 'trend analysis']
        }
        
        return opportunities.get(format_name, ['create general content'])
    
    def _estimate_topic_lifespan(self, avg_velocity: float, creator_count: int) -> int:
        """Estimate how long a topic will remain trending"""
        if avg_velocity > 50 and creator_count > 100:
            return 168  # 7 days
        elif avg_velocity > 30 and creator_count > 50:
            return 120  # 5 days
        elif avg_velocity > 20:
            return 72  # 3 days
        else:
            return 48  # 2 days

# Example usage and testing
if __name__ == "__main__":
    engine = TopicClusteringEngine()
    
    print("=== Topic/Conversation Clustering Engine ===")
    
    # Cluster topics
    topics = engine.cluster_topics(hours_window=48, min_cluster_size=3)
    print(f"\nTopic Clusters: {len(topics)}")
    
    for topic in topics[:5]:
        print(f"\n📌 {topic.topic_name}")
        print(f"   Category: {topic.topic_category}")
        print(f"   Creators: {topic.creator_count}")
        print(f"   Viral Potential: {topic.viral_potential:.1f}/100")
        print(f"   Keywords: {', '.join(topic.topic_keywords[:5])}")
        print(f"   Opportunities: {', '.join(topic.content_opportunities[:3])}")
    
    # Detect conversations
    conversations = engine.detect_conversations(hours_window=48)
    print(f"\n\nConversations Detected: {len(conversations)}")
    
    for conv in conversations[:5]:
        print(f"\n💬 {conv.conversation_name}")
        print(f"   Type: {conv.conversation_type}")
        print(f"   Participation: {conv.participation_count}")
        print(f"   Viral Potential: {conv.viral_potential:.1f}/100")
        print(f"   Opportunities: {', '.join(conv.creator_opportunities[:3])}")