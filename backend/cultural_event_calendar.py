"""
Cultural Event Calendar
India-specific cultural events with content suggestions and optimal timing
"""
import os
import sys
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


class CulturalEventCalendar:
    """
    India-specific cultural event calendar with content suggestions
    """
    
    # Cultural events for 2026-2027
    CULTURAL_EVENTS = {
        'ganesh_chaturthi_2026': {
            'name': 'Ganesh Chaturthi',
            'date': '2026-09-14',
            'duration_days': 10,
            'content_themes': ['ganpati', 'morya', 'modak', 'aarti', 'festive_wear', 'visarjan'],
            'content_automation': ['Modak making recipe', 'Ganpati welcome reels', 'Mandap decor ideas', 'Aarti singing challenge'],
            'creator_opportunities': ['Ethnic fashion sponsors', 'Festive food brand partnerships', 'Pandal tour vlogs'],
            'optimal_posting_days': [-2, -1, 0, 1, 2],
            'hashtags': ['#GaneshChaturthi2026', '#GanpatiBappaMorya', '#Ganpati2026'],
            'trending_hashtags': ['#ganpatidecoration', '#modakrecipe', '#bappamorya'],
            'content_ideas': [
                'Ganesha idol welcome ceremony',
                'Modak preparation step-by-step',
                'Ethnic outfit transition reel',
                'Eco-friendly Ganesha making',
                'Visarjan procession highlights'
            ],
            'region_specific': {
                'maharashtra': ['Dhol Tasha', 'Modak', 'Pandal Visits'],
                'south': ['Gauri Ganesha', 'Kolam', 'Prasadam'],
                'north': ['Ganpati Sthapna', 'Sweets']
            }
        },
        'navratri_2026': {
            'name': 'Navratri (Sharad)',
            'date': '2026-09-28',
            'duration_days': 9,
            'content_themes': ['garba', 'dandiya', 'chaniya_choli', 'ethnic_makeup', 'fasting_recipes'],
            'content_automation': ['9 Days 9 Colors Outfits', 'Garba step tutorials', 'Fasting snack ideas', 'Dandiya night makeup'],
            'creator_opportunities': ['Traditional jewellery sponsors', 'Garba venue promotions', 'Ethnic makeup tutorials'],
            'optimal_posting_days': [-3, -1, 0, 1, 2],
            'hashtags': ['#Navratri2026', '#GarbaLover', '#DandiyaNight', '#9Days9Colors'],
            'trending_hashtags': ['#garbareels', '#chaniyacholi', '#navratrilook'],
            'content_ideas': [
                '9 Days 9 Colors outfit lookbook',
                'Popular Garba steps tutorial',
                'GRWM for Dandiya night',
                'Fast-friendly Sabudana Khichdi recipe',
                'Dandiya night vlog'
            ],
            'region_specific': {
                'gujarat': ['Garba Nights', 'Chaniya Choli', 'Aarti'],
                'north': ['Kanya Pujan', 'Mata Rani Chowki', 'Fasting']
            }
        },
        'durga_puja_2026': {
            'name': 'Durga Puja',
            'date': '2026-10-17',
            'duration_days': 5,
            'content_themes': ['pujo', 'pandal_hopping', 'dhunuchi_naach', 'saree_draping', 'bengali_sweets'],
            'content_automation': ['Pandal hopping guide', 'Traditional Saree GRWM', 'Dhunuchi dance challenge', 'Bengali bhog recipes'],
            'creator_opportunities': ['Saree brand sponsorships', 'Restaurant Pujo menu features', 'Pandal media coverage'],
            'optimal_posting_days': [-2, -1, 0, 1],
            'hashtags': ['#DurgaPuja2026', '#Pujo2026', '#SubhoSaptami', '#SubhoNabami'],
            'trending_hashtags': ['#pandalhopping', '#bengalilook', '#dhunuchinaach'],
            'content_ideas': [
                'Top 5 Must-Visit Pandals vlog',
                'Traditional Red & White Saree look',
                'Dhunuchi Naach energy video',
                'Kolkata street food tour during Pujo',
                'Sindoor Khela moments'
            ],
            'region_specific': {
                'east': ['Pandal Hopping', 'Bhog', 'Sindoor Khela', 'Cultural Shows']
            }
        },
        'dussehra_2026': {
            'name': 'Dussehra (Vijayadashami)',
            'date': '2026-10-20',
            'duration_days': 1,
            'content_themes': ['ramlila', 'ravan_dahan', 'victory_good_over_evil', 'festive_greetings'],
            'content_automation': ['Ramlila highlights', 'Ravan Dahan fireworks', 'Festive wish reels'],
            'creator_opportunities': ['Local event partnerships', 'Festive fashion sponsors'],
            'optimal_posting_days': [-1, 0, 1],
            'hashtags': ['#Dussehra2026', '#Vijayadashami', '#HappyDussehra'],
            'trending_hashtags': ['#ravandahan', '#ramlila'],
            'content_ideas': [
                'Ravan Dahan fireworks footage',
                'Vijayadashami festive greeting reel'
            ]
        },
        'karva_chauth_2026': {
            'name': 'Karva Chauth',
            'date': '2026-10-29',
            'duration_days': 1,
            'content_themes': ['sargi', 'mehndi', 'fasting', 'ethnic_red_suit', 'moon_sighting'],
            'content_automation': ['Mehndi design ideas', 'Sargi thali prep', 'Red ethnic outfit GRWM', 'Moon sighting moment'],
            'creator_opportunities': ['Jewellery brand collaborations', 'Mehndi artist showcases', 'Skincare fasting tips'],
            'optimal_posting_days': [-2, -1, 0],
            'hashtags': ['#KarvaChauth2026', '#KarwaChauthSpecial', '#MehndiDesigns'],
            'trending_hashtags': ['#karwachauthlook', '#sargithali'],
            'content_ideas': [
                'Quick & elegant Mehndi design ideas',
                'Sargi thali morning preparation',
                'Red saree / lehenga GRWM',
                'Pooja thali decoration ideas',
                'Moon sighting ritual reel'
            ]
        },
        'diwali_2026': {
            'name': 'Diwali',
            'date': '2026-11-14',
            'duration_days': 5,
            'content_themes': ['lights', 'diyas', 'rangoli', 'sweets', 'fireworks', 'family', 'gifts'],
            'content_automation': ['Home decor tutorials', 'Recipe videos', 'Outfit showcases', 'Family vlogs'],
            'creator_opportunities': ['Partner with home decor brands', 'Festive recipe collaborations', 'Traditional outfit sponsorships'],
            'optimal_posting_days': [-2, -1, 0, 1],
            'hashtags': ['#Diwali2026', '#FestivalOfLights', '#DiwaliVibes', '#IndianFestival'],
            'trending_hashtags': ['#diwalireels', '#diwalicrackers', '#diwalidecoration'],
            'content_ideas': [
                'Diya lighting ceremony',
                'Rangoli making tutorial',
                'Sweet preparation',
                'Family celebration moments',
                'Fireworks display',
                'Gift opening',
                'Traditional outfit showcase'
            ]
        },
        'holi_2027': {
            'name': 'Holi',
            'date': '2027-03-14',
            'duration_days': 2,
            'content_themes': ['colors', 'water', 'dance', 'music', 'friends', 'celebration', 'fun'],
            'content_automation': ['Color play videos', 'Party content', 'Music videos', 'Safety tips'],
            'creator_opportunities': ['Partner with color/fashion brands', 'Music artist collaborations', 'Event venue sponsorships'],
            'optimal_posting_days': [-1, 0, 1],
            'hashtags': ['#Holi2027', '#FestivalOfColors', '#HoliVibes', '#RangHoli'],
            'trending_hashtags': ['#holireels', '#colors', '#holicelebration'],
            'content_ideas': [
                'Color application',
                'Dance to Holi songs',
                'Friends celebration',
                'Before/after colorful photos',
                'Traditional sweets',
                'Water balloon fights',
                'Music performances'
            ],
            'region_specific': {
                'north': ['Lathmar Holi', 'Bhangra', 'Gulal'],
                'south': ['Rang Panchami', 'Traditional games'],
                'east': ['Dol Jatra', 'Playful colors'],
                'west': ['Holi Dahan', 'Community celebration']
            }
        },
        'independence_day_2026': {
            'name': 'Independence Day',
            'date': '2026-08-15',
            'duration_days': 2,
            'content_themes': ['patriotism', 'tricolor', 'freedom', 'celebration', 'pride', 'history'],
            'content_automation': ['Patriotic edits', 'Freedom quote reads', 'Tricolor outfit showcases'],
            'creator_opportunities': ['Partner with patriotic clothing brands', 'Music label collaborations', 'Event sponsorships'],
            'optimal_posting_days': [-2, -1, 0, 1],
            'hashtags': ['#IndependenceDay2026', '#India', '#JaiHind', '#Azadi'],
            'trending_hashtags': ['#independencedayreels', '#indianpride', '#15august'],
            'content_ideas': [
                'Flag hoisting',
                'Patriotic songs',
                'Historical facts',
                'Freedom fighter stories',
                'Cultural performances',
                'National pride moments',
                'Tricolor themes'
            ],
            'region_specific': {
                'delhi': ['Red Fort', 'PM speech'],
                'mumbai': ['School celebrations', 'Flag hoisting'],
                'kolkata': ['Cultural programs', 'Parades'],
                'chennai': ['School events', 'Patriotic songs']
            }
        },
        'christmas_2026': {
            'name': 'Christmas',
            'date': '2026-12-25',
            'duration_days': 3,
            'content_themes': ['decorations', 'carols', 'family', 'gifts', 'celebration', 'cake', 'santa'],
            'content_automation': ['Decor tutorials', 'Gift guides', 'Recipe videos', 'Family vlogs'],
            'creator_opportunities': ['Partner with gift/fashion brands', 'Bakery collaborations', 'Event venue sponsorships'],
            'optimal_posting_days': [-3, -2, -1, 0, 1],
            'hashtags': ['#Christmas2026', '#Xmas', '#ChristmasVibes', '#FestivalSeason'],
            'trending_hashtags': ['#christmasreels', '#xmasvibes', '#holidayseason'],
            'content_ideas': [
                'Christmas tree decoration',
                'Cake baking',
                'Gift wrapping',
                'Carol singing',
                'Family dinner',
                'Santa surprises',
                'Winter fashion'
            ],
            'region_specific': {
                'goa': ['Midnight mass', 'Beach celebrations'],
                'kerala': ['Traditional cakes', 'Family gatherings'],
                'northeast': ['Community feasts', 'Carols'],
                'metro_cities': ['Parties', 'Decorations']
            }
        }
    }
    
    @staticmethod
    def get_upcoming_events(days_ahead: int = 90) -> List[Dict]:
        """
        Get upcoming cultural events within specified days
        
        Args:
            days_ahead: Number of days to look ahead
        
        Returns:
            List of upcoming events sorted by date
        """
        current_date = datetime.now(timezone.utc).date()
        cutoff_date = current_date + timedelta(days=days_ahead)
        
        upcoming_events = []
        
        for event_key, event_data in CulturalEventCalendar.CULTURAL_EVENTS.items():
            event_date = datetime.fromisoformat(event_data['date']).date()
            
            if current_date <= event_date <= cutoff_date:
                days_until = (event_date - current_date).days
                event_copy = event_data.copy()
                event_copy['days_until'] = days_until
                event_copy['is_upcoming'] = True
                upcoming_events.append(event_copy)
        
        # Sort by date
        upcoming_events.sort(key=lambda x: x['days_until'])
        
        return upcoming_events
    
    @staticmethod
    def get_event_content_suggestions(event_name: str, region: str = None) -> Dict:
        """
        Get content suggestions for a specific event
        
        Args:
            event_name: Name of the event
            region: Specific region (optional)
        
        Returns:
            Content suggestions with themes, hashtags, and ideas
        """
        # Find event by name
        event_data = None
        for event in CulturalEventCalendar.CULTURAL_EVENTS.values():
            if event['name'].lower() == event_name.lower():
                event_data = event
                break
        
        if not event_data:
            return {
                'error': f'Event {event_name} not found',
                'available_events': [e['name'] for e in CulturalEventCalendar.CULTURAL_EVENTS.values()]
            }
        
        suggestions = {
            'event_name': event_data['name'],
            'date': event_data['date'],
            'duration_days': event_data['duration_days'],
            'content_themes': event_data['content_themes'],
            'hashtags': event_data['hashtags'],
            'trending_hashtags': event_data['trending_hashtags'],
            'content_ideas': event_data['content_ideas'],
            'optimal_posting_days': event_data['optimal_posting_days']
        }
        
        # Add region-specific content if provided
        if region and 'region_specific' in event_data:
            region_data = event_data['region_specific'].get(region.lower())
            if region_data:
                suggestions['region_specific'] = region_data
        
        return suggestions
    
    @staticmethod
    def get_optimal_posting_window(event_name: str) -> Dict:
        """
        Get optimal posting window for an event
        
        Args:
            event_name: Name of the event
        
        Returns:
            Optimal posting days and times
        """
        event_data = None
        for event in CulturalEventCalendar.CULTURAL_EVENTS.values():
            if event['name'].lower() == event_name.lower():
                event_data = event
                break
        
        if not event_data:
            return {'error': 'Event not found'}
        
        event_date = datetime.fromisoformat(event_data['date'])
        optimal_days = event_data['optimal_posting_days']
        
        # Calculate specific dates
        optimal_dates = []
        for day_offset in optimal_days:
            target_date = event_date + timedelta(days=day_offset)
            optimal_dates.append({
                'date': target_date.date().isoformat(),
                'days_offset': day_offset,
                'label': f"{'Day before' if day_offset < 0 else 'Day after' if day_offset > 0 else 'Event day'} {abs(day_offset)}" if day_offset != 0 else 'Event day'
            })
        
        return {
            'event_date': event_data['date'],
            'optimal_dates': optimal_dates,
            'optimal_times': ['18:00-21:00 IST', '12:00-15:00 IST'],
            'urgency': 'HIGH' if optimal_dates[0]['days_offset'] <= 3 else 'MEDIUM'
        }


# Test the cultural event calendar
if __name__ == "__main__":
    print("=== Cultural Event Calendar ===")
    
    print("\n[Test 1] Upcoming Events (90 days)")
    upcoming = CulturalEventCalendar.get_upcoming_events(90)
    print(f"  [OK] Found {len(upcoming)} upcoming events")
    for event in upcoming[:3]:
        print(f"    - {event['name']}: {event['date']} ({event['days_until']} days away)")
    
    print("\n[Test 2] Event Content Suggestions")
    suggestions = CulturalEventCalendar.get_event_content_suggestions('Christmas', 'metro_cities')
    print(f"  [OK] Event: {suggestions['event_name']}")
    print(f"  [OK] Themes: {suggestions['content_themes'][:3]}")
    print(f"  [OK] Hashtags: {suggestions['hashtags'][:3]}")
    
    print("\n[Test 3] Optimal Posting Window")
    window = CulturalEventCalendar.get_optimal_posting_window('Christmas')
    print(f"  [OK] Event date: {window['event_date']}")
    print(f"  [OK] Optimal dates: {len(window['optimal_dates'])}")
    print(f"  [OK] Urgency: {window['urgency']}")
    
    print("\n=== Cultural Event Calendar Working ===")