import unittest
from unittest.mock import MagicMock
from backend.supabase_metrics_client import MonitoredSupabaseClient, SupabaseMetricsTracker

class TestN1Caching(unittest.TestCase):
    def setUp(self):
        self.raw_client = MagicMock()
        self.raw_builder = MagicMock()
        self.raw_client.table.return_value = self.raw_builder
        self.raw_builder.select.return_value = self.raw_builder
        self.raw_builder.eq.return_value = self.raw_builder
        self.raw_builder.limit.return_value = self.raw_builder
        self.raw_builder.order.return_value = self.raw_builder
        self.raw_builder.insert.return_value = self.raw_builder
        self.raw_builder.update.return_value = self.raw_builder
        self.raw_builder.execute.return_value = MagicMock(data=[{"id": 1, "audio_id": "aud_100", "title": "Test Track"}])

        self.tracker = SupabaseMetricsTracker()
        self.client = MonitoredSupabaseClient(self.raw_client, tracker=self.tracker)

    def test_reels_n1_elimination(self):
        # 1st call for audio_id "aud_100" -> Real DB request
        res1 = self.client.table("reels").select("audio_title, owner_username").eq("audio_id", "aud_100").execute()
        self.assertEqual(self.tracker.requests_by_table["reels"], 1)
        self.assertEqual(self.tracker.cache_hits_by_table["reels"], 0)

        # 2nd call for SAME audio_id "aud_100" -> Hit in-memory cache (0 DB requests)
        res2 = self.client.table("reels").select("audio_title, owner_username").eq("audio_id", "aud_100").execute()
        self.assertEqual(self.tracker.requests_by_table["reels"], 1)
        self.assertEqual(self.tracker.cache_hits_by_table["reels"], 1)
        self.assertEqual(res1.data, res2.data)

    def test_audio_trend_scores_n1_elimination(self):
        # 1st call for audio_id "aud_200"
        self.client.table("audio_trend_scores").select("id").eq("audio_id", "aud_200").execute()
        self.assertEqual(self.tracker.requests_by_table["audio_trend_scores"], 1)
        self.assertEqual(self.tracker.cache_hits_by_table["audio_trend_scores"], 0)

        # 2nd call for audio_id "aud_200" -> Cache hit
        self.client.table("audio_trend_scores").select("id").eq("audio_id", "aud_200").execute()
        self.assertEqual(self.tracker.requests_by_table["audio_trend_scores"], 1)
        self.assertEqual(self.tracker.cache_hits_by_table["audio_trend_scores"], 1)

    def test_users_n1_elimination(self):
        # 1st call for user_id "usr_abc"
        self.client.table("users").select("tier").eq("id", "usr_abc").execute()
        self.assertEqual(self.tracker.requests_by_table["users"], 1)
        self.assertEqual(self.tracker.cache_hits_by_table["users"], 0)

        # 2nd call for user_id "usr_abc" -> Cache hit
        self.client.table("users").select("tier").eq("id", "usr_abc").execute()
        self.assertEqual(self.tracker.requests_by_table["users"], 1)
        self.assertEqual(self.tracker.cache_hits_by_table["users"], 1)

    def test_persist_telemetry(self):
        # Execute 1 request on reels and 1 on trends
        self.client.table("reels").select("*").eq("audio_id", "aud_x").execute()
        self.client.table("trends").select("id").limit(1).execute()

        # Call persist
        self.tracker.persist(workflow="scraper_test", github_run_id=12345678, sb_client=self.raw_client)

        # Verify egress_log insert was called
        self.raw_client.table.assert_any_call("egress_log")
        self.raw_client.table.assert_any_call("cron_runs")

if __name__ == "__main__":
    unittest.main()
