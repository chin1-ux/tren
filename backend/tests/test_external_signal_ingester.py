import unittest
from datetime import datetime, timezone
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from external_signal_ingester import ExternalSignalIngester


class TestExternalSignalIngester(unittest.TestCase):
    def setUp(self):
        self.ingester = ExternalSignalIngester(max_existing_reels_floor=5)

    def test_standalone_hashtag_derivation(self):
        """Ensure standalone title and artist tags are derived cleanly, discarding concatenated noise."""
        title = "Tauba Tauba"
        artist = "Karan Aujla"

        tags = self.ingester.derive_standalone_hashtags(title, artist)
        
        # Must include standalone normalized title and artist
        self.assertIn("taubatauba", tags)
        self.assertIn("karanaujla", tags)
        
        # Must NOT include concatenated title+artist noise
        self.assertNotIn("taubataubakaranaujla", tags)
        self.assertNotIn("karanaujlataubatauba", tags)

    def test_db_coverage_floor(self):
        """Tracks with >= 5 reels in DB must be filtered out as covered; tracks with < 5 qualify."""
        # 6 reels in DB -> Covered (REJECT)
        self.assertTrue(self.ingester.is_covered_in_db(existing_reel_count=6))
        self.assertTrue(self.ingester.is_covered_in_db(existing_reel_count=5))
        
        # 4 reels in DB -> Unseeded / Under-represented (QUALIFY)
        self.assertFalse(self.ingester.is_covered_in_db(existing_reel_count=4))
        self.assertFalse(self.ingester.is_covered_in_db(existing_reel_count=0))

    def test_meta_tag_rejection_in_derivation(self):
        """Generic meta-words in titles or artists are filtered out by Quality Gate."""
        tags = self.ingester.derive_standalone_hashtags("Viral Trending Dance", "Explore Artist")
        # 'viral', 'trending', 'explore' should be filtered out by meta blacklist
        for tag in tags:
            self.assertNotIn(tag, ['viral', 'trending', 'explore'])


if __name__ == '__main__':
    unittest.main()
