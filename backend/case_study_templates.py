"""
Case Study Templates
Templates for documenting user success stories
Phase 5: Pre-Seed Preparation
"""

CASE_STUDY_TEMPLATE = """
# Case Study: {Creator Name}

## Overview
- **Creator:** {Creator Name}
- **Niche:** {Niche}
- **Followers Before:** {Initial Followers}
- **Followers After:** {Final Followers}
- **Growth:** {Growth Percentage}
- **Period:** {Time Period}

## Problem
{Describe the creator's challenges before using Trendrop}

## Solution
{How Trendrop helped the creator}

## Results
- **Follower Growth:** {Follower Growth}
- **Engagement Rate:** {Engagement Rate}
- **Viral Posts:** {Number of Viral Posts}
- **Revenue Impact:** {Revenue Impact (if applicable)}

## Key Features Used
- [ ] Early Trend Detection
- [ ] Virality Prediction
- [ ] India-Specific Features
- [ ] Video Analysis
- [ ] AI Content Generation

## Testimonial
"{Creator's testimonial about their experience}"

## Metrics
| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Followers | {Initial} | {Final} | {Growth} |
| Engagement Rate | {Initial} | {Final} | {Growth} |
| Viral Posts | {Initial} | {Final} | {Growth} |
| Average Views | {Initial} | {Final} | {Growth} |

## Timeline
- **Day 0:** Started using Trendrop
- **Day 7:** First viral post
- **Day 30:** {Milestone}
- **Day 60:** {Milestone}
- **Day 90:** {Milestone}

## Tips for Other Creators
{Advice from the creator for other users}
"""

SAMPLE_CASE_STUDIES = [
    {
        "creator_name": "Priya Sharma",
        "niche": "Fitness",
        "initial_followers": "10,000",
        "final_followers": "25,000",
        "growth_percentage": "150%",
        "period": "3 months",
        "problem": "Priya was struggling to find trending audio and was posting at suboptimal times. Her engagement rate was stagnant at 2%.",
        "solution": "Using Trendrop's early trend detection, Priya found trending audio 6 hours before competitors. She also used the optimal posting times feature to post during peak hours (18:00-21:00 IST).",
        "results": {
            "follower_growth": "+15,000 followers",
            "engagement_rate": "5.8%",
            "viral_posts": "7",
            "revenue_impact": "Started earning ₹5,000/mo from brand deals"
        },
        "key_features": ["Early Trend Detection", "Optimal Posting Times", "India-Specific Features"],
        "testimonial": "Trendrop changed my content game. I went from 2% to 6% engagement in just 3 months. The early trend detection feature is a game-changer.",
        "metrics": {
            "followers": {"initial": "10,000", "final": "25,000", "improvement": "+150%"},
            "engagement": {"initial": "2%", "final": "5.8%", "improvement": "+190%"},
            "viral_posts": {"initial": "0", "final": "7", "improvement": "+7"},
            "avg_views": {"initial": "500", "final": "2,500", "improvement": "+400%"}
        },
        "timeline": {
            "day_0": "Started using Trendrop",
            "day_7": "First viral post using early trend detection",
            "day_30": "Hit 15,000 followers",
            "day_60": "Started getting brand deals",
            "day_90": "Reached 25,000 followers"
        },
        "tips": "Always check the early detection tab before creating content. Joining trends 6 hours early gives you 3x more reach."
    },
    {
        "creator_name": "Rahul Verma",
        "niche": "Comedy",
        "initial_followers": "5,000",
        "final_followers": "50,000",
        "growth_percentage": "900%",
        "period": "4 months",
        "problem": "Rahul was posting consistently but his videos weren't going viral. He didn't know which trends to follow and was wasting time on dying trends.",
        "solution": "Trendrop's virality prediction helped Rahul understand which of his content ideas would work before posting. He also used India-specific features during festivals for extra reach.",
        "results": {
            "follower_growth": "+45,000 followers",
            "engagement_rate": "8.2%",
            "viral_posts": "12",
            "revenue_impact": "Started earning ₹15,000/mo from sponsorships"
        },
        "key_features": ["Virality Prediction", "India-Specific Features", "Cultural Event Calendar"],
        "testimonial": "I went from 5K to 50K followers in 4 months. The virality prediction saved me so much time - I only create content that will actually work.",
        "metrics": {
            "followers": {"initial": "5,000", "final": "50,000", "improvement": "+900%"},
            "engagement": {"initial": "3%", "final": "8.2%", "improvement": "+173%"},
            "viral_posts": {"initial": "1", "final": "12", "improvement": "+11"},
            "avg_views": {"initial": "300", "final": "5,000", "improvement": "+1,567%"}
        },
        "timeline": {
            "day_0": "Started using Trendrop",
            "day_14": "First viral video using virality prediction",
            "day_30": "Used Diwali content ideas - got 10K views",
            "day_60": "Hit 25,000 followers",
            "day_90": "Crossed 50,000 followers"
        },
        "tips": "Use the cultural event calendar during festivals. My Diwali content got 10x more reach than usual."
    }
]


def generate_case_study(creator_data: dict) -> str:
    """
    Generate a case study from creator data
    
    Args:
        creator_data: Dictionary with creator information
    
    Returns:
        Formatted case study markdown
    """
    return CASE_STUDY_TEMPLATE.format(**creator_data)


def get_sample_case_studies() -> list:
    """
    Get sample case studies for demonstration
    
    Returns:
        List of sample case studies
    """
    return SAMPLE_CASE_STUDIES


if __name__ == "__main__":
    print("=== Case Study Templates ===")
    
    print("\n[Test 1] Case Study Template")
    print("  [OK] Case study template defined")
    print("  [OK] Sample case studies available: " + str(len(SAMPLE_CASE_STUDIES)))
    
    for i, study in enumerate(SAMPLE_CASE_STUDIES, 1):
        print(f"\n  [Sample {i}] {study['creator_name']} - {study['niche']}")
        print(f"    Growth: {study['growth_percentage']}")
        print(f"    Features: {', '.join(study['key_features'])}")
    
    print("\n=== Case Study Templates Working ===")