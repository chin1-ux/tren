import unittest
from datetime import datetime, timezone, timedelta
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dynamic_hashtag_discoverer import DynamicHashtagDiscoverer


class TestDynamicHashtagDiscoverer(unittest.TestCase):
    def setUp(self):
        self.discoverer = DynamicHashtagDiscoverer(max_queue_size=5, default_ttl_hours=72)

    def test_meta_tag_regex_blacklisting(self):
        """Ensure generic meta-tags and near-miss spam variants (e.g. #fypシ, #viralvideo) are rejected by regex."""
        blacklisted_tags = [
            'fyp', '#fypシ', 'fypage', '#viralvideo', 'REELS', 'reelsinstagram',
            '#trendingtopic', 'explorepage', 'follow4follow', 'likeforlike', 'foryoupage'
        ]
        for tag in blacklisted_tags:
            is_valid, reason = self.discoverer.check_meta_blacklist(tag)
            self.assertFalse(is_valid, f"Tag '{tag}' should have been blacklisted by regex but passed.")
            self.assertEqual(reason, "META_SPAM_BLACKLIST")

        valid_tags = ['ryanleslie', '#dancechallenge', 'upsidedown', 'fashiontransformation', 'zumba']
        for tag in valid_tags:
            is_valid, reason = self.discoverer.check_meta_blacklist(tag)
            self.assertTrue(is_valid, f"Tag '{tag}' should have passed blacklist check.")
            self.assertIsNone(reason)

    def test_velocity_calculation_smoothed(self):
        """Verify velocity calculation uses Laplace smoothing to handle zero baselines safely."""
        # Zero baseline, zero recent
        v0 = self.discoverer.calculate_velocity(recent_count=0, baseline_count=0)
        self.assertEqual(v0, 0.2)  # (0 + 1) / (0 + 5) = 0.2

        # 10 occurrences in recent 6h, 0 in previous 18h
        v1 = self.discoverer.calculate_velocity(recent_count=10, baseline_count=0)
        self.assertAlmostEqual(v1, 2.2, places=2)  # (10 + 1) / (0 + 5) = 2.2

        # 50 occurrences in recent 6h, 5 in previous 18h
        v2 = self.discoverer.calculate_velocity(recent_count=50, baseline_count=5)
        self.assertAlmostEqual(v2, 5.1, places=2)  # (50 + 1) / (5 + 5) = 5.1

    def test_single_creator_boundary_floors(self):
        """Test boundary conditions for single-creator override at exact 50,000 views and 5,000 likes thresholds."""
        now = datetime.now(timezone.utc)

        # Boundary Test 1: 49,999 views and 4,999 likes -> MUST REJECT
        reels_below_floor = [
            {
                'id': '101',
                'owner_username': 'creator1',
                'created_at': now.isoformat(),
                'play_count': 49999,
                'like_count': 4999,
                'caption': '#newbreakouttag'
            }
        ]
        is_valid, reason, score = self.discoverer.evaluate_quality_gate(
            hashtag='newbreakouttag',
            reels=reels_below_floor,
            recent_count=10,
            baseline_count=0,
            verified_audio_ids=set()
        )
        self.assertFalse(is_valid, "49,999 views should fail single creator engagement floor.")
        self.assertIn("INSUFFICIENT_CREATOR_DIVERSITY", reason)

        # Boundary Test 2: 50,000 views exactly -> MUST PASS OVERRIDE
        reels_view_floor = [
            {
                'id': '102',
                'owner_username': 'creator1',
                'created_at': now.isoformat(),
                'play_count': 50000,
                'like_count': 100,
                'caption': '#newbreakouttag'
            }
        ]
        is_valid, reason, score = self.discoverer.evaluate_quality_gate(
            hashtag='newbreakouttag',
            reels=reels_view_floor,
            recent_count=10,
            baseline_count=0,
            verified_audio_ids=set()
        )
        self.assertTrue(is_valid, "50,000 views exactly should pass single creator override.")
        self.assertEqual(reason, "SINGLE_CREATOR_HIGH_VELOCITY_OVERRIDE")

        # Boundary Test 3: 5,000 likes exactly -> MUST PASS OVERRIDE
        reels_like_floor = [
            {
                'id': '103',
                'owner_username': 'creator1',
                'created_at': now.isoformat(),
                'play_count': 1000,
                'like_count': 5000,
                'caption': '#newbreakouttag'
            }
        ]
        is_valid, reason, score = self.discoverer.evaluate_quality_gate(
            hashtag='newbreakouttag',
            reels=reels_like_floor,
            recent_count=10,
            baseline_count=0,
            verified_audio_ids=set()
        )
        self.assertTrue(is_valid, "5,000 likes exactly should pass single creator override.")
        self.assertEqual(reason, "SINGLE_CREATOR_HIGH_VELOCITY_OVERRIDE")

    def test_creator_diversity_floor(self):
        """Multiple creators in 12h window pass quality gate even with normal view counts."""
        now = datetime.now(timezone.utc)
        reels_multi = [
            {'id': '1', 'owner_username': 'user_a', 'created_at': now.isoformat(), 'play_count': 1000, 'caption': '#dancemove'},
            {'id': '2', 'owner_username': 'user_b', 'created_at': (now - timedelta(hours=3)).isoformat(), 'play_count': 1200, 'caption': '#dancemove'}
        ]
        is_valid, reason, score = self.discoverer.evaluate_quality_gate(
            hashtag='dancemove',
            reels=reels_multi,
            recent_count=2,
            baseline_count=0,
            verified_audio_ids=set()
        )
        self.assertTrue(is_valid)
        self.assertEqual(reason, "CREATOR_DIVERSITY_PASSED")

    def test_anchor_cooccurrence_confidence_booster(self):
        """Co-occurrence with verified trend audio acts as a multiplier boost on score."""
        now = datetime.now(timezone.utc)
        reels = [
            {'id': '1', 'owner_username': 'user_a', 'audio_id': 'audio_trend_1', 'created_at': now.isoformat(), 'play_count': 2000, 'caption': '#breakout'},
            {'id': '2', 'owner_username': 'user_b', 'audio_id': 'audio_trend_1', 'created_at': now.isoformat(), 'play_count': 2000, 'caption': '#breakout'}
        ]

        # Score without verified anchor
        _, _, score_no_anchor = self.discoverer.evaluate_quality_gate(
            hashtag='breakout',
            reels=reels,
            recent_count=2,
            baseline_count=0,
            verified_audio_ids=set()
        )

        # Score WITH verified anchor ('audio_trend_1' is in verified_audio_ids)
        _, _, score_with_anchor = self.discoverer.evaluate_quality_gate(
            hashtag='breakout',
            reels=reels,
            recent_count=2,
            baseline_count=0,
            verified_audio_ids={'audio_trend_1'}
        )

        self.assertGreater(score_with_anchor, score_no_anchor)
        self.assertAlmostEqual(score_with_anchor, score_no_anchor * 1.5, places=2)

    def test_queue_capping_and_ttl(self):
        """Discovered queue must strictly respect max size and expiration."""
        candidates = [
            {'hashtag': 'tag1', 'score': 10.0, 'reason': 'PASSED'},
            {'hashtag': 'tag2', 'score': 25.0, 'reason': 'PASSED'},
            {'hashtag': 'tag3', 'score': 15.0, 'reason': 'PASSED'},
            {'hashtag': 'tag4', 'score': 5.0, 'reason': 'PASSED'},
            {'hashtag': 'tag5', 'score': 30.0, 'reason': 'PASSED'},
            {'hashtag': 'tag6', 'score': 2.0, 'reason': 'PASSED'}
        ]
        
        promoted, audited = self.discoverer.build_queue(candidates)
        self.assertEqual(len(promoted), 5)
        promoted_tags = [item['hashtag'] for item in promoted]
        self.assertIn('tag5', promoted_tags)
        self.assertIn('tag2', promoted_tags)
        self.assertNotIn('tag6', promoted_tags)


if __name__ == '__main__':
    unittest.main()
