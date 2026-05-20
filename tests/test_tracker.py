"""Tests for SQLite signal tracker."""

import tempfile
from pathlib import Path

from token_sentiment.tracker import SignalTracker


def test_tracker_records_run() -> None:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.sqlite"
        tracker = SignalTracker(db)
        tracker.record_run(
            symbol="PEPE",
            chain="ethereum",
            social_mentions=10,
            social_sentiment_raw=5.5,
            onchain_liquidity=26000000,
            onchain_volume_24h=500000,
            final_score=42,
            final_band="bullish",
            llm_tokens_used=750,
            duration_ms=1500,
        )
        assert tracker.total_runs() == 1
        runs = tracker.recent_runs(limit=5)
        assert len(runs) == 1
        assert runs[0]["symbol"] == "PEPE"
        assert runs[0]["final_band"] == "bullish"


def test_tracker_records_llm_call() -> None:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.sqlite"
        tracker = SignalTracker(db)
        tracker.record_llm_call(
            symbol="WIF",
            prompt_tokens=300,
            completion_tokens=200,
            duration_ms=800,
        )
        assert tracker.total_llm_tokens() == 500


def test_tracker_aggregates_by_symbol() -> None:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.sqlite"
        tracker = SignalTracker(db)
        for i in range(3):
            tracker.record_run(symbol="PEPE", llm_tokens_used=500)
        for i in range(2):
            tracker.record_run(symbol="WIF", llm_tokens_used=300)

        agg = tracker.by_symbol()
        assert len(agg) == 2
        assert agg[0][0] == "PEPE"
        assert agg[0][1] == 3
        assert agg[0][2] == 1500


def test_tracker_zero_state() -> None:
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.sqlite"
        tracker = SignalTracker(db)
        assert tracker.total_runs() == 0
        assert tracker.total_llm_tokens() == 0
        assert tracker.recent_runs() == []
