"""
Unit tests for View-Velocity Outlier Detector
"""

import unittest
from backend.view_velocity_detector import evaluate_view_velocity_outlier


class TestViewVelocityDetector(unittest.TestCase):

    def test_tier_1_exact_baseline_pass(self):
        reel = {"view_count": 15000, "owner_username": "creator_a"}
        baseline = {"post_count": 10, "median_views": 4000.0}  # 15000 >= 3 * 4000 (12000)
        res = evaluate_view_velocity_outlier(reel, baseline)
        self.assertTrue(res["is_view_velocity_outlier"])
        self.assertEqual(res["outlier_tier"], "exact_baseline")
        self.assertFalse(res["needs_baseline_fetch"])

    def test_tier_1_exact_baseline_fail(self):
        reel = {"view_count": 10000, "owner_username": "creator_a"}
        baseline = {"post_count": 10, "median_views": 4000.0}  # 10000 < 3 * 4000 (12000)
        res = evaluate_view_velocity_outlier(reel, baseline)
        self.assertFalse(res["is_view_velocity_outlier"])
        self.assertEqual(res["outlier_tier"], "exact_baseline")

    def test_tier_2_heuristic_tier_pass(self):
        # Creator with 3,000 followers: threshold = max(20000, 3000 * 15) = 45,000
        reel = {"view_count": 50000, "owner_follower_count": 3000, "owner_username": "creator_b"}
        res = evaluate_view_velocity_outlier(reel, None)
        self.assertTrue(res["is_view_velocity_outlier"])
        self.assertEqual(res["outlier_tier"], "heuristic_tier")
        self.assertTrue(res["needs_baseline_fetch"])

    def test_tier_2_heuristic_tier_fail(self):
        # Creator with 5,000 followers: threshold = max(20000, 5000 * 15) = 75,000
        reel = {"view_count": 60000, "owner_follower_count": 5000, "owner_username": "creator_b"}
        res = evaluate_view_velocity_outlier(reel, None)
        self.assertFalse(res["is_view_velocity_outlier"])
        self.assertEqual(res["outlier_tier"], "heuristic_tier")

    def test_tier_3_untracked_micro_breakout_pass(self):
        # Micro-creator with 41 followers getting 101,000 views (DdPAAMPoanb case study parameters)
        reel = {
            "reel_id": "DdPAAMPoanb",
            "view_count": 101000,
            "owner_follower_count": 41,
            "owner_username": "micro_gym_creator",
        }
        res = evaluate_view_velocity_outlier(reel, None)
        self.assertTrue(res["is_view_velocity_outlier"])
        self.assertEqual(res["outlier_tier"], "untracked_micro")
        self.assertTrue(res["needs_baseline_fetch"])

    def test_default_2500_followers_routes_to_tier_3(self):
        # Default 2500 placeholder without baseline MUST route to Tier 3 (50k floor), not Tier 2 (37.5k)
        reel_below_50k = {"view_count": 40000, "owner_follower_count": 2500, "owner_username": "hashtag_reel"}
        res1 = evaluate_view_velocity_outlier(reel_below_50k, None)
        self.assertFalse(res1["is_view_velocity_outlier"])
        self.assertIsNone(res1["outlier_tier"])

    def test_macro_account_without_baseline_is_not_untracked_micro(self):
        # Creator with 31,356 followers (DdRNOXeM5NU) without baseline MUST NOT route to Tier 3 untracked_micro
        reel_macro = {"reel_id": "DdRNOXeM5NU", "view_count": 1006000, "owner_follower_count": 31356, "owner_username": "swetaganguly9"}
        res = evaluate_view_velocity_outlier(reel_macro, None)
        self.assertFalse(res["is_view_velocity_outlier"])
        self.assertIsNone(res["outlier_tier"])


if __name__ == "__main__":
    unittest.main()


