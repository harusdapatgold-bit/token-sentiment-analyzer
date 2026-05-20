"""Sentiment lexicon — keyword-based scoring (deterministic, zero LLM tokens).

Approach: curated word lists for crypto-specific sentiment. Each keyword has
a weight (-3 to +3). The scorer sums weights from matched keywords in social
text, normalizes to -100..+100 range, and assigns a band.
"""

from __future__ import annotations

from dataclasses import dataclass

# Positive signals (bullish / euphoric)
BULLISH_KEYWORDS: dict[str, int] = {
    "moon": 2, "mooning": 3, "pump": 2, "pumping": 3, "bullish": 2,
    "breakout": 2, "ath": 3, "all time high": 3, "gem": 2, "100x": 3,
    "1000x": 3, "undervalued": 2, "accumulate": 2, "buy the dip": 2,
    "btd": 2, "wagmi": 2, "lfg": 2, "send it": 2, "alpha": 2,
    "massive": 1, "explode": 2, "rocket": 2, "parabolic": 3,
    "reversal": 1, "recovery": 1, "green": 1, "profit": 1,
    "listing": 2, "partnership": 2, "adoption": 2, "upgrade": 1,
    "launch": 1, "mainnet": 2, "airdrop": 1, "staking": 1,
}

# Negative signals (bearish / panic)
BEARISH_KEYWORDS: dict[str, int] = {
    "dump": -2, "dumping": -3, "rug": -3, "rugpull": -3, "scam": -3,
    "ponzi": -3, "bearish": -2, "crash": -3, "crashing": -3,
    "dead": -2, "rip": -2, "ngmi": -2, "sell": -1, "selling": -2,
    "exit": -2, "exit scam": -3, "honeypot": -3, "hack": -3,
    "exploit": -3, "drain": -3, "rug pull": -3, "red": -1,
    "loss": -1, "liquidated": -2, "rekt": -2, "bag": -1,
    "bagholder": -2, "fud": -1, "fear": -1, "panic": -2,
    "delay": -1, "failed": -2, "vulnerability": -2, "warning": -1,
    "unlocked": -1, "vesting": -1, "inflation": -1,
}

# FUD-specific (manipulation signals)
FUD_KEYWORDS: list[str] = [
    "fud", "fake", "manipulation", "coordinated", "bot", "wash",
    "wash trading", "insider", "front run", "frontrun",
]

# Shill-specific (manipulation signals)
SHILL_KEYWORDS: list[str] = [
    "shill", "shilling", "paid", "sponsored", "guaranteed",
    "easy money", "free money", "no risk", "trust me", "financial advice",
]


@dataclass
class LexiconResult:
    raw_score: float
    positive_hits: int
    negative_hits: int
    fud_hits: int
    shill_hits: int
    matched_keywords: list[str]


def score_text(text: str) -> LexiconResult:
    """Score a text blob against the sentiment lexicon.

    Returns raw_score (unbounded sum of weights) and hit counts.
    """
    lower = text.lower()
    raw_score = 0.0
    positive_hits = 0
    negative_hits = 0
    fud_hits = 0
    shill_hits = 0
    matched: list[str] = []

    for kw, weight in BULLISH_KEYWORDS.items():
        if kw in lower:
            raw_score += weight
            positive_hits += 1
            matched.append(f"+{kw}")

    for kw, weight in BEARISH_KEYWORDS.items():
        if kw in lower:
            raw_score += weight
            negative_hits += 1
            matched.append(f"-{kw}")

    for kw in FUD_KEYWORDS:
        if kw in lower:
            fud_hits += 1
            matched.append(f"!{kw}")

    for kw in SHILL_KEYWORDS:
        if kw in lower:
            shill_hits += 1
            matched.append(f"${kw}")

    return LexiconResult(
        raw_score=raw_score,
        positive_hits=positive_hits,
        negative_hits=negative_hits,
        fud_hits=fud_hits,
        shill_hits=shill_hits,
        matched_keywords=matched,
    )


def normalize_score(raw: float, max_abs: float = 30.0) -> int:
    """Normalize raw lexicon score to -100..+100 range."""
    clamped = max(-max_abs, min(max_abs, raw))
    return int(round((clamped / max_abs) * 100))


def score_to_band(score: int) -> str:
    """Map normalized score to sentiment band."""
    if score <= -60:
        return "panic"
    elif score <= -20:
        return "bearish"
    elif score <= 20:
        return "neutral"
    elif score <= 60:
        return "bullish"
    else:
        return "euphoric"
