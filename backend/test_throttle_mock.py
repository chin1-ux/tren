import logging
import sys
from unittest.mock import MagicMock

logging.basicConfig(level=logging.WARNING, format='%(levelname)s: %(message)s')

class MockResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

class MockRequests:
    def get(self, url, **kwargs):
        html = """
        <html>
            <head><title>Instagram</title></head>
            <body>
                <h2>Error</h2>
                <p>Please wait a few minutes before you try again.</p>
            </body>
        </html>
        """
        return MockResponse(html, 200)

sys.modules['requests'] = MockRequests()

from trend_refresher import TrendRefresher
refresher = TrendRefresher()

# Disable sleep so tests run fast
import time
time.sleep = MagicMock()

# Mock the database select to return 5 trends
class MockBuilder:
    def execute(self):
        class MockData:
            data = [{"id": i, "audio_id": f"audio_{i}", "status": "rising", "audio_use_count": 0, "velocity_avg": 0} for i in range(5)]
        return MockData()
    def select(self, *args): return self
    def in_(self, *args): return self

refresher.supabase = MagicMock()
refresher.supabase.table.return_value = MockBuilder()
refresher._refresh_audio_use_count = MagicMock(return_value=False)
refresher._refresh_peaking_score = MagicMock()

print("=== RUNNING FULL PIPELINE WITH MOCKED LOGIN WALL ===")
summary = refresher.refresh_all()
print(f"\nFinal Summary Dictionary:")
print(summary)
