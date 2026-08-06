"""
Pitch Deck Structure
Structure for pre-seed funding pitch deck
Phase 5: Pre-Seed Preparation
"""

PITCH_DECK_STRUCTURE = {
    "slide_1": {
        "title": "Trendrop",
        "subtitle": "AI-Powered Trend Intelligence for Indian Instagram Creators",
        "tagline": "Predict Trends Before They Go Viral"
    },
    "slide_2": {
        "title": "Problem",
        "points": [
            "Indian creators struggle to find trending content",
            "Most tools show trends AFTER they're viral (too late)",
            "No India-specific intelligence for cultural events",
            "Video optimization is guesswork without data",
            "Creators waste time on content that won't perform"
        ]
    },
    "slide_3": {
        "title": "Solution",
        "points": [
            "Early Trend Detection - Predict trends 6-12 hours before virality",
            "Virality Prediction - Know if content will work BEFORE posting",
            "India-Specific Intelligence - Regional trends, cultural events, language support",
            "Video Analysis - Metadata + visual analysis with actionable recommendations",
            "Real Data Integration - Instagram + YouTube APIs for real-time insights"
        ]
    },
    "slide_4": {
        "title": "Market Opportunity",
        "data": {
            "instagram_creators_india": "30M+",
            "creator_economy_india": "$5B by 2025",
            "growth_rate": "30% YoY",
            "market_gap": "No India-specific trend intelligence tool exists"
        }
    },
    "slide_5": {
        "title": "Product",
        "features": [
            {
                "name": "Early Detection",
                "description": "Predict trends 6-12h before virality",
                "differentiator": "Competitors show trends AFTER they're viral"
            },
            {
                "name": "Virality Prediction",
                "description": "Predict content performance before posting",
                "differentiator": "No other tool offers this"
            },
            {
                "name": "India Intelligence",
                "description": "Regional trends, cultural events, language support",
                "differentiator": "Global tools lack India focus"
            },
            {
                "name": "Video Analysis",
                "description": "Metadata + visual analysis with recommendations",
                "differentiator": "Video optimization is usually expensive"
            }
        ]
    },
    "slide_6": {
        "title": "Traction",
        "metrics": {
            "users": "500-1,000 target",
            "paying_users": "50-100 target",
            "mrr": "$1,000-2,000 target",
            "conversion_rate": "10-15% target",
            "churn_rate": "<5% target"
        }
    },
    "slide_7": {
        "title": "Business Model",
        "revenue_streams": [
            {
                "name": "Subscription",
                "pricing": "Free, Pro ($5/mo), Business ($20/mo)",
                "revenue_share": "80%"
            },
            {
                "name": "Enterprise",
                "pricing": "Custom pricing for agencies",
                "revenue_share": "15%"
            },
            {
                "name": "API",
                "pricing": "Pay-per-call for enterprise",
                "revenue_share": "5%"
            }
        ]
    },
    "slide_8": {
        "title": "Go-to-Market",
        "strategy": [
            "Phase 1: Launch to early adopters (Week 1-4)",
            "Phase 2: Creator partnerships (Week 5-8)",
            "Phase 3: Influencer marketing (Week 9-12)",
            "Phase 4: Paid ads (Month 4+)",
            "Phase 5: Enterprise sales (Month 6+)"
        ]
    },
    "slide_9": {
        "title": "Competition",
        "competitors": [
            {
                "name": "Instagram Insights",
                "strength": "Free, built-in",
                "weakness": "No trend prediction, no India focus"
            },
            {
                "name": "Creator Studio",
                "strength": "Official Meta tool",
                "weakness": "No early detection, no virality prediction"
            },
            {
                "name": "Viral TikTok",
                "strength": "Global trends",
                "weakness": "No India focus, no Instagram focus"
            }
        ],
        "differentiation": "Only tool with early detection + virality prediction + India intelligence"
    },
    "slide_10": {
        "title": "Team",
        "members": [
            {
                "name": "Founder",
                "role": "CEO & Product",
                "background": "Builder with passion for creator economy"
            }
        ],
        "hiring_plan": "Looking to hire: CTO, Marketing Lead, Content Lead"
    },
    "slide_11": {
        "title": "The Ask",
        "funding": {
            "amount": "$250,000",
            "use_of_funds": [
                "Product Development: 40%",
                "Marketing & Growth: 30%",
                "Team: 20%",
                "Operations: 10%"
            ],
            "milestones": [
                "1,000 paying users",
                "$5,000 MRR",
                "3 case studies",
                "Enterprise partnerships"
            ],
            "timeline": "12 months"
        }
    },
    "slide_12": {
        "title": "Contact",
        "contact": {
            "email": "founder@trendrop.ai",
            "website": "https://trendrop.ai",
            "social": "@trendrop_ai"
        }
    }
}


def generate_pitch_deck_content() -> dict:
    """
    Generate pitch deck content
    
    Returns:
        Dictionary with all slide content
    """
    return PITCH_DECK_STRUCTURE


def export_pitch_deck_to_markmark() -> str:
    """
    Export pitch deck to markdown format
    
    Returns:
        Markdown string of pitch deck
    """
    content = []
    
    for slide_num, slide_data in PITCH_DECK_STRUCTURE.items():
        content.append(f"# {slide_data['title']}\n")
        
        if 'subtitle' in slide_data:
            content.append(f"## {slide_data['subtitle']}\n")
        
        if 'tagline' in slide_data:
            content.append(f"**{slide_data['tagline']}**\n")
        
        if 'points' in slide_data:
            for point in slide_data['points']:
                content.append(f"- {point}\n")
        
        if 'data' in slide_data:
            for key, value in slide_data['data'].items():
                content.append(f"- **{key}:** {value}\n")
        
        if 'features' in slide_data:
            for feature in slide_data['features']:
                content.append(f"### {feature['name']}\n")
                content.append(f"- {feature['description']}\n")
                content.append(f"- *Differentiation:* {feature['differentiator']}\n")
        
        if 'metrics' in slide_data:
            for key, value in slide_data['metrics'].items():
                content.append(f"- **{key}:** {value}\n")
        
        if 'revenue_streams' in slide_data:
            for stream in slide_data['revenue_streams']:
                content.append(f"### {stream['name']}\n")
                content.append(f"- Pricing: {stream['pricing']}\n")
                content.append(f"- Revenue Share: {stream['revenue_share']}\n")
        
        if 'strategy' in slide_data:
            for phase in slide_data['strategy']:
                content.append(f"- {phase}\n")
        
        if 'competitors' in slide_data:
            for competitor in slide_data['competitors']:
                content.append(f"### {competitor['name']}\n")
                content.append(f"- Strength: {competitor['strength']}\n")
                content.append(f"- Weakness: {competitor['weakness']}\n")
            content.append(f"\n**Differentiation:** {slide_data['differentiation']}\n")
        
        if 'members' in slide_data:
            for member in slide_data['members']:
                content.append(f"### {member['name']}\n")
                content.append(f"- Role: {member['role']}\n")
                content.append(f"- Background: {member['background']}\n")
            content.append(f"\n**Hiring Plan:** {slide_data['hiring_plan']}\n")
        
        if 'funding' in slide_data:
            funding = slide_data['funding']
            content.append(f"- **Amount:** {funding['amount']}\n")
            content.append(f"- **Timeline:** {funding['timeline']}\n")
            content.append(f"\n**Use of Funds:**\n")
            for use in funding['use_of_funds']:
                content.append(f"- {use}\n")
            content.append(f"\n**Milestones:**\n")
            for milestone in funding['milestones']:
                content.append(f"- {milestone}\n")
        
        if 'contact' in slide_data:
            for key, value in slide_data['contact'].items():
                content.append(f"- **{key}:** {value}\n")
        
        content.append("\n---\n")
    
    return "\n".join(content)


if __name__ == "__main__":
    print("=== Pitch Deck Structure ===")
    
    print("\n[Test 1] Pitch Deck Structure")
    print("  [OK] Pitch deck structure defined")
    print(f"  [OK] Total slides: {len(PITCH_DECK_STRUCTURE)}")
    
    for slide_num, slide_data in PITCH_DECK_STRUCTURE.items():
        print(f"  [Slide] {slide_data['title']}")
    
    print("\n[Test 2] Export to Markdown")
    markdown = export_pitch_deck_to_markmark()
    print(f"  [OK] Generated {len(markdown)} characters of markdown")
    
    print("\n=== Pitch Deck Structure Working ===")
    print("\nNote: Pitch deck can be exported to:")
    print("  - Markdown (for documentation)")
    print("  - PowerPoint (using export tools)")
    print("  - Google Slides (using import tools)")
    print("  - Canva (for visual design)")