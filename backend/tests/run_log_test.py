import os
import sys
import logging
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Configure logging to stdout
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

import nightly_llm_batch

print("=== RAW LOG OUTPUT TEST RUN ===")

# Test 1: List-wrapped response coercion warning
with patch("nightly_llm_batch.create_client") as mock_create_client, \
     patch("nightly_llm_batch.call_llm") as mock_call_llm:
    
    mock_sb = MagicMock()
    mock_create_client.return_value = mock_sb
    mock_sb.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"id": 4109, "audio_title": "Karuppa Kooda Va", "audio_artist": "Test Artist"}
    ]
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
    
    print("\n--- Triggering List-Wrapped Coercion Warning ---")
    nightly_llm_batch.run_nightly_batch(limit=1)

# Test 2: Invalid non-dict response warning
with patch("nightly_llm_batch.create_client") as mock_create_client, \
     patch("nightly_llm_batch.call_llm") as mock_call_llm:
    
    mock_sb = MagicMock()
    mock_create_client.return_value = mock_sb
    mock_sb.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.limit.return_value.execute.return_value.data = [
        {"id": 4110, "audio_title": "Invalid Audio Track", "audio_artist": "Test Artist"}
    ]
    mock_call_llm.return_value = "invalid raw text response"
    
    print("\n--- Triggering Invalid Non-Dict Response Warning ---")
    nightly_llm_batch.run_nightly_batch(limit=1)

print("\n=== RAW LOG OUTPUT TEST COMPLETE ===")
