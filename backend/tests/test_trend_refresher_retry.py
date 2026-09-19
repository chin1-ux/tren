import unittest
from unittest.mock import MagicMock, call
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trend_refresher import TrendRefresher


class TestTrendRefresherRetry(unittest.TestCase):
    def test_retry_supabase_call_success_first_attempt(self):
        refresher = TrendRefresher.__new__(TrendRefresher)
        mock_fn = MagicMock(return_value="SUCCESS")
        
        result = refresher._retry_supabase_call(mock_fn, max_retries=3, delay=0.01)
        self.assertEqual(result, "SUCCESS")
        self.assertEqual(mock_fn.call_count, 1)

    def test_retry_supabase_call_remote_protocol_error_retry_and_succeed(self):
        refresher = TrendRefresher.__new__(TrendRefresher)
        
        # Fails twice with RemoteProtocolError (Server disconnected), succeeds on 3rd attempt
        error_msg = "httpcore.RemoteProtocolError: Server disconnected"
        mock_fn = MagicMock(side_effect=[
            Exception(error_msg),
            Exception("Connection reset by peer"),
            "RECOVERED_DATA"
        ])

        result = refresher._retry_supabase_call(mock_fn, max_retries=3, delay=0.01)
        self.assertEqual(result, "RECOVERED_DATA")
        self.assertEqual(mock_fn.call_count, 3)

    def test_retry_supabase_call_exhaust_retries_raises(self):
        refresher = TrendRefresher.__new__(TrendRefresher)
        error_msg = "httpcore.RemoteProtocolError: Server disconnected"
        mock_fn = MagicMock(side_effect=Exception(error_msg))

        with self.assertRaises(Exception) as ctx:
            refresher._retry_supabase_call(mock_fn, max_retries=3, delay=0.01)
        
        self.assertIn("Server disconnected", str(ctx.exception))
        self.assertEqual(mock_fn.call_count, 3)


if __name__ == '__main__':
    unittest.main()
