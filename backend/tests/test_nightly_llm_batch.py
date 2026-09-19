import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import nightly_llm_batch

class TestNightlyLLMBatch(unittest.TestCase):
    @patch("nightly_llm_batch.create_client")
    @patch("nightly_llm_batch.call_llm")
    def test_dict_response(self, mock_call_llm, mock_create_client):
        mock_sb = MagicMock()
        mock_create_client.return_value = mock_sb
        mock_sb.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": 101, "audio_title": "Test Audio", "audio_artist": "Test Artist"}
        ]
        mock_call_llm.return_value = {
            "optimal_post_hour_ist": 20,
            "format_transferable": True,
            "transfer_instructions": "Adapt format to niche.",
            "why_this_works": "Catchy beat",
            "ideal_content_description": "Dance video",
            "audio_cue_second": 5,
            "text_overlay_template": "Watch till end",
            "hook_brief": "Start fast"
        }
        
        summary = nightly_llm_batch.run_nightly_batch(limit=1)
        self.assertEqual(summary["succeeded"], 1)
        self.assertEqual(summary["llm_unavailable"], 0)

    @patch("nightly_llm_batch.create_client")
    @patch("nightly_llm_batch.call_llm")
    def test_list_wrapped_response_coercion(self, mock_call_llm, mock_create_client):
        mock_sb = MagicMock()
        mock_create_client.return_value = mock_sb
        mock_sb.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": 102, "audio_title": "List Audio", "audio_artist": "List Artist"}
        ]
        # LLM returns a single-element list [{...}] instead of dict
        mock_call_llm.return_value = [{
            "optimal_post_hour_ist": 19,
            "format_transferable": False,
            "transfer_instructions": "Use original audio.",
            "why_this_works": "Trending audio",
            "ideal_content_description": "Vlog reel",
            "audio_cue_second": 0,
            "text_overlay_template": "New trend alert",
            "hook_brief": "Show result first"
        }]
        
        with self.assertLogs("nightly_llm_batch", level="WARNING") as cm:
            summary = nightly_llm_batch.run_nightly_batch(limit=1)
            self.assertEqual(summary["succeeded"], 1)
            self.assertEqual(summary["llm_unavailable"], 0)
            self.assertTrue(any("coercing result[0]" in log for log in cm.output))

    @patch("nightly_llm_batch.create_client")
    @patch("nightly_llm_batch.call_llm")
    def test_invalid_non_dict_response_fallback(self, mock_call_llm, mock_create_client):
        mock_sb = MagicMock()
        mock_create_client.return_value = mock_sb
        mock_sb.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": 103, "audio_title": "Invalid Audio", "audio_artist": "Invalid Artist"}
        ]
        # LLM returns invalid string or non-dict list
        mock_call_llm.return_value = "invalid json string payload"
        
        with self.assertLogs("nightly_llm_batch", level="WARNING") as cm:
            summary = nightly_llm_batch.run_nightly_batch(limit=1)
            self.assertEqual(summary["succeeded"], 0)
            self.assertEqual(summary["llm_unavailable"], 1)
            self.assertTrue(any("non-dict LLM payload type" in log for log in cm.output))

if __name__ == "__main__":
    unittest.main()
