"""
Unit Tests for Search V2 Engine (Order 81 Phase 4)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from search_v2_engine import (
    parse_search_query,
    rank_and_filter_search,
    build_template_count_line,
    build_editable_chips,
    execute_search_v2,
    is_gibberish
)

class TestSearchV2Engine(unittest.TestCase):

    def test_01_gym_query_parsing(self):
        q = "what should I use for a gym reel?"
        parsed = parse_search_query(q)
        self.assertFalse(parsed["is_gibberish"])
        self.assertTrue(any(n in ["Fitness", "Gym", "Workout"] for n in parsed["niches"]))

    def test_02_global_fashion_dance_rising(self):
        q = "global fashion and dance rising"
        parsed = parse_search_query(q)
        self.assertEqual(parsed["mode"], "global")
        self.assertEqual(parsed["stage"], "Blowing up")
        self.assertTrue("Fashion" in parsed["niches"])
        self.assertTrue("Dance" in parsed["niches"])

    def test_03_old_but_still_alive(self):
        q = "old but still alive"
        parsed = parse_search_query(q)
        self.assertEqual(parsed["stage"], "Still going")

    def test_04_gibberish_query(self):
        q = "asdf qwer"
        parsed = parse_search_query(q)
        self.assertTrue(parsed["is_gibberish"])
        results, relaxed = rank_and_filter_search([], parsed)
        self.assertEqual(len(results), 0)

    def test_05_bhojpuri_india_mode_empty(self):
        q = "bhojpuri"
        parsed = parse_search_query(q, current_mode="india")
        self.assertEqual(parsed["language"], "bho")
        # Sample with only Tier C / low use bhojpuri trends
        mock_trends = [
            {"id": 1, "audio_title": "Bhojpuri Low Use", "audio_artist": "Singer A", "language": "bho", "audio_use_count": 5, "quality_tier": "C"}
        ]
        results, relaxed = rank_and_filter_search(mock_trends, parsed)
        self.assertEqual(len(results), 0, "Bhojpuri in India mode with <20 use count must be empty")

    def test_06_artist_diversity_constraint(self):
        """Top 10 must have at most 2 tracks from the same artist."""
        parsed = {
            "is_gibberish": False,
            "niches": [],
            "mode": "india",
            "stage": None,
            "include_expired": False,
            "language": None,
            "sort": "momentum",
            "keywords": ["dance"]
        }
        mock_trends = [
            {"id": i, "audio_title": f"Song {i}", "audio_artist": "Prolific Artist", "search_text": "dance", "reel_count": 100 - i, "trend_age_hours": 12, "quality_tier": "A"}
            for i in range(1, 10)
        ]
        mock_trends.extend([
            {"id": 20 + i, "audio_title": f"Other {i}", "audio_artist": f"Artist {i}", "search_text": "dance", "reel_count": 50, "trend_age_hours": 12, "quality_tier": "B"}
            for i in range(1, 10)
        ])
        results, relaxed = rank_and_filter_search(mock_trends, parsed)
        top_10 = results[:10]
        prolific_count = sum(1 for t in top_10 if t["audio_artist"] == "Prolific Artist")
        self.assertLessEqual(prolific_count, 2, "Artist diversity constraint violated: more than 2 tracks from same artist in top 10")

    def test_07_count_line_template(self):
        line1 = build_template_count_line(5, "gym motivation", "momentum", relaxed=False)
        self.assertEqual(line1, 'Found 5 sounds for "gym motivation" sorted by momentum.')
        line2 = build_template_count_line(0, "asdf qwer", "momentum", relaxed=False)
        self.assertEqual(line2, 'No matching sounds found for "asdf qwer".')

    def test_08_relax_one_filter_fallback(self):
        """If strict query with stage + niche yields 0, relaxes stage filter."""
        parsed = {
            "is_gibberish": False,
            "niches": ["Fitness"],
            "mode": "india",
            "stage": "Blowing up",
            "include_expired": False,
            "language": None,
            "sort": "momentum",
            "keywords": []
        }
        # Only has a "Still going" Fitness trend
        mock_trends = [
            {"id": 1, "audio_title": "Gym Anthem", "audio_artist": "Artist X", "stage": "Still going", "niche_tag": "Fitness", "search_text": "gym fitness workout", "reel_count": 10, "trend_age_hours": 10, "quality_tier": "A"}
        ]
        results, relaxed = rank_and_filter_search(mock_trends, parsed)
        self.assertEqual(len(results), 1)
        self.assertTrue(relaxed, "Expected relaxed=True when stage filter was relaxed")

if __name__ == "__main__":
    unittest.main()
