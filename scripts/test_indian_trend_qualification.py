import os
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from companion_audio_promoter import parse_compact_count, promote_audio_to_trends
from artist_language_map import get_artist_language

def test_indian_parsing():
    test_cases = [
        ("9.6L reels", 960000),
        ("1.9L reels", 190000),
        ("1.5 Lakh reels", 150000),
        ("2.3 Lakhs", 230000),
        ("1.2 Cr", 12000000),
        ("1 Crore", 10000000),
        ("50K", 50000),
        ("1.2M", 1200000),
        ("500", 500)
    ]
    print("=== TEST 1: Number Parsing ===")
    all_passed = True
    for raw, expected in test_cases:
        res = parse_compact_count(raw)
        passed = (res == expected)
        if not passed:
            all_passed = False
        print(f"  '{raw}' -> {res} (Expected: {expected}) : {'PASS' if passed else 'FAIL'}")
    assert all_passed, "Some count test cases failed!"

def test_artist_mapping():
    print("\n=== TEST 2: Artist-to-Language Mapping ===")
    test_artists = [
        ("Babbu Maan", "pa"),
        ("Sanjay Leela Bhansali", "hi"),
        ("Aditya Narayan", "hi"),
        ("Doja Cat", "en"),
        ("Diljit Dosanjh", "pa"),
        ("Arijit Singh", "hi"),
        ("Anirudh Ravichander", "ta"),
        ("AP Dhillon", "pa"),
        ("Sanjay Leela Bhansali, Aditya Narayan", "hi")
    ]
    all_passed = True
    for artist, expected_lang in test_artists:
        res = get_artist_language(artist)
        passed = (res == expected_lang)
        if not passed:
            all_passed = False
        print(f"  '{artist}' -> '{res}' (Expected: '{expected_lang}') : {'PASS' if passed else 'FAIL'}")
    assert all_passed, "Some artist mappings failed!"

def test_promotion_payloads():
    print("\n=== TEST 3: Promotion Payload Dry-Run ===")
    
    # 1. Babbu Maan - Saaun Di Jhadi
    meta_1 = {
        "audio_id": "1840291823901",
        "title": "Saaun Di Jhadi",
        "artist": "Babbu Maan",
        "reels_count_int": parse_compact_count("9.6L reels"),
        "raw_reels_count": "9.6L reels",
        "is_trending_badge": True,
        "is_viral": True,
        "top_views": ["120K", "95K", "80K"]
    }
    res_1 = promote_audio_to_trends(None, meta_1, dry_run=True)
    p1 = res_1["payload"]
    print("Babbu Maan Payload:")
    print(f"  Title: {p1['audio_title']}")
    print(f"  Artist: {p1['audio_artist']}")
    print(f"  Lang / LangFinal: {p1['language']} / {p1['language_final']}")
    print(f"  Reel Count: {p1['audio_use_count']}")
    print(f"  Why This Works: {p1['why_this_works']}")
    assert p1["language_final"] == "pa"
    assert p1["audio_use_count"] == 960000
    assert "↗ Trending" in p1["why_this_works"]

    # 2. Sanjay Leela Bhansali - Ishqaun Dhishqyaun
    meta_2 = {
        "audio_id": "1940291823902",
        "title": "Ishqaun Dhishqyaun",
        "artist": "Sanjay Leela Bhansali, Aditya Narayan",
        "reels_count_int": parse_compact_count("1.9L reels"),
        "raw_reels_count": "1.9L reels",
        "is_trending_badge": False,
        "is_viral": True,
        "top_views": ["65K", "45K"]
    }
    res_2 = promote_audio_to_trends(None, meta_2, dry_run=True)
    p2 = res_2["payload"]
    print("\nIshqaun Dhishqyaun Payload:")
    print(f"  Title: {p2['audio_title']}")
    print(f"  Artist: {p2['audio_artist']}")
    print(f"  Lang / LangFinal: {p2['language']} / {p2['language_final']}")
    print(f"  Reel Count: {p2['audio_use_count']}")
    print(f"  Why This Works: {p2['why_this_works']}")
    assert p2["language_final"] == "hi"
    assert p2["audio_use_count"] == 190000

    print("\nALL VERIFICATIONS PASSED 100%!")

if __name__ == "__main__":
    test_indian_parsing()
    test_artist_mapping()
    test_promotion_payloads()
