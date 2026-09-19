import unittest
from datetime import datetime, timezone, timedelta


class TestTrendsSortOrder(unittest.TestCase):
    def test_newest_sort_preserves_strict_recency(self):
        """Ensure sorting by first_detected_at DESC puts the newest trend on top regardless of score."""
        now = datetime.now(timezone.utc)
        
        t_fresh = {
            'id': 1,
            'audio_title': 'Aas Paas Khuda',
            'first_detected_at': now.isoformat(),
            'composite_score': 10.0
        }
        t_older = {
            'id': 2,
            'audio_title': 'Old Viral Track',
            'first_detected_at': (now - timedelta(days=2)).isoformat(),
            'composite_score': 99.0
        }

        trends = [t_older, t_fresh]
        
        # Sort by newest (first_detected_at DESC)
        trends.sort(key=lambda t: t.get("first_detected_at") or "", reverse=True)
        
        self.assertEqual(trends[0]['id'], 1)
        self.assertEqual(trends[0]['audio_title'], 'Aas Paas Khuda')

    def test_opportunity_sort_vs_newest_sort_behavior(self):
        """Verify the difference between explicit opportunity sorting vs recency sorting."""
        now = datetime.now(timezone.utc)
        
        t_high_opp_older = {
            'id': 10,
            'audio_title': 'High Opportunity',
            'first_detected_at': (now - timedelta(days=1)).isoformat(),
            'opportunity_score': 95.0,
        }
        t_fresh_lower_opp = {
            'id': 11,
            'audio_title': 'Fresh Audio',
            'first_detected_at': now.isoformat(),
            'opportunity_score': 20.0,
        }

        trends = [t_high_opp_older, t_fresh_lower_opp]
        
        # 1. When sort='newest': Fresh Audio must be #1
        newest_list = list(trends)
        newest_list.sort(key=lambda t: t.get("first_detected_at") or "", reverse=True)
        self.assertEqual(newest_list[0]['id'], 11)

        # 2. When sort='opportunity': High Opportunity must be #1
        opp_list = list(trends)
        opp_list.sort(key=lambda t: t.get("opportunity_score") or 0.0, reverse=True)
        self.assertEqual(opp_list[0]['id'], 10)


if __name__ == '__main__':
    unittest.main()
