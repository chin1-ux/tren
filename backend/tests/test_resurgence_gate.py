import unittest
from unittest.mock import MagicMock
from trend_detector import _save_trend

class TestResurgenceGate(unittest.TestCase):
    def test_expired_trend_single_reel_noise_denied(self):
        """Single reel noise on an expired trend MUST be denied resurgence promotion."""
        mock_sb = MagicMock()
        
        trends_table_mock = MagicMock()
        mock_existing = MagicMock()
        mock_existing.data = [{"id": 101, "status": "expired", "peak_velocity": 50000}]
        trends_table_mock.select.return_value.eq.return_value.execute.return_value = mock_existing

        snaps_table_mock = MagicMock()
        mock_snaps = MagicMock()
        mock_snaps.data = [{"velocity_avg": 5000.0, "creator_count": 1, "captured_at": "2026-09-13T10:00:00Z"}]
        snaps_table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_snaps

        def mock_table(name):
            if name == "trends":
                return trends_table_mock
            elif name == "trend_snapshots":
                return snaps_table_mock
            return MagicMock()

        mock_sb.table.side_effect = mock_table

        single_reel_trend = {
            "audio_id": "abrar_theme_123",
            "audio_title": "Abrar's Theme",
            "audio_artist": "Harshavardhan Rameshwar",
            "audio_use_count": 3000000,
            "avg_velocity": 110241.8,
            "max_velocity": 110241.8,
            "reel_count": 1,
            "unique_creators": 1,
            "saturation_score": 0.5,
            "window_hours_remaining": 48.0,
            "confidence": 0.85,
            "niche_tag": "viral",
            "trend_type": "audio",
            "language": "hi",
            "trend_origin": "scraped"
        }

        _save_trend(single_reel_trend, mock_sb)

        trends_table_mock.update.assert_called_once()
        update_call_args = trends_table_mock.update.call_args[0][0]
        
        self.assertNotIn("status", update_call_args)
        self.assertEqual(update_call_args["status_reason"]["trigger_source"], "resurgence_gate_denied")

    def test_expired_trend_single_creator_historical_snapshots_denied(self):
        """Historical snapshots with creator_count < 2 MUST deny resurgence even if current batch has 3+ creators."""
        mock_sb = MagicMock()

        trends_table_mock = MagicMock()
        mock_existing = MagicMock()
        mock_existing.data = [{"id": 103, "status": "expired", "peak_velocity": 50000}]
        trends_table_mock.select.return_value.eq.return_value.execute.return_value = mock_existing

        # 2 snapshots with high velocity BUT creator_count = 1 (single-creator noise)
        snaps_table_mock = MagicMock()
        mock_snaps = MagicMock()
        mock_snaps.data = [
            {"velocity_avg": 5000.0, "creator_count": 1, "captured_at": "2026-09-13T12:00:00Z"},
            {"velocity_avg": 4500.0, "creator_count": 1, "captured_at": "2026-09-13T10:00:00Z"}
        ]
        snaps_table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_snaps

        def mock_table(name):
            if name == "trends":
                return trends_table_mock
            elif name == "trend_snapshots":
                return snaps_table_mock
            return MagicMock()

        mock_sb.table.side_effect = mock_table

        single_creator_history_trend = {
            "audio_id": "abrar_theme_123",
            "audio_title": "Abrar's Theme",
            "audio_artist": "Harshavardhan Rameshwar",
            "audio_use_count": 3000000,
            "avg_velocity": 12500.0,
            "max_velocity": 25000.0,
            "reel_count": 5,
            "unique_creators": 3,
            "saturation_score": 0.5,
            "window_hours_remaining": 48.0,
            "confidence": 0.9,
            "niche_tag": "viral",
            "trend_type": "audio",
            "language": "hi",
            "trend_origin": "scraped"
        }

        _save_trend(single_creator_history_trend, mock_sb)

        trends_table_mock.update.assert_called_once()
        update_call_args = trends_table_mock.update.call_args[0][0]

        self.assertNotIn("status", update_call_args)
        self.assertEqual(update_call_args["status_reason"]["trigger_source"], "resurgence_gate_denied")

    def test_expired_trend_sustained_signal_promoted_to_resurging(self):
        """Sustained signal across 2+ snapshots with >= 2 creator count AND >= 3 creators currently MUST promote to 'resurging'."""
        mock_sb = MagicMock()

        trends_table_mock = MagicMock()
        mock_existing = MagicMock()
        mock_existing.data = [{"id": 102, "status": "expired", "peak_velocity": 50000}]
        trends_table_mock.select.return_value.eq.return_value.execute.return_value = mock_existing

        # 2 consecutive snapshots with elevated velocity AND >= 3 creator count
        snaps_table_mock = MagicMock()
        mock_snaps = MagicMock()
        mock_snaps.data = [
            {"velocity_avg": 5000.0, "creator_count": 3, "captured_at": "2026-09-13T12:00:00Z"},
            {"velocity_avg": 4500.0, "creator_count": 3, "captured_at": "2026-09-13T10:00:00Z"}
        ]
        snaps_table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_snaps

        def mock_table(name):
            if name == "trends":
                return trends_table_mock
            elif name == "trend_snapshots":
                return snaps_table_mock
            return MagicMock()

        mock_sb.table.side_effect = mock_table

        resurging_trend = {
            "audio_id": "abrar_theme_123",
            "audio_title": "Abrar's Theme",
            "audio_artist": "Harshavardhan Rameshwar",
            "audio_use_count": 3000000,
            "avg_velocity": 12500.0,
            "max_velocity": 25000.0,
            "reel_count": 5,
            "unique_creators": 4,
            "saturation_score": 0.5,
            "window_hours_remaining": 48.0,
            "confidence": 0.9,
            "niche_tag": "viral",
            "trend_type": "audio",
            "language": "hi",
            "trend_origin": "scraped"
        }

        _save_trend(resurging_trend, mock_sb)

        trends_table_mock.update.assert_called_once()
        update_call_args = trends_table_mock.update.call_args[0][0]

        self.assertEqual(update_call_args["status"], "resurging")
        self.assertEqual(update_call_args["status_reason"]["trigger_source"], "resurgence_gate")

    def test_resurgence_gate_fails_on_low_velocity_alone(self):
        """Passes creator count (4 >= 3) and snapshot count (2 >= 2) with high historical creators (4 >= 3), BUT fails solely on low current velocity (< 3000)."""
        mock_sb = MagicMock()

        trends_table_mock = MagicMock()
        mock_existing = MagicMock()
        mock_existing.data = [{"id": 104, "status": "expired", "peak_velocity": 50000}]
        trends_table_mock.select.return_value.eq.return_value.execute.return_value = mock_existing

        snaps_table_mock = MagicMock()
        mock_snaps = MagicMock()
        mock_snaps.data = [
            {"velocity_avg": 5000.0, "creator_count": 4, "captured_at": "2026-09-13T12:00:00Z"},
            {"velocity_avg": 4500.0, "creator_count": 4, "captured_at": "2026-09-13T10:00:00Z"}
        ]
        snaps_table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_snaps

        def mock_table(name):
            if name == "trends":
                return trends_table_mock
            elif name == "trend_snapshots":
                return snaps_table_mock
            return MagicMock()

        mock_sb.table.side_effect = mock_table

        low_velocity_trend = {
            "audio_id": "abrar_theme_123",
            "audio_title": "Abrar's Theme",
            "audio_artist": "Harshavardhan Rameshwar",
            "audio_use_count": 3000000,
            "avg_velocity": 1500.0,  # Below 3,000 threshold
            "max_velocity": 1500.0,
            "reel_count": 6,
            "unique_creators": 4,
            "saturation_score": 0.5,
            "window_hours_remaining": 48.0,
            "confidence": 0.9,
            "niche_tag": "viral",
            "trend_type": "audio",
            "language": "hi",
            "trend_origin": "scraped"
        }

        _save_trend(low_velocity_trend, mock_sb)

        trends_table_mock.update.assert_called_once()
        update_call_args = trends_table_mock.update.call_args[0][0]

        self.assertNotIn("status", update_call_args)
        self.assertEqual(update_call_args["status_reason"]["trigger_source"], "resurgence_gate_denied")
        self.assertEqual(update_call_args["status_reason"]["decision_metrics"]["velocity_avg"], 1500.0)

    def test_resurgence_gate_fails_asymmetric_historical_creators(self):
        """Passes current creators (3 >= 3) and current velocity (5000 >= 3000), but snapshot creator_count is 2 (passes old <2 rule, FAILS new symmetric <3 rule)."""
        mock_sb = MagicMock()

        trends_table_mock = MagicMock()
        mock_existing = MagicMock()
        mock_existing.data = [{"id": 105, "status": "expired", "peak_velocity": 50000}]
        trends_table_mock.select.return_value.eq.return_value.execute.return_value = mock_existing

        snaps_table_mock = MagicMock()
        mock_snaps = MagicMock()
        # Historical snapshots have creator_count = 2 (would pass under old >=2 rule, FAILS under new symmetric >=3 rule)
        mock_snaps.data = [
            {"velocity_avg": 5000.0, "creator_count": 2, "captured_at": "2026-09-13T12:00:00Z"},
            {"velocity_avg": 4500.0, "creator_count": 2, "captured_at": "2026-09-13T10:00:00Z"}
        ]
        snaps_table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_snaps

        def mock_table(name):
            if name == "trends":
                return trends_table_mock
            elif name == "trend_snapshots":
                return snaps_table_mock
            return MagicMock()

        mock_sb.table.side_effect = mock_table

        asymmetric_trend = {
            "audio_id": "abrar_theme_123",
            "audio_title": "Abrar's Theme",
            "audio_artist": "Harshavardhan Rameshwar",
            "audio_use_count": 3000000,
            "avg_velocity": 5000.0,
            "max_velocity": 5000.0,
            "reel_count": 5,
            "unique_creators": 3,
            "saturation_score": 0.5,
            "window_hours_remaining": 48.0,
            "confidence": 0.9,
            "niche_tag": "viral",
            "trend_type": "audio",
            "language": "hi",
            "trend_origin": "scraped"
        }

        _save_trend(asymmetric_trend, mock_sb)

        trends_table_mock.update.assert_called_once()
        update_call_args = trends_table_mock.update.call_args[0][0]

        self.assertNotIn("status", update_call_args)
        self.assertEqual(update_call_args["status_reason"]["trigger_source"], "resurgence_gate_denied")
        self.assertEqual(update_call_args["status_reason"]["decision_metrics"]["unique_creators"], 3)


    def test_resurgence_gate_preserves_peak_velocity_on_denial(self):
        """When resurgence is denied, peak_velocity must update via max(current, peak), preserving higher historical peak."""
        mock_sb = MagicMock()

        trends_table_mock = MagicMock()
        mock_existing = MagicMock()
        mock_existing.data = [{"id": 106, "status": "expired", "peak_velocity": 85000.0}]
        trends_table_mock.select.return_value.eq.return_value.execute.return_value = mock_existing

        snaps_table_mock = MagicMock()
        mock_snaps = MagicMock()
        mock_snaps.data = [{"velocity_avg": 1000.0, "creator_count": 1, "captured_at": "2026-09-13T10:00:00Z"}]
        snaps_table_mock.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = mock_snaps

        def mock_table(name):
            if name == "trends":
                return trends_table_mock
            elif name == "trend_snapshots":
                return snaps_table_mock
            return MagicMock()

        mock_sb.table.side_effect = mock_table

        update_trend = {
            "audio_id": "abrar_theme_123",
            "audio_title": "Abrar's Theme",
            "audio_artist": "Harshavardhan Rameshwar",
            "audio_use_count": 3000000,
            "avg_velocity": 12000.0,  # Higher than current 1000, but LOWER than peak_velocity 85000
            "max_velocity": 12000.0,
            "reel_count": 1,
            "unique_creators": 1,
            "saturation_score": 0.5,
            "window_hours_remaining": 48.0,
            "confidence": 0.85,
            "niche_tag": "viral",
            "trend_type": "audio",
            "language": "hi",
            "trend_origin": "scraped"
        }

        _save_trend(update_trend, mock_sb)

        trends_table_mock.update.assert_called_once()
        update_call_args = trends_table_mock.update.call_args[0][0]

        # peak_velocity MUST be max(12000.0, 85000.0) = 85000.0
        self.assertEqual(update_call_args["peak_velocity"], 85000.0)

if __name__ == "__main__":
    unittest.main()

