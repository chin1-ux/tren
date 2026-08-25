"""
AI Content Generation System
Generates captions, content ideas, hooks, and scripts based on trending topics and creator preferences.
"""
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
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
        filename="content_generator.log",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
except Exception:
    pass

logger = logging.getLogger(__name__)

@dataclass
class GeneratedCaption:
    """Represents an AI-generated caption"""
    caption: str
    hashtags: List[str]
    tone: str  # "professional", "casual", "funny", "inspiring"
    target_audience: str
    cta: str  # Call to action
    emoji_usage: str  # "minimal", "moderate", "heavy"

@dataclass
class ContentIdea:
    """Represents a generated content idea"""
    title: str
    description: str
    content_type: str  # "reel", "story", "post", "carousel"
    niche: str
    difficulty: str  # "easy", "medium", "hard"
    estimated_engagement: str  # "low", "medium", "high"
    required_resources: List[str]
    script_outline: List[str]
    suggested_hashtags: List[str]

@dataclass
class HookSuggestion:
    """Represents a suggested hook for content"""
    hook_text: str
    hook_type: str  # "question", "statement", "shock", "curiosity"
    estimated_retention: float  # 0-100
    best_for_content: List[str]

class AIContentGenerator:
    """
    AI Content Generation System
    Generates captions, ideas, hooks, and scripts based on trends and creator data
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
        
        # India-specific caption templates
        self.india_caption_templates = {
            'hindi': [
                "{content} kya baat hai! ✨ Dekhiye ye video.",
                "{content} bohot mast hai! 🔥 zaroor try karein.",
                "POV: {content} dekh kar shock ho gaye! 😱",
                "{content} ka magic dekhiye nahi to miss karoge! 💥",
                "Indian style mein {content} - kaisa laga? 🇮🇳"
            ],
            'tamil': [
                "{content} super ah irukku! ✨ Paathu paarunga.",
                "{content} vera level! 🔥 Kandippa try pannunga.",
                "POV: {content} paathu shock aagalam! 😱",
                "{content} magic-a paathu miss pannatha! 💥",
                "Tamil style-la {content} - eppadi irukku? 🇮🇳"
            ],
            'telugu': [
                "{content} chala bagundi! ✨ Chudandi.",
                "{content} marma! 🔖 Saradaga try cheyandi.",
                "POV: {content} chusi shock ayyaru! 😱",
                "{content} magic chusi miss cheyyakandi! 💥",
                "Telugu style lo {content} - ela undi? 🇮🇳"
            ],
            'punjabi': [
                "{content} kamal hai! ✨ Dekho ji.",
                "{content} tez hai! 🔥 Jaroor try karo.",
                "POV: {content} dekh ke shock ho gaye! 😱",
                "{content} magic dekho miss na karo! 💥",
                "Punjabi style mein {content} - kaisa laga? 🇮🇳"
            ]
        }
        
        # India-specific content ideas
        self.india_content_ideas = {
            'festival': [
                {
                    'title': 'Diwali Special Reel',
                    'description': 'Create a Diwali celebration reel with traditional decorations and lights',
                    'content_type': 'reel',
                    'niche': 'lifestyle',
                    'difficulty': 'medium',
                    'script_outline': ['Show diya lighting', 'Rangoli making', 'Family celebration', 'Fireworks']
                },
                {
                    'title': 'Holi Colors Celebration',
                    'description': 'Vibrant Holi celebration content with colors and music',
                    'content_type': 'reel',
                    'niche': 'entertainment',
                    'difficulty': 'easy',
                    'script_outline': ['Color application', 'Dance to trending song', 'Friends celebration', 'Before/after']
                },
                {
                    'title': 'Eid Special Content',
                    'description': 'Eid celebration with traditional food and family time',
                    'content_type': 'reel',
                    'niche': 'food',
                    'difficulty': 'medium',
                    'script_outline': ['Food preparation', 'Family gathering', 'Traditional dress', 'Celebration moments']
                }
            ],
            'regional': [
                {
                    'title': 'South Indian Recipe',
                    'description': 'Traditional South Indian dish preparation',
                    'content_type': 'reel',
                    'niche': 'food',
                    'difficulty': 'medium',
                    'script_outline': ['Ingredients', 'Cooking process', 'Final dish', 'Tasting reaction']
                },
                {
                    'title': 'Punjabi Bhangra Dance',
                    'description': 'Energetic Bhangra dance performance',
                    'content_type': 'reel',
                    'niche': 'entertainment',
                    'difficulty': 'hard',
                    'script_outline': ['Traditional steps', 'Energy buildup', 'Group dance', 'Finale pose']
                },
                {
                    'title': 'Marathi Festival Tradition',
                    'description': 'Showcase Marathi cultural traditions',
                    'content_type': 'carousel',
                    'niche': 'culture',
                    'difficulty': 'medium',
                    'script_outline': ['Festival history', 'Traditional attire', 'Rituals', 'Modern adaptation']
                }
            ]
        }
        
        # India-specific cultural events
        self.india_cultural_events = {
            'diwali': {
                'name': 'Diwali',
                'date': 'Variable (Oct-Nov)',
                'content_themes': ['lights', 'diyas', 'rangoli', 'sweets', 'fireworks', 'family'],
                'hashtags': ['#Diwali2024', '#FestivalOfLights', '#DiwaliVibes', '#IndianFestival'],
                'trending_hashtags': ['#diwalireels', '#diwalicrackers', '#diwalidecoration']
            },
            'holi': {
                'name': 'Holi',
                'date': 'Variable (March)',
                'content_themes': ['colors', 'water', 'dance', 'music', 'friends', 'celebration'],
                'hashtags': ['#Holi2024', '#FestivalOfColors', '#HoliVibes', '#RangHoli'],
                'trending_hashtags': ['#holireels', '#colors', '#holicelebration']
            },
            'eid': {
                'name': 'Eid',
                'date': 'Variable (Variable)',
                'content_themes': ['prayer', 'food', 'family', 'tradition', 'celebration', 'charity'],
                'hashtags': ['#Eid2024', '#EidMubarak', '#EidVibes', '#Festival'],
                'trending_hashtags': ['#eidreels', '#eidcelebration', '#eidspecial']
            },
            'navratri': {
                'name': 'Navratri',
                'date': 'Variable (Sept-Oct)',
                'content_themes': ['dance', 'garba', 'devotion', 'traditional', 'nine_nights'],
                'hashtags': ['#Navratri2024', '#Garba', '#NavratriVibes', '#NineNights'],
                'trending_hashtags': ['#garbareels', '#navratridance', '#dandiya']
            },
            'christmas': {
                'name': 'Christmas',
                'date': 'December 25',
                'content_themes': ['decorations', 'carols', 'family', 'gifts', 'celebration'],
                'hashtags': ['#Christmas2024', '#Xmas', '#ChristmasVibes', '#FestivalSeason'],
                'trending_hashtags': ['#christmasreels', '#xmasvibes', '#holidayseason']
            },
            'independence_day': {
                'name': 'Independence Day',
                'date': 'August 15',
                'content_themes': ['patriotism', 'tricolor', 'freedom', 'celebration', 'pride'],
                'hashtags': ['#IndependenceDay2024', '#India75', '#JaiHind', '#AzadiKaAmritMahotsav'],
                'trending_hashtags': ['#independencedayreels', '#indianpride', '#15august']
            }
        }
        
        # Caption templates
        self.caption_templates = {
            'casual': [
                "Just wanted to share this with you all! {content} ✨",
                "Can we talk about {content} for a sec? Because... wow 🤯",
                "POV: You're scrolling and see {content} 💀",
                "Not me getting obsessed with {content} again 🫠",
                "If you know, you know... {content} 😉"
            ],
            'professional': [
                "Here's what you need to know about {content}. Let's dive in 👇",
                "The key to success with {content} is simpler than you think.",
                "Expert tip: {content} can transform your approach.",
                "Breaking down {content} step by step for you.",
                "Professional insight on {content} that most people miss."
            ],
            'funny': [
                "Me trying to explain {content} to my friends like 💀",
                "When you finally understand {content} but nobody else does 🤡",
                "{content} be like: exists me: trauma",
                "My relationship with {content} is complicated 🫠",
                "POV: {content} took over your life without permission"
            ],
            'inspiring': [
                "This is your sign to try {content} today ✨",
                "Remember: {content} is the first step to your dreams.",
                "Don't wait for {content} to come to you. Go get it.",
                "Your journey with {content} starts now. Believe that.",
                "Every expert in {content} was once a beginner. Keep going."
            ]
        }
        
        # Content idea templates
        self.content_ideas = {
            'fitness': [
                {
                    'title': '30-Day Challenge Transformation',
                    'description': 'Document your fitness journey over 30 days with daily updates',
                    'content_type': 'reel',
                    'difficulty': 'medium',
                    'script_outline': ['Day 1 introduction', 'Weekly progress updates', 'Final transformation reveal']
                },
                {
                    'title': 'Beginner-Friendly Workout Tutorial',
                    'description': 'Simple workout routine for beginners with clear instructions',
                    'content_type': 'reel',
                    'difficulty': 'easy',
                    'script_outline': ['Introduction', 'Exercise demonstrations', 'Tips and modifications']
                }
            ],
            'food': [
                {
                    'title': 'Quick Recipe Under 5 Minutes',
                    'description': 'Show how to make a delicious recipe in under 5 minutes',
                    'content_type': 'reel',
                    'difficulty': 'easy',
                    'script_outline': ['Ingredients reveal', 'Step-by-step cooking', 'Final presentation']
                },
                {
                    'title': 'Restaurant Review & Food Tour',
                    'description': 'Review a popular restaurant with food highlights',
                    'content_type': 'reel',
                    'difficulty': 'medium',
                    'script_outline': ['Restaurant intro', 'Food tasting', 'Final verdict']
                }
            ],
            'comedy': [
                {
                    'title': 'Relatable Daily Struggle',
                    'description': 'Share a funny, relatable situation everyone experiences',
                    'content_type': 'reel',
                    'difficulty': 'easy',
                    'script_outline': ['Setup the situation', 'Exaggerate the struggle', 'Relatable punchline']
                },
                {
                    'title': 'Trend Parody',
                    'description': 'Create a funny parody of a current trend',
                    'content_type': 'reel',
                    'difficulty': 'medium',
                    'script_outline': ['Trend setup', 'Comedy twist', 'Reaction']
                }
            ],
            'fashion': [
                {
                    'title': 'Outfit of the Day Reveal',
                    'description': 'Showcase your outfit with style tips',
                    'content_type': 'reel',
                    'difficulty': 'easy',
                    'script_outline': ['Outfit reveal', 'Styling tips', 'Where to buy']
                },
                {
                    'title': 'Budget Fashion Haul',
                    'description': 'Show affordable fashion finds and styling options',
                    'content_type': 'reel',
                    'difficulty': 'medium',
                    'script_outline': ['Budget reveal', 'Item showcase', 'Styling options']
                }
            ]
        }
        
        # Hook templates
        self.hook_templates = {
            'question': [
                "Wait, have you tried {topic}?",
                "Did you know this about {topic}?",
                "Why does nobody talk about {topic}?",
                "Can we talk about {topic} for a second?",
                "What if I told you {topic} could change everything?"
            ],
            'statement': [
                "This is why {topic} matters.",
                "Stop ignoring {topic}. Here's why.",
                "The truth about {topic} nobody tells you.",
                "{topic} is more important than you think.",
                "I finally figured out {topic}. Here's how."
            ],
            'shock': [
                "You're doing {topic} completely wrong.",
                "Nobody told you this about {topic}.",
                "This {topic} hack changed my life.",
                "Why {topic} is actually dangerous.",
                "The dark side of {topic} nobody mentions."
            ],
            'curiosity': [
                "You won't believe what happened with {topic}.",
                "The secret behind {topic} revealed.",
                "What happens when you try {topic}...",
                "The unexpected truth about {topic}.",
                "I discovered something wild about {topic}."
            ]
        }
    
    def generate_india_caption(self, trend_name: str, language: str = "hindi", tone: str = "casual") -> GeneratedCaption:
        """
        Generate India-specific caption in regional language
        """
        # Select template based on language
        templates = self.india_caption_templates.get(language, self.india_caption_templates['hindi'])
        template = templates[hash(trend_name) % len(templates)]
        
        # Generate caption
        caption = template.format(content=trend_name)
        
        # Generate hashtags (mix of English and regional)
        hashtags = self._generate_india_hashtags(trend_name, language)
        
        # Generate CTA
        cta = self._generate_india_cta(language)
        
        return GeneratedCaption(
            caption=caption,
            hashtags=hashtags,
            tone=tone,
            target_audience=f"india_{language}",
            cta=cta,
            emoji_usage="moderate"
        )
    
    def generate_india_content_ideas(self, event_type: str = "festival", count: int = 3) -> List[ContentIdea]:
        """
        Generate India-specific content ideas for cultural events
        """
        ideas = self.india_content_ideas.get(event_type, self.india_content_ideas['festival'])
        
        generated_ideas = []
        for i, idea_template in enumerate(ideas[:count]):
            idea = ContentIdea(
                title=idea_template['title'],
                description=idea_template['description'],
                content_type=idea_template['content_type'],
                niche=idea_template['niche'],
                difficulty=idea_template['difficulty'],
                estimated_engagement="high",
                required_resources=["phone", "lighting", "traditional elements"],
                script_outline=idea_template['script_outline'],
                suggested_hashtags=self._generate_event_hashtags(event_type)
            )
            generated_ideas.append(idea)
        
        return generated_ideas
    
    def get_cultural_event_content(self, event_name: str) -> Dict:
        """
        Get content suggestions for a specific cultural event
        """
        event_data = self.india_cultural_events.get(event_name.lower())
        
        if not event_data:
            return {
                'error': f'Event {event_name} not found',
                'available_events': list(self.india_cultural_events.keys())
            }
        
        return {
            'event_name': event_data['name'],
            'date': event_data['date'],
            'content_themes': event_data['content_themes'],
            'hashtags': event_data['hashtags'],
            'trending_hashtags': event_data['trending_hashtags'],
            'content_ideas': self.generate_india_content_ideas('festival', 3),
            'caption_templates': [
                f"Celebrating {event_data['name']} with {theme}! ✨"
                for theme in event_data['content_themes'][:3]
            ]
        }
    
    def _generate_india_hashtags(self, trend_name: str, language: str) -> List[str]:
        """Generate India-specific hashtags"""
        base_hashtags = self._generate_hashtags(trend_name, 'general')
        
        # Add regional hashtags
        regional_tags = {
            'hindi': ['#hindireels', '#indiancreators', '#trendingindia'],
            'tamil': ['#tamilreels', '#southindian', '#tamiltrending'],
            'telugu': ['#telugureels', '#southindian', '#telugutrending'],
            'punjabi': ['#punjabireels', '#northindian', '#punjabitrending']
        }
        
        return base_hashtags + regional_tags.get(language, regional_tags['hindi'])
    
    def _generate_event_hashtags(self, event_type: str) -> List[str]:
        """Generate hashtags for cultural events"""
        if event_type == 'festival':
            return ['#IndianFestival', '#CulturalCelebration', '#IndiaVibes', '#Traditional']
        elif event_type == 'regional':
            return ['#RegionalContent', '#LocalCulture', '#IndianTradition', '#DesiVibes']
        else:
            return ['#India', '#Desi', '#IndianContent', '#Cultural']
    
    def _generate_india_cta(self, language: str) -> str:
        """Generate India-specific call to action"""
        ctas = {
            'hindi': "Follow karo for more! 🔔",
            'tamil': "Follow pannunga for more! 🔔",
            'telugu': "Follow cheyyandi for more! 🔔",
            'punjabi': "Follow karo for more! 🔔"
        }
        return ctas.get(language, "Follow for more! 🔔")
    
    def generate_caption(self, trend_name: str, tone: str = "casual", niche: str = "general") -> GeneratedCaption:
        """
        Generate a caption for a specific trend or topic
        """
        # Select template based on tone
        templates = self.caption_templates.get(tone, self.caption_templates['casual'])
        template = templates[hash(trend_name) % len(templates)]
        
        # Generate caption
        caption = template.format(content=trend_name)
        
        # Generate hashtags
        hashtags = self._generate_hashtags(trend_name, niche)
        
        # Generate CTA
        cta = self._generate_cta(tone)
        
        return GeneratedCaption(
            caption=caption,
            hashtags=hashtags,
            tone=tone,
            target_audience=niche,
            cta=cta,
            emoji_usage="moderate"
        )
    
    def generate_content_ideas(self, niche: str, count: int = 5) -> List[ContentIdea]:
        """
        Generate content ideas for a specific niche
        """
        ideas = self.content_ideas.get(niche, self.content_ideas.get('fitness', []))
        
        generated_ideas = []
        for i, idea_template in enumerate(ideas[:count]):
            # Add variety
            idea = ContentIdea(
                title=idea_template['title'],
                description=idea_template['description'],
                content_type=idea_template['content_type'],
                niche=niche,
                difficulty=idea_template['difficulty'],
                estimated_engagement="high" if idea_template['difficulty'] == "easy" else "medium",
                required_resources=["phone", "lighting", "editing app"],
                script_outline=idea_template['script_outline'],
                suggested_hashtags=self._generate_hashtags(niche, niche)
            )
            generated_ideas.append(idea)
        
        return generated_ideas
    
    def generate_hooks(self, topic: str, count: int = 5) -> List[HookSuggestion]:
        """
        Generate hook suggestions for a specific topic
        """
        hooks = []
        
        for hook_type, templates in self.hook_templates.items():
            template = templates[hash(topic + hook_type) % len(templates)]
            hook_text = template.format(topic=topic)
            
            # Estimate retention based on hook type
            retention_scores = {
                'question': 75,
                'statement': 70,
                'shock': 85,
                'curiosity': 80
            }
            
            # Best content types for each hook
            best_for = {
                'question': ['reel', 'story'],
                'statement': ['reel', 'post'],
                'shock': ['reel', 'story'],
                'curiosity': ['reel', 'carousel']
            }
            
            hooks.append(HookSuggestion(
                hook_text=hook_text,
                hook_type=hook_type,
                estimated_retention=retention_scores.get(hook_type, 70),
                best_for_content=best_for.get(hook_type, ['reel'])
            ))
        
        return hooks[:count]
    
    def generate_script_outline(self, content_type: str, topic: str, duration_seconds: int = 30) -> List[str]:
        """
        Generate a script outline for content
        """
        if duration_seconds <= 15:
            # Short form - 3 parts
            return [
                f"0-3s: Hook about {topic}",
                f"3-12s: Main content about {topic}",
                f"12-15s: CTA and outro"
            ]
        elif duration_seconds <= 30:
            # Medium form - 5 parts
            return [
                f"0-3s: Strong hook about {topic}",
                f"3-10s: Introduction to {topic}",
                f"10-20s: Main content/deep dive",
                f"20-27s: Key takeaway or insight",
                f"27-30s: CTA and engagement prompt"
            ]
        else:
            # Long form - 7 parts
            return [
                f"0-3s: Attention-grabbing hook",
                f"3-8s: Introduction to {topic}",
                f"8-20s: Main content with details",
                f"20-30s: Expert tips or insights",
                f"30-40s: Practical application",
                f"40-50s: Common mistakes to avoid",
                f"50-60s: CTA and next steps"
            ]
    
    def _generate_hashtags(self, topic: str, niche: str) -> List[str]:
        """Generate relevant hashtags"""
        base_hashtags = {
            'fitness': ['#fitness', '#workout', '#gym', '#fitnessmotivation', '#health'],
            'food': ['#food', '#foodie', '#recipe', '#cooking', '#foodlover'],
            'comedy': ['#funny', '#comedy', '#humor', '#viral', '#relatable'],
            'fashion': ['#fashion', '#style', '#ootd', '#fashionista', '#outfit'],
            'travel': ['#travel', '#vacation', '#explore', '#adventure', '#travelgram'],
            'beauty': ['#beauty', '#makeup', '#skincare', '#beautytips', '#glow'],
            'motivation': ['#motivation', '#inspire', '#success', '#mindset', '#goals'],
            'general': ['#viral', '#trending', '#fyp', '#foryou', '#explore']
        }
        
        hashtags = base_hashtags.get(niche, base_hashtags['general'])
        
        # Add topic-specific hashtag
        topic_hashtag = f"#{topic.replace(' ', '').replace('-', '')}"
        if len(topic_hashtag) > 2:
            hashtags.insert(0, topic_hashtag)
        
        return hashtags[:10]
    
    def _generate_cta(self, tone: str) -> str:
        """Generate a call to action based on tone"""
        ctas = {
            'casual': ["Drop a 💕 if you agree!", "Save this for later 🔖", "Share with someone who needs this"],
            'professional': ["Save this post for reference", "Follow for more expert tips", "Share with your network"],
            'funny': ["Tag someone who needs to see this 😂", "Save for when you need a laugh", "Share with your drama friends"],
            'inspiring': ["Save this as your daily reminder ✨", "Share to inspire someone else", "Follow for daily motivation"]
        }
        
        return ctas.get(tone, ctas['casual'])[hash(tone) % len(ctas.get(tone, ctas['casual']))]

# Example usage and testing
if __name__ == "__main__":
    generator = AIContentGenerator()
    
    print("=== AI Content Generation System ===")
    
    # Generate caption
    caption = generator.generate_caption("Dance Challenge", tone="casual", niche="fitness")
    print(f"\nGenerated Caption:")
    print(f"  {caption.caption}")
    print(f"  Hashtags: {', '.join(caption.hashtags)}")
    print(f"  CTA: {caption.cta}")
    
    # Generate content ideas
    ideas = generator.generate_content_ideas("fitness", count=3)
    print(f"\nContent Ideas: {len(ideas)}")
    for idea in ideas:
        print(f"  {idea.title}")
        print(f"    {idea.description}")
        print(f"    Difficulty: {idea.difficulty}")
    
    # Generate hooks
    hooks = generator.generate_hooks("Workout Routine", count=4)
    print(f"\nHook Suggestions: {len(hooks)}")
    for hook in hooks:
        print(f"  [{hook.hook_type.upper()}] {hook.hook_text}")
        print(f"    Retention: {hook.estimated_retention}%")
    
    # Generate script outline
    script = generator.generate_script_outline("reel", "Morning Routine", 30)
    print(f"\nScript Outline (30s):")
    for line in script:
        print(f"  {line}")