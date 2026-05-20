"""SQLite-backed tracker for sentiment analysis runs and LLM token usage."""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sentiment_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    chain TEXT,
    social_mentions INT DEFAULT 0,
    social_sentiment_raw REAL DEFAULT 0,
    onchain_liquidity REAL DEFAULT 0,
    onchain_volume_24h REAL DEFAULT 0,
    final_score INT DEFAULT 0,
    final_band TEXT,
    llm_tokens_used INT DEFAULT 0,
    duration_ms INT DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sentiment_runs_ts ON sentiment_runs(ts);
CREATE INDEX IF NOT EXISTS idx_sentiment_runs_symbol ON sentiment_runs(symbol);

CREATE TABLE IF NOT EXISTS llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    total_tokens INT NOT NULL,
    duration_ms INT DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_ts ON llm_calls(ts);
"""


class SignalTracker:
    """Thread-safe SQLite tracker for sentiment runs and LLM usage."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.execute("PRAGMA journal_mode=WAL;")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def record_run(
        self,
        *,
        symbol: str,
        chain: Optional[str] = None,
        social_mentions: int = 0,
        social_sentiment_raw: float = 0.0,
        onchain_liquidity: float = 0.0,
        onchain_volume_24h: float = 0.0,
        final_score: int = 0,
        final_band: Optional[str] = None,
        llm_tokens_used: int = 0,
        duration_ms: int = 0,
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO sentiment_runs "
                "(ts, symbol, chain, social_mentions, social_sentiment_raw, "
                "onchain_liquidity, onchain_volume_24h, final_score, final_band, "
                "llm_tokens_used, duration_ms) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ts, symbol, chain, social_mentions, social_sentiment_raw,
                    onchain_liquidity, onchain_volume_24h, final_score, final_band,
                    llm_tokens_used, duration_ms,
                ),
            )

    def record_llm_call(
        self,
        *,
        symbol: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: int = 0,
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        total = prompt_tokens + completion_tokens
        with self._lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO llm_calls "
                "(ts, symbol, prompt_tokens, completion_tokens, total_tokens, duration_ms) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, symbol, prompt_tokens, completion_tokens, total, duration_ms),
            )

    def total_llm_tokens(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(total_tokens), 0) FROM llm_calls"
            ).fetchone()
        return int(row[0]) if row else 0

    def total_runs(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM sentiment_runs").fetchone()
        return int(row[0]) if row else 0

    def recent_runs(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT ts, symbol, chain, final_score, final_band, "
                "onchain_liquidity, social_mentions, llm_tokens_used "
                "FROM sentiment_runs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def by_symbol(self, limit: int = 10) -> list[tuple[str, int, int]]:
        """Return (symbol, runs, total_llm_tokens) sorted by tokens desc."""
        with self._connect() as conn:
            return [
                (r[0], int(r[1]), int(r[2]))
                for r in conn.execute(
                    "SELECT symbol, COUNT(*) as c, COALESCE(SUM(llm_tokens_used), 0) as t "
                    "FROM sentiment_runs GROUP BY symbol ORDER BY t DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            ]
