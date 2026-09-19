import unittest
from datetime import datetime, timezone, timedelta
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from caption_topic_clusterer import CaptionTopicClusterer


class TestCaptionTopicClusterer(unittest.TestCase):
    def setUp(self):
        self.clusterer = CaptionTopicClusterer(
            similarity_threshold=0.60,
            min_creators_floor=2,
            min_views_single_creator=50000
        )

    def test_ngram_extraction(self):
        """Extract clean 2-grams and 3-grams from caption text."""
        caption = "POV: Wait till the end for the transformation glowup! #fashion #style"
        ngrams = self.clusterer.extract_ngrams(caption)
        
        # Must extract phrases like 'transformation glowup'
        self.assertIn("transformation glowup", ngrams)

    def test_stopword_filtering_prevents_garbage_ngrams(self):
        """Ensure pure function word stopwords like 'of the', 'in the' are stripped."""
        caption = "This is a video of the team in the house for the show."
        ngrams = self.clusterer.extract_ngrams(caption)
        
        # 'of the', 'in the', 'for the' MUST NOT be extracted
        self.assertNotIn("of the", ngrams)
        self.assertNotIn("in the", ngrams)
        self.assertNotIn("for the", ngrams)

    def test_boilerplate_and_named_entity_filtering(self):
        """Ensure generic credit boilerplate and personal creator names are filtered."""
        caption = "The story: written and directed by Anishma Anilkumar. All rights reserved."
        ngrams = self.clusterer.extract_ngrams(caption)
        
        creators = {"anishma", "anilkumar"}
        
        for ng in ngrams:
            self.assertTrue(
                self.clusterer.is_synopsis_or_spam(ng, creators),
                f"N-gram '{ng}' should be flagged as boilerplate/named entity."
            )

    def test_synopsis_and_hashtag_spam_filtering(self):
        """Ensure movie/show synopses ('revolves around') and hashtag-spam ('#viral #fyp') are filtered."""
        caption = "The film revolves around a young hero who was born in Kerala. #viral #fyp #explore"
        ngrams = self.clusterer.extract_ngrams(caption)

        # 1. 'fyp', 'viral', 'explore' tokens must be stripped
        for ng in ngrams:
            self.assertNotIn("fyp", ng)
            self.assertNotIn("viral", ng)
            self.assertNotIn("explore", ng)

        # 2. Synopsis phrases ('revolves around', 'was born') must be flagged by is_synopsis_or_spam
        self.assertTrue(self.clusterer.is_synopsis_or_spam("revolves around", set()))
        self.assertTrue(self.clusterer.is_synopsis_or_spam("was born", set()))

    def test_celebrity_and_proper_name_suppression(self):
        """Ensure third-party celebrity / Title Case proper names ('Mamitha Baiju') are suppressed."""
        caption = "New movie trailer starring Mamitha Baiju in lead role."
        ngrams = self.clusterer.extract_ngrams(caption)
        
        # 'mamitha baiju' in Title Case caption MUST be flagged as proper name/celebrity entity
        self.assertTrue(self.clusterer.is_proper_name_or_celebrity(caption, "mamitha baiju"))

    def test_cta_marketing_spam_filtering(self):
        """Ensure CTA and marketing engagement spam ('dm us', 'link in bio') are filtered."""
        self.assertTrue(self.clusterer.is_synopsis_or_spam("dm us", set()))
        self.assertTrue(self.clusterer.is_synopsis_or_spam("link in bio", set()))
        self.assertTrue(self.clusterer.is_synopsis_or_spam("comment below", set()))

    def test_cta_token_combinations_and_digit_leak_filtering(self):
        """Ensure token combinations ('or dm link to', 'thank you for help') and digit leaks ('1999') are filtered."""
        self.assertTrue(self.clusterer.is_synopsis_or_spam("or dm link to", set()))
        self.assertTrue(self.clusterer.is_synopsis_or_spam("thank you 1999", set()))
        self.assertTrue(self.clusterer.is_synopsis_or_spam("thank you for help", set()))

    def test_foreign_language_token_filtering(self):
        """Ensure foreign non-target language tokens ('escala 6x1', 'deputado federal') are filtered."""
        self.assertTrue(self.clusterer.is_synopsis_or_spam("escala 6x1", set()))
        self.assertTrue(self.clusterer.is_synopsis_or_spam("deputado federal", set()))

    def test_cluster_key_generation_prevents_collision(self):
        """Ensure cluster key uses top 2 discriminating n-grams to avoid single-word collisions."""
        ngrams1 = ["pov wait", "wait till", "transformation glowup"]
        ngrams2 = ["pov wait", "outfit reveal", "fashion style"]

        key1 = self.clusterer.generate_cluster_key(ngrams1)
        key2 = self.clusterer.generate_cluster_key(ngrams2)

        self.assertNotEqual(key1, key2, "Distinct format trends sharing 'pov wait' must NOT collide on cluster key.")
        self.assertTrue(key1.startswith("format_"))
        self.assertTrue(key2.startswith("format_"))

    def test_creator_diversity_gating(self):
        """Reels from >=2 creators pass quality gate; single low-view reel gets rejected."""
        now = datetime.now(timezone.utc)
        
        reels_single_low_view = [
            {'id': '101', 'owner_username': 'user1', 'play_count': 1000, 'created_at': now.isoformat(), 'caption': 'POV: Wait till the end!'}
        ]
        
        reels_multi_creator = [
            {'id': '102', 'owner_username': 'user1', 'play_count': 1000, 'created_at': now.isoformat(), 'caption': 'POV: Wait till the end!'},
            {'id': '103', 'owner_username': 'user2', 'play_count': 1500, 'created_at': now.isoformat(), 'caption': 'POV: Wait till the end!'}
        ]

        is_valid_1, reason_1, _ = self.clusterer.evaluate_format_gate(reels_single_low_view)
        self.assertFalse(is_valid_1)
        self.assertIn("INSUFFICIENT_CREATOR_DIVERSITY", reason_1)

        is_valid_2, reason_2, _ = self.clusterer.evaluate_format_gate(reels_multi_creator)
        self.assertTrue(is_valid_2)
        self.assertEqual(reason_2, "CREATOR_DIVERSITY_PASSED")

    def test_single_creator_high_velocity_override(self):
        """Single creator reel with >= 50,000 views passes override."""
        now = datetime.now(timezone.utc)
        reels_high_view = [
            {'id': '104', 'owner_username': 'viral_creator', 'play_count': 55000, 'created_at': now.isoformat(), 'caption': 'POV: Transformation glowup!'}
        ]

        is_valid, reason, _ = self.clusterer.evaluate_format_gate(reels_high_view)
        self.assertTrue(is_valid)
        self.assertEqual(reason, "SINGLE_CREATOR_HIGH_VELOCITY_OVERRIDE")

    def test_lifecycle_status_assignment(self):
        """Status emerging for 2 creators, rising for >= 5 creators."""
        self.assertEqual(self.clusterer.determine_lifecycle_status(creator_count=2, velocity=0.5, peak_velocity=0.5), "emerging")
        self.assertEqual(self.clusterer.determine_lifecycle_status(creator_count=5, velocity=2.0, peak_velocity=2.0), "rising")
        self.assertEqual(self.clusterer.determine_lifecycle_status(creator_count=5, velocity=0.2, peak_velocity=1.0), "peaked")


if __name__ == '__main__':
    unittest.main()
