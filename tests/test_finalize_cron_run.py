"""
tests/test_finalize_cron_run.py
-------------------------------
Unit tests for finalize_cron_run schema validation.
Verifies that:
1. finalize_cron_run payload uses 'cutoff_reason' (not invalid 'notes').
2. 'github_run_id' is correctly converted to integer when valid digits.
"""

import unittest
from unittest.mock import patch, MagicMock
from scripts.finalize_cron_run import finalize_run

class TestFinalizeCronRun(unittest.TestCase):

    @patch("supabase.create_client")
    @patch.dict("os.environ", {
        "SUPABASE_URL": "https://dummy.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "dummy_key",
        "GITHUB_RUN_ID": "39104947512",
        "WORKFLOW_STATUS": "success"
    })
    def test_finalize_uses_valid_schema_fields(self, mock_create_client):
        mock_sb = MagicMock()
        mock_create_client.return_value = mock_sb
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table
        
        # Mock no existing row
        mock_table.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        
        finalize_run()
        
        # Verify insert call payload
        insert_calls = mock_table.insert.call_args_list
        self.assertTrue(len(insert_calls) > 0)
        payload = insert_calls[0][0][0]
        
        # 'notes' must NOT be in payload
        self.assertNotIn("notes", payload)
        # 'cutoff_reason' must be in payload
        self.assertIn("cutoff_reason", payload)
        # 'github_run_id' must be integer
        self.assertEqual(payload["github_run_id"], 39104947512)

if __name__ == "__main__":
    unittest.main()
