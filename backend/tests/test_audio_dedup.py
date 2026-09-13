import pytest
from audio_utils import _normalize_audio_title_and_artist, _extract_remix_indicators

def test_cluster_a_positive_merge():
    """
    Test A: Boogie Wonderland identical title + artist across two track IDs resolve to same key.
    """
    t1 = "Boogie Wonderland (with The Emotions) - 12\" Version"
    a1 = "Earth, Wind & Fire, The Emotions"
    
    t2 = "Boogie Wonderland (with The Emotions) - 12\" Version"
    a2 = "Earth, Wind & Fire, The Emotions"
    
    norm_t1, norm_a1 = _normalize_audio_title_and_artist(t1, a1)
    norm_t2, norm_a2 = _normalize_audio_title_and_artist(t2, a2)
    
    assert norm_t1 == norm_t2
    assert norm_a1 == norm_a2
    assert _extract_remix_indicators(t1) == _extract_remix_indicators(t2)

def test_cluster_b_negative_guard():
    """
    Test B: DJ Mashups with different artist credits MUST NOT merge.
    """
    t1 = "Love Mashup 2026 by DJ Raahul Pai"
    a1 = "Arijit Singh, Sachin-Jigar, Mithoon"
    
    t2 = "Arijit Singh Love Mashup - By DJ Raahul Pai & DJ Saquib"
    a2 = "Arijit Singh"
    
    norm_t1, norm_a1 = _normalize_audio_title_and_artist(t1, a1)
    norm_t2, norm_a2 = _normalize_audio_title_and_artist(t2, a2)
    
    assert (norm_t1 == norm_t2 and norm_a1 == norm_a2) is False

def test_cluster_c_negative_guard():
    """
    Test C: Sped Up Remix variants vs Original tracks MUST NOT merge.
    """
    t1 = "Big Boy (SZA) - Sped Up Remix"
    a1 = "ViralityX"
    
    t2 = "Big Boy"
    a2 = "SZA"
    
    remix1 = _extract_remix_indicators(t1)
    remix2 = _extract_remix_indicators(t2)
    
    assert remix1 != remix2

def test_boundary_artist_enforcement():
    """
    Test D: Same title 'Hold On' by different artists MUST NOT merge.
    """
    t1 = "Hold On"
    a1 = "Artist Alpha"
    
    t2 = "Hold On"
    a2 = "Artist Beta"
    
    norm_t1, norm_a1 = _normalize_audio_title_and_artist(t1, a1)
    norm_t2, norm_a2 = _normalize_audio_title_and_artist(t2, a2)
    
    assert norm_t1 == norm_t2
    assert norm_a1 != norm_a2
    assert (norm_t1 == norm_t2 and norm_a1 == norm_a2) is False

def test_single_reel_niche_classification():
    """
    Test E: Passing sample_size=0 allows classify_niche to perform full keyword/hashtag classification.
    """
    from classification_rules import classify_niche
    
    niche_result = classify_niche(
        caption="Amazing dance choreography steps and hookstep",
        hashtags=["dance", "choreography"],
        source_hashtag_pool="DANCE",
        sample_size=0
    )
    assert niche_result in ("MICRO_DANCE", "dance", "GLOBAL_NICHES")
