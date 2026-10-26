"""
Seasonal & Cultural Event Intelligence Engine (Trendrop)
Permanent, dynamic recurrence engine supporting Indian cultural festivals,
global pop-culture viral spikes (Halloween, Valentine's, etc.), and commercial surge weeks.
"""
import os
import sys
import json
import random
import logging
import calendar
from datetime import datetime, timezone, timedelta, date
from typing import Dict, List, Optional, Any
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
    Calculate the 4-Phase Festive & Pop-Culture Viral Curve based on distance to the event date.
    
    Phases:
      1. PRE_RADAR (> 18 days out): Early scouting, script planning, and prop sourcing
      2. PRE_FESTIVE_SURGE (4 - 18 days out): Golden Filming Window (high reach, lowest saturation)
      3. PEAK_HYPE (1 - 3 days out): Peak velocity (GRWMs, countdowns, last-minute hacks)
      4. DAY_OF (Day 0): Saturation peak (feed flood, heavy personal greetings)
      5. AFTERMATH (-1 to -3 days after): Relatable recovery, detox, and comedy memes
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


# ==============================================================================
# CANONICAL SEASONAL & CULTURAL EVENT REGISTRY
# Recurrence-driven: No hardcoded years in event keys. Automatically rolls over.
# ==============================================================================
MASTER_EVENT_REGISTRY = {
    "navratri": {
        "name": "Navratri (Garba & Dandiya Nights)",
        "local_name": "नवरात्रि / गरबा",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-09-22",
            "2026": "2026-10-11",
            "2027": "2027-09-30",
            "2028": "2028-10-19",
            "2029": "2029-10-08",
            "2030": "2030-09-28"
        },
        "duration_days": 9,
        "primary_regions": ["gujarat", "maharashtra", "delhi", "rajasthan", "mumbai", "pan_india"],
        "feed_flood_intensity": 0.98,
        "content_themes": ["garba", "dandiya", "chaniya_choli", "falguni_pathak", "fasting_recipes", "garba_steps"],
        "content_automation": ["9 days 9 colors outfit series", "Fast Garba step tutorial", "Chaniya Choli styling hacks", "Navratri fasting meal prep"],
        "creator_opportunities": ["Ethnic jewellery & lehenga brands", "Garba venue promotions", "Beauty & waterproof makeup", "Dance workshops"],
        "niche_opportunities": {
            "fashion": 0.99,
            "dance": 1.0,
            "food": 0.88,
            "comedy": 0.94,
            "fitness": 0.90,
            "travel": 0.85,
            "tech": 0.70,
            "all": 0.96
        },
        "audio_vibe": "High-energy Dhol beats, Sanedo drops, modern Gujarati folk-fusion, Falguni Pathak remixes",
        "optimal_posting_days": [-14, -7, -3, -1, 0, 1],
        "hashtags": ["#Navratri2026", "#GarbaLover", "#DandiyaNights", "#NavratriLook", "#ChaniyaCholi", "#GarbaReels"],
        "trending_hashtags": ["#garba", "#navratri", "#falguni", "#dandiya", "#garbastyle"],
        "content_ideas": [
            "9 Days, 9 Colors: Aesthetic Chaniya Choli color transition reel",
            "3 Easy Garba Steps for Beginners so you don't stand awkwardly in the circle",
            "POV: Trying to find your friends inside a 10,000-person Garba ground",
            "Sweat-Proof Festive Makeup Routine that survives 4 hours of nonstop Garba"
        ]
    },
    "durga_puja": {
        "name": "Durga Puja",
        "local_name": "দুর্গাপূজা",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-09-28",
            "2026": "2026-10-17",
            "2027": "2027-10-06",
            "2028": "2028-10-24",
            "2029": "2029-10-13",
            "2030": "2030-10-02"
        },
        "duration_days": 5,
        "primary_regions": ["west_bengal", "assam", "tripura", "east_india", "delhi"],
        "feed_flood_intensity": 0.96,
        "content_themes": ["pujo", "pandal_hopping", "dhunuchi_naach", "saree_draping", "bengali_bhog", "sindoor_khela"],
        "content_automation": ["Pandal hopping guide", "Traditional Saree GRWM", "Dhunuchi dance challenge", "Bengali bhog recipes"],
        "creator_opportunities": ["Saree brand sponsorships", "Restaurant Pujo menu features", "Pandal media coverage", "Street photography"],
        "niche_opportunities": {
            "fashion": 0.98,
            "food": 0.95,
            "travel": 0.92,
            "dance": 0.90,
            "comedy": 0.85,
            "fitness": 0.70,
            "tech": 0.65,
            "all": 0.90
        },
        "audio_vibe": "Rhythmic Dhak beats, Shankha blowing acoustic swells, celebratory folk fusion",
        "optimal_posting_days": [-10, -5, -2, -1, 0],
        "hashtags": ["#DurgaPuja2026", "#PujoVibes", "#PandalHopping", "#DhakErAwaaj", "#KolkataDurgaPuja"],
        "trending_hashtags": ["#pujo", "#durgapuja", "#dhunuchinaach", "#pandal", "#bengaliculture"],
        "content_ideas": [
            "Top 5 theme pandals in North vs South Kolkata route map",
            "Red & White traditional Tant Saree draping in 60 seconds",
            "POV: Standing in the 2-hour queue outside a famous pandal at 2 AM",
            "High-energy Dhunuchi dance spin transition in slow-motion"
        ]
    },
    "dussehra": {
        "name": "Dussehra (Vijayadashami)",
        "local_name": "दशहरा / विजयदशमी",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-10-02",
            "2026": "2026-10-20",
            "2027": "2027-10-10",
            "2028": "2028-10-28",
            "2029": "2029-10-17",
            "2030": "2030-10-06"
        },
        "duration_days": 1,
        "primary_regions": ["north_india", "karnataka", "maharashtra", "delhi", "gujarat"],
        "feed_flood_intensity": 0.88,
        "content_themes": ["ramlila", "ravan_dahan", "victory_good_over_evil", "new_beginnings", "vehicle_puja", "mysore_dasara"],
        "content_automation": ["Ramlila highlights", "Ravan Dahan fireworks", "Festive wish reels", "Mysore Palace illumination"],
        "creator_opportunities": ["Local cultural event partnerships", "Ethnic wear brands", "Automobile puja sponsors"],
        "niche_opportunities": {
            "comedy": 0.92,
            "fashion": 0.88,
            "travel": 0.90,
            "finance": 0.78,
            "fitness": 0.75,
            "food": 0.82,
            "tech": 0.70,
            "all": 0.85
        },
        "audio_vibe": "Powerful percussion, Ram Siya Ram chants, cinematic bass drops on fireworks",
        "optimal_posting_days": [-7, -3, -1, 0],
        "hashtags": ["#Dussehra2026", "#Vijayadashami", "#RavanDahan", "#GoodOverEvil", "#HappyDussehra"],
        "trending_hashtags": ["#ravandahan", "#ramlila", "#mysoredasara", "#dussehraspecial"],
        "content_ideas": [
            "Ravan Dahan fireworks slow-mo drop at night",
            "Why Vijayadashami is considered the ultimate day for new investments/purchases",
            "POV: Trying to leave Ramlila ground before the crowd rushes out",
            "Mysore Palace lights turn-on moment cinematic reel"
        ]
    },
    "karva_chauth": {
        "name": "Karwa Chauth",
        "local_name": "करवा चौथ",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-10-10",
            "2026": "2026-10-29",
            "2027": "2027-10-19",
            "2028": "2028-10-27",
            "2029": "2029-10-16",
            "2030": "2030-11-04"
        },
        "duration_days": 1,
        "primary_regions": ["punjab", "delhi", "uttar_pradesh", "rajasthan", "haryana", "north_india"],
        "feed_flood_intensity": 0.93,
        "content_themes": ["sargi", "mehndi", "fasting_hacks", "red_lehenga", "moon_sighting", "couple_goals"],
        "content_automation": ["Mehndi design ideas", "Sargi thali prep", "Red ethnic outfit GRWM", "Moon sighting moment"],
        "creator_opportunities": ["Jewellery brand collaborations", "Mehndi artist showcases", "Skincare hydration tips", "Couple apparel"],
        "niche_opportunities": {
            "fashion": 0.99,
            "fitness": 0.88,
            "comedy": 0.94,
            "food": 0.80,
            "finance": 0.72,
            "travel": 0.60,
            "tech": 0.65,
            "all": 0.92
        },
        "audio_vibe": "Romantic Bollywood strings, Punjabi wedding acoustic, emotional sufi lo-fi",
        "optimal_posting_days": [-8, -5, -2, -1, 0],
        "hashtags": ["#KarvaChauth2026", "#KarwaChauthSpecial", "#MehndiDesigns", "#RedSaree", "#ChandChupaBadalMein"],
        "trending_hashtags": ["#karwachauthlook", "#sargithali", "#chandkabniklega", "#fastinggoals"],
        "content_ideas": [
            "5-Minute Sargi Thali checklist to sustain energy all day without fainting",
            "Red Saree transition with heirloom jewellery reveal",
            "POV: Husband tracking the moon on weather satellites from 6 PM",
            "Non-greasy, long-lasting mehndi aftercare tips for deepest stain"
        ]
    },
    "halloween": {
        "name": "Halloween",
        "local_name": "हैलॉवीन / Spooky Season",
        "category": "global_pop",
        "category_label": "🌐 Global Pop & Viral",
        "recurrence_type": "fixed_solar",
        "month": 10,
        "day": 31,
        "duration_days": 1,
        "primary_regions": ["global", "metro_india", "mumbai", "delhi", "bangalore", "pune", "hyderabad"],
        "feed_flood_intensity": 0.95,
        "content_themes": ["sfx_makeup", "costume_transformation", "horror_transition", "spooky_treats", "tim_burton", "ghost_filter"],
        "content_automation": [
            "10-Minute budget costume DIY with clothes you own",
            "SFX cut/wound tutorial using kajal & lipstick",
            "Spooky mocktails with dry ice bubbling effect",
            "POV: Trying to explain Halloween dress-up to desi parents"
        ],
        "creator_opportunities": [
            "Cosmetics & FX makeup brands",
            "Party venue showcases & nightlife",
            "Snack, bakery & mocktail brand sponsorships",
            "Fashion thrift & DIY apparel collabs"
        ],
        "niche_opportunities": {
            "fashion": 0.98,
            "dance": 0.94,
            "food": 0.92,
            "comedy": 0.95,
            "tech": 0.88,
            "fitness": 0.82,
            "travel": 0.85,
            "finance": 0.70,
            "all": 0.93
        },
        "audio_vibe": "Dark synthwave, eerie phonk bass drops, Michael Jackson Thriller remix, Wednesday Addams cello, spooky dialogue hooks",
        "optimal_posting_days": [-18, -10, -5, -2, -1, 0],
        "hashtags": ["#Halloween2026", "#SpookySeason", "#HalloweenCostume", "#HalloweenMakeup", "#CostumeTransformation", "#HalloweenReels"],
        "trending_hashtags": ["#spookyvibes", "#halloweenvibes", "#sfxmakeup", "#costumeideas", "#horrorreels"],
        "content_ideas": [
            "10-Minute SFX Vampire/Goth Glam transformation with drugstore makeup",
            "POV: Trying to explain Halloween dress-up to your desi Indian parents",
            "3 Spooky dry-ice bubbling party drinks in under 60 seconds",
            "VFX Tutorial: Floating ghost illusion in CapCut in 3 easy steps"
        ]
    },
    "diwali": {
        "name": "Diwali (Festival of Lights)",
        "local_name": "दीपावली / दिवाली",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-10-20",
            "2026": "2026-11-08",
            "2027": "2027-10-29",
            "2028": "2028-10-17",
            "2029": "2029-11-05",
            "2030": "2030-10-26"
        },
        "duration_days": 3,
        "primary_regions": ["pan_india", "north_india", "west_india", "south_india", "east_india", "global_diaspora"],
        "feed_flood_intensity": 0.99,
        "content_themes": ["diwali_cleaning", "dhanteras", "rangoli_hacks", "mithai_making", "diwali_outfits", "card_parties", "patakha_comedy"],
        "content_automation": ["Diwali Safai transformation", "Dhanteras gold buying guide", "Easy Rangoli tool hacks", "Card party snack platter"],
        "creator_opportunities": ["Home decor sponsorships", "Festive gifting kits", "Ethnic wear campaigns", "Appliance brand tie-ups"],
        "niche_opportunities": {
            "fashion": 0.99,
            "food": 0.98,
            "comedy": 0.97,
            "finance": 0.95,
            "fitness": 0.90,
            "travel": 0.88,
            "tech": 0.92,
            "all": 0.98
        },
        "audio_vibe": "Uplifting festive sitar-tabla drops, high-tempo celebratory Bollywood, nostalgic retro fusion",
        "optimal_posting_days": [-14, -8, -4, -2, -1, 0],
        "hashtags": ["#Diwali2026", "#Deepavali", "#DiwaliSafai", "#FestivalOfLights", "#DiwaliLook", "#MuhuratTrading"],
        "trending_hashtags": ["#diwalivibes", "#diwalireels", "#diwalihacks", "#diwalisweets", "#festiveseason"],
        "content_ideas": [
            "POV: Mom assigning cleaning duties on Diwali Safai weekend",
            "5-Minute Rangoli using everyday kitchen utensils (Forks, bottle caps)",
            "Festive Sweet Platter without refined sugar for fitness lovers",
            "The Dhanteras Gold vs SGB breakdown for young investors"
        ]
    },
    "bhai_dooj": {
        "name": "Bhai Dooj",
        "local_name": "भाई दूज / भाऊबीज",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-10-22",
            "2026": "2026-11-10",
            "2027": "2027-10-31",
            "2028": "2028-10-19",
            "2029": "2029-11-07",
            "2030": "2030-10-28"
        },
        "duration_days": 1,
        "primary_regions": ["north_india", "maharashtra", "gujarat", "bengal", "bihar"],
        "feed_flood_intensity": 0.82,
        "content_themes": ["sibling_rivalry", "bhai_dooj_gifts", "tika_ceremony", "family_lunch", "relatable_brother_sister"],
        "content_automation": ["Sibling comedy skits", "Budget gift guide for sisters", "Tika ceremony GRWM", "Sibling roast reel"],
        "creator_opportunities": ["Gadget gifting collabs", "Cosmetics hampers", "Chocolates & confectionery partnerships"],
        "niche_opportunities": {
            "comedy": 0.98,
            "fashion": 0.85,
            "tech": 0.88,
            "food": 0.80,
            "finance": 0.70,
            "fitness": 0.65,
            "travel": 0.60,
            "all": 0.88
        },
        "audio_vibe": "Fun acoustic guitar, playful brother-sister Bollywood soundtrack, warm wholesome lo-fi",
        "optimal_posting_days": [-5, -2, -1, 0],
        "hashtags": ["#BhaiDooj2026", "#SiblingGoals", "#BrotherSisterLove", "#BhaiDoojGifts", "#Bhaubeej"],
        "trending_hashtags": ["#siblingrivalry", "#bhaidoojlook", "#brothersister", "#festivebonding"],
        "content_ideas": [
            "POV: Demanding cash instead of a gift from your brother on Bhai Dooj",
            "Top 5 Tech Gifts under ₹2,000 for your sister",
            "Wholesome sibling childhood photo vs now glow-up transition"
        ]
    },
    "chhath_puja": {
        "name": "Chhath Puja",
        "local_name": "छठ पूजा",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-10-27",
            "2026": "2026-11-15",
            "2027": "2027-11-04",
            "2028": "2028-10-24",
            "2029": "2029-11-11",
            "2030": "2030-11-01"
        },
        "duration_days": 4,
        "primary_regions": ["bihar", "eastern_up", "jharkhand", "delhi_ncr", "mumbai", "purvanchal"],
        "feed_flood_intensity": 0.94,
        "content_themes": ["thekua_recipe", "sandhya_arghya", "suryadev_worship", "ghat_decor", "chhoti_chhath", "kharna"],
        "content_automation": ["Traditional Thekua making recipe", "Ghat sunrise timelapse", "Chhath devotion aesthetic reel"],
        "creator_opportunities": ["Flour & Ghee brand partnerships", "Traditional brassware showcases", "Regional cultural documentaries"],
        "niche_opportunities": {
            "food": 0.97,
            "travel": 0.93,
            "fashion": 0.82,
            "comedy": 0.60,
            "fitness": 0.75,
            "finance": 0.50,
            "tech": 0.60,
            "all": 0.85
        },
        "audio_vibe": "Soulful Sharda Sinha Chhath geet, traditional shehnai, pure riverbank dawn ambience",
        "optimal_posting_days": [-8, -4, -2, -1, 0],
        "hashtags": ["#ChhathPuja2026", "#ChhathGeet", "#Thekua", "#Arghya", "#BiharDiaries", "#SuryaUpasana"],
        "trending_hashtags": ["#chhathmahaparv", "#biharculture", "#chhathghat", "#thekuarecipe"],
        "content_ideas": [
            "Authentic Khasta Thekua recipe using traditional wooden sancha",
            "4:30 AM Sunrise Arghya timelapse at the riverbank with Sharda Sinha vocals",
            "Why Chhath Puja is considered the most eco-friendly festival in the world"
        ]
    },
    "black_friday": {
        "name": "Black Friday & Cyber Week",
        "local_name": "ब्लैक फ्राइडे / Shopping Surge",
        "category": "commercial_tech",
        "category_label": "🛍️ Shopping & Sales",
        "recurrence_type": "nth_weekday",
        "month": 11,
        "weekday": 4,  # Friday
        "nth": 4,
        "duration_days": 4,
        "primary_regions": ["global", "metro_india", "delhi", "mumbai", "bangalore", "hyderabad"],
        "feed_flood_intensity": 0.94,
        "content_themes": ["gadget_deals", "sneaker_drops", "software_deals", "fashion_sale", "budget_buying_guide"],
        "content_automation": ["Top 5 real tech discounts vs fake sales", "Sneaker sale haul & try-on", "Secret software lifetime deals"],
        "creator_opportunities": ["Affiliate marketing links", "Tech brand sponsorships", "Fashion e-commerce hauls", "Credit card cashbacks"],
        "niche_opportunities": {
            "tech": 1.0,
            "fashion": 0.96,
            "finance": 0.95,
            "fitness": 0.85,
            "food": 0.70,
            "all": 0.92
        },
        "audio_vibe": "Fast-paced corporate bass, futuristic electronic synth, energetic hype drop",
        "optimal_posting_days": [-10, -5, -2, -1, 0, 1],
        "hashtags": ["#BlackFriday2026", "#CyberMonday", "#TechDeals", "#SaleAlert", "#BudgetShopping", "#AmazonDeals"],
        "trending_hashtags": ["#blackfridaysale", "#shoppinghaul", "#techdeals", "#salehack"],
        "content_ideas": [
            "Don't get tricked: How to check price history before buying on Black Friday",
            "Top 5 Tech Steals under ₹3,000 actually worth your money",
            "POV: Refreshing your cart at midnight vs Out of Stock banner"
        ]
    },
    "christmas": {
        "name": "Christmas",
        "local_name": "क्रिसमस / Bada Din",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "fixed_solar",
        "month": 12,
        "day": 25,
        "duration_days": 1,
        "primary_regions": ["goa", "kerala", "mumbai", "northeast_india", "bangalore", "kolkata", "global"],
        "feed_flood_intensity": 0.92,
        "content_themes": ["christmas_tree", "plum_cake", "secret_santa", "winter_fashion", "cozy_aesthetic", "goa_christmas"],
        "content_automation": ["Secret Santa gift guide under ₹500", "Plum cake baking ASMR", "Winter cozy outfit layering", "Park Street Kolkata lighting walk"],
        "creator_opportunities": ["Bakery & confectionery features", "Winter apparel styling", "Party decor collaborations"],
        "niche_opportunities": {
            "food": 0.97,
            "fashion": 0.96,
            "travel": 0.92,
            "comedy": 0.88,
            "fitness": 0.72,
            "finance": 0.75,
            "tech": 0.80,
            "all": 0.90
        },
        "audio_vibe": "Jingle bell acoustic jazz, warm fireside lofi, modern pop Christmas remixes",
        "optimal_posting_days": [-14, -7, -3, -1, 0],
        "hashtags": ["#Christmas2026", "#MerryChristmas", "#SecretSanta", "#WinterFashion", "#GoaChristmas", "#PlumCake"],
        "trending_hashtags": ["#christmasvibes", "#christmastree", "#secretsantagifts", "#wintercozy"],
        "content_ideas": [
            "5 Secret Santa Gifts under ₹500 that your coworkers won't immediately re-gift",
            "No-Oven Rich Fruit Plum Cake recipe for beginners",
            "Walking through Kolkata's Park Street illuminated for Christmas Eve in 4K"
        ]
    },
    "new_year": {
        "name": "New Year's Eve & Day",
        "local_name": "नया साल / 2027 Countdown",
        "category": "global_pop",
        "category_label": "🌐 Global Pop & Viral",
        "recurrence_type": "fixed_solar",
        "month": 12,
        "day": 31,
        "duration_days": 1,
        "primary_regions": ["global", "pan_india", "mumbai", "delhi", "bangalore", "goa"],
        "feed_flood_intensity": 0.98,
        "content_themes": ["new_year_resolutions", "recap_reel", "countdown_party", "fitness_goals", "reset_routine", "glowup_journey"],
        "content_automation": ["2026 Year Recap Template", "NYE Party Glam outfit reveal", "Realistic New Year habits that actually stick", "POV: Sleeping through 12 AM"],
        "creator_opportunities": ["Fitness gym membership drives", "Planner & productivity stationery", "Party wear & footwear brands"],
        "niche_opportunities": {
            "fitness": 1.0,
            "finance": 0.98,
            "fashion": 0.96,
            "comedy": 0.95,
            "food": 0.82,
            "tech": 0.90,
            "travel": 0.88,
            "all": 0.96
        },
        "audio_vibe": "Cinematic emotional buildup into explosive midnight EDM drop, nostalgic acoustic year review",
        "optimal_posting_days": [-7, -3, -1, 0, 1],
        "hashtags": ["#NewYear2027", "#NYE2026", "#YearRecap", "#NewYearResolution", "#GlowUp", "#ResetRoutine"],
        "trending_hashtags": ["#nyeoutfit", "#newyearnewme", "#recap2026", "#fitnessgoals2027"],
        "content_ideas": [
            "Stop setting 10 unrealistic New Year resolutions: Do this 1 habit stack instead",
            "12-second aesthetic photo dump template of your best 2026 moments",
            "POV: Introverts on New Year's Eve staying home with food vs Club Chaos"
        ]
    },
    "valentines_day": {
        "name": "Valentine's Week",
        "local_name": "वैलेंटाइन डे / Love Season",
        "category": "global_pop",
        "category_label": "🌐 Global Pop & Viral",
        "recurrence_type": "fixed_solar",
        "month": 2,
        "day": 14,
        "duration_days": 7,
        "primary_regions": ["global", "pan_india", "delhi", "mumbai", "bangalore", "kolkata"],
        "feed_flood_intensity": 0.94,
        "content_themes": ["rose_day", "date_night_ideas", "singles_humor", "couple_outfits", "diy_gifts", "budget_date"],
        "content_automation": ["Date night outfit GRWM", "Budget DIY gift hamper", "POV: Singles during Valentine's week", "Romantic dinner spot guide"],
        "creator_opportunities": ["Perfume & fragrance brands", "Jewellery & apparel gifts", "Chocolates & dining experiences"],
        "niche_opportunities": {
            "fashion": 0.98,
            "comedy": 0.97,
            "food": 0.94,
            "travel": 0.88,
            "fitness": 0.70,
            "finance": 0.75,
            "tech": 0.65,
            "all": 0.92
        },
        "audio_vibe": "Romantic acoustic indie, soft R&B guitar riffs, trending emotional Bollywood drops",
        "optimal_posting_days": [-10, -5, -2, -1, 0],
        "hashtags": ["#ValentinesDay2027", "#DateNightLook", "#ValentinesGift", "#CoupleGoals", "#SingleLifeHumor"],
        "trending_hashtags": ["#valentineslook", "#diyvalentinesgift", "#datenightoutfit", "#singlevibes"],
        "content_ideas": [
            "3 Date Night outfit ideas under ₹1,500 that look luxurious",
            "POV: Being single during Valentine's week vs My bank account",
            "How to cook a 3-course restaurant-quality candlelit dinner at home"
        ]
    },
    "makar_sankranti_pongal": {
        "name": "Makar Sankranti & Pongal",
        "local_name": "मकर संक्रांति / பொங்கல் / Uttarayan",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "fixed_solar",
        "month": 1,
        "day": 14,
        "duration_days": 2,
        "primary_regions": ["tamil_nadu", "gujarat", "maharashtra", "andhra_pradesh", "karnataka", "punjab"],
        "feed_flood_intensity": 0.88,
        "content_themes": ["kite_flying", "uttarayan_terrace", "sweet_pongal", "til_gul", "harvest_celebration", "kolam_art"],
        "content_automation": ["Terrace kite fight battle reel", "Traditional Sakkarai Pongal in clay pot", "Tilgur laddu recipe in 15 mins"],
        "creator_opportunities": ["Traditional kitchenware", "Sun protection / sunglasses brands", "Ethnic cotton wear"],
        "niche_opportunities": {
            "food": 0.96,
            "comedy": 0.88,
            "travel": 0.86,
            "fashion": 0.82,
            "fitness": 0.75,
            "all": 0.86
        },
        "audio_vibe": "High-energy whistling terrace chants (Kai Po Che), rhythmic folk nadaswaram, joyful fusion",
        "optimal_posting_days": [-6, -3, -1, 0],
        "hashtags": ["#MakarSankranti2027", "#Pongal2027", "#KaiPoChe", "#Uttarayan", "#TilGulGhya", "#HarvestFestival"],
        "trending_hashtags": ["#kiteflying", "#pongalcelebration", "#terracevibes", "#tilgurladdoo"],
        "content_ideas": [
            "POV: That one competitive cousin on the terrace during Uttarayan kite wars",
            "Authentic temple-style Sweet Pongal recipe with ghee-roasted cashews",
            "Spectacular drone view of Gujarat skies filled with 10,000 kites"
        ]
    },
    "republic_day": {
        "name": "Republic Day",
        "local_name": "गणतंत्र दिवस",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "fixed_solar",
        "month": 1,
        "day": 26,
        "duration_days": 1,
        "primary_regions": ["pan_india", "delhi", "all_states"],
        "feed_flood_intensity": 0.86,
        "content_themes": ["kartavya_path_parade", "tri_color_aesthetic", "patriotism", "indian_heritage", "tri_color_recipes"],
        "content_automation": ["Tricolor food recipe", "Kartavya Path flypast highlights", "Tricolor ethnic styling"],
        "creator_opportunities": ["Made in India brand features", "National pride campaigns", "Educational infographics"],
        "niche_opportunities": {
            "food": 0.90,
            "fashion": 0.85,
            "fitness": 0.82,
            "comedy": 0.65,
            "travel": 0.80,
            "all": 0.82
        },
        "audio_vibe": "Inspiring orchestral national anthems, modern patriotic guitar riffs (Vande Mataram, Teri Mitti)",
        "optimal_posting_days": [-5, -2, -1, 0],
        "hashtags": ["#RepublicDay2027", "#26January", "#VandeMataram", "#ProudIndian", "#KartavyaPath"],
        "trending_hashtags": ["#tricolorfood", "#indianairforce", "#deshbhakti"],
        "content_ideas": [
            "3-Layered Tricolor Idli / Smoothie bowl aesthetic recipe",
            "Goosebump moments from the Indian Air Force Republic Day flypast in 4K",
            "Why the Indian Constitution is the longest and most detailed written charter in the world"
        ]
    },
    "maha_shivratri": {
        "name": "Maha Shivratri",
        "local_name": "महाशिवरात्रि",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-02-26",
            "2026": "2026-02-15",
            "2027": "2027-03-06",
            "2028": "2028-02-24",
            "2029": "2029-02-12",
            "2030": "2030-03-03"
        },
        "duration_days": 1,
        "primary_regions": ["varanasi", "kashmir", "uttar_pradesh", "maharashtra", "south_india", "pan_india"],
        "feed_flood_intensity": 0.91,
        "content_themes": ["shiv_tandav", "varanasi_ghat", "fasting_sattvic_food", "night_vigil", "spiritual_meditation"],
        "content_automation": ["Shiv Tandav powerful bass audio reel", "Varanasi Maha Aarti night walkthrough", "Fasting recipes"],
        "creator_opportunities": ["Spiritual & wellness retreats", "Ayurvedic products", "Temple tourism content"],
        "niche_opportunities": {
            "travel": 0.95,
            "dance": 0.92,
            "fitness": 0.88,
            "food": 0.84,
            "all": 0.88
        },
        "audio_vibe": "Deep Shiva chants (Har Har Shambhu, Shiv Tandav Stotram), booming Damru percussion, meditative flute",
        "optimal_posting_days": [-6, -3, -1, 0],
        "hashtags": ["#MahaShivratri2027", "#HarHarMahadev", "#ShivTandav", "#VaranasiGhats", "#Bholenath"],
        "trending_hashtags": ["#omnamahshivaya", "#shivshakti", "#kashivishwanath"],
        "content_ideas": [
            "Powerful classical dance transition on Shiv Tandav Stotram bass drop",
            "4K Night walking tour of Varanasi Ghats during Maha Shivratri",
            "The science behind fasting and staying awake on the night of Shivratri"
        ]
    },
    "holi": {
        "name": "Holi (Festival of Colors)",
        "local_name": "होली / धुलंडी",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-03-14",
            "2026": "2026-03-03",
            "2027": "2027-03-22",
            "2028": "2028-03-11",
            "2029": "2029-03-01",
            "2030": "2030-03-19"
        },
        "duration_days": 2,
        "primary_regions": ["north_india", "braj_mathura", "west_bengal", "maharashtra", "pan_india", "global"],
        "feed_flood_intensity": 0.99,
        "content_themes": ["color_explosions", "gujiya_making", "holi_skincare", "water_balloon_skits", "lathmar_holi", "holi_outfit"],
        "content_automation": ["Pre & Post Holi Skincare/Haircare routine", "Crispy Mawa Gujiya recipe", "Slow-motion color explosion drop", "White kurta to rainbow color transition"],
        "creator_opportunities": ["Skincare & sunscreen brands", "Hair oil & deep conditioners", "White cotton apparel", "Party & event organizers"],
        "niche_opportunities": {
            "fashion": 0.98,
            "food": 0.97,
            "comedy": 0.98,
            "dance": 0.96,
            "fitness": 0.78,
            "all": 0.97
        },
        "audio_vibe": "Explosive Dholak-Dhol beats, Rang Barse remixed with modern bass drops, energetic Bollywood party tracks",
        "optimal_posting_days": [-10, -5, -2, -1, 0, 1],
        "hashtags": ["#Holi2027", "#FestivalOfColors", "#RangBarse", "#HoliLook", "#GujiyaRecipe", "#BalamPichkari"],
        "trending_hashtags": ["#holivibes", "#holiparty", "#colorblast", "#holiskincare"],
        "content_ideas": [
            "The Ultimate Pre-Holi Hair & Skin Armor: Oils to apply so colors wash out in 1 shower",
            "POV: Trying to walk home peacefully on Holi morning in an Indian neighborhood",
            "Slow-motion Gulal cloud throw with high-tempo Bollywood drop"
        ]
    },
    "eid_ul_fitr": {
        "name": "Eid ul-Fitr",
        "local_name": "ईद-उल-फ़ित्र",
        "category": "cultural_in",
        "category_label": "🪔 Indian Cultural",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-03-31",
            "2026": "2026-03-20",
            "2027": "2027-03-10",
            "2028": "2028-02-27",
            "2029": "2029-02-15",
            "2030": "2030-02-05"
        },
        "duration_days": 2,
        "primary_regions": ["hyderabad", "delhi", "lucknow", "kerala", "mumbai", "kashmir", "global"],
        "feed_flood_intensity": 0.95,
        "content_themes": ["sheer_khurma", "biryani_feasts", "eid_outfit_grwm", "chaand_raat", "eidi_skits", "itr_perfumes"],
        "content_automation": ["Authentic Sheer Khurma recipe", "Chaand Raat shopping walkthrough", "Eid ethnic kurta styling"],
        "creator_opportunities": ["Ethnic menswear & shararas", "Attar / luxury perfumes", "Culinary feast collaborations"],
        "niche_opportunities": {
            "food": 0.99,
            "fashion": 0.98,
            "comedy": 0.90,
            "travel": 0.88,
            "all": 0.94
        },
        "audio_vibe": "Soulful acoustic Qawwali, celebratory Sufi lo-fi, melodic harmonium and tabla drops",
        "optimal_posting_days": [-8, -4, -2, -1, 0],
        "hashtags": ["#EidMubarak2027", "#EidUlFitr", "#SheerKhurma", "#ChaandRaat", "#EidOutfit", "#Eidi"],
        "trending_hashtags": ["#eidlook", "#eidfeast", "#chaandraatvibes", "#eidreels"],
        "content_ideas": [
            "The Secret to 100-Year-Old Traditional Sheer Khurma (Step by Step)",
            "Chaand Raat street food tour in Old Delhi / Charminar at 3 AM",
            "POV: Counting your Eidi money after all the relatives leave"
        ]
    },
    "ipl_season": {
        "name": "IPL Opening Season",
        "local_name": "आईपीएल / Cricket Festival",
        "category": "sports_entertainment",
        "category_label": "🏏 Sports Season",
        "recurrence_type": "lunisolar_lookup",
        "dates": {
            "2025": "2025-03-22",
            "2026": "2026-03-28",
            "2027": "2027-03-27",
            "2028": "2028-03-25",
            "2029": "2029-03-24",
            "2030": "2030-03-23"
        },
        "duration_days": 60,
        "primary_regions": ["pan_india", "chennai", "mumbai", "bangalore", "kolkata", "delhi"],
        "feed_flood_intensity": 0.97,
        "content_themes": ["matchday_vibes", "fan_rivalry", "stadium_snacks", "jersey_styling", "cricket_memes", "ipl_watch_party"],
        "content_automation": ["Watch party snack platter", "POV: CSK vs RCB fans in the same living room", "Stadium vlog"],
        "creator_opportunities": ["Sports apparel & jerseys", "Food delivery apps (Swiggy/Zomato)", "Beverage brand collaborations"],
        "niche_opportunities": {
            "comedy": 1.0,
            "food": 0.94,
            "fashion": 0.88,
            "fitness": 0.85,
            "tech": 0.80,
            "finance": 0.82,
            "all": 0.94
        },
        "audio_vibe": "Stadium horns, high-energy anthems (Whistle Podu, Korbo Lorbo, RCB chant), fast cinematic beat drops",
        "optimal_posting_days": [-10, -5, -2, 0, 1],
        "hashtags": ["#IPL2027", "#TataIPL", "#CricketLovers", "#MatchDay", "#CSKvsRCB", "#CricketReels"],
        "trending_hashtags": ["#iplreels", "#iplmemes", "#cricketfever", "#matchdayvibes"],
        "content_ideas": [
            "POV: Explaining to your non-cricket partner why the next 2 months of your life are booked 7:30 PM daily",
            "Stadium-style crispy Loaded Nachos in 10 minutes before the first ball",
            "Can an average gym-goer sprint between wickets as fast as Virat Kohli? (Fitness Test)"
        ]
    }
}


# ==============================================================================
# SEASONAL & CULTURAL ENGINE CLASS
# ==============================================================================
class SeasonalEventEngine:
    """
    Self-rolling, recurrence-driven seasonal & cultural trend intelligence engine.
    Calculates dynamic dates across years, 4-phase virality curves, and niche-specific blueprints.
    """

    @staticmethod
    def resolve_event_date_for_year(event_data: Dict[str, Any], target_year: int) -> Optional[date]:
        """
        Dynamically calculate or lookup the exact calendar date for a given year.
        Handles fixed solar dates, nth-weekdays, and lunisolar astronomical dates.
        """
        rtype = event_data.get("recurrence_type")
        if rtype == "fixed_solar":
            try:
                return date(target_year, event_data["month"], event_data["day"])
            except ValueError:
                return None
        elif rtype == "nth_weekday":
            try:
                cal = calendar.monthcalendar(target_year, event_data["month"])
                weekday = event_data["weekday"]
                days = [week[weekday] for week in cal if week[weekday] != 0]
                nth = event_data["nth"]
                chosen_day = days[nth - 1] if nth <= len(days) else days[-1]
                return date(target_year, event_data["month"], chosen_day)
            except Exception:
                return None
        elif rtype == "lunisolar_lookup":
            dates_map = event_data.get("dates", {})
            date_str = dates_map.get(str(target_year))
            if date_str:
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass
        return None

    @classmethod
    def resolve_next_occurrence(cls, canonical_slug: str, event_data: Dict[str, Any], reference_date: Optional[date] = None) -> Optional[Dict[str, Any]]:
        """
        Finds the current active or next upcoming occurrence of an event relative to reference_date.
        If an event is past its 3-day aftermath in the current year, it automatically rolls to next year.
        """
        today = reference_date or datetime.now(timezone.utc).date()
        current_year = today.year

        # 1. Check current year
        candidate_date = cls.resolve_event_date_for_year(event_data, current_year)
        chosen_year = current_year

        # If date has passed aftermath (event_date < today - 3 days), roll over to next year
        if not candidate_date or candidate_date < (today - timedelta(days=3)):
            candidate_date = cls.resolve_event_date_for_year(event_data, current_year + 1)
            chosen_year = current_year + 1

        if not candidate_date:
            return None

        days_until = (candidate_date - today).days
        date_iso = candidate_date.isoformat()
        wave = calculate_wave_phase(date_iso)

        resolved = event_data.copy()
        resolved["canonical_slug"] = canonical_slug
        resolved["slug"] = f"{canonical_slug}_{chosen_year}"
        resolved["year"] = chosen_year
        resolved["date"] = date_iso
        resolved["start_date"] = date_iso
        resolved["event_date"] = date_iso
        resolved["event_name"] = event_data["name"]
        resolved["days_until"] = days_until
        resolved["is_upcoming"] = days_until >= 0
        resolved["wave_phase"] = wave
        return resolved

    @classmethod
    def get_all_resolved_events_dict(cls, reference_date: Optional[date] = None) -> Dict[str, Dict[str, Any]]:
        """
        Returns a dictionary of all active/upcoming events, keyed by BOTH
        their year-specific slug (e.g. 'halloween_2026') AND canonical slug ('halloween').
        Guarantees 100% backwards compatibility for legacy lookups.
        """
        today = reference_date or datetime.now(timezone.utc).date()
        result = {}
        for canonical_slug, data in MASTER_EVENT_REGISTRY.items():
            resolved = cls.resolve_next_occurrence(canonical_slug, data, today)
            if resolved:
                year_slug = resolved["slug"]
                result[year_slug] = resolved
                # Also alias under canonical slug for flexible lookup
                result[canonical_slug] = resolved
        return result

    # Dynamic property for backwards compatibility with `CulturalEventCalendar.CULTURAL_EVENTS`
    class _EventsDictProxy(dict):
        def __getitem__(self, key):
            events = SeasonalEventEngine.get_all_resolved_events_dict()
            return events[key]
        def get(self, key, default=None):
            events = SeasonalEventEngine.get_all_resolved_events_dict()
            return events.get(key, default)
        def items(self):
            events = SeasonalEventEngine.get_all_resolved_events_dict()
            return events.items()
        def values(self):
            events = SeasonalEventEngine.get_all_resolved_events_dict()
            return events.values()
        def keys(self):
            events = SeasonalEventEngine.get_all_resolved_events_dict()
            return events.keys()
        def __contains__(self, key):
            events = SeasonalEventEngine.get_all_resolved_events_dict()
            return key in events
        def __len__(self):
            events = SeasonalEventEngine.get_all_resolved_events_dict()
            return len(events)

    CULTURAL_EVENTS = _EventsDictProxy()

    @classmethod
    def get_upcoming_events(cls, days_ahead: int = 150, category: Optional[str] = None) -> List[Dict]:
        """
        Get upcoming seasonal & cultural events within specified days, enriched with wave phases.
        """
        today = datetime.now(timezone.utc).date()
        cutoff_date = today + timedelta(days=days_ahead)
        upcoming = []

        seen_slugs = set()
        for canonical_slug, data in MASTER_EVENT_REGISTRY.items():
            ev = cls.resolve_next_occurrence(canonical_slug, data, today)
            if not ev:
                continue
            ev_date = datetime.fromisoformat(ev["date"]).date()
            if (today - timedelta(days=3)) <= ev_date <= cutoff_date:
                if category and category != "all" and ev.get("category") != category:
                    continue
                if ev["slug"] not in seen_slugs:
                    seen_slugs.add(ev["slug"])
                    upcoming.append(ev)

        upcoming.sort(key=lambda x: x["days_until"])
        return upcoming

    @classmethod
    def get_festive_radar(cls, days_ahead: int = 150, niche: Optional[str] = None, category: Optional[str] = None) -> Dict:
        """
        Returns full Seasonal & Cultural Viral Radar with active waves, golden filming windows,
        category breakdowns, and niche compatibility rankings.
        """
        events = cls.get_upcoming_events(days_ahead=days_ahead, category=category)
        active_surge_events = []
        upcoming_horizon_events = []
        concluded_events = []

        target_niche = (niche or "all").lower().strip()

        for ev in events:
            niche_opps = ev.get("niche_opportunities", {})
            niche_score = int(niche_opps.get(target_niche, niche_opps.get("all", 0.8)) * 100)
            ev["niche_fit_score"] = niche_score
            ev["target_niche"] = target_niche

            phase_code = ev["wave_phase"]["phase"]
            if phase_code in ("PRE_FESTIVE_SURGE", "PEAK_HYPE", "DAY_OF", "AFTERMATH"):
                active_surge_events.append(ev)
            elif phase_code == "PRE_RADAR":
                upcoming_horizon_events.append(ev)
            else:
                concluded_events.append(ev)

        # Highlight: event currently in golden filming surge, or closest peak
        golden_event = next(
            (e for e in active_surge_events if e["wave_phase"]["phase"] == "PRE_FESTIVE_SURGE"),
            active_surge_events[0] if active_surge_events else (upcoming_horizon_events[0] if upcoming_horizon_events else None)
        )

        return {
            "current_date": datetime.now(timezone.utc).date().isoformat(),
            "target_niche": target_niche,
            "category_filter": category or "all",
            "golden_opportunity": golden_event,
            "active_wave_festivals": active_surge_events,
            "upcoming_radar_festivals": upcoming_horizon_events,
            "total_monitored": len(events)
        }

    @classmethod
    def get_event_content_suggestions(cls, event_name: str, region: Optional[str] = None) -> Dict:
        """Legacy helper for backwards compatibility."""
        events = cls.get_all_resolved_events_dict()
        target = None
        for ev in events.values():
            if ev["name"].lower() == event_name.lower() or ev.get("canonical_slug", "").lower() == event_name.lower() or ev.get("slug", "").lower() == event_name.lower():
                target = ev
                break

        if not target:
            return {"error": f"Event {event_name} not found", "available_events": [e["name"] for e in events.values()]}

        return {
            "event_name": target["name"],
            "date": target["date"],
            "duration_days": target["duration_days"],
            "content_themes": target["content_themes"],
            "hashtags": target["hashtags"],
            "trending_hashtags": target.get("trending_hashtags", []),
            "content_ideas": target.get("content_ideas", []),
            "optimal_posting_days": target.get("optimal_posting_days", [-7, -3, 0])
        }

    @classmethod
    def get_optimal_posting_window(cls, event_name: str) -> Dict:
        """Legacy helper for backwards compatibility."""
        events = cls.get_all_resolved_events_dict()
        target = None
        for ev in events.values():
            if ev["name"].lower() == event_name.lower() or ev.get("canonical_slug", "").lower() == event_name.lower() or ev.get("slug", "").lower() == event_name.lower():
                target = ev
                break

        if not target:
            return {"error": "Event not found"}

        event_date = datetime.fromisoformat(target["date"])
        optimal_dates = []
        for day_offset in target.get("optimal_posting_days", [-7, -3, 0]):
            target_date = event_date + timedelta(days=day_offset)
            optimal_dates.append({
                "date": target_date.date().isoformat(),
                "days_offset": day_offset,
                "label": f"{'Day before' if day_offset < 0 else 'Day after' if day_offset > 0 else 'Event day'} {abs(day_offset)}" if day_offset != 0 else "Event day"
            })

        return {
            "event_date": target["date"],
            "optimal_dates": optimal_dates,
            "optimal_times": ["18:00-21:00 IST", "12:00-14:00 IST"],
            "urgency": "HIGH" if optimal_dates and optimal_dates[0]["days_offset"] <= 3 else "MEDIUM"
        }

    @classmethod
    def generate_festive_reel_ideas(
        cls,
        event_slug: str,
        niche: str = "all",
        custom_angle: Optional[str] = None,
        tone: str = "relatable",
        format_style: str = "grwm",
        target_goal: str = "viral_reach",
        grounding_audios: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate 3 high-impact, actionable reel concepts for a festival and creator niche.
        Uses LLM with rich prompt and structured JSON output, with a deterministic fallback library.
        Customized by creator format, tone, and viral goals.
        """
        events = cls.get_all_resolved_events_dict()
        event_data = events.get(event_slug)
        if not event_data:
            # Try searching by name or canonical slug
            clean_search = event_slug.lower().strip()
            for k, v in events.items():
                if v["name"].lower() == clean_search or v.get("canonical_slug", "").lower() == clean_search:
                    event_data = v
                    event_slug = v["slug"]
                    break

        if not event_data:
            return {
                "error": f"Festival '{event_slug}' not recognized.",
                "available_slugs": list(events.keys())
            }

        wave = calculate_wave_phase(event_data["date"])
        clean_niche = (niche or "all").lower().strip()
        clean_tone = (tone or "relatable").lower().strip()
        clean_format = (format_style or "grwm").lower().strip()
        clean_goal = (target_goal or "viral_reach").lower().strip()

        # Cache check: return instant cached response if generated within 24h
        cache_key = f"{event_slug}:{clean_niche}:{clean_tone}:{clean_format}:{clean_goal}:{(custom_angle or '').strip().lower()}"
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

        # Professional viral prompt engineering
        system_prompt = (
            "You are India's and global Instagram Reel Creative Director and virality strategist. "
            "You specialize in cultural events, festival anticipation waves, and high-retention short-form video. "
            "You produce high-performing, authentic, modern, and creator-friendly concepts that avoid corporate fluff, generic Hallmark greetings, or boring clichés. "
            "Every hook must be conversational, sharp, and create an irresistible curiosity gap or relatable truth in the first 3 seconds. "
            "Script flows must feature exact visual camera actions, pacing, and spoken voiceover lines."
        )

        user_prompt = f"""
Event: {event_data['name']} ({event_data.get('local_name', '')})
Event Date: {event_data['date']}
Wave Phase: {wave['phase_name']} ({wave['badge']}) - {wave['days_until']} days until event.
Optimal Filming Strategy: {wave['filming_action']}
Creator Niche: {clean_niche}
Creator Format / Video Style: {clean_format} (e.g. GRWM, Faceless B-Roll, Fast Hack, POV Skit, Audio-Synced Cut)
Requested Tone / Vibe: {clean_tone} (e.g. Relatable/Humorous, Aesthetic/Luxury, High-Energy Hype, Educational, Heartfelt)
Primary Growth Goal: {clean_goal} (e.g. Mass Reach & Shares, High Saves & Bookmarks, Comment Debate)
Custom Angle / Creator Note: {custom_angle or 'None provided'}
Cultural Themes: {', '.join(event_data.get('content_themes', []))}
Recommended Audio Vibe: {event_data.get('audio_vibe', 'Trending upbeat festive fusion beat')}
{real_audios_text}

Rules for output quality:
1. NO generic 'Celebrate with family' or 'Joy is in the air' greetings. Make it punchy, practical, or hilarious.
2. Hook (0-3s) must be word-for-word spoken or on-screen text matching the requested {clean_tone} tone and {clean_format} format.
3. Flow (0-3s, 4-15s, 16-25s) must specify camera framing (e.g., 'Overhead flatlay', 'Tight selfie jump-cut', 'Slow-motion macro pan') and audio drop sync.
4. virality_score must be an integer between 88 and 98 based on format strength.

Return ONLY a valid JSON object in this exact schema:
{{
  "event_name": "{event_data['name']}",
  "event_slug": "{event_slug}",
  "niche": "{clean_niche}",
  "tone": "{clean_tone}",
  "format_style": "{clean_format}",
  "target_goal": "{clean_goal}",
  "wave_phase": {json.dumps(wave)},
  "audio_recommendation": "{event_data.get('audio_vibe', '')}",
  "recommended_hashtags": {json.dumps(event_data.get('hashtags', [])[:5])},
  "concepts": [
    {{
      "concept_title": "Short punchy, creative title",
      "hook_3s": "Exact word-for-word spoken hook or on-screen text for the first 3 seconds",
      "hook_archetype": "Contrarian Truth | Relatable POV | Curiosity Gap | Visual Pattern Interrupt | Bold Statement",
      "format_archetype": "{clean_format.upper()} Format",
      "blueprint_flow": [
        "0-3s: Visual setup, camera angle, and spoken hook",
        "4-15s: Core high-value delivery, transition, or comedic escalation",
        "16-25s: Call-to-action driving the {clean_goal} goal (save/share/comment)"
      ],
      "sound_style": "Specific audio style description matching current trending archetypes",
      "optimal_post_window": "Specific posting day and IST time based on current wave phase",
      "why_algorithm_favors": "Specific algorithmic distribution trigger (e.g., high loop rate, DM shareability, collection saves)",
      "virality_score": 94
    }}
  ]
}}
"""
        # Try LLM generation
        if call_llm:
            try:
                response = call_llm(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_mime_type="application/json",
                    timeout=30
                )
                parsed = None
                if isinstance(response, dict) and "concepts" in response and len(response["concepts"]) >= 3:
                    parsed = response
                elif isinstance(response, dict) and "text" in response:
                    raw_text = response["text"].strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text[7:]
                    if raw_text.startswith("```"):
                        raw_text = raw_text[3:]
                    if raw_text.endswith("```"):
                        raw_text = raw_text[:-3]
                    parsed = json.loads(raw_text.strip())

                if parsed and "concepts" in parsed and len(parsed["concepts"]) >= 3:
                    parsed["is_ai_generated"] = True
                    _FESTIVE_IDEAS_CACHE[cache_key] = {
                        "cached_at": now_ts,
                        "data": parsed
                    }
                    return parsed
            except Exception as e:
                logger.warning(f"LLM festive generation failed ({e}), switching to rich deterministic fallback.")

        # Deterministic Fallback Engine
        fallback_concepts = cls.get_fallback_ideas(event_data, wave, clean_niche)
        fallback_response = {
            "event_name": event_data["name"],
            "event_slug": event_slug,
            "niche": clean_niche,
            "tone": clean_tone,
            "format_style": clean_format,
            "target_goal": clean_goal,
            "wave_phase": wave,
            "audio_recommendation": event_data.get("audio_vibe", "Trending upbeat festive audio"),
            "recommended_hashtags": event_data.get("hashtags", ["#ReelsIndia", "#ViralReels"])[:5],
            "concepts": fallback_concepts,
            "is_fallback": True
        }

        _FESTIVE_IDEAS_CACHE[cache_key] = {
            "cached_at": now_ts,
            "data": fallback_response
        }
        return fallback_response

    @classmethod
    def get_fallback_ideas(cls, event_data: Dict, wave: Dict, niche: str) -> List[Dict]:
        """
        Deep, high-converting fallback ideas tailored to event + niche.
        Ensures users get immediate, stunning, realistic ideas with 0 latency.
        """
        ev_name = event_data["name"]
        slug = event_data.get("canonical_slug", "")

        # Specialized Halloween Blueprints
        if "halloween" in slug:
            if "fashion" in niche:
                return [
                    {
                        "concept_title": "10-Minute SFX Vampire/Goth Transformation",
                        "hook_3s": "You don't need a ₹3,000 SFX kit for Halloween — use this kajal hack instead.",
                        "hook_archetype": "Contrarian Truth",
                        "format_archetype": "Fast-Paced GRWM Cut",
                        "blueprint_flow": [
                            "0-3s: Dramatic side-by-side or quick before/after flash showing dark glam look.",
                            "4-15s: 3-step breakdown: Black kajal smudge, red lip-tint blend for fake blood, highlight on cheekbones.",
                            "16-25s: Full costume reveal with dark moody lighting. 'Save this before your party tomorrow!'"
                        ],
                        "sound_style": "Dark synthwave beat drop or eerie cello swell",
                        "optimal_post_window": "3-7 days before Halloween, 7:00 PM IST",
                        "why_algorithm_favors": "Massive save rates from viewers looking for last-minute costume inspiration.",
                        "virality_score": 96
                    },
                    {
                        "concept_title": "POV: Last-minute college Halloween outfit vs My closet",
                        "hook_3s": "Creating 3 iconic Halloween characters using ONLY clothes already in my closet.",
                        "hook_archetype": "Curiosity Gap",
                        "format_archetype": "Quick Outfit Switch Skit",
                        "blueprint_flow": [
                            "0-3s: Rummaging through a closet looking distressed, text on screen.",
                            "4-16s: 3 rapid outfit reveals: Wednesday Addams (Black dress), Matrix Neo (Leather jacket), 90s Vampire.",
                            "17-25s: Which one should I wear? Vote 1, 2, or 3 in the comments!"
                        ],
                        "sound_style": "High-energy Phonk transition drop",
                        "optimal_post_window": "2-4 days before Halloween, 8:30 PM IST",
                        "why_algorithm_favors": "Comment-triggering voting mechanic boosts algorithmic reach.",
                        "virality_score": 94
                    },
                    {
                        "concept_title": "Tim Burton Aesthetic Makeup Tutorial",
                        "hook_3s": "Turning myself into a Corpse Bride character with drugstore makeup.",
                        "hook_archetype": "Visual Transformation",
                        "format_archetype": "Timelapse Transformation",
                        "blueprint_flow": [
                            "0-3s: Half-face painted blue and hollowed eyes with spooky stare.",
                            "4-15s: Satisfying contouring and shading timelapse cuts timed to beat pulses.",
                            "16-25s: Final look reveal with veil and candlelit backlight. 'Drop a 🖤 if you love Tim Burton!'"
                        ],
                        "sound_style": "Eerie haunting music box or melancholic piano drop",
                        "optimal_post_window": "5-10 days before Halloween, 6:00 PM IST",
                        "why_algorithm_favors": "High watch-time and replay rate on visual satisfaction.",
                        "virality_score": 97
                    }
                ]
            elif "food" in niche:
                return [
                    {
                        "concept_title": "3 Spooky Dry-Ice Mocktails (Party Showstopper)",
                        "hook_3s": "How to make party drinks bubble and smoke like a witch's cauldron.",
                        "hook_archetype": "Visual Transformation",
                        "format_archetype": "Aesthetic ASMR Cut",
                        "blueprint_flow": [
                            "0-3s: Close-up of deep purple drink bubbling with smoky dry-ice fog pouring over the glass.",
                            "4-16s: 3 recipe layers: Berry syrup, sparkling soda, food-grade glitter, and safe dry-ice handling tip.",
                            "17-25s: Final toast under blacklight. 'Save this reel for your Halloween party weekend!'"
                        ],
                        "sound_style": "Satisfying liquid ASMR mixed with eerie ambient synth",
                        "optimal_post_window": "4-6 days before Halloween, 5:30 PM IST",
                        "why_algorithm_favors": "High DM share rate among friends planning weekend parties.",
                        "virality_score": 95
                    },
                    {
                        "concept_title": "5-Minute Blood-Drip Strawberry Milkshake",
                        "hook_3s": "The easiest Halloween dessert you can whip up in 5 minutes flat.",
                        "hook_archetype": "Quick Hack",
                        "format_archetype": "Fast Recipe Reel",
                        "blueprint_flow": [
                            "0-3s: Dripping thick strawberry syrup down the rim of an aesthetic chilled glass.",
                            "4-15s: Blending vanilla ice cream, milk, and crushed Oreos. Pouring in slow-motion.",
                            "16-25s: Topping with whipped cream and candy worms. 'Recipe in caption!'"
                        ],
                        "sound_style": "Upbeat spooky lofi beat",
                        "optimal_post_window": "2-5 days before event, 4:00 PM IST",
                        "why_algorithm_favors": "Simple recipe replication drives bookmarks and saves.",
                        "virality_score": 91
                    },
                    {
                        "concept_title": "POV: Desi Mom reacting to Halloween horror bakes",
                        "hook_3s": "My mom's honest reaction when I baked 'severed finger' butter cookies.",
                        "hook_archetype": "Relatable POV",
                        "format_archetype": "Family Comedy Skit",
                        "blueprint_flow": [
                            "0-3s: Presenting realistic almond-finger cookies to an unsuspecting Indian mom.",
                            "4-16s: Her horrified reaction, lecture about wasting food, and immediate scolding in regional language.",
                            "17-25s: Her actually tasting it and admitting it's delicious. 'Drop a 😂 if your mom would react the same!'"
                        ],
                        "sound_style": "Comical dialogue audio with classic sitcom whistle",
                        "optimal_post_window": "3-7 days before Halloween, 8:00 PM IST",
                        "why_algorithm_favors": "Universal family relatability drives massive comment sections.",
                        "virality_score": 98
                    }
                ]
            elif "comedy" in niche:
                return [
                    {
                        "concept_title": "POV: Trick or Treating in an Indian Society",
                        "hook_3s": "What happens when you actually try Trick-or-Treating in a Mumbai apartment building.",
                        "hook_archetype": "Relatable POV",
                        "format_archetype": "Skit / Door-to-Door Journey",
                        "blueprint_flow": [
                            "0-3s: Dressed in a ghost sheet ringing a neighbor's doorbell shouting 'Trick or Treat!'",
                            "4-16s: Auntie opens door, gets confused, tries to give leftover Diwali Soan Papdi or asks 'Beta kiske bete ho?'",
                            "17-25s: Walking away with a box of dry fruits and a lecture on Sharma ji's son. 'Who else tried this?'"
                        ],
                        "sound_style": "Trending desi comedy audio dialogue",
                        "optimal_post_window": "3-6 days before Halloween, 8:00 PM IST",
                        "why_algorithm_favors": "Extremely viral in Indian metro audiences via WhatsApp and Instagram DMs.",
                        "virality_score": 99
                    },
                    {
                        "concept_title": "Expectations vs Reality: Halloween in India",
                        "hook_3s": "Halloween parties on Instagram vs What actually happens in Delhi / Bangalore.",
                        "hook_archetype": "Split-Screen Satire",
                        "format_archetype": "Expectation vs Reality",
                        "blueprint_flow": [
                            "0-3s: Left side: Hollywood mansion costume party aesthetic. Right side: Standing in bumper-to-bumper traffic dressed as Joker.",
                            "4-16s: Expectation: Aesthetic couples costumes. Reality: 50 guys wearing the same Squid Game tracksuit.",
                            "17-25s: Ending punchline eating roadside momos in full face paint at midnight."
                        ],
                        "sound_style": "Upbeat comedic phonk transition",
                        "optimal_post_window": "2-5 days before event, 7:30 PM IST",
                        "why_algorithm_favors": "Hyper-relatable urban satire sparks huge tagging in comments.",
                        "virality_score": 96
                    },
                    {
                        "concept_title": "Explaining my Halloween costume to my Nani",
                        "hook_3s": "Nani thinking I got into an accident because of my SFX wound makeup.",
                        "hook_archetype": "Relatable POV",
                        "format_archetype": "Candid Reaction Skit",
                        "blueprint_flow": [
                            "0-3s: Walking into the living room with fake zombie cuts.",
                            "4-15s: Nani immediately bringing Haldi Doodh and chanting prayers to ward off evil eyes.",
                            "16-25s: Explaining it's cosmetic paint while she wipes it with a wet towel."
                        ],
                        "sound_style": "Warm wholesome desi comedy soundtrack",
                        "optimal_post_window": "2-4 days before Halloween, 6:30 PM IST",
                        "why_algorithm_favors": "Intergenerational family humor generates emotional resonance and shares.",
                        "virality_score": 93
                    }
                ]

        # Standard Niche Blueprints for any event
        if "fitness" in niche:
            return [
                {
                    "concept_title": f"The {ev_name} Damage Control Protocol",
                    "hook_3s": f"Stop starving yourself before {ev_name} — do this 3-rule trick instead.",
                    "hook_archetype": "Contrarian Truth",
                    "format_archetype": "3-Step Fast Blueprint",
                    "blueprint_flow": [
                        "0-3s: Show festive food vs a clean meal with the text hook.",
                        "4-15s: Break down the protein anchor rule: 30g protein + 500ml water 20 mins before celebrations.",
                        "16-25s: Save this reel for the festive week and leave your goal in comments."
                    ],
                    "sound_style": "Low-tempo confident Lo-Fi beat",
                    "optimal_post_window": f"{max(1, wave['days_until'] - 2)} days before {ev_name}, 7:00 PM IST",
                    "why_algorithm_favors": "High saves rate from viewers wanting to prevent festive weight gain.",
                    "virality_score": 94
                },
                {
                    "concept_title": f"POV: Maintaining calorie deficit during {ev_name}",
                    "hook_3s": "My gym trainer vs My Mom offering me hot festive treats.",
                    "hook_archetype": "Relatable POV",
                    "format_archetype": "Split-Screen Skit",
                    "blueprint_flow": [
                        "0-3s: Side-by-side jump cut of refusing food vs family forcing extra servings.",
                        "4-15s: Fast paced cuts of giving in and doing pushups in festive clothes at midnight.",
                        "16-25s: Funny punchline text: 'Calories during festivals don't count if you eat with family.'"
                    ],
                    "sound_style": "Trending comical dialogue beat",
                    "optimal_post_window": "3-5 days before event, 8:30 PM IST",
                    "why_algorithm_favors": "High shareability via Instagram DMs to gym friends.",
                    "virality_score": 96
                },
                {
                    "concept_title": f"The 12-Minute Fast {ev_name} Workout (No Equipment)",
                    "hook_3s": f"No time for gym this {ev_name}? Do this 12-minute metabolic burner at home.",
                    "hook_archetype": "Curiosity Gap",
                    "format_archetype": "Fast-Cut Follow-Along",
                    "blueprint_flow": [
                        "0-3s: Fast timer graphic on screen with explosive bodyweight movement.",
                        "4-18s: 4 rapid exercises (Burpees, Jump Squats, Mountain Climbers, High Knees).",
                        "19-25s: 'Save this reel so you don't skip your workout on festival morning!'"
                    ],
                    "sound_style": "High-BPM Phonk or electronic remix",
                    "optimal_post_window": "Festival Eve or morning of, 7:30 AM IST",
                    "why_algorithm_favors": "Saves and audio replays as viewers bookmark the workout.",
                    "virality_score": 90
                }
            ]
        elif "finance" in niche:
            return [
                {
                    "concept_title": f"The {ev_name} Spending Trap (Don't fall for this)",
                    "hook_3s": f"90% of people will regret this purchase during {ev_name} sales.",
                    "hook_archetype": "Contrarian Warning",
                    "format_archetype": "Talking Head with Price Chart",
                    "blueprint_flow": [
                        "0-3s: Show fake festive discounts vs actual price history tracker.",
                        "4-16s: Explain the psychological trick of festive sales and how to use price tracker extensions.",
                        "17-25s: Give the 24-Hour Wishlist Rule before clicking 'Buy Now'."
                    ],
                    "sound_style": "Curiosity investigative beat with subtle synth pulses",
                    "optimal_post_window": "7-10 days before event, 6:00 PM IST",
                    "why_algorithm_favors": "Urgent utility and high comment discussions on shopping deals.",
                    "virality_score": 93
                },
                {
                    "concept_title": f"Smart Budget Allocation for {ev_name}",
                    "hook_3s": "Got your festive bonus? Do not spend a rupee until you watch this.",
                    "hook_archetype": "Urgent Blueprint",
                    "format_archetype": "Calculator Demonstration",
                    "blueprint_flow": [
                        "0-3s: Screen recording of festive bonus calculation.",
                        "4-15s: 50% into emergency debt/prepayment, 30% for gifts & indulgence, 20% into index funds.",
                        "16-25s: 'Comment BUDGET and I will DM you my free festive tracking spreadsheet.'"
                    ],
                    "sound_style": "Smooth lo-fi chill hip-hop",
                    "optimal_post_window": "10-14 days before event, 8:00 PM IST",
                    "why_algorithm_favors": "Comment-triggering keyword optimization increases engagement velocity.",
                    "virality_score": 91
                },
                {
                    "concept_title": "Gold vs Digital Gold vs Sovereign Bonds",
                    "hook_3s": "Buying physical gold this season? You might be losing 20% on making charges.",
                    "hook_archetype": "Curiosity Gap",
                    "format_archetype": "Comparison Chart",
                    "blueprint_flow": [
                        "0-3s: Hold physical jewellery vs digital smartphone portfolio screen.",
                        "4-15s: 3-column breakdown: Making charges, safety risk, and sovereign interest returns.",
                        "16-25s: Clear actionable takeaway on where smart investors put their money."
                    ],
                    "sound_style": "Upbeat clean tech-minimalist lo-fi",
                    "optimal_post_window": "5-8 days before event, 7:30 PM IST",
                    "why_algorithm_favors": "High bookmarking and re-shares to family WhatsApp groups.",
                    "virality_score": 95
                }
            ]
        elif "food" in niche:
            return [
                {
                    "concept_title": f"15-Minute Instant {ev_name} Dessert (No Complex Prep)",
                    "hook_3s": "Forgot to buy treats for guests? Make this gourmet dessert in 15 minutes flat.",
                    "hook_archetype": "Visual Transformation",
                    "format_archetype": "Fast-Paced Aesthetic Recipe Cut",
                    "blueprint_flow": [
                        "0-3s: High-contrast close-up of cutting into a creamy, pistachio-loaded treat.",
                        "4-16s: 3 ingredient reveal with fast sizzle cuts.",
                        "17-25s: Final garnish shot with plated presentation. 'Full recipe in caption!'"
                    ],
                    "sound_style": "Satisfying cooking ASMR mixed with uplifting acoustic vibes",
                    "optimal_post_window": "3-6 days before event, 12:30 PM IST (lunch prep time)",
                    "why_algorithm_favors": "Massive save rates from home cooks preparing festive menus.",
                    "virality_score": 97
                },
                {
                    "concept_title": f"The Leftover {ev_name} Treat Makeover",
                    "hook_3s": "What to do with all those leftover festive boxes when no one wants to eat them?",
                    "hook_archetype": "Relatable POV",
                    "format_archetype": "Creative Recipe Fusion",
                    "blueprint_flow": [
                        "0-3s: Show 5 stacked unopened boxes of festive sweets or snacks.",
                        "4-16s: Transform them into a gourmet parfait jar or cheesecake crust in 30 seconds.",
                        "17-25s: Taste test reaction. 'Never throw away festive leftovers again!'"
                    ],
                    "sound_style": "Upbeat acoustic whistle and clap",
                    "optimal_post_window": "1-3 days AFTER the festival, 4:00 PM IST",
                    "why_algorithm_favors": "Direct post-event utility reaches peak audience satisfaction.",
                    "virality_score": 95
                },
                {
                    "concept_title": f"Healthy Sugar-Free {ev_name} Platter",
                    "hook_3s": "Satisfy your festive sweet tooth without a sugar crash.",
                    "hook_archetype": "Curiosity Gap",
                    "format_archetype": "Step-by-Step Plating",
                    "blueprint_flow": [
                        "0-3s: Beautiful glass platter loaded with dark chocolate date bites and fig rolls.",
                        "4-15s: 100% natural ingredients, no refined sugar, diabetic-friendly.",
                        "16-25s: 'Drop a ❤️ if you want the exact calorie breakdown in comments!'"
                    ],
                    "sound_style": "Chill organic guitar lo-fi",
                    "optimal_post_window": "7-10 days before event, 7:00 PM IST",
                    "why_algorithm_favors": "Health-conscious shares and saves across health circles.",
                    "virality_score": 93
                }
            ]
        elif "fashion" in niche:
            return [
                {
                    "concept_title": f"The {ev_name} Outfit Color Palette Guide",
                    "hook_3s": f"Stop wearing the same plain outfits to every {ev_name}. Try these 3 combos instead.",
                    "hook_archetype": "Contrarian Advice",
                    "format_archetype": "3-Look Fast Transition",
                    "blueprint_flow": [
                        "0-3s: Show boring generic outfit with a big red X on screen.",
                        "4-16s: 3 fresh unexpected color combinations with high-energy clothing snap transitions.",
                        "17-25s: Full mirror spin with accessorized styling. 'Which color palette is your favorite?'"
                    ],
                    "sound_style": "High-velocity bass transition drop",
                    "optimal_post_window": "7-12 days before event, 7:30 PM IST",
                    "why_algorithm_favors": "Saves and audio-synced transition replays drive algorithmic promotion.",
                    "virality_score": 98
                },
                {
                    "concept_title": f"Restyling 1 Outfit in 3 Ways for {ev_name}",
                    "hook_3s": "You don't need a new outfit for every festive function. Watch this.",
                    "hook_archetype": "Practical Utility",
                    "format_archetype": "Capsule Wardrobe Styling",
                    "blueprint_flow": [
                        "0-3s: Starting in a versatile neutral staple piece.",
                        "4-15s: Look 1 (Daytime puja), Look 2 (Evening party), Look 3 (Family dinner) via smart layering.",
                        "16-25s: 'Save this so you don't overspend on fast fashion this week!'"
                    ],
                    "sound_style": "Smooth confident chic R&B beat",
                    "optimal_post_window": "5-8 days before event, 6:00 PM IST",
                    "why_algorithm_favors": "Sustainable and budget-conscious content gets shared heavily in DMs.",
                    "virality_score": 96
                },
                {
                    "concept_title": f"Last-Minute {ev_name} Glow Up (24 Hours Prior)",
                    "hook_3s": "Festive event is tomorrow and you look exhausted? Do this tonight.",
                    "hook_archetype": "Urgent Problem Solver",
                    "format_archetype": "Night Routine GRWM",
                    "blueprint_flow": [
                        "0-3s: Tired face in bathroom mirror, text with countdown.",
                        "4-15s: Ice-water face dunk, de-puffing lymphatic massage, and intense overnight barrier cream.",
                        "16-25s: Morning glow reveal in natural sunlight. 'Save this emergency skin routine!'"
                    ],
                    "sound_style": "Relaxing spa ASMR audio with gentle lo-fi beats",
                    "optimal_post_window": "1-2 days before event, 9:00 PM IST",
                    "why_algorithm_favors": "Immediate urgency drives immediate saves and execution.",
                    "virality_score": 94
                }
            ]
        elif "comedy" in niche:
            return [
                {
                    "concept_title": f"POV: The Different Types of People at {ev_name}",
                    "hook_3s": f"Every Indian family has these exact 4 people during {ev_name}.",
                    "hook_archetype": "Relatable Character Trope",
                    "format_archetype": "Multi-Character Skit",
                    "blueprint_flow": [
                        "0-3s: Character 1 (The one who only came for food), fast jump cuts.",
                        "4-16s: Character 2 (The photographer directing everyone), Character 3 (The relative asking about marriage), Character 4 (The kid hiding in a room with phone).",
                        "17-25s: Tag that one friend who is definitely Character 2!"
                    ],
                    "sound_style": "Trending comedic dialogue beat",
                    "optimal_post_window": "3-6 days before event, 8:30 PM IST",
                    "why_algorithm_favors": "Massive comment tagging generates viral comment thread velocity.",
                    "virality_score": 98
                },
                {
                    "concept_title": f"Expectations vs Reality of {ev_name}",
                    "hook_3s": f"What I thought my {ev_name} would look like vs Reality.",
                    "hook_archetype": "Contrast Satire",
                    "format_archetype": "Expectation vs Reality",
                    "blueprint_flow": [
                        "0-3s: Expectation: Aesthetic candlelit reels with soft smiles and perfect outfits.",
                        "4-16s: Reality: Sweating, untangling lights for 3 hours, or dealing with last-minute chaos.",
                        "17-25s: 'Drop a ❤️ if your celebrations are always 100% pure chaotic fun!'"
                    ],
                    "sound_style": "Dramatic orchestral sound interrupted by funny screech sound effect",
                    "optimal_post_window": "Day before or morning of event, 11:00 AM IST",
                    "why_algorithm_favors": "Hyper-relatable authenticity resonates far more than staged aesthetic perfection.",
                    "virality_score": 97
                },
                {
                    "concept_title": f"POV: Leaving the {ev_name} gathering",
                    "hook_3s": "Trying to say goodbye to Indian relatives when you just want to go home.",
                    "hook_archetype": "Relatable POV",
                    "format_archetype": "Endless Goodbye Skit",
                    "blueprint_flow": [
                        "0-3s: Saying goodbye at the door.",
                        "4-16s: Talking for another 45 minutes at the elevator, then in the parking lot, then through car window.",
                        "17-25s: 'It's been 2 hours and we haven't left the gate.' Who else's family does this?"
                    ],
                    "sound_style": "Desi situational acoustic comedic background",
                    "optimal_post_window": "Night of event, 10:30 PM IST",
                    "why_algorithm_favors": "High late-night engagement and relatable laughter shared to stories.",
                    "virality_score": 95
                }
            ]
        elif "tech" in niche:
            return [
                {
                    "concept_title": f"How to Capture Stunning 4K {ev_name} Reels on Any Smartphone",
                    "hook_3s": "Your festive reels look blurry because you haven't turned on this 1 hidden setting.",
                    "hook_archetype": "Curiosity & Hack",
                    "format_archetype": "Phone Screen Recording & Camera Demo",
                    "blueprint_flow": [
                        "0-3s: Blurry festive footage vs crystal-clear 4K HDR footage side by side.",
                        "4-16s: 3 camera settings: Lock AE/AF, lower exposure by -0.7 for highlights, switch to 4K 60fps.",
                        "17-25s: 'Save this before tonight's celebration so you capture memories in crisp 4K!'"
                    ],
                    "sound_style": "Clean tech tutorial lo-fi synth",
                    "optimal_post_window": "2-4 days before event, 6:30 PM IST",
                    "why_algorithm_favors": "High utility drives high saves and bookmarks.",
                    "virality_score": 96
                },
                {
                    "concept_title": f"Smart Home Automation Hacks for {ev_name}",
                    "hook_3s": "Watch my entire house light up for the festival with 1 voice command.",
                    "hook_archetype": "Visual Transformation",
                    "format_archetype": "Smart Home Demonstration",
                    "blueprint_flow": [
                        "0-3s: Dark room. Say trigger word: 'Alexa / Siri, Festive Mode.'",
                        "4-16s: Smart RGB lights warm up, festive string lights turn on via smart plugs, and ambient music begins playing automatically.",
                        "17-25s: Breakdown of the ₹1,500 smart plug setup. 'Full routine in caption!'"
                    ],
                    "sound_style": "Futuristic electronic synth swell with bass drop",
                    "optimal_post_window": "5-8 days before event, 7:00 PM IST",
                    "why_algorithm_favors": "High tech-lifestyle aspirational appeal drives shares.",
                    "virality_score": 94
                },
                {
                    "concept_title": f"Top 3 Real Tech Deals for {ev_name} (Avoid the fake 70% discounts)",
                    "hook_3s": "Don't get fooled by 70% OFF banners — here are the 3 real tech steals this season.",
                    "hook_archetype": "Contrarian Warning",
                    "format_archetype": "Price History Proof Breakdown",
                    "blueprint_flow": [
                        "0-3s: Flash big sale banner with price tracker chart showing inflated baseline.",
                        "4-16s: 3 genuine price-drop gadgets: TWS Earbuds, Smartwatch, and Powerbank with verifiable 40% drops.",
                        "17-25s: 'Link in bio for verified price trackers!'"
                    ],
                    "sound_style": "Energetic modern upbeat corporate beat",
                    "optimal_post_window": "6-10 days before event, 8:00 PM IST",
                    "why_algorithm_favors": "High purchase-intent saves and comment inquiries on links.",
                    "virality_score": 93
                }
            ]
        else:
            # Default Universal Blueprints
            return [
                {
                    "concept_title": f"The Ultimate {ev_name} Checklist (Don't Forget These 5 Things)",
                    "hook_3s": f"Save this checklist before {ev_name} so you don't panic on festival morning.",
                    "hook_archetype": "Urgent Utility",
                    "format_archetype": "Fast Bullet Checklist",
                    "blueprint_flow": [
                        "0-3s: On-screen aesthetic graphic checklist with fast dynamic zoom.",
                        "4-16s: 5 essential items: Festive outfit steaming, gift wrapping, charging batteries, booking travel/sweets.",
                        "17-25s: 'Screenshot this checklist so you are 100% prepared!'"
                    ],
                    "sound_style": "Upbeat cheerful acoustic sitar and guitar fusion",
                    "optimal_post_window": "4-7 days before event, 6:00 PM IST",
                    "why_algorithm_favors": "High screenshot and save rate pushes reel into Instagram explore feed.",
                    "virality_score": 93
                },
                {
                    "concept_title": f"The 3-Second {ev_name} Transformation",
                    "hook_3s": f"Watch this ordinary room / outfit transform for {ev_name} in 3 seconds.",
                    "hook_archetype": "Visual Transformation",
                    "format_archetype": "Audio-Synced Jump Cut",
                    "blueprint_flow": [
                        "0-3s: Casual everyday setting with hand covering the lens or finger snap.",
                        "4-16s: Beat drops: Room is illuminated with warm fairy lights, flowers, and festive aesthetics.",
                        "17-25s: Slow-motion aesthetic walk with traditional festive audio. 'Happy celebrations everyone!'"
                    ],
                    "sound_style": "High-energy festive Indian drop with cinematic bass",
                    "optimal_post_window": "Festival Eve or Day of, 6:00 PM IST",
                    "why_algorithm_favors": "High re-watch rate on visual satisfaction and audio sync.",
                    "virality_score": 96
                },
                {
                    "concept_title": f"What {ev_name} Really Means to Me",
                    "hook_3s": "In a world of constant hustle, this is why I never skip this celebration.",
                    "hook_archetype": "Emotional Connection",
                    "format_archetype": "Voiceover Storytelling",
                    "blueprint_flow": [
                        "0-3s: Cinematic golden hour shot of lighting lamps or smiling with family.",
                        "4-16s: Sincere personal reflection voiceover about gratitude, roots, and slowing down.",
                        "17-25s: Warm closing thought: 'May your home be filled with light and laughter.'"
                    ],
                    "sound_style": "Emotional piano and bansuri flute melody",
                    "optimal_post_window": "Festival Eve or Day 0, 8:00 PM IST",
                    "why_algorithm_favors": "High emotional resonance triggers heartfelt comments and family sharing.",
                    "virality_score": 92
                }
            ]


# Permanent alias for existing imports across backend
CulturalEventCalendar = SeasonalEventEngine