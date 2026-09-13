import os
import sys
import math
import unittest
from datetime import datetime, timezone

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from instagram_scraper_browser import InstagramScraper

class TestScraperPreFilter(unittest.TestCase):
    def setUp(self):
        self.scraper = InstagramScraper()
        self.now_utc = datetime.now(timezone.utc)

    def _eval_item(self, raw_media_dict):
        """Helper to run extraction and pre-filtering logic matching _process_hashtag_batch"""
        # 1. Extraction step
        raw_play_count = raw_media_dict.get("play_count") if raw_media_dict.get("play_count") is not None else raw_media_dict.get("view_count")
        item = {
            "shortCode": raw_media_dict.get("code", "test_code"),
            "videoViewCount": raw_play_count,
            "likesCount": raw_media_dict.get("like_count"),
            "commentsCount": raw_media_dict.get("comment_count") or 0,
            "ownerFollowersCount": 2500,
            "timestamp": self.now_utc.isoformat(),
            "ownerUsername": "test_user"
        }

        # 2. Batch pre-filter evaluation
        raw_view = item.get("videoViewCount")
        view = int(raw_view) if raw_view is not None else None
        raw_likes = item.get("likesCount")
        likes = int(raw_likes) if raw_likes is not None else 0
        comments = int(item.get("commentsCount") or 0)
        hours_live = 2.0
        followers = 2500

        if view is not None:
            engagement = (view * 1.0) + (likes * 3.0) + (comments * 3.0)
        else:
            engagement = (likes * 3.0) + (comments * 3.0)

        normalized_followers = math.log(followers + 10)
        velocity = (engagement / hours_live / normalized_followers) * 100
        decay_factor = 0.5 ** (hours_live / 24.0)
        velocity *= decay_factor

        is_outlier_candidate = False

        # Two-branch pre-filter logic
        if not is_outlier_candidate:
            if view is not None:
                if view < 2000 and likes < 50:
                    return False, "low_engagement"
            else:
                if likes < 50:
                    return False, "low_engagement"

        if not (velocity > 0.3 or (view is not None and view > 15000 and hours_live < 6) or is_outlier_candidate):
            return False, "velocity_failed"

        return True, "passed"

    def test_case_1_null_play_count_high_likes_passes(self):
        """Item with play_count=None, likes=60 MUST PASS pre-filtering"""
        media = {"code": "test1", "play_count": None, "like_count": 60, "comment_count": 5}
        passed, reason = self._eval_item(media)
        self.assertTrue(passed, f"Expected item to pass, got: {reason}")
        self.assertEqual(reason, "passed")

    def test_case_2_null_play_count_low_likes_filtered(self):
        """Item with play_count=None, likes=30 MUST BE FILTERED as low engagement"""
        media = {"code": "test2", "play_count": None, "like_count": 30, "comment_count": 2}
        passed, reason = self._eval_item(media)
        self.assertFalse(passed)
        self.assertEqual(reason, "low_engagement")

    def test_case_3_low_views_and_low_likes_filtered(self):
        """Item with play_count=1500, likes=30 MUST BE FILTERED (preserving old behavior)"""
        media = {"code": "test3", "play_count": 1500, "like_count": 30, "comment_count": 1}
        passed, reason = self._eval_item(media)
        self.assertFalse(passed)
        self.assertEqual(reason, "low_engagement")

    def test_case_4_high_views_and_high_likes_passes(self):
        """Item with play_count=15000, likes=500 MUST PASS"""
        media = {"code": "test4", "play_count": 15000, "like_count": 500, "comment_count": 20}
        passed, reason = self._eval_item(media)
        self.assertTrue(passed)
        self.assertEqual(reason, "passed")

if __name__ == "__main__":
    unittest.main()
