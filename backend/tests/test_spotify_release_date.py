import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from spotify_fetcher import SpotifyFetcher

class TestSpotifyReleaseDate(unittest.TestCase):
    @patch('spotify_fetcher.requests.get')
    def test_fetch_search_tracks_extracts_release_date(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tracks": {
                "items": [
                    {
                        "id": "test_spotify_123",
                        "name": "Boogie Wonderland",
                        "popularity": 80,
                        "artists": [{"name": "Earth, Wind & Fire"}],
                        "album": {
                            "release_date": "1979-05-01",
                            "release_date_precision": "day"
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        fetcher = SpotifyFetcher()
        fetcher.access_token = "mock_token"
        tracks = fetcher.fetch_search_tracks("boogie wonderland")

        self.assertEqual(len(tracks), 1)
        track = tracks[0]
        self.assertEqual(track["release_date"], "1979-05-01")
        self.assertEqual(track["release_year"], 1979)

    def test_check_crossovers_vintage_tagging(self):
        fetcher = SpotifyFetcher()
        fetcher.supabase = MagicMock()
        mock_select = MagicMock()
        mock_select.select.return_value.eq.return_value.execute.return_value.data = []
        fetcher.supabase.table.return_value = mock_select

        market_tracks = [
            {
                "market": "SEARCH",
                "rank": 1,
                "title": "Boogie Wonderland",
                "artist": "Earth, Wind & Fire",
                "spotify_id": "test_spotify_123",
                "release_date": "1979-05-01",
                "release_year": 1979
            }
        ]

        crossovers = fetcher.check_crossovers(market_tracks)
        self.assertEqual(len(crossovers), 1)
        crossover = crossovers[0]
        self.assertEqual(crossover["release_date"], "1979-05-01")
        self.assertEqual(crossover["release_year"], 1979)
        self.assertTrue(crossover["niche_relevance"].get("vintage_catalog"))
        self.assertEqual(crossover["status"], "candidate")

    def test_check_crossovers_recent_release_not_vintage(self):
        """Test year-boundary case: track released 30 days ago (across calendar year boundary) is NOT tagged vintage."""
        fetcher = SpotifyFetcher()
        fetcher.supabase = MagicMock()
        mock_select = MagicMock()
        mock_select.select.return_value.eq.return_value.execute.return_value.data = []
        fetcher.supabase.table.return_value = mock_select

        recent_dt = datetime.now(timezone.utc) - timedelta(days=30)
        recent_release_str = recent_dt.strftime("%Y-%m-%d")
        recent_year = recent_dt.year

        market_tracks = [
            {
                "market": "SEARCH",
                "rank": 1,
                "title": "Fresh Hit Single",
                "artist": "New Artist",
                "spotify_id": "test_spotify_fresh_456",
                "release_date": recent_release_str,
                "release_year": recent_year
            }
        ]

        crossovers = fetcher.check_crossovers(market_tracks)
        self.assertEqual(len(crossovers), 1)
        crossover = crossovers[0]
        self.assertFalse(crossover["niche_relevance"].get("vintage_catalog", False))

if __name__ == "__main__":
    unittest.main()
