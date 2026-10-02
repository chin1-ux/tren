"""
Cultural Event Calendar & Festive Viral Radar
India-specific cultural events, 4-phase viral curve prediction, and niche-specific reel concept generation.
"""
import os
import sys
import json
import random
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv

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
logger = logging.getLogger(__name__)

try:
    from llm import call_llm
except ImportError:
    try:
        from backend.llm import call_llm
    except ImportError:
        try:
            from .llm import call_llm
        except ImportError:
            call_llm = None

# 24-hour server-side cache for generated festive ideas
_FESTIVE_IDEAS_CACHE: Dict[str, Dict] = {}
_FESTIVE_CACHE_TTL_SECONDS: int = 86400  # 24 hours


def calculate_wave_phase(event_date_str: str) -> Dict:
    """
    Calculate the 4-Phase Festive Viral Curve based on distance to the event date.
    
    Phases:
      1. PRE_RADAR (> 14 days out): Early scouting & prop prep
      2. PRE_FESTIVE_SURGE (5 - 14 days out): Golden Filming Window (high reach, low saturation)
      3. PEAK_HYPE (1 - 4 days out): Peak velocity (GRWMs, countdowns, last-minute hacks)
      4. DAY_OF (Day 0): Saturation peak (feed flood, high noise)
      5. AFTERMATH (-1 to -3 days after): Relatable recovery, detox & exhaustion memes
      6. EXPIRED (< -3 days)
    """
    current_date = datetime.now(timezone.utc).date()
    event_date = datetime.fromisoformat(event_date_str).date()
    days_until = (event_date - current_date).days

    if days_until > 18:
        return {
            "phase": "PRE_RADAR",
            "phase_name": "Early Horizon",
            "badge": "🔭 Radar Detected",
            "badge_color": "blue",
            "days_until": days_until,
            "status_text": f"{days_until} days away. Pre-production & script planning window.",
            "filming_action": "Plan scripts, assemble moodboards, and order props before festive price spikes.",
            "saturation_level": "LOW (5%)",
            "urgency": "LOW",
            "is_golden_window": False,
        }
    elif 4 <= days_until <= 18:
        return {
            "phase": "PRE_FESTIVE_SURGE",
            "phase_name": "Pre-Festive Surge",
            "badge": "🔥 Golden Filming Window",
            "badge_color": "emerald",
            "days_until": days_until,
            "status_text": f"{days_until} days out — Algorithmic distribution peak for anticipation, glow-ups & shopping.",
            "filming_action": "FILM & POST NOW. Viewers are actively researching outfits, recipes, routines & budget hacks. Zero feed congestion.",
            "saturation_level": "OPTIMAL (25%)",
            "urgency": "HIGH",
            "is_golden_window": True,
        }
    elif 1 <= days_until <= 3:
        return {
            "phase": "PEAK_HYPE",
            "phase_name": "Peak Hype Window",
            "badge": "⚡ Peak Hype",
            "badge_color": "amber",
            "days_until": days_until,
            "status_text": f"{days_until} days to go — Immediate countdown, last-minute hacks, and GRWM excitement.",
            "filming_action": "Post quick-consumption reels (GRWM, 10-minute recipes, final outfit reveal). Fast velocity.",
            "saturation_level": "MODERATE (60%)",
            "urgency": "VERY_HIGH",
            "is_golden_window": False,
        }
    elif days_until == 0:
        return {
            "phase": "DAY_OF",
            "phase_name": "Festival Day (Peak Saturation)",
            "badge": "⚠️ Feed Flood Peak",
            "badge_color": "rose",
            "days_until": 0,
            "status_text": "Today! Feeds are congested with millions of personal greetings and celebration clips.",
            "filming_action": "Post high-emotion, aesthetic vibes or real-time celebration reels only. Heavy feed competition.",
            "saturation_level": "SATURATED (95%)",
            "urgency": "MEDIUM",
            "is_golden_window": False,
        }
    elif -3 <= days_until < 0:
        return {
            "phase": "AFTERMATH",
            "phase_name": "Relatable Aftermath & Memes",
            "badge": "🔄 Recovery & Memes",
            "badge_color": "purple",
            "days_until": days_until,
            "status_text": f"{abs(days_until)} days after. Recovery, post-celebration detox, and relatable hangover memes.",
            "filming_action": "Pivot to relatable comedy, gym comeback routines, and leftover sweet makeover recipes.",
            "saturation_level": "COOLING (30%)",
            "urgency": "MEDIUM",
            "is_golden_window": False,
        }
    else:
        return {
            "phase": "EXPIRED",
            "phase_name": "Concluded",
            "badge": "Concluded",
            "badge_color": "slate",
            "days_until": days_until,
            "status_text": "Event cycle completed.",
            "filming_action": "Archive and focus on the next upcoming festival.",
            "saturation_level": "INACTIVE",
            "urgency": "NONE",
            "is_golden_window": False,
        }


class CulturalEventCalendar:
    """
    India-specific cultural event calendar with 4-phase viral curve prediction
    and niche-specific reel blueprints.
    """

    CULTURAL_EVENTS = {
        'durga_puja_2026': {
            'slug': 'durga_puja_2026',
            'name': 'Durga Puja',
            'local_name': 'দুর্গাপূজা',
            'date': '2026-10-17',
            'duration_days': 5,
            'primary_regions': ['west_bengal', 'assam', 'tripura', 'east_india', 'delhi'],
            'feed_flood_intensity': 0.96,
            'content_themes': ['pujo', 'pandal_hopping', 'dhunuchi_naach', 'saree_draping', 'bengali_bhog', 'sindoor_khela'],
            'content_automation': ['Pandal hopping guide', 'Traditional Saree GRWM', 'Dhunuchi dance challenge', 'Bengali bhog recipes'],
            'creator_opportunities': ['Saree brand sponsorships', 'Restaurant Pujo menu features', 'Pandal media coverage', 'Street photography'],
            'niche_opportunities': {
                'fashion': 0.98,
                'food': 0.95,
                'travel': 0.92,
                'dance': 0.90,
                'fitness': 0.70,
                'comedy': 0.85,
                'tech': 0.75,
                'finance': 0.65,
                'all': 0.90
            },
            'audio_vibe': 'Dhak drum beats, Rabindra Sangeet lo-fi, upbeat Dhunuchi energetic trance',
            'optimal_posting_days': [-10, -7, -3, -1, 0, 1],
            'hashtags': ['#DurgaPuja2026', '#Pujo2026', '#PandalHopping', '#DhunuchiDance', '#SubhoSaptami'],
            'trending_hashtags': ['#pandalhopping', '#bengalilook', '#dhunuchinaach', '#pujovibes'],
            'content_ideas': [
                'Top 5 Must-Visit Pandals vlog (Kolkata & Delhi)',
                'Traditional Red & White Garad Saree look with gold jewellery',
                'Dhunuchi Naach high-energy slow-motion transition',
                'Kolkata street food tour during Pujo nights',
                'Emotional Sindoor Khela farewell moment'
            ]
        },
        'dussehra_2026': {
            'slug': 'dussehra_2026',
            'name': 'Dussehra (Vijayadashami)',
            'local_name': 'दशहरा / विजयदशमी',
            'date': '2026-10-20',
            'duration_days': 1,
            'primary_regions': ['north_india', 'karnataka', 'maharashtra', 'delhi', 'gujarat'],
            'feed_flood_intensity': 0.88,
            'content_themes': ['ramlila', 'ravan_dahan', 'victory_good_over_evil', 'new_beginnings', 'vehicle_puja', 'mysore_dasara'],
            'content_automation': ['Ramlila highlights', 'Ravan Dahan fireworks', 'Festive wish reels', 'Mysore Palace illumination'],
            'creator_opportunities': ['Local cultural event partnerships', 'Ethnic wear brands', 'Automobile puja sponsors'],
            'niche_opportunities': {
                'comedy': 0.92,
                'fashion': 0.88,
                'travel': 0.90,
                'finance': 0.78,
                'fitness': 0.75,
                'food': 0.82,
                'tech': 0.70,
                'all': 0.85
            },
            'audio_vibe': 'Powerful percussion, Ram Siya Ram chants, cinematic bass drops on fireworks',
            'optimal_posting_days': [-7, -3, -1, 0],
            'hashtags': ['#Dussehra2026', '#Vijayadashami', '#RavanDahan', '#GoodOverEvil', '#HappyDussehra'],
            'trending_hashtags': ['#ravandahan', '#ramlila', '#mysoredasara', '#dussehraspecial'],
            'content_ideas': [
                'Ravan Dahan fireworks slow-mo drop at night',
                'Why Vijayadashami is considered the ultimate day for new investments/purchases',
                'POV: Trying to leave Ramlila ground before the crowd rushes out',
                'Mysore Palace lights turn-on moment cinematic reel'
            ]
        },
        'karva_chauth_2026': {
            'slug': 'karva_chauth_2026',
            'name': 'Karwa Chauth',
            'local_name': 'करवा चौथ',
            'date': '2026-10-29',
            'duration_days': 1,
            'primary_regions': ['punjab', 'delhi', 'uttar_pradesh', 'rajasthan', 'haryana', 'north_india'],
            'feed_flood_intensity': 0.93,
            'content_themes': ['sargi', 'mehndi', 'fasting_hacks', 'red_lehenga', 'moon_sighting', 'couple_goals'],
            'content_automation': ['Mehndi design ideas', 'Sargi thali prep', 'Red ethnic outfit GRWM', 'Moon sighting moment'],
            'creator_opportunities': ['Jewellery brand collaborations', 'Mehndi artist showcases', 'Skincare hydration tips', 'Couple apparel'],
            'niche_opportunities': {
                'fashion': 0.99,
                'fitness': 0.88,
                'comedy': 0.94,
                'food': 0.80,
                'finance': 0.72,
                'travel': 0.60,
                'tech': 0.65,
                'all': 0.92
            },
            'audio_vibe': 'Romantic Bollywood strings, Punjabi wedding acoustic, emotional sufi lo-fi',
            'optimal_posting_days': [-8, -5, -2, -1, 0],
            'hashtags': ['#KarvaChauth2026', '#KarwaChauthSpecial', '#MehndiDesigns', '#RedSaree', '#ChandChupaBadalMein'],
            'trending_hashtags': ['#karwachauthlook', '#sargithali', '#chandkabniklega', '#fastinggoals'],
            'content_ideas': [
                '5-Minute Sargi Thali checklist to sustain energy all day without fainting',
                'Red Saree transition with heirloom jewellery reveal',
                'POV: Husband tracking the moon on weather satellites from 6 PM',
                'Non-greasy, long-lasting mehndi aftercare tips for deepest stain'
            ]
        },
        'diwali_2026': {
            'slug': 'diwali_2026',
            'name': 'Diwali (Deepavali)',
            'local_name': 'दिवाली / दीपावली',
            'date': '2026-11-14',
            'duration_days': 5,
            'primary_regions': ['pan_india', 'north_india', 'west_india', 'south_india', 'east_india'],
            'feed_flood_intensity': 0.99,
            'content_themes': ['diwali_safai', 'diyas', 'rangoli', 'mithai', 'muhurat_trading', 'tech_sales', 'family_reunion', 'festive_fashion'],
            'content_automation': ['Diwali safai memes', 'Home decor DIY', 'Muhurat trading picks', 'Festive sweet recipes', 'Diwali party GRWM'],
            'creator_opportunities': ['Home decor brands', 'Apparel & ethnic wear', 'Consumer electronics & gadgets', 'Jewellery & gold', 'Food & snacks'],
            'niche_opportunities': {
                'fashion': 0.99,
                'food': 0.98,
                'comedy': 0.99,
                'tech': 0.95,
                'finance': 0.96,
                'fitness': 0.89,
                'travel': 0.85,
                'dance': 0.92,
                'all': 0.98
            },
            'audio_vibe': 'Festive Bollywood dholak, uplifting sitar & acoustic, modern celebration pop',
            'optimal_posting_days': [-14, -10, -7, -3, -1, 0, 1],
            'hashtags': ['#Diwali2026', '#Deepavali', '#DiwaliSafai', '#FestivalOfLights', '#DiwaliLook', '#MuhuratTrading'],
            'trending_hashtags': ['#diwalireels', '#diwalidecoration', '#diwalisweets', '#soanpapdimeme'],
            'content_ideas': [
                'Relatable Diwali Safai comedy: Finding artifacts from 2012 under the bed',
                'The 5-Day Festive Sweet Strategy: How to enjoy Kaju Katli without guilt',
                'Top 3 Gadget Gifts under ₹2,000 worth buying during festive sales',
                'Muhurat Trading 101: 3 defensive index stocks to buy for Diwali Shagun',
                'Diwali night Diya lighting aesthetic 4K cinematic b-roll'
            ]
        },
        'bhai_dooj_2026': {
            'slug': 'bhai_dooj_2026',
            'name': 'Bhai Dooj',
            'local_name': 'भाई दूज / भाई टीका',
            'date': '2026-11-16',
            'duration_days': 1,
            'primary_regions': ['pan_india', 'north_india', 'maharashtra', 'bengal'],
            'feed_flood_intensity': 0.84,
            'content_themes': ['sibling_bond', 'shagun_money', 'gift_unboxing', 'brother_sister_comedy'],
            'content_automation': ['Sibling roast reels', 'Gift opening', 'Tikka ceremony'],
            'creator_opportunities': ['Gifting brands', 'Personalized accessories', 'Sweets & chocolates'],
            'niche_opportunities': {
                'comedy': 0.97,
                'fashion': 0.82,
                'finance': 0.80,
                'food': 0.78,
                'all': 0.84
            },
            'audio_vibe': 'Playful Bollywood sibling tracks, upbeat acoustic guitar, comical dialogue cuts',
            'optimal_posting_days': [-4, -2, 0],
            'hashtags': ['#BhaiDooj2026', '#SiblingBond', '#BhaiDoojSpecial', '#BrotherSister'],
            'trending_hashtags': ['#bhaidoojgift', '#siblinggoals', '#bhaidoojlook'],
            'content_ideas': [
                'POV: Sister demanding ₹5,000 shagun for applying a 10-rupee tilak',
                'Last-minute thoughtful gifts for your sister under ₹1,000 that look expensive',
                'Expectation vs Reality: Brother-sister celebration'
            ]
        },
        'chhath_puja_2026': {
            'slug': 'chhath_puja_2026',
            'name': 'Chhath Puja',
            'local_name': 'छठ पूजा',
            'date': '2026-11-16',
            'duration_days': 4,
            'primary_regions': ['bihar', 'uttar_pradesh', 'jharkhand', 'delhi', 'mumbai'],
            'feed_flood_intensity': 0.95,
            'content_themes': ['arghya', 'thekua_recipe', 'surya_upasana', 'river_ghat', 'tradition_purity', 'chhoti_chhath'],
            'content_automation': ['Thekua making tutorial', 'Ghat preparation vlog', 'Sunset arghya cinematic moments'],
            'creator_opportunities': ['Regional food & grain brands', 'Traditional clothing', 'Travel vloggers documenting ghats'],
            'niche_opportunities': {
                'food': 0.96,
                'travel': 0.94,
                'fashion': 0.85,
                'fitness': 0.82,
                'comedy': 0.60,
                'all': 0.88
            },
            'audio_vibe': 'Traditional folk Sharda Sinha songs, flute river melodies, devotional chants',
            'optimal_posting_days': [-8, -4, -1, 0, 1],
            'hashtags': ['#ChhathPuja2026', '#ChhathMahaparv', '#Thekua', '#ChhathGhat', '#JaiChhathiMaiya'],
            'trending_hashtags': ['#chhathpuja', '#shardasinha', '#biharculture', '#arghya'],
            'content_ideas': [
                'Authentic Crispy Thekua recipe passed down 3 generations (no-fail method)',
                'Why Chhath Puja is one of the world’s most disciplined, zero-waste Vedic rituals',
                'Sunrise at the Ganga Ghat during Bhorwa Arghya in 4K'
            ]
        },
        'wedding_season_2026': {
            'slug': 'wedding_season_2026',
            'name': 'Winter Wedding Season (Shaadi Season)',
            'local_name': 'शादी का सीज़न',
            'date': '2026-11-25',
            'duration_days': 45,
            'primary_regions': ['pan_india', 'delhi_ncr', 'punjab', 'rajasthan', 'mumbai'],
            'feed_flood_intensity': 0.94,
            'content_themes': ['sangeet_dance', 'lehenga_transitions', 'budget_guest_looks', 'haldi_mehendi', 'shaadi_food_buffet'],
            'content_automation': ['Guest outfit lookbooks', 'Sangeet hook steps', 'Wedding budget hacks'],
            'creator_opportunities': ['Jewellery rentals', 'Ethnic fashion designers', 'Makeup artists', 'Luxury destinations'],
            'niche_opportunities': {
                'fashion': 1.0,
                'dance': 0.98,
                'comedy': 0.95,
                'food': 0.90,
                'fitness': 0.92,
                'finance': 0.88,
                'tech': 0.75,
                'all': 0.96
            },
            'audio_vibe': 'High-BPM Punjabi Dhol, trending Bollywood Sangeet mashups, emotional Shehnai-lofi transitions',
            'optimal_posting_days': [-14, -7, 0, 7, 14],
            'hashtags': ['#ShaadiSeason2026', '#IndianWedding', '#SangeetChoreography', '#LehengaLook', '#WeddingGuest'],
            'trending_hashtags': ['#shaadireels', '#sangeetdance', '#weddingoutfit', '#haldivibes'],
            'content_ideas': [
                '3 Ways to style ONE ₹2,000 kurta for 3 different wedding functions without anyone noticing',
                'Easy 30-second Sangeet hook step anyone in your family can learn',
                'The Wedding Buffet Survival Rule: What to eat first so you don’t feel bloated in photos',
                'POV: Wedding guest who only came for the live pasta counter and kulfi'
            ]
        },
        'christmas_2026': {
            'slug': 'christmas_2026',
            'name': 'Christmas & Year-End Holidays',
            'local_name': 'क्रिसमस',
            'date': '2026-12-25',
            'duration_days': 4,
            'primary_regions': ['goa', 'kerala', 'northeast_india', 'metro_cities', 'mumbai', 'bangalore'],
            'feed_flood_intensity': 0.88,
            'content_themes': ['winter_fashion', 'plum_cake', 'tree_decor', 'secret_santa', 'cafe_hopping', 'year_end_reflections'],
            'content_automation': ['Secret Santa under ₹500', 'Winter layering guide', 'Plum cake baking'],
            'creator_opportunities': ['Winter apparel', 'Bakeries & confectionaries', 'Gifting platforms', 'Travel stays'],
            'niche_opportunities': {
                'fashion': 0.92,
                'food': 0.94,
                'travel': 0.95,
                'tech': 0.80,
                'comedy': 0.85,
                'finance': 0.70,
                'all': 0.86
            },
            'audio_vibe': 'Cozy acoustic carols, lo-fi jingle bells, upbeat holiday jazz',
            'optimal_posting_days': [-10, -5, -2, 0],
            'hashtags': ['#Christmas2026', '#SecretSanta', '#WinterVibes', '#ChristmasBaking', '#HolidaySeason'],
            'trending_hashtags': ['#christmasreels', '#secretsantagift', '#winteraesthetic'],
            'content_ideas': [
                '5 Secret Santa gifts under ₹499 that people will actually keep and love',
                'Winter aesthetic layering tips for Indian climate (cool, not sweaty)',
                'Eggless microwave plum cake recipe ready in 15 minutes'
            ]
        },
        'new_year_2027': {
            'slug': 'new_year_2027',
            'name': 'New Year 2027',
            'local_name': 'नया साल 2027',
            'date': '2027-01-01',
            'duration_days': 2,
            'primary_regions': ['pan_india', 'metro_cities', 'goa', 'bangalore', 'mumbai', 'delhi'],
            'feed_flood_intensity': 0.98,
            'content_themes': ['resolutions', '2026_recap', 'gym_reset', 'budget_financial_plan', 'party_looks', 'mindset'],
            'content_automation': ['2026 Recap template', 'Realistic habit tracker', 'Gym routine for beginners'],
            'creator_opportunities': ['Gym memberships & supplements', 'Productivity tools & planners', 'Party wear & nightlife', 'Financial apps'],
            'niche_opportunities': {
                'fitness': 1.0,
                'finance': 0.98,
                'comedy': 0.95,
                'fashion': 0.90,
                'tech': 0.92,
                'travel': 0.88,
                'all': 0.95
            },
            'audio_vibe': 'Euphoric electronic synth drops, nostalgic 2026 mashups, energetic gym motivation beats',
            'optimal_posting_days': [-12, -7, -3, -1, 0, 1, 3],
            'hashtags': ['#NewYear2027', '#2026Recap', '#FitnessReset', '#NewYearResolutions', '#FinancialGoals2027'],
            'trending_hashtags': ['#recap2026', '#gymmotivation', '#newyearreels', '#resolutions'],
            'content_ideas': [
                'Why 92% of New Year gym resolutions die by Jan 18 — and the 2-habit rule to fix it',
                'Financial Reset: What to do with your bank accounts on Jan 1st before spending a rupee',
                'Relatable comedy: Deciding whether to party on NYE or stay in bed with Netflix'
            ]
        },
        'makar_sankranti_pongal_2027': {
            'slug': 'makar_sankranti_pongal_2027',
            'name': 'Makar Sankranti / Pongal / Lohri',
            'local_name': 'मकर संक्रांति / பொங்கல் / ਲੋਹੜੀ',
            'date': '2027-01-14',
            'duration_days': 3,
            'primary_regions': ['gujarat', 'maharashtra', 'tamil_nadu', 'andhra_pradesh', 'punjab', 'karnataka', 'bihar'],
            'feed_flood_intensity': 0.91,
            'content_themes': ['kite_flying', 'til_gul', 'pongal_pot', 'bonfire_lohri', 'harvest_food', 'traditional_yellow_black'],
            'content_automation': ['Kite battle POV', 'Ven Pongal cooking', 'Lohri Punjabi suit GRWM'],
            'creator_opportunities': ['Ethnic fashion brands', 'Regional edible oils & jaggery', 'Action cameras (kite POV)'],
            'niche_opportunities': {
                'food': 0.96,
                'fashion': 0.92,
                'travel': 0.88,
                'comedy': 0.85,
                'tech': 0.82,
                'fitness': 0.76,
                'all': 0.90
            },
            'audio_vibe': 'Lohri Dhol beats, upbeat Gujarati Kai Po Che folk fusion, South Indian Nadaswaram modern rhythm',
            'optimal_posting_days': [-8, -4, -1, 0],
            'hashtags': ['#MakarSankranti2027', '#HappyPongal', '#HappyLohri', '#KaiPoChe', '#Uttarayan'],
            'trending_hashtags': ['#kiteflying', '#tilgul', '#pongalspecial', '#lohricelebration'],
            'content_ideas': [
                'First-person GoPro camera tied to a kite string diving over Ahmedabad rooftops',
                'Traditional Sweet Pongal in an earthen pot step-by-step in 45 seconds',
                'Why black outfits are traditionally worn on Makar Sankranti (Scientific + cultural breakdown)'
            ]
        },
        'republic_day_2027': {
            'slug': 'republic_day_2027',
            'name': 'Republic Day',
            'local_name': 'गणतंत्र दिवस',
            'date': '2027-01-26',
            'duration_days': 1,
            'primary_regions': ['pan_india', 'delhi', 'schools', 'colleges'],
            'feed_flood_intensity': 0.89,
            'content_themes': ['patriotism', 'tricolor', 'kartavya_path_parade', 'indian_achievements', 'school_nostalgia'],
            'content_automation': ['Tricolor snack recipe', 'Patriotic song edit', 'School flag hoisting nostalgia'],
            'creator_opportunities': ['Made-in-India brands', 'Tech innovations in India', 'Patriotic ethnic clothing'],
            'niche_opportunities': {
                'current_affairs': 0.98,
                'dance': 0.92,
                'food': 0.88,
                'tech': 0.90,
                'comedy': 0.80,
                'all': 0.87
            },
            'audio_vibe': 'Symphonic patriotic orchestrations (A.R. Rahman style), Marching band beats, emotional flute renditions',
            'optimal_posting_days': [-5, -2, -1, 0],
            'hashtags': ['#RepublicDay2027', '#26January', '#KartavyaPath', '#ProudToBeIndian', '#VandeMataram'],
            'trending_hashtags': ['#republicdayreels', '#indianpatriotism', '#tricolor'],
            'content_ideas': [
                '5 Indian military innovations & defense tech showcased at this year’s parade',
                'Relatable school nostalgia: The struggle to collect your laddu and 2 bananas on 26th Jan',
                'Tricolor Dhokla or Idli platter in 3 easy steps'
            ]
        },
        'maha_shivratri_2027': {
            'slug': 'maha_shivratri_2027',
            'name': 'Maha Shivratri',
            'local_name': 'महाशिवरात्रि',
            'date': '2027-03-06',
            'duration_days': 1,
            'primary_regions': ['pan_india', 'uttarakhand', 'kashi', 'ujjain', 'tamil_nadu'],
            'feed_flood_intensity': 0.93,
            'content_themes': ['mahadev_bhakti', 'bholenath_audios', 'fasting_vrat', 'night_vigil', 'temple_darshan'],
            'content_automation': ['Mahadev trance video', 'Fasting energy drink', 'Kashi/Ujjain temple reel'],
            'creator_opportunities': ['Spiritual travel vlogs', 'Yoga & meditation lifestyle', 'Traditional puja aesthetics'],
            'niche_opportunities': {
                'fitness': 0.92,
                'travel': 0.96,
                'food': 0.85,
                'dance': 0.88,
                'all': 0.89
            },
            'audio_vibe': 'Shiv Tandav Stotram trance, Damru percussion, flute & chillum lo-fi (consistently top 5 trending audio in India)',
            'optimal_posting_days': [-6, -3, -1, 0],
            'hashtags': ['#MahaShivratri2027', '#HarHarMahadev', '#ShivTandav', '#Bholenath', '#KashiVishwanath'],
            'trending_hashtags': ['#shivratri', '#mahadevreels', '#omnamahshivaya'],
            'content_ideas': [
                'High-energy gym motivation reel set to modern Shiv Tandav electronic beat',
                'The science behind night-long wakefulness on Shivratri and spinal alignment',
                'Cinematic 4K darshan of the Jyotirlinga at dawn'
            ]
        },
        'holi_2027': {
            'slug': 'holi_2027',
            'name': 'Holi (Festival of Colors)',
            'local_name': 'होली',
            'date': '2027-03-14',
            'duration_days': 2,
            'primary_regions': ['pan_india', 'north_india', 'gujarat', 'maharashtra', 'delhi', 'rajasthan'],
            'feed_flood_intensity': 0.99,
            'content_themes': ['gulal', 'color_transitions', 'hair_skin_protection', 'gujiya_recipe', 'thandai', 'friend_group_fun'],
            'content_automation': ['Pre-Holi skincare shield', 'Color splash slow-motion transition', 'Instant Gujiya recipe'],
            'creator_opportunities': ['Sunscreen & skincare brands', 'Hair oils & protection', 'Beverage & Thandai mixers', 'Waterproof gadgets'],
            'niche_opportunities': {
                'fashion': 0.95,
                'food': 0.96,
                'fitness': 0.85,
                'comedy': 0.98,
                'tech': 0.88,
                'dance': 0.96,
                'all': 0.96
            },
            'audio_vibe': 'High-octane Bollywood Holi classics, fast Dhol-tasha, playful water balloon drops',
            'optimal_posting_days': [-10, -6, -2, -1, 0, 1],
            'hashtags': ['#Holi2027', '#FestivalOfColors', '#RangBarse', '#HoliLook', '#BalamPichkari'],
            'trending_hashtags': ['#holireels', '#holiskincare', '#gujiyarecipe', '#holidance'],
            'content_ideas': [
                'The 3-layer skin & hair barrier routine that prevents chemical colors from sticking to your nails and hair',
                'White kurta color throw instant transition matching the bass drop',
                'Air-fryer Gujiya: 70% fewer calories than deep-fried without losing crunch',
                'POV: The one friend who swore they would play a dry, gentle tilak-only Holi'
            ]
        },
        'eid_ul_fitr_2027': {
            'slug': 'eid_ul_fitr_2027',
            'name': 'Eid ul-Fitr',
            'local_name': 'ईद उल-फ़ित्र',
            'date': '2027-03-24',
            'duration_days': 2,
            'primary_regions': ['pan_india', 'hyderabad', 'lucknow', 'delhi', 'kerala', 'mumbai'],
            'feed_flood_intensity': 0.94,
            'content_themes': ['sheer_khurma', 'biryani', 'eid_outfit_grwm', 'chand_raat', 'eidi', 'family_gatherings'],
            'content_automation': ['Sheer Khurma recipe', 'Eid Kurta/Sharara lookbook', 'Chand Raat shopping vlog'],
            'creator_opportunities': ['Ethnic menswear & womenswear', 'Perfumes & Attar brands', 'Dry fruit & sweet sponsors'],
            'niche_opportunities': {
                'fashion': 0.98,
                'food': 0.99,
                'comedy': 0.88,
                'travel': 0.85,
                'finance': 0.78,
                'all': 0.91
            },
            'audio_vibe': 'Sufi acoustic melodies, gentle Qawwali lo-fi, celebratory Arabic-Bollywood fusion',
            'optimal_posting_days': [-7, -3, -1, 0, 1],
            'hashtags': ['#EidUlFitr2027', '#EidMubarak', '#SheerKhurma', '#ChandRaat', '#EidOutfit'],
            'trending_hashtags': ['#eidlook', '#eidspecial', '#eidmubarak2027', '#biryanilovers'],
            'content_ideas': [
                'Authentic rich Sheer Khurma recipe made with slow-roasted sewai and condensed milk',
                'Emerald green & ivory Sharara transition for Eid prayers',
                'Chand Raat bazaar walk in Old Delhi / Charminar at 2 AM'
            ]
        },
        'ipl_2027': {
            'slug': 'ipl_2027',
            'name': 'IPL Cricket Season 2027 Kick-Off',
            'local_name': 'आईपीएल 2027',
            'date': '2027-03-28',
            'duration_days': 60,
            'primary_regions': ['pan_india', 'mumbai', 'chennai', 'bangalore', 'kolkata', 'delhi'],
            'feed_flood_intensity': 0.97,
            'content_themes': ['team_rivalries', 'jersey_drip', 'match_watch_snacks', 'fantasy_cricket_tips', 'stadium_vlogs'],
            'content_automation': ['Team anthem remix', 'Match day snack platter', 'Fan rivalry comedy'],
            'creator_opportunities': ['Sports merch', 'Snacks & cold beverages', 'Screen mirroring & projectors', 'Sports fantasy apps'],
            'niche_opportunities': {
                'comedy': 0.99,
                'food': 0.95,
                'fitness': 0.92,
                'tech': 0.90,
                'fashion': 0.85,
                'finance': 0.80,
                'all': 0.94
            },
            'audio_vibe': 'Stadium horns, high-energy stadium anthems (Whistle Podu, Korbo Lorbo, RCB chant), fast cuts',
            'optimal_posting_days': [-10, -5, -2, 0, 1],
            'hashtags': ['#IPL2027', '#TataIPL', '#CricketLovers', '#MatchDay', '#CSKvsRCB'],
            'trending_hashtags': ['#iplreels', '#iplmemes', '#cricketfever', '#matchdayvibes'],
            'content_ideas': [
                'POV: Explaining to your non-cricket partner why the next 2 months of your life are booked 7:30 PM daily',
                'Stadium-style crispy Loaded Nachos in 10 minutes before the first ball',
                'Fitness test comparison: Can an average gym-goer sprint between wickets as fast as Virat Kohli?'
            ]
        }
    }

    @classmethod
    def get_upcoming_events(cls, days_ahead: int = 120) -> List[Dict]:
        """
        Get upcoming cultural events within specified days, enriched with wave phases.
        """
        current_date = datetime.now(timezone.utc).date()
        cutoff_date = current_date + timedelta(days=days_ahead)
        upcoming_events = []

        for slug, data in cls.CULTURAL_EVENTS.items():
            event_date = datetime.fromisoformat(data['date']).date()
            # Include events that are upcoming or in aftermath (within last 3 days)
            if (current_date - timedelta(days=3)) <= event_date <= cutoff_date:
                days_until = (event_date - current_date).days
                wave = calculate_wave_phase(data['date'])
                
                ev = data.copy()
                ev['slug'] = slug
                ev['days_until'] = days_until
                ev['is_upcoming'] = days_until >= 0
                ev['wave_phase'] = wave
                # Backwards compatible alias keys for older frontend components
                ev['start_date'] = data['date']
                ev['event_date'] = data['date']
                ev['event_name'] = data['name']
                upcoming_events.append(ev)

        # Sort: first by urgency (days_until absolute order, closest active events first)
        upcoming_events.sort(key=lambda x: x['days_until'])
        return upcoming_events

    @classmethod
    def get_festive_radar(cls, days_ahead: int = 150, niche: Optional[str] = None) -> Dict:
        """
        Returns full Festive Viral Radar with active waves, golden filming windows,
        and niche compatibility rankings.
        """
        events = cls.get_upcoming_events(days_ahead)
        active_surge_events = []
        upcoming_horizon_events = []
        concluded_events = []

        target_niche = (niche or "all").lower().strip()

        for ev in events:
            # Calculate niche fit percentage
            niche_opps = ev.get('niche_opportunities', {})
            niche_score = int(niche_opps.get(target_niche, niche_opps.get('all', 0.8)) * 100)
            ev['niche_fit_score'] = niche_score
            ev['target_niche'] = target_niche

            phase_code = ev['wave_phase']['phase']
            if phase_code in ("PRE_FESTIVE_SURGE", "PEAK_HYPE", "DAY_OF", "AFTERMATH"):
                active_surge_events.append(ev)
            elif phase_code == "PRE_RADAR":
                upcoming_horizon_events.append(ev)
            else:
                concluded_events.append(ev)

        # Primary highlighted event is the one currently in golden filming surge or closest peak
        golden_event = next(
            (e for e in active_surge_events if e['wave_phase']['phase'] == "PRE_FESTIVE_SURGE"),
            active_surge_events[0] if active_surge_events else (upcoming_horizon_events[0] if upcoming_horizon_events else None)
        )

        return {
            "current_date": datetime.now(timezone.utc).date().isoformat(),
            "target_niche": target_niche,
            "golden_opportunity": golden_event,
            "active_wave_festivals": active_surge_events,
            "upcoming_radar_festivals": upcoming_horizon_events,
            "total_monitored": len(events)
        }

    @classmethod
    def get_event_content_suggestions(cls, event_name: str, region: Optional[str] = None) -> Dict:
        """Legacy helper for backwards compatibility."""
        target = None
        for ev in cls.CULTURAL_EVENTS.values():
            if ev['name'].lower() == event_name.lower() or ev['slug'].lower() == event_name.lower():
                target = ev
                break
        
        if not target:
            return {'error': f'Event {event_name} not found', 'available_events': [e['name'] for e in cls.CULTURAL_EVENTS.values()]}
        
        return {
            'event_name': target['name'],
            'date': target['date'],
            'duration_days': target['duration_days'],
            'content_themes': target['content_themes'],
            'hashtags': target['hashtags'],
            'trending_hashtags': target['trending_hashtags'],
            'content_ideas': target['content_ideas'],
            'optimal_posting_days': target['optimal_posting_days']
        }

    @classmethod
    def get_optimal_posting_window(cls, event_name: str) -> Dict:
        """Legacy helper for backwards compatibility."""
        target = None
        for ev in cls.CULTURAL_EVENTS.values():
            if ev['name'].lower() == event_name.lower() or ev['slug'].lower() == event_name.lower():
                target = ev
                break
        
        if not target:
            return {'error': 'Event not found'}

        event_date = datetime.fromisoformat(target['date'])
        optimal_dates = []
        for day_offset in target['optimal_posting_days']:
            target_date = event_date + timedelta(days=day_offset)
            optimal_dates.append({
                'date': target_date.date().isoformat(),
                'days_offset': day_offset,
                'label': f"{'Day before' if day_offset < 0 else 'Day after' if day_offset > 0 else 'Event day'} {abs(day_offset)}" if day_offset != 0 else 'Event day'
            })

        return {
            'event_date': target['date'],
            'optimal_dates': optimal_dates,
            'optimal_times': ['18:00-21:00 IST', '12:00-14:00 IST'],
            'urgency': 'HIGH' if optimal_dates and optimal_dates[0]['days_offset'] <= 3 else 'MEDIUM'
        }

    @classmethod
    def generate_festive_reel_ideas(
        cls,
        event_slug: str,
        niche: str = "all",
        custom_angle: Optional[str] = None,
        grounding_audios: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate 3 high-impact, actionable reel concepts for a festival and creator niche.
        Uses LLM with rich prompt and structured JSON output, with a deterministic fallback library.
        """
        event_data = cls.CULTURAL_EVENTS.get(event_slug)
        if not event_data:
            # Try searching by name
            for k, v in cls.CULTURAL_EVENTS.items():
                if v['name'].lower() == event_slug.lower():
                    event_data = v
                    event_slug = k
                    break

        if not event_data:
            return {
                "error": f"Festival '{event_slug}' not recognized.",
                "available_slugs": list(cls.CULTURAL_EVENTS.keys())
            }

        wave = calculate_wave_phase(event_data['date'])
        clean_niche = (niche or "all").lower().strip()

        # Cache check: return instant cached response if generated within 24h
        cache_key = f"{event_slug}:{clean_niche}:{(custom_angle or '').strip().lower()}"
        now_ts = datetime.now(timezone.utc).timestamp()
        if cache_key in _FESTIVE_IDEAS_CACHE:
            entry = _FESTIVE_IDEAS_CACHE[cache_key]
            if now_ts - entry.get("cached_at", 0) < _FESTIVE_CACHE_TTL_SECONDS:
                logger.info(f"Serving festive ideas from 24h cache for {cache_key}")
                cached_data = entry["data"].copy()
                cached_data["is_cached"] = True
                return cached_data

        # Database Grounding: Real trending rising audios currently in Trendrop DB
        real_audios_text = ""
        if grounding_audios and len(grounding_audios) > 0:
            real_audios_text = f"Currently Rising Audios in Trendrop DB to pair with: {', '.join(grounding_audios)}"

        # Build prompt for LLM
        system_prompt = (
            "You are India's top Instagram Reel Growth Architect and virality strategist. "
            "You specialize in festival and cultural trend distribution in India. "
            "Crucially, you know that the highest viral distribution happens 5-14 days BEFORE "
            "a festival (anticipation, preparations, hacks, trials, relatable stress), NOT on the day of when feeds are flooded. "
            "You provide high-converting, actionable, word-for-word reel concepts with scroll-stopping 3-second hooks."
        )

        user_prompt = f"""
Festival: {event_data['name']} ({event_data.get('local_name', '')})
Event Date: {event_data['date']}
Current Status / Wave Phase: {wave['phase_name']} ({wave['badge']}) - {wave['days_until']} days until event.
Filming Strategy: {wave['filming_action']}
Creator Niche: {clean_niche}
Custom Angle / Note from Creator: {custom_angle or 'None provided'}
Audience Culture & Themes: {', '.join(event_data.get('content_themes', []))}
Recommended Audio Vibe: {event_data.get('audio_vibe', 'Trending Indian upbeat beat')}
{real_audios_text}

Create 3 distinct, high-impact reel concepts tailored specifically to this niche and festival wave phase:
1. Concept 1: The Anticipation / Preparation Angle (High saves & shares)
2. Concept 2: The Relatable POV / Comedy Angle (High comments & shares)
3. Concept 3: The Quick Hack / Blueprint Angle (High retention & follows)

Return ONLY a valid JSON object in this exact schema:
{{
  "event_name": "{event_data['name']}",
  "event_slug": "{event_slug}",
  "niche": "{clean_niche}",
  "wave_phase": {json.dumps(wave)},
  "audio_recommendation": "{event_data.get('audio_vibe', '')}",
  "recommended_hashtags": {json.dumps(event_data.get('hashtags', [])[:5])},
  "concepts": [
    {{
      "concept_title": "Short punchy title",
      "hook_3s": "Word-for-word spoken hook or on-screen text for the first 3 seconds",
      "hook_archetype": "Contrarian Truth | Relatable POV | Curiosity Gap | Visual Transformation",
      "format_archetype": "Split-Screen | GRWM & Chat | 3-Step Fast Blueprint | Skit",
      "blueprint_flow": [
        "0-3s: Hook visual and voiceover",
        "4-15s: Core insight or quick progression",
        "16-25s: Climax / Call to Action"
      ],
      "sound_style": "Exact type of audio or beat to pair with",
      "optimal_post_window": "Best dates and IST time range to post",
      "why_algorithm_favors": "Why Instagram distributes this content right now",
      "virality_score": 92
    }}
  ]
}}
"""
        # Call LLM if available
        if call_llm:
            try:
                parsed = call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_mime_type="application/json",
                    timeout=30
                )
                if isinstance(parsed, dict) and "concepts" in parsed and len(parsed["concepts"]) >= 3:
                    parsed["is_ai_generated"] = True
                    _FESTIVE_IDEAS_CACHE[cache_key] = {"cached_at": now_ts, "data": parsed}
                    return parsed
                elif isinstance(parsed, str):
                    cleaned = re.sub(r"^```json\s*", "", parsed.strip())
                    cleaned = re.sub(r"```$", "", cleaned.strip())
                    data = json.loads(cleaned)
                    if isinstance(data, dict) and "concepts" in data and len(data["concepts"]) >= 3:
                        data["is_ai_generated"] = True
                        _FESTIVE_IDEAS_CACHE[cache_key] = {"cached_at": now_ts, "data": data}
                        return data
            except Exception as e:
                logger.warning(f"Festive LLM generation failed or returned invalid JSON: {e}")

        # Deterministic rich fallback library
        fallback_res = cls._generate_deterministic_festive_ideas(event_data, event_slug, clean_niche, wave)
        _FESTIVE_IDEAS_CACHE[cache_key] = {"cached_at": now_ts, "data": fallback_res}
        return fallback_res

    @classmethod
    def _generate_deterministic_festive_ideas(
        cls,
        event_data: Dict,
        event_slug: str,
        niche: str,
        wave: Dict
    ) -> Dict:
        """
        Deep, high-converting fallback ideas tailored to festival + niche.
        Ensures users get immediate, stunning, realistic ideas with 0 latency.
        """
        ev_name = event_data['name']
        audio_vibe = event_data.get('audio_vibe', 'Trending festive Indian audio with high-energy drop')
        hashtags = event_data.get('hashtags', ['#FestivalVibes', '#ReelsIndia'])

        # Niche-specific blueprint templates
        if "fitness" in niche:
            concepts = [
                {
                    "concept_title": f"The {ev_name} Damage Control Protocol",
                    "hook_3s": f"Stop starving yourself before {ev_name} — do this 3-rule trick instead.",
                    "hook_archetype": "Contrarian Truth",
                    "format_archetype": "3-Step Fast Blueprint",
                    "blueprint_flow": [
                        "0-3s: Show a plate of festive sweets vs a clean meal with the text hook.",
                        "4-15s: Break down the protein anchor rule: eat 30g protein + 500ml water 20 mins before festive dinner.",
                        "16-25s: Tell them to save this reel for the festive week and leave their goal in the comments."
                    ],
                    "sound_style": "Low-tempo confident Lo-Fi beat with subtle Indian flute",
                    "optimal_post_window": f"{max(1, wave['days_until'] - 2)} days before {ev_name}, 7:00 PM IST",
                    "why_algorithm_favors": "High saves rate from viewers wanting to prevent festive weight gain.",
                    "virality_score": 94
                },
                {
                    "concept_title": f"POV: Trying to maintain a calorie deficit during {ev_name}",
                    "hook_3s": "My gym trainer vs My Indian Mom offering me hot sweets.",
                    "hook_archetype": "Relatable POV",
                    "format_archetype": "Split-Screen Skit",
                    "blueprint_flow": [
                        "0-3s: Side-by-side or quick jump cut of you refusing food vs your mom forcing the 3rd laddu.",
                        "4-15s: Fast paced cuts of you giving up and doing pushups in festive clothes at midnight.",
                        "16-25s: Funny punchline text: 'Calories during festivals don't count if you eat with family.'"
                    ],
                    "sound_style": "Trending comical dialogue beat or high-energy Dhol drop",
                    "optimal_post_window": "3-5 days before event, 8:30 PM IST",
                    "why_algorithm_favors": "Extremely high shareability via Instagram DMs to gym friends.",
                    "virality_score": 96
                },
                {
                    "concept_title": f"The 12-Minute Fast Festive Workout (No Equipment)",
                    "hook_3s": f"No time for gym this {ev_name}? Do this 12-minute metabolic burner at home.",
                    "hook_archetype": "Curiosity Gap",
                    "format_archetype": "Fast-Cut Follow-Along",
                    "blueprint_flow": [
                        "0-3s: Fast timer graphic on screen with explosive bodyweight movement.",
                        "4-18s: 4 rapid exercises (Burpees, Jump Squats, Mountain Climbers, High Knees) with rep counts on screen.",
                        "19-25s: 'Save this reel so you don’t skip your workout on festival morning!'"
                    ],
                    "sound_style": "High-BPM Phonk or electronic remix of traditional Indian rhythm",
                    "optimal_post_window": "Festival Eve or morning of, 7:30 AM IST",
                    "why_algorithm_favors": "Saves and audio replays as viewers bookmark the workout.",
                    "virality_score": 90
                }
            ]
        elif "finance" in niche:
            concepts = [
                {
                    "concept_title": f"The {ev_name} Spending Trap (Don't fall for this)",
                    "hook_3s": f"90% of people will regret this purchase during {ev_name} sales.",
                    "hook_archetype": "Contrarian Warning",
                    "format_archetype": "Talking Head with Green Screen Price Chart",
                    "blueprint_flow": [
                        "0-3s: Show fake festive discounts vs actual price history tracker.",
                        "4-16s: Explain the psychological trick of festive sales and how to use price tracker extensions.",
                        "17-25s: Give the 24-Hour Festive Wishlist Rule before clicking 'Buy Now'."
                    ],
                    "sound_style": "Curiosity investigative beat with subtle synth pulses",
                    "optimal_post_window": "7-10 days before event, 6:00 PM IST",
                    "why_algorithm_favors": "Urgent utility and high comment discussions on shopping deals.",
                    "virality_score": 93
                },
                {
                    "concept_title": f"Dhanteras & {ev_name} Shagun: Physical Gold vs Digital Gold vs SGBs",
                    "hook_3s": "Buying physical gold jewellery this festival? You might be losing 20% on making charges.",
                    "hook_archetype": "Curiosity Gap",
                    "format_archetype": "Comparison Chart",
                    "blueprint_flow": [
                        "0-3s: Hold a gold coin or ring vs a digital smartphone portfolio screen.",
                        "4-15s: 3-column breakdown: Making charges, safety/theft risk, and sovereign interest returns.",
                        "16-25s: Clear actionable takeaway on where smart investors put their festive bonus."
                    ],
                    "sound_style": "Upbeat clean tech-minimalist lo-fi",
                    "optimal_post_window": "5-8 days before event, 7:30 PM IST",
                    "why_algorithm_favors": "High bookmarking and re-shares to family WhatsApp groups.",
                    "virality_score": 95
                },
                {
                    "concept_title": f"Festive Bonus Allocation: The 50-30-20 Indian Rule",
                    "hook_3s": "Got your festive Diwali bonus? Do not spend a rupee until you watch this.",
                    "hook_archetype": "Urgent Blueprint",
                    "format_archetype": "Calculator Demonstration",
                    "blueprint_flow": [
                        "0-3s: Screen recording of a ₹50,000 bonus calculation.",
                        "4-15s: 50% into emergency debt/prepayment, 30% for gifts & festive indulgence, 20% into index funds.",
                        "16-25s: 'Comment BONUS and I will DM you my free festive budget spreadsheet.'"
                    ],
                    "sound_style": "Smooth lo-fi chill hip-hop",
                    "optimal_post_window": "10-14 days before event, 8:00 PM IST",
                    "why_algorithm_favors": "Comment-triggering keyword optimization increases engagement velocity.",
                    "virality_score": 91
                }
            ]
        elif "food" in niche:
            concepts = [
                {
                    "concept_title": f"15-Minute Instant {ev_name} Sweet (No Mawa, No Chashni)",
                    "hook_3s": "Forgot to buy sweets for guests? Make this gourmet dessert in 15 minutes flat.",
                    "hook_archetype": "Visual Transformation",
                    "format_archetype": "Fast-Paced Aesthetic Recipe Cut",
                    "blueprint_flow": [
                        "0-3s: High-contrast close-up of cutting into a creamy, pistacchio-loaded sweet.",
                        "4-16s: 3 ingredient reveal (Milk powder, condensed milk, cardamom). Fast sizzle cuts.",
                        "17-25s: Final garnish shot with plated presentation. 'Full recipe in caption!'"
                    ],
                    "sound_style": "Satisfying cooking ASMR mixed with uplifting Indian acoustic sitar",
                    "optimal_post_window": "3-6 days before event, 12:30 PM IST (lunch prep time)",
                    "why_algorithm_favors": "Massive save rates from home cooks preparing festive menus.",
                    "virality_score": 97
                },
                {
                    "concept_title": f"The Leftover {ev_name} Mithai Makeover",
                    "hook_3s": "What to do with all those leftover sweets when no one wants to eat them?",
                    "hook_archetype": "Relatable POV",
                    "format_archetype": "Creative Recipe Fusion",
                    "blueprint_flow": [
                        "0-3s: Show 5 stacked unopened boxes of Soan Papdi or Gulab Jamun.",
                        "4-16s: Transform them into a Gulab Jamun Cheesecake or Soan Papdi Parfait jar.",
                        "17-25s: Taste test reaction. 'Never throw away festive sweets again!'"
                    ],
                    "sound_style": "Upbeat cheerful acoustic guitar with playful snaps",
                    "optimal_post_window": "1-3 days AFTER the festival, 4:00 PM IST",
                    "why_algorithm_favors": "High engagement during the aftermath wave when everyone faces sweet fatigue.",
                    "virality_score": 94
                },
                {
                    "concept_title": f"Air-Fryer Festive Snacks: 80% Less Oil",
                    "hook_3s": "Craving festive fried snacks but hate the heavy oil feeling? Watch this.",
                    "hook_archetype": "Curiosity Hack",
                    "format_archetype": "Side-by-Side Comparison",
                    "blueprint_flow": [
                        "0-3s: Crunch test audio on microphone with golden brown snack.",
                        "4-15s: Show temperature and timing secret for getting deep-fried crunch in an air fryer.",
                        "16-25s: Dip into spicy chutney and bite. 'Save this before festive shopping!'"
                    ],
                    "sound_style": "Crisp ASMR audio over light festive tabla beat",
                    "optimal_post_window": "5-8 days before event, 5:30 PM IST",
                    "why_algorithm_favors": "Combines health consciousness with festive indulgence.",
                    "virality_score": 92
                }
            ]
        elif "fashion" in niche:
            concepts = [
                {
                    "concept_title": f"3 Ways to Restyle Your Old Lehenga for {ev_name}",
                    "hook_3s": "Don't spend ₹15,000 on a new festive outfit — do this with your old lehenga.",
                    "hook_archetype": "Contrarian Hack",
                    "format_archetype": "Fast Transition Lookbook",
                    "blueprint_flow": [
                        "0-3s: Holding an old lehenga skirt with a confused expression.",
                        "4-16s: 3 quick snap transitions: 1) Paired with an oversized white shirt, 2) With a contrasting cape blazer, 3) Draped like an Indo-western saree.",
                        "17-25s: Spin into the full festive glow. 'Which style was your favorite? 1, 2, or 3?'"
                    ],
                    "sound_style": "Trending Bollywood royal instrumental transition drop",
                    "optimal_post_window": "7-12 days before event, 6:30 PM IST",
                    "why_algorithm_favors": "High comment voting ('1, 2 or 3') boosts algorithmic distribution.",
                    "virality_score": 98
                },
                {
                    "concept_title": f"5-Minute Festive Glow Makeup (Sweat-Proof & Transfer-Proof)",
                    "hook_3s": "How to make your festive makeup last 8 hours through pujas and dancing.",
                    "hook_archetype": "Curiosity Problem-Solver",
                    "format_archetype": "Macro Close-Up GRWM",
                    "blueprint_flow": [
                        "0-3s: Macro shot of glowing skin with setting spray mist.",
                        "4-16s: 3 key steps: Ice water prep, cream blush beneath powder, and targeted setting technique.",
                        "17-25s: Tissue paper blot test showing 0 makeup transfer. 'Save for your festive night!'"
                    ],
                    "sound_style": "Clean modern Lo-Fi pop with gentle melodic hooks",
                    "optimal_post_window": "3-5 days before event, 7:00 PM IST",
                    "why_algorithm_favors": "Saves and shares among women getting ready for festive gatherings.",
                    "virality_score": 95
                },
                {
                    "concept_title": f"Men's Festive Kurta Guide: Look Expensive on a Budget",
                    "hook_3s": "Guys, stop wearing plain black kurtas to every festival. Try this instead.",
                    "hook_archetype": "Direct Callout",
                    "format_archetype": "Wardrobe Transformation",
                    "blueprint_flow": [
                        "0-3s: Show boring plain kurta vs rich jewel-tone textured silk kurta.",
                        "4-15s: 3 affordable upgrades: Nehru jacket layering, antique brass pocket square, and leather Kolhapuri shoes.",
                        "16-25s: Final polished walking shot with watch adjustment."
                    ],
                    "sound_style": "Confident regal Indian orchestral hip-hop beat",
                    "optimal_post_window": "6-10 days before event, 8:00 PM IST",
                    "why_algorithm_favors": "High male-creator audience bookmarking and girlfriend-shares.",
                    "virality_score": 91
                }
            ]
        elif "comedy" in niche:
            concepts = [
                {
                    "concept_title": f"The Indian Household {ev_name} Safai Panic",
                    "hook_3s": "POV: Mom starts cleaning the house 2 weeks before the festival.",
                    "hook_archetype": "Relatable POV",
                    "format_archetype": "Multi-Character Skit",
                    "blueprint_flow": [
                        "0-3s: Mom holding a broom at 6 AM turning off your fan: 'Wake up, guests are coming in 14 days!'",
                        "4-16s: Cleaning things nobody ever looks at (the top of the fan, curtains, 2014 school trophies).",
                        "17-25s: The inevitable moment of discovering childhood report cards and getting scolded."
                    ],
                    "sound_style": "Dramatic Bollywood tense background music transitioning to comedy flute",
                    "optimal_post_window": "8-14 days before event, 8:30 PM IST",
                    "why_algorithm_favors": "Extreme relatability across all Indian demographics; guaranteed DM shares.",
                    "virality_score": 99
                },
                {
                    "concept_title": f"The Mystery of the Re-Gifted Soan Papdi Box",
                    "hook_3s": "Tracking the journey of this one Soan Papdi box traveling across India.",
                    "hook_archetype": "Storytelling / Mockumentary",
                    "format_archetype": "Narrated Satirical Documentary",
                    "blueprint_flow": [
                        "0-3s: Close-up of a festive sweet box with a subtle pencil mark at the bottom.",
                        "4-16s: Tracing how Uncle Sharma gave it to Papa, Papa gave it to the accountant, and the accountant gifted it back.",
                        "17-25s: Opening the box to find the same mark. 'Tag someone who gives Soan Papdi!'"
                    ],
                    "sound_style": "National Geographic suspense theme meets comedic tabla",
                    "optimal_post_window": "2-4 days before event, 7:00 PM IST",
                    "why_algorithm_favors": "Culturally universal inside joke with massive comment tagging.",
                    "virality_score": 97
                },
                {
                    "concept_title": f"Relatives Asking About Marriage During {ev_name}",
                    "hook_3s": "POV: Trying to grab food at the festive gathering without getting questioned by aunts.",
                    "hook_archetype": "Stealth Comedy",
                    "format_archetype": "Action Movie Spoof",
                    "blueprint_flow": [
                        "0-3s: Mission Impossible music while crawling past aunties discussing match-making.",
                        "4-15s: Getting trapped near the snack table: 'Beta what package are you earning now?'",
                        "16-25s: Dramatic eye contact with your cousin who is also trapped."
                    ],
                    "sound_style": "Spy action music cut with traditional Shehnai",
                    "optimal_post_window": "Festival Eve or Day 0, 8:00 PM IST",
                    "why_algorithm_favors": "Instant emotional resonance with young creators and Gen-Z/Millennials.",
                    "virality_score": 94
                }
            ]
        elif "tech" in niche:
            concepts = [
                {
                    "concept_title": f"Top 5 Festive Tech Deals That Are Actually Real Discounts",
                    "hook_3s": "Don't get fooled by 70% OFF banners — here are the 3 real tech steals this festival.",
                    "hook_archetype": "Value Filter",
                    "format_archetype": "B-roll Product Showcase with Price Badges",
                    "blueprint_flow": [
                        "0-3s: Holding 3 top gadgets with striking price drop graphics.",
                        "4-16s: Rapid-fire 30s breakdown of ANC earbuds, fast charger power bank, and smartwatch with true price history.",
                        "17-25s: 'Comment GADGET and I will send you the direct non-inflated sale links!'"
                    ],
                    "sound_style": "Crisp electronic synth beats with mechanical sound effects",
                    "optimal_post_window": "6-10 days before event, 6:30 PM IST",
                    "why_algorithm_favors": "High purchase intent driving high saves and click-throughs.",
                    "virality_score": 93
                },
                {
                    "concept_title": f"How to Take Insane 4K Festive Night Photos on Any Phone",
                    "hook_3s": "Stop taking blurry, overexposed Diya and festive photos with your phone.",
                    "hook_archetype": "Visual Tutorial",
                    "format_archetype": "Camera Screen-Recording Overlay",
                    "blueprint_flow": [
                        "0-3s: Bad photo (blown out bright light) vs stunning cinematic golden hour portrait.",
                        "4-16s: 3 camera settings to change: Lock exposure, pull brightness slider down by 30%, and wipe the camera lens.",
                        "17-25s: Reveal the final wallpaper-worthy shot. 'Try this tonight with candles!'"
                    ],
                    "sound_style": "Cinematic modern atmospheric soundscape",
                    "optimal_post_window": "3-5 days before event, 7:00 PM IST",
                    "why_algorithm_favors": "Direct immediate utility that viewers test within 24 hours.",
                    "virality_score": 96
                },
                {
                    "concept_title": f"Tech Gadgets You Must Keep Charged for {ev_name} Day",
                    "hook_3s": "The 3 tech mistakes that will ruin your festive family photos.",
                    "hook_archetype": "Mistake Callout",
                    "format_archetype": "Quick Checklist",
                    "blueprint_flow": [
                        "0-3s: Phone dying at 1% right during the cake cutting / puja moment.",
                        "4-15s: 3 must-haves: 65W fast charger, wireless mic for loud celebrations, and 50GB cloud space clear-out.",
                        "16-25s: 'Send this to the family member whose phone is always at 2% battery!'"
                    ],
                    "sound_style": "Fast tech-house punchy beat",
                    "optimal_post_window": "1-2 days before event, 7:30 PM IST",
                    "why_algorithm_favors": "High tagging of friends/family with notoriously dead phones.",
                    "virality_score": 90
                }
            ]
        else:
            # Pan-niche / Lifestyle default
            concepts = [
                {
                    "concept_title": f"The Ultimate {ev_name} Preparation Timeline",
                    "hook_3s": f"{wave['days_until']} days until {ev_name} — here is your step-by-step checklist.",
                    "hook_archetype": "Time-Sensitive Blueprint",
                    "format_archetype": "Aesthetic Checklist",
                    "blueprint_flow": [
                        "0-3s: Clean graphic checklist sliding on screen with festive background.",
                        "4-16s: Day-by-day prep guide: Outfits chosen by Day -5, Sweets sorted by Day -3, Day 0 fully relaxed.",
                        "17-25s: 'Save this checklist so you don't panic on festival eve!'"
                    ],
                    "sound_style": audio_vibe,
                    "optimal_post_window": f"{max(1, wave['days_until'] - 2)} days before {ev_name}, 7:00 PM IST",
                    "why_algorithm_favors": "High save-to-view ratio signals authority to the Instagram algorithm.",
                    "virality_score": 93
                },
                {
                    "concept_title": f"Expectation vs Reality: {ev_name} Celebrations",
                    "hook_3s": "What I thought my festival week would look like vs Reality.",
                    "hook_archetype": "Relatable Contrast",
                    "format_archetype": "Side-by-Side Video",
                    "blueprint_flow": [
                        "0-3s: Aesthetic Pinterest board of glowing lights and smiling calm people.",
                        "4-16s: Jump cut to you sweating, fighting with fairy lights, and running around last-minute.",
                        "17-25s: 'Drop a ❤️ if your festival always turns into chaotic fun!'"
                    ],
                    "sound_style": "Trending fast Indian comical dialogue remix",
                    "optimal_post_window": "2-4 days before event, 8:00 PM IST",
                    "why_algorithm_favors": "High emotional engagement and comment interactions.",
                    "virality_score": 95
                },
                {
                    "concept_title": f"Aesthetic {ev_name} Glow-Up Transition",
                    "hook_3s": "Watch this ordinary room / outfit transform for the festival in 3 seconds.",
                    "hook_archetype": "Visual Transformation",
                    "format_archetype": "Beat-Drop Transition",
                    "blueprint_flow": [
                        "0-3s: Plain everyday look / dark room matching the audio buildup.",
                        "4-8s: Clapping hands or snapping fingers on the exact bass drop.",
                        "9-25s: Explosive reveal of vibrant festive lighting, golden warm accents, and full ethnic attire in 4K."
                    ],
                    "sound_style": audio_vibe,
                    "optimal_post_window": "Festival Eve or Day of, 6:00 PM IST",
                    "why_algorithm_favors": "Audio synchrony and visual payoff drive high completion rate (watch time > 100%).",
                    "virality_score": 96
                }
            ]

        return {
            "event_name": ev_name,
            "event_slug": event_slug,
            "niche": niche,
            "wave_phase": wave,
            "audio_recommendation": audio_vibe,
            "recommended_hashtags": hashtags[:5],
            "is_ai_generated": False,
            "concepts": concepts
        }


if __name__ == "__main__":
    print("=== Cultural Event Calendar & Festive Radar ===")
    radar = CulturalEventCalendar.get_festive_radar(120, "fitness")
    print(f"Active Waves: {len(radar['active_wave_festivals'])}")
    print(f"Upcoming Horizon: {len(radar['upcoming_radar_festivals'])}")
    if radar['golden_opportunity']:
        g = radar['golden_opportunity']
        print(f"Golden Opportunity: {g['name']} ({g['wave_phase']['badge']}) - {g['days_until']} days away")
    
    ideas = CulturalEventCalendar.generate_festive_reel_ideas('karva_chauth_2026', 'fitness')
    print(f"Generated {len(ideas.get('concepts', []))} concepts for {ideas['event_name']}")
    for c in ideas.get('concepts', []):
        print(f" - {c['concept_title']} | Hook: '{c['hook_3s']}'")