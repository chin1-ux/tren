import unittest
from unittest.mock import MagicMock
from backend.cadence_governor import calculate_cadence_gap, handle_supabase_402_over_quota

class TestCadenceGovernor(unittest.TestCase):
    def test_cadence_thresholds(self):
        # >= 15 MB -> 360
        self.assertEqual(calculate_cadence_gap(20.0), 360)
        self.assertEqual(calculate_cadence_gap(15.0), 360)
        
        # 8 - 15 MB -> 240
        self.assertEqual(calculate_cadence_gap(14.9), 240)
        self.assertEqual(calculate_cadence_gap(8.0), 240)
        
        # < 8 MB -> 165
        self.assertEqual(calculate_cadence_gap(7.9), 165)
        self.assertEqual(calculate_cadence_gap(1.2), 165)

    def test_mocked_402_clean_stop(self):
        mock_client = MagicMock()
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": 1}])
        
        err_402 = Exception("HTTP 402: Payment Required. Project exceeded egress quota.")
        handled = handle_supabase_402_over_quota(err_402, sb_client=mock_client)
        
        self.assertTrue(handled)
        mock_client.table.assert_called_with("cron_runs")
        # Verify insert payload contained quota_exceeded
        args, kwargs = mock_table.insert.call_args
        payload = args[0]
        self.assertEqual(payload["conclusion"], "quota_exceeded")
        self.assertIn("402 Payment Required", payload["cutoff_reason"])

    def test_normal_error_not_handled_as_402(self):
        err_normal = Exception("Connection reset by peer")
        handled = handle_supabase_402_over_quota(err_normal, sb_client=None)
        self.assertFalse(handled)

if __name__ == "__main__":
    unittest.main()
