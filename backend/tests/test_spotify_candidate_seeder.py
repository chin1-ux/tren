import pytest
from audio_utils import _normalize_audio_title_and_artist, _extract_remix_indicators
from spotify_seeder import (
    extract_artist_fallback,
    _are_artists_matching,
    is_passive_match,
    MIN_TITLE_LEN_FOR_ARTIST_BYPASS,
    MIN_ARTIST_LEN_FOR_SUBSTRING
)

def test_normalize_title_length_guard():
    """Verify single/double character normalized titles are stripped to empty string."""
    # Arabic script stripped of non-ASCII leaving digit '1'
    norm_t, norm_a = _normalize_audio_title_and_artist("ما تيسر من سورة الاعراف 1", "Abdel Rahman")
    assert norm_t == ""
    assert norm_a == "abdel rahman"

    # Valid title (len >= 3) passes clean
    norm_t2, norm_a2 = _normalize_audio_title_and_artist("Baby", "Justin Bieber")
    assert norm_t2 == "baby"
    assert norm_a2 == "justin bieber"


def test_missing_artist_short_title_rejected_regression():
    """
    EXPLICIT REGRESSION TEST: Generic short title ('Baby', len=4) with missing artist on both sides
    MUST be rejected to prevent false-positive auto-binding across unrelated tracks.
    """
    s_title = "Baby"
    s_artist = ""
    s_trend_name = "Baby"

    r_title = "Baby"
    r_artist = ""

    # Must return False because len("baby") = 4 < MIN_TITLE_LEN_FOR_ARTIST_BYPASS (15)
    matched = is_passive_match(s_title, s_artist, s_trend_name, r_title, r_artist)
    assert matched is False


def test_missing_artist_long_distinctive_title_permitted():
    """Distinctive long title (>= 15 chars) with missing artist is permitted to match."""
    s_title = "Boogie Wonderland (with The Emotions) - 12\" Version"
    s_artist = ""
    s_trend_name = "Boogie Wonderland (with The Emotions) - 12\" Version"

    r_title = "Boogie Wonderland (with The Emotions) - 12\" Version"
    r_artist = ""

    matched = is_passive_match(s_title, s_artist, s_trend_name, r_title, r_artist)
    assert matched is True


def test_short_artist_requires_exact_equality():
    """Short artist names (< 5 chars like 'SZA') require exact equality; substring match rejected."""
    # Substring overlap 'sza' in 'szaman' should be rejected because len('sza') = 3 < 5
    res = _are_artists_matching("sza", "szaman", norm_title_len=20)
    assert res is False

    # Exact match for 'sza' succeeds
    res_exact = _are_artists_matching("sza", "sza", norm_title_len=20)
    assert res_exact is True


def test_long_artist_substring_containment_permitted():
    """Long artist names (>= 5 chars) permit substring containment for collab/feature strings."""
    res = _are_artists_matching("arijit singh", "arijit singh, sachin-jigar", norm_title_len=10)
    assert res is True


def test_extract_artist_fallback_legacy_rows():
    """Verify legacy candidate rows with artist=None extract artist from 'Title - Artist' trend_name."""
    # Legacy row where artist is None
    art = extract_artist_fallback("Copines - Speed Up - Aya Nakamura", None)
    assert art == "Aya Nakamura"

    # Explicit artist column takes precedence
    art_explicit = extract_artist_fallback("Copines - Aya Nakamura", "Aya Nakamura")
    assert art_explicit == "Aya Nakamura"


def test_remix_mismatch_rejected():
    """Original track vs Remix track must be rejected by strict remix set equality."""
    s_title = "KALYANI - Remix"
    s_artist = "ARJN"
    s_trend_name = "KALYANI - Remix - ARJN"

    r_title = "KALYANI"
    r_artist = "ARJN"

    matched = is_passive_match(s_title, s_artist, s_trend_name, r_title, r_artist)
    assert matched is False


def test_exact_true_positive_passive_match():
    """True positive match with matching title, artist, and remix indicators succeeds."""
    s_title = "Family Affair"
    s_artist = "Mary J. Blige"
    s_trend_name = "Family Affair - Mary J. Blige"

    r_title = "Family Affair"
    r_artist = "Mary J. Blige"

    matched = is_passive_match(s_title, s_artist, s_trend_name, r_title, r_artist)
    assert matched is True


def test_vintage_catalog_track_excluded_from_seeding():
    """
    EXPLICIT REGRESSION TEST: A track flagged with vintage_catalog=True (such as 2001's Family Affair)
    MUST be excluded from auto-binding by the Seeder candidate filter.
    """
    from spotify_seeder import bind_spotify_candidates_to_scraped_audio

    class MockSupabase:
        def __init__(self):
            self.ct_table = MockTable([
                {
                    "id": "family-affair-2001",
                    "trend_name": "Family Affair - Mary J. Blige",
                    "artist": "Mary J. Blige",
                    "status": "candidate",
                    "audio_id": None,
                    "niche_relevance": {"vintage_catalog": True},
                    "release_year": 2001
                }
            ])
            self.reels_table = MockTable([
                {
                    "audio_id": "1335304429999756",
                    "audio_title": "Family Affair",
                    "audio_artist": "Mary J. Blige"
                }
            ])

        def table(self, name):
            if name == "content_trends":
                return self.ct_table
            if name == "reels":
                return self.reels_table
            return MockTable([])

    class MockTable:
        def __init__(self, data):
            self.data = data

        def select(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        def is_(self, *args, **kwargs):
            return self

        def not_(self, *args, **kwargs):
            return self

        def execute(self):
            return self

    mock_sb = MockSupabase()
    results = bind_spotify_candidates_to_scraped_audio(mock_sb)
    # Assert Family Affair (vintage_catalog=True) was explicitly excluded from binding
    assert len(results) == 0

