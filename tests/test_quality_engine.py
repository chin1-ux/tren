import sys
import unittest
sys.path.append(".")
from backend.quality_engine import evaluate_quality, is_sacred_recitation_audio, get_grounded_why_this_works

class TestQualityEngine(unittest.TestCase):
    def test_sacred_recitation_quarantined(self):
        # Quran recitation should be Tier C
        trend = {
            "id": 101,
            "audio_title": "Surah Al-Mulk Beautiful Quran Recitation",
            "audio_artist": "Qari Abdul Basit",
            "language_final": "ar",
            "why_this_works": "Great for web design promo and business reel"
        }
        eval_res = evaluate_quality(trend, distinct_creators=5, is_saved_by_user=False, mode="india")
        self.assertEqual(eval_res["tier"], "C")
        self.assertIn("sacred_recitation_not_creator_audio", eval_res["reasons"])
        self.assertIsNone(eval_res["signals"]["why_this_works_grounded"])

    def test_single_creator_quarantined(self):
        trend = {
            "id": 102,
            "audio_title": "My Viral Beat Drop",
            "audio_artist": "CoolProducer",
            "language_final": "en"
        }
        eval_res = evaluate_quality(trend, distinct_creators=1, is_saved_by_user=False, mode="india")
        self.assertEqual(eval_res["tier"], "C")
        self.assertIn("single_creator_quarantine", eval_res["reasons"])

    def test_bhojpuri_threshold(self):
        trend = {
            "id": 103,
            "audio_title": "Lollypop Lagelu Remix",
            "audio_artist": "Pawan Singh",
            "language_final": "bhojpuri"
        }
        # 5 creators: must be quarantined
        res_low = evaluate_quality(trend, distinct_creators=5, is_saved_by_user=False, mode="india")
        self.assertEqual(res_low["tier"], "C")
        self.assertTrue(any("bhojpuri_low_creators" in r for r in res_low["reasons"]))

        # 22 creators: allowed in Tier A/B
        res_high = evaluate_quality(trend, distinct_creators=22, is_saved_by_user=False, mode="india")
        self.assertIn(res_high["tier"], ["A", "B"])

    def test_foreign_language_in_india_mode(self):
        trend = {
            "id": 104,
            "audio_title": "Passinho Do Jamal",
            "audio_artist": "MC Jamal",
            "language_final": "pt"
        }
        # 2 creators in India mode: quarantine
        res_low = evaluate_quality(trend, distinct_creators=2, is_saved_by_user=False, mode="india")
        self.assertEqual(res_low["tier"], "C")

        # 3 creators in India mode: allowed
        res_high = evaluate_quality(trend, distinct_creators=3, is_saved_by_user=False, mode="india")
        self.assertIn(res_high["tier"], ["A", "B"])

    def test_never_hide_hard_rule_saved_by_user(self):
        # Even if single-creator or foreign, user save is NEVER Tier C
        trend = {
            "id": 105,
            "audio_title": "Personal Sound Bite",
            "audio_artist": "User123",
            "language_final": "pt"
        }
        eval_res = evaluate_quality(trend, distinct_creators=1, is_saved_by_user=True, mode="india")
        self.assertNotEqual(eval_res["tier"], "C")
        self.assertIn("never_hide_saved_by_user", eval_res["reasons"])

    def test_never_hide_hard_rule_market_fit_multi_creator(self):
        # 3 distinct creators in Hindi must NEVER be in Tier C
        trend = {
            "id": 106,
            "audio_title": "Chikni Chameli",
            "audio_artist": "Shreya Ghoshal",
            "language_final": "hi"
        }
        eval_res = evaluate_quality(trend, distinct_creators=3, is_saved_by_user=False, mode="india")
        self.assertNotEqual(eval_res["tier"], "C")
        self.assertIn(eval_res["tier"], ["A", "B"])

    def test_why_this_works_grounding(self):
        # If no sample captions exist, returns None (no hallucinated pitch)
        grounded = get_grounded_why_this_works("Used for fashion and fitness reels", sample_captions=[], is_sacred=False)
        self.assertIsNone(grounded)

        # If sample captions exist, retains grounded note
        grounded_valid = get_grounded_why_this_works("Used for GRWM outfits", sample_captions=["GRWM for college #outfit"], is_sacred=False)
        self.assertEqual(grounded_valid, "Used for GRWM outfits")

if __name__ == "__main__":
    unittest.main()
