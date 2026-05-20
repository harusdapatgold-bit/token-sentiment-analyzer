"""Pydantic data contracts exchanged between agents."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SentimentBand = Literal["bearish", "neutral", "bullish", "euphoric", "panic"]


class SocialSignal(BaseModel):
    """Aggregated social-media signals from public sources."""

    symbol: str
    mentions_24h: int = 0
    mentions_1h: int = 0
    velocity: float = 0.0  # mentions_1h / (mentions_24h / 24)
    positive_keywords: int = 0
    negative_keywords: int = 0
    fud_keywords: int = 0
    shill_keywords: int = 0
    sources_seen: list[str] = Field(default_factory=list)
    sample_titles: list[str] = Field(default_factory=list)


class OnchainSignal(BaseModel):
    """Deterministic onchain metrics from DexScreener."""

    symbol: str
    chain: str | None = None
    address: str | None = None
    liquidity_usd: float = 0.0
    volume_24h: float = 0.0
    price_usd: float = 0.0
    price_change_1h: float = 0.0
    price_change_24h: float = 0.0
    txns_buys_24h: int = 0
    txns_sells_24h: int = 0
    pair_age_days: int | None = None
    fdv_usd: float | None = None


class SentimentScore(BaseModel):
    """Deterministic sentiment scoring derived from signals."""

    symbol: str
    score: int = Field(ge=-100, le=100)  # -100 panic, 0 neutral, +100 euphoric
    band: SentimentBand
    flags: list[str] = Field(default_factory=list)
    rationale_inputs: dict[str, float] = Field(default_factory=dict)


class AnalysisReport(BaseModel):
    """Full pipeline output — combined signals + score + optional brief."""

    symbol: str
    timestamp: datetime
    social: SocialSignal
    onchain: OnchainSignal
    score: SentimentScore
    brief_markdown: str | None = None
    total_llm_tokens: int = 0
