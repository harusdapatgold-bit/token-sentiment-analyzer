"""Tests for sentiment lexicon scoring."""

from token_sentiment.lexicon import (
    BEARISH_KEYWORDS,
    BULLISH_KEYWORDS,
    normalize_score,
    score_text,
    score_to_band,
)


def test_lexicon_scores_bullish_text() -> None:
    text = "PEPE is mooning, bullish breakout, big pump incoming, ATH soon"
    result = score_text(text)
    assert result.raw_score > 5
    assert result.positive_hits >= 3


def test_lexicon_scores_bearish_text() -> None:
    text = "Total rug pull, scam project, dumping hard, dead coin, panic selling"
    result = score_text(text)
    assert result.raw_score < -5
    assert result.negative_hits >= 3


def test_lexicon_detects_fud() -> None:
    text = "Coordinated FUD attack, fake news, manipulation"
    result = score_text(text)
    assert result.fud_hits >= 2


def test_lexicon_detects_shill() -> None:
    text = "Trust me bro, easy money, no risk, financial advice"
    result = score_text(text)
    assert result.shill_hits >= 3


def test_normalize_score_clamps() -> None:
    assert normalize_score(100, max_abs=30) == 100
    assert normalize_score(-100, max_abs=30) == -100
    assert normalize_score(0) == 0
    assert normalize_score(15, max_abs=30) == 50


def test_score_to_band_thresholds() -> None:
    assert score_to_band(-80) == "panic"
    assert score_to_band(-30) == "bearish"
    assert score_to_band(0) == "neutral"
    assert score_to_band(40) == "bullish"
    assert score_to_band(80) == "euphoric"


def test_lexicon_neutral_text() -> None:
    text = "Today is a regular day with nothing special happening"
    result = score_text(text)
    assert result.raw_score == 0
    assert result.positive_hits == 0
    assert result.negative_hits == 0


def test_lexicon_keyword_lists_have_entries() -> None:
    assert len(BULLISH_KEYWORDS) > 20
    assert len(BEARISH_KEYWORDS) > 20
