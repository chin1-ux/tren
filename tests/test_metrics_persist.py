"""
tests/test_metrics_persist.py
-----------------------------
Unit tests for SupabaseMetricsTracker persist() functionality.
Verifies that:
1. Per-table rows are written to egress_log.
2. Aggregate row is updated in cron_runs for the given github_run_id.
"""

import unittest
from unittest.mock import MagicMock
from backend.supabase_metrics_client import SupabaseMetricsTracker

class TestMetricsPersist(unittest.TestCase):

    def test_persist_writes_to_egress_log_and_cron_runs(self):
        tracker = SupabaseMetricsTracker()
        tracker.record_request("trends", 1500, 25.0)
        tracker.record_request("reels", 3200, 40.0)

        mock_sb = MagicMock()
        mock_egress_table = MagicMock()
        mock_cron_table = MagicMock()

        def table_side_effect(name):
            if name == "egress_log":
                return mock_egress_table
            elif name == "cron_runs":
                return mock_cron_table
            return MagicMock()

        mock_sb.table.side_effect = table_side_effect

        # Call persist
        tracker.persist(workflow="scraper", github_run_id=39104947512, sb_client=mock_sb)

        # 1. Verify egress_log insert
        mock_egress_table.insert.assert_called_once()
        inserted_rows = mock_egress_table.insert.call_args[0][0]
        self.assertEqual(len(inserted_rows), 2)
        tables = [r["table_name"] for r in inserted_rows]
        self.assertIn("trends", tables)
        self.assertIn("reels", tables)
        for r in inserted_rows:
            self.assertEqual(r["github_run_id"], 39104947512)
            self.assertEqual(r["workflow"], "scraper")

        # 2. Verify cron_runs update
        mock_cron_table.update.assert_called_once()
        update_payload = mock_cron_table.update.call_args[0][0]
        self.assertEqual(update_payload["egress_requests"], 2)
        self.assertEqual(update_payload["egress_bytes"], 4700)
        mock_cron_table.update.return_value.eq.assert_called_once_with("github_run_id", 39104947512)

if __name__ == "__main__":
    unittest.main()
