import unittest
from backend.claim_checker import check_sound_claims, is_sacred_content, is_marathi_quote_content

class TestClaimCheckerRegressions(unittest.TestCase):
    def test_regression_7725_invented_bpm_and_808(self):
        input_ev = "fast edit cuts, anime edits, drift clips #animeedit #drift #edits"
        old_output = "The track features an aggressive 180 BPM tempo and distorted 808 basslines driving high-octane automotive and combat anime transitions."
        
        valid_old, flagged_old, sanitized = check_sound_claims(input_ev, old_output)
        self.assertFalse(valid_old, "Old output with invented BPM/808 must fail claim check")
        self.assertTrue(any("bpm" in term for term in flagged_old))
        self.assertTrue(any("808" in term for term in flagged_old or "bass" in term for term in flagged_old))
        
        # New grounded output describing only creator use-case
        new_output = "Used by creators for dynamic pacing in fast-cut anime edits and automotive drift sequences."
        valid_new, flagged_new, _ = check_sound_claims(input_ev, new_output)
        self.assertTrue(valid_new, "New creator-only output must pass claim check")
        self.assertEqual(flagged_new, [])

    def test_regression_7934_invented_beat_drops(self):
        input_ev = "Telugu romantic melody #telugusongs #transition #lovesong"
        old_output = "The energetic tempo and distinct beat drops create strong cues for transition reels."
        
        valid_old, flagged_old, _ = check_sound_claims(input_ev, old_output)
        self.assertFalse(valid_old, "Old output claiming beat drops without sound evidence must fail")
        self.assertTrue(any("tempo" in term or "beat drop" in term for term in flagged_old))

        new_output = "Creators use this romantic audio for couple moments and synchronized outfit change transitions."
        valid_new, flagged_new, _ = check_sound_claims(input_ev, new_output)
        self.assertTrue(valid_new, "New output must pass")

    def test_regression_8033_generic_tags_invented_vocals(self):
        input_ev = "#reelstrending #viralsong #explorepage #instareels"
        old_output = "Features punchy vocals and an infectious tempo that boosts audience retention."
        
        valid_old, flagged_old, _ = check_sound_claims(input_ev, old_output)
        self.assertFalse(valid_old, "Old output with punchy vocals and infectious tempo on generic tags must fail")
        self.assertTrue(any("vocal" in term or "infectious" in term or "tempo" in term for term in flagged_old))

        new_output = "Generic viral hashtag usage without distinctive format patterns; use-case is broad or unknown."
        valid_new, flagged_new, _ = check_sound_claims(input_ev, new_output)
        self.assertTrue(valid_new, "New output must pass")

    def test_sacred_quran_recitation(self):
        title = "عيني فيها تسمي سلسبيلا"
        input_ev = "عيني فيها تسمي سلسبيلا #قرآن #quran #recitation #islamic"
        self.assertTrue(is_sacred_content(input_ev, title), "Quran recitation must be recognized as sacred")

    def test_marathi_quotes_distinction(self):
        title = "आयुष्यात काही गोष्टी वेळेवरच"
        input_ev = "आयुष्यात काही गोष्टी वेळेवरच समजतात #marathiquotes #suvichar #life"
        self.assertFalse(is_sacred_content(input_ev, title), "Marathi life quotes must NOT be classified as sacred prayer audio")
        self.assertTrue(is_marathi_quote_content(input_ev, title), "Must be classified as Marathi quote content")

if __name__ == "__main__":
    unittest.main()
