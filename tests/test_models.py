"""Tests for Pydantic data models."""

from datetime import datetime, timezone

from token_sentiment.models import (
    AnalysisReport,
    OnchainSignal,
    SentimentScore,
    SocialSignal,
)


def test_social_signal_defaults() -> None:
    s = SocialSignal(symbol="PEPE")
    assert s.symbol == "PEPE"
    assert s.mentions_24h == 0
    assert s.sources_seen == []


def test_onchain_signal_defaults() -> None:
    o = OnchainSignal(symbol="PEPE")
    assert o.symbol == "PEPE"
    assert o.liquidity_usd == 0.0
    assert o.pair_age_days is None


def test_sentiment_score_validates_range() -> None:
    s = SentimentScore(symbol="PEPE", score=42, band="bullish")
    assert s.score == 42
    assert s.band == "bullish"


def test_analysis_report_full() -> None:
    report = AnalysisReport(
        symbol="PEPE",
        timestamp=datetime.now(timezone.utc),
        social=SocialSignal(symbol="PEPE"),
        onchain=OnchainSignal(symbol="PEPE", liquidity_usd=26e6),
        score=SentimentScore(symbol="PEPE", score=42, band="bullish"),
    )
    assert report.symbol == "PEPE"
    assert report.onchain.liquidity_usd == 26e6
    assert report.brief_markdown is None
