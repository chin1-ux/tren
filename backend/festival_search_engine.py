import os
import json
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("festival_search_engine")

# Niche-specific content idea matrix templates
NICHE_IDEAS_MATRIX = {
    "food": [
        "Traditional festive dish recipe with a modern 30-second twist",
        "3 healthy sugar-free sweets for festive celebrations",
        "Behind-the-scenes festive feast preparation & plating aesthetics"
    ],
    "fitness": [
        "15-minute quick burn workout before heavy festive meals",
        "How to stay consistent with your workout routine during celebrations",
        "Post-festive detox stretch routine & hydration tips"
    ],
    "fashion": [
        "3 affordable festive outfit transitions from traditional to modern",
        "Color combination styling guide for upcoming celebrations",
        "Last-minute accessories styling reel with transition audio"
    ],
    "travel": [
        "Top 3 places to experience authentic festive celebrations this week",
        "Vibrant festive street decor & cultural walkthrough Reel",
        "Budget weekend getaway guide during the festival weekend"
    ],
    "comedy": [
        "POV: Relatives visiting during festive preparations vs reality",
        "Expectations vs Reality of shopping for festival outfits",
        "Hilarious types of people at festive family gatherings"
    ],
    "motivation": [
        "Reflecting on gratitude & personal growth during this festival season",
        "How to balance work, family, and self-care during busy holidays",
        "Festive spirit: Spreading kindness & uplifting your community"
    ],
    "current_affairs": [
        "Economic & cultural impact of upcoming festival celebrations",
        "Global celebrations: How different regions mark this occasion",
        "Historical origins & evolution of festival traditions"
    ]
}

DEFAULT_IDEAS = [
    "High-energy festive celebration transition video",
    "3 quick tips to make the most of this upcoming festival",
    "POV: Preparing for the holiday weekend with your squad"
]

# Dynamic Festival & Event Registry (Indian + Global)
MASTER_FESTIVALS_CALENDAR = [
    {"name": "Maha Shivratri", "date_str": "2026-03-08", "category": "regional_in", "region": "India"},
    {"name": "Holi Celebration", "date_str": "2026-03-25", "category": "major_in", "region": "India"},
    {"name": "Good Friday", "date_str": "2026-04-03", "category": "global", "region": "Global"},
    {"name": "Easter Sunday", "date_str": "2026-04-05", "category": "global", "region": "Global"},
    {"name": "Eid ul-Fitr", "date_str": "2026-03-20", "category": "major_in", "region": "Global & India"},
    {"name": "Tamil New Year (Puthandu)", "date_str": "2026-04-14", "category": "regional_in", "region": "Tamil Nadu"},
    {"name": "Vaisakhi", "date_str": "2026-04-14", "category": "regional_in", "region": "Punjab"},
    {"name": "Poila Boishakh", "date_str": "2026-04-15", "category": "regional_in", "region": "Bengal"},
    {"name": "IPL Opening Season", "date_str": "2026-03-28", "category": "sports", "region": "India"},
    {"name": "Rath Yatra", "date_str": "2026-07-16", "category": "regional_in", "region": "Odisha"},
    {"name": "Independence Day", "date_str": "2026-08-15", "category": "national_in", "region": "India"},
    {"name": "Raksha Bandhan", "date_str": "2026-08-28", "category": "major_in", "region": "India"},
    {"name": "Janmashtami", "date_str": "2026-09-04", "category": "major_in", "region": "India"},
    {"name": "Ganesh Chaturthi", "date_str": "2026-09-14", "category": "major_in", "region": "Maharashtra / India"},
    {"name": "Onam", "date_str": "2026-09-24", "category": "regional_in", "region": "Kerala"},
    {"name": "Navratri", "date_str": "2026-10-11", "category": "major_in", "region": "India"},
    {"name": "Durga Puja", "date_str": "2026-10-17", "category": "regional_in", "region": "Bengal"},
    {"name": "Dussehra (Vijayadashami)", "date_str": "2026-10-20", "category": "major_in", "region": "India"},
    {"name": "Diwali", "date_str": "2026-11-08", "category": "major_in", "region": "India & Global"},
    {"name": "Halloween", "date_str": "2026-10-31", "category": "global", "region": "Global"},
    {"name": "Christmas", "date_str": "2026-12-25", "category": "global", "region": "Global"},
    {"name": "New Year's Eve", "date_str": "2026-12-31", "category": "global", "region": "Global"},
]

def get_upcoming_10day_festivals(user_niche: str = "all") -> list[dict]:
    """
    Returns live upcoming festivals & major events occurring strictly within the next 10 days (0 <= days <= 10).
    Injects tailored content ideas based on creator niche.
    """
    today = datetime.now(timezone.utc).date()
    horizon_days = 10

    results = []
    for fest in MASTER_FESTIVALS_CALENDAR:
        try:
            fest_date = datetime.strptime(fest["date_str"], "%Y-%m-%d").date()
            days_until = (fest_date - today).days

            # Include festivals happening in the next 10 days (or currently today)
            if 0 <= days_until <= horizon_days:
                niche_ideas = NICHE_IDEAS_MATRIX.get(user_niche.lower(), DEFAULT_IDEAS)
                
                results.append({
                    "name": fest["name"],
                    "date": fest_date.strftime("%B %d, %Y"),
                    "days_until": days_until,
                    "region": fest["region"],
                    "category": fest["category"],
                    "urgency_label": "TODAY" if days_until == 0 else f"{days_until} days away",
                    "urgency_badge": "bg-red-500" if days_until <= 3 else "bg-amber-500" if days_until <= 7 else "bg-blue-500",
                    "content_ideas": niche_ideas,
                    "target_niche": user_niche
                })
        except Exception as e:
            logger.error(f"Error parsing festival {fest.get('name')}: {e}")

    # Sort by closest date first
    results.sort(key=lambda x: x["days_until"])
    
    # If no festivals fall strictly within the 10-day window right now, return the closest upcoming 3 festivals
    if len(results) == 0:
        upcoming = []
        for fest in MASTER_FESTIVALS_CALENDAR:
            try:
                fest_date = datetime.strptime(fest["date_str"], "%Y-%m-%d").date()
                days_until = (fest_date - today).days
                if days_until > 0:
                    upcoming.append((days_until, fest, fest_date))
            except Exception:
                pass
        upcoming.sort(key=lambda x: x[0])
        for days_until, fest, fest_date in upcoming[:3]:
            niche_ideas = NICHE_IDEAS_MATRIX.get(user_niche.lower(), DEFAULT_IDEAS)
            results.append({
                "name": fest["name"],
                "date": fest_date.strftime("%B %d, %Y"),
                "days_until": days_until,
                "region": fest["region"],
                "category": fest["category"],
                "urgency_label": f"{days_until} days away",
                "urgency_badge": "bg-blue-500",
                "content_ideas": niche_ideas,
                "target_niche": user_niche
            })

    return results
