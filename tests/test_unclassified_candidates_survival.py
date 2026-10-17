import unittest
import os
import sys

# Add backend to sys.path
backend_dir = os.path.abspath("backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from trend_engine import TrendEngine, classify_single_trend

class TestUnclassifiedCandidatesSurvival(unittest.TestCase):
    def test_classify_single_trend_sets_confidence_above_threshold(self):
        """
        Prove that classify_single_trend sets confidence=0.75 without LLM classification,
        ensuring it is safely above the 0.55 low-confidence drop gate.
        """
        trend = {
            "audio_title": "Test Emerging Sound",
            "audio_artist": "Test Artist",
            "trend_score": 10.0,
            "reels": [
                {
                    "reel_id": "r1",
                    "caption": "fun aesthetic dance clip",
                    "hashtags": ["dance", "viral"],
                    "view_count": 1000,
                    "like_count": 100,
                    "audio_id": "aud_1",
                    "creator_country": "IN"
                }
            ]
        }
        
        success = classify_single_trend(trend)
        self.assertTrue(success, "classify_single_trend should return True")
        self.assertGreaterEqual(trend.get("confidence", 0.0), 0.70, "Confidence must be >= 0.70 to pass gate")
        
        # Test the exact gate formula at trend_engine.py:1218
        raw_conf = trend.get("confidence", 0.0)
        blended_conf = min(0.98, max(0.0, raw_conf) + min(0.12, (trend.get("trend_score", 0.0) or 0.0) / 50))
        self.assertGreater(blended_conf, 0.55, "Blended confidence must be strictly > 0.55 to prevent drop")
        
        # Verify that used_for_note is None or unclassified, but candidate survives
        self.assertIsNone(trend.get("used_for_note"), "used_for_note should be None when unclassified")
        self.assertEqual(trend.get("llm_classification_status"), "skipped_local_fallback", "Should have fallback status")

if __name__ == "__main__":
    unittest.main()
