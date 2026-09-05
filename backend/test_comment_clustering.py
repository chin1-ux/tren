import unittest
from comment_clustering import (
    clean_comments,
    extract_phrases_regex,
    CommentClusteringEngine,
    build_batch_naming_prompt
)

class TestCommentClustering(unittest.TestCase):
    def test_clean_comments(self):
        raw = ["nice", "wow", "  King Kohli is back! ", "🔥", "lol", "Manchester United match was crazy"]
        cleaned = clean_comments(raw)
        self.assertEqual(len(cleaned), 2)
        self.assertIn("King Kohli is back!", cleaned)
        self.assertIn("Manchester United match was crazy", cleaned)

    def test_extract_phrases_regex(self):
        text = "Did you see that Kohli wicket? The referee decision was terrible."
        phrases = extract_phrases_regex(text)
        self.assertIn("referee decision", phrases)
        self.assertIn("kohli", phrases)

    def test_clustering_and_cpdi(self):
        engine = CommentClusteringEngine()
        # Mock alias table locally
        engine.alias_table = {
            "king kohli": "virat_kohli",
            "kohli": "virat_kohli",
            "vk": "virat_kohli",
            "virat kohli": "virat_kohli"
        }

        # Simulate comments across different posts/creators
        mock_comments = [
            {"text": "Kohli is goat", "post_id": "p1", "creator_id": "c1", "extracted_phrases": ["kohli"]},
            {"text": "King kohli innings", "post_id": "p2", "creator_id": "c2", "extracted_phrases": ["king kohli"]},
            {"text": "VK is the best", "post_id": "p3", "creator_id": "c3", "extracted_phrases": ["vk"]},
            {"text": "Virat Kohli did it again", "post_id": "p4", "creator_id": "c4", "extracted_phrases": ["virat kohli"]},
            {"text": "King Kohli storm", "post_id": "p5", "creator_id": "c5", "extracted_phrases": ["king kohli"]},
        ]

        clusters = engine.build_clusters(mock_comments)
        
        # All aliases should map to virat_kohli (either direct key or fuzzy matching)
        self.assertIn("virat_kohli", clusters)
        
        # Test validation filters
        # Using a custom threshold since 'virat kohli' has lower token_sort_ratio to 'kohli' (~62%)
        flagged = engine.calculate_cpdi_and_flag(clusters, min_unique_posts=5, cpdi_threshold=0.15)
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["canonical_key"], "virat_kohli")
        self.assertEqual(flagged[0]["unique_posts_count"], 5)
        self.assertEqual(flagged[0]["unique_creators_count"], 5)
        # CPDI = 5 creators / 5 comments = 1.0
        self.assertEqual(flagged[0]["cpdi"], 1.0)

    def test_batch_naming_prompt(self):
        flagged = [{
            "canonical_key": "virat_kohli",
            "unique_posts_count": 5,
            "sample_phrases": ["Kohli is goat", "King kohli innings"]
        }]
        prompt = build_batch_naming_prompt(flagged)
        self.assertIn("virat_kohli", prompt)
        self.assertIn("3-word title", prompt)

if __name__ == '__main__':
    unittest.main()
