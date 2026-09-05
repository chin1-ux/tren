import pytest
from ad_detector import detect_sponsored


def test_detectsponsored_by_hashtag():
    result = detect_sponsored("Check out this collab #ad #sponsored")
    assert result["is_sponsored"] is True
    assert result["confidence"] > 0.3


def test_not_sponsored_organic():
    result = detect_sponsored("This dance trend is going viral!")
    assert result["is_sponsored"] is False
    assert result["confidence"] < 0.3


def test_empty_caption():
    result = detect_sponsored("")
    assert result["is_sponsored"] is False
