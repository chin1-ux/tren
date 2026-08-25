#!/usr/bin/env python3
"""
Unit test for velocity-based enrollment logic without database connection.
Tests the decision logic only.
"""

def test_enrollment_criteria():
    """Test the new enrollment criteria logic"""
    
    print("=== Testing Velocity-Based Enrollment Logic ===\n")
    
    # Test Case 1: 2+ reels (original criteria)
    print("Test 1: 2+ reels (original criteria)")
    reel_count = 2
    high_velocity_signal = False
    should_enroll = reel_count >= 2 or high_velocity_signal
    print(f"  Reel count: {reel_count}, High velocity: {high_velocity_signal}")
    print(f"  Should enroll: {should_enroll}")
    print(f"  Expected: True [PASS]\n" if should_enroll else "  Expected: True [FAIL]\n")
    
    # Test Case 2: 1 reel, high velocity (new criteria)
    print("Test 2: 1 reel, high velocity")
    reel_count = 1
    high_velocity_signal = True
    should_enroll = reel_count >= 2 or high_velocity_signal
    print(f"  Reel count: {reel_count}, High velocity: {high_velocity_signal}")
    print(f"  Should enroll: {should_enroll}")
    print(f"  Expected: True [PASS]\n" if should_enroll else "  Expected: True [FAIL]\n")
    
    # Test Case 3: 1 reel, low velocity (should not enroll)
    print("Test 3: 1 reel, low velocity")
    reel_count = 1
    high_velocity_signal = False
    should_enroll = reel_count >= 2 or high_velocity_signal
    print(f"  Reel count: {reel_count}, High velocity: {high_velocity_signal}")
    print(f"  Should enroll: {should_enroll}")
    print(f"  Expected: False [PASS]\n" if not should_enroll else "  Expected: False [FAIL]\n")
    
    # Test Case 4: 0 reels (should not enroll)
    print("Test 4: 0 reels")
    reel_count = 0
    high_velocity_signal = False
    should_enroll = reel_count >= 2 or high_velocity_signal
    print(f"  Reel count: {reel_count}, High velocity: {high_velocity_signal}")
    print(f"  Should enroll: {should_enroll}")
    print(f"  Expected: False [PASS]\n" if not should_enroll else "  Expected: False [FAIL]\n")
    
    # Test Case 5: High velocity threshold testing
    print("Test 5: Velocity threshold testing")
    
    test_reels = [
        {"velocity_score": 6000, "view_count": 5000, "like_count": 500},   # High velocity
        {"velocity_score": 1000, "view_count": 20000, "like_count": 2000}, # High engagement
        {"velocity_score": 100, "view_count": 100, "like_count": 10},      # Low everything
    ]
    
    for i, reel in enumerate(test_reels, 1):
        vel = reel.get("velocity_score", 0.0) or 0.0
        views = reel.get("view_count", 0) or 0
        likes = reel.get("like_count", 0) or 0
        
        high_velocity = vel > 5000 or (likes > 1000 and views > 10000)
        print(f"  Reel {i}: velocity={vel}, views={views}, likes={likes}")
        print(f"  High velocity signal: {high_velocity}")
        
        expected = [True, True, False][i-1]
        print(f"  Expected: {expected} {'[PASS]' if high_velocity == expected else '[FAIL]'}\n")
    
    # Test Case 6: Edge cases - exactly at thresholds
    print("Test 6: Edge cases - exactly at thresholds")
    
    edge_reels = [
        {"velocity_score": 5000, "view_count": 10000, "like_count": 1000},  # Exactly at thresholds (should FAIL - needs >)
        {"velocity_score": 5001, "view_count": 10000, "like_count": 1000},  # Just above velocity threshold (should PASS)
        {"velocity_score": 5000, "view_count": 10001, "like_count": 1001},  # Just above engagement thresholds (should PASS)
    ]
    
    for i, reel in enumerate(edge_reels, 1):
        vel = reel.get("velocity_score", 0.0) or 0.0
        views = reel.get("view_count", 0) or 0
        likes = reel.get("like_count", 0) or 0
        
        high_velocity = vel > 5000 or (likes > 1000 and views > 10000)
        print(f"  Reel {i}: velocity={vel}, views={views}, likes={likes}")
        print(f"  High velocity signal: {high_velocity}")
        
        expected = [False, True, True][i-1]
        print(f"  Expected: {expected} {'[PASS]' if high_velocity == expected else '[FAIL]'}\n")
    
    # Test Case 7: Missing/NULL data handling
    print("Test 7: Missing/NULL data handling")
    
    null_reels = [
        {"velocity_score": None, "view_count": None, "like_count": None},  # All NULL
        {"velocity_score": 6000, "view_count": None, "like_count": None},  # High velocity, NULL engagement
        {"velocity_score": None, "view_count": 20000, "like_count": 2000},  # NULL velocity, high engagement
        {"velocity_score": 0, "view_count": 0, "like_count": 0},  # All zeros
        {"velocity_score": -100, "view_count": -50, "like_count": -10},  # Negative values (edge case)
    ]
    
    for i, reel in enumerate(null_reels, 1):
        vel = reel.get("velocity_score", 0.0) or 0.0
        views = reel.get("view_count", 0) or 0
        likes = reel.get("like_count", 0) or 0
        
        high_velocity = vel > 5000 or (likes > 1000 and views > 10000)
        print(f"  Reel {i}: velocity={vel}, views={views}, likes={likes}")
        print(f"  High velocity signal: {high_velocity}")
        
        expected = [False, True, True, False, False][i-1]
        print(f"  Expected: {expected} {'[PASS]' if high_velocity == expected else '[FAIL]'}\n")
    
    # Test Case 8: Partial engagement (one threshold met, not both)
    print("Test 8: Partial engagement (one threshold met, not both)")
    
    partial_reels = [
        {"velocity_score": 100, "view_count": 20000, "like_count": 500},   # High views, low likes (should FAIL)
        {"velocity_score": 100, "view_count": 5000, "like_count": 2000},  # High likes, low views (should FAIL)
        {"velocity_score": 100, "view_count": 20000, "like_count": 2000}, # Both high (should PASS)
    ]
    
    for i, reel in enumerate(partial_reels, 1):
        vel = reel.get("velocity_score", 0.0) or 0.0
        views = reel.get("view_count", 0) or 0
        likes = reel.get("like_count", 0) or 0
        
        high_velocity = vel > 5000 or (likes > 1000 and views > 10000)
        print(f"  Reel {i}: velocity={vel}, views={views}, likes={likes}")
        print(f"  High velocity signal: {high_velocity}")
        
        expected = [False, False, True][i-1]
        print(f"  Expected: {expected} {'[PASS]' if high_velocity == expected else '[FAIL]'}\n")
    
    print("=== All Tests Complete ===")

if __name__ == '__main__':
    test_enrollment_criteria()
