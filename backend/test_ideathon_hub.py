#!/usr/bin/env python3
"""
Test script for Ideathon Hub endpoints
Tests: Daily Ideas, Score Reel, Generate Hooks, Calendar
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from creator_tools import CreatorTools

def test_daily_ideas():
    """Test daily ideas generation"""
    print("Testing Daily Ideas...")
    try:
        ct = CreatorTools()
        ideas = ct.get_daily_ideas("test@example.com")
        print(f"[PASS] Daily Ideas: {len(ideas)} ideas generated")
        for i, idea in enumerate(ideas[:2]):  # Show first 2
            print(f"  {i+1}. {idea.get('title', 'No title')}: {idea.get('hook', 'No hook')}")
        return True
    except Exception as e:
        print(f"[FAIL] Daily Ideas failed: {e}")
        return False

def test_score_reel():
    """Test reel scoring"""
    print("\nTesting Score Reel...")
    try:
        ct = CreatorTools()
        score = ct.get_pre_post_score(
            niche="dance",
            hook="Check this out!",
            audio_title="Trending audio",
            caption="Amazing dance video #dance #viral",
            hashtags=["#dance", "#viral"],
            post_time="18:30"
        )
        print(f"[PASS] Score Reel: Overall score {score.get('overall_score', 0)}")
        print(f"  Breakdown: {score.get('breakdown', {})}")
        return True
    except Exception as e:
        print(f"[FAIL] Score Reel failed: {e}")
        return False

def test_generate_hooks():
    """Test hook generation"""
    print("\nTesting Generate Hooks...")
    try:
        ct = CreatorTools()
        hooks = ct.generate_hooks(niche="dance", topic="viral reels")
        print(f"[PASS] Generate Hooks: {len(hooks.get('hooks', []))} hooks generated")
        for i, hook in enumerate(hooks.get('hooks', [])[:2]):  # Show first 2
            print(f"  {i+1}. {hook.get('style', 'No style')}: {hook.get('text', 'No text')}")
        return True
    except Exception as e:
        print(f"[FAIL] Generate Hooks failed: {e}")
        return False

def test_calendar():
    """Test calendar generation"""
    print("\nTesting Calendar...")
    try:
        ct = CreatorTools()
        calendar = ct.generate_calendar(
            user_email="test@example.com",
            niche="dance",
            language="en",
            frequency="daily"
        )
        print(f"[PASS] Calendar: {len(calendar.get('calendar', []))} days generated")
        for i, day in enumerate(calendar.get('calendar', [])[:2]):  # Show first 2
            print(f"  Day {day.get('day', 0)}: {day.get('topic', 'No topic')}")
        return True
    except Exception as e:
        print(f"[FAIL] Calendar failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Ideathon Hub Backend Tests")
    print("=" * 50)
    
    results = []
    results.append(("Daily Ideas", test_daily_ideas()))
    results.append(("Score Reel", test_score_reel()))
    results.append(("Generate Hooks", test_generate_hooks()))
    results.append(("Calendar", test_calendar()))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    print("=" * 50)
    if all_passed:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)
