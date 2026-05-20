"""Main pipeline — orchestrate social + onchain + sentiment scoring."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from .config import Settings
from .dexscreener import fetch_onchain
from .lexicon import score_text, normalize_score, score_to_band
from .models import AnalysisReport, OnchainSignal, SentimentScore, SocialSignal
from .tracker import SignalTracker


async def run_pipeline(
    symbol: str,
    *,
    settings: Settings,
    tracker: SignalTracker,
    social_text: str = "",
) -> AnalysisReport:
    """Run full sentiment analysis pipeline for a token.

    Steps:
    1. Fetch onchain metrics (DexScreener) — deterministic, zero LLM tokens
    2. Score social text via lexicon — deterministic, zero LLM tokens
    3. Combine into SentimentScore
    4. Optionally call MiMo for synthesis brief (light, ~500-800 tokens)
    """
    start_ts = datetime.now(timezone.utc)

    # Step 1: Onchain signals
    async with httpx.AsyncClient() as client:
        onchain = await fetch_onchain(symbol, client=client)
    if not onchain:
        onchain = OnchainSignal(symbol=symbol)

    # Step 2: Social sentiment (lexicon-based, zero LLM)
    lex_result = score_text(social_text)
    raw_score = normalize_score(lex_result.raw_score)
    band = score_to_band(raw_score)

    social = SocialSignal(
        symbol=symbol,
        mentions_24h=len(social_text.split()),
        positive_keywords=lex_result.positive_hits,
        negative_keywords=lex_result.negative_hits,
        fud_keywords=lex_result.fud_hits,
        shill_keywords=lex_result.shill_hits,
        sources_seen=["lexicon"],
        sample_titles=lex_result.matched_keywords[:5],
    )

    score = SentimentScore(
        symbol=symbol,
        score=raw_score,
        band=band,
        flags=[kw for kw in lex_result.matched_keywords if kw.startswith("!")],
        rationale_inputs={
            "positive_hits": lex_result.positive_hits,
            "negative_hits": lex_result.negative_hits,
            "fud_signals": lex_result.fud_hits,
            "shill_signals": lex_result.shill_hits,
        },
    )

    # Step 3: Optional MiMo synthesis (light usage)
    brief_md = None
    llm_tokens = 0
    if social_text and len(social_text) > 50:  # Only synthesize if meaningful text
        brief_md, llm_tokens = await _synthesize_brief(
            symbol, score, onchain, settings
        )

    # Record run
    duration_ms = int((datetime.now(timezone.utc) - start_ts).total_seconds() * 1000)
    tracker.record_run(
        symbol=symbol,
        chain=onchain.chain,
        social_mentions=social.mentions_24h,
        social_sentiment_raw=lex_result.raw_score,
        onchain_liquidity=onchain.liquidity_usd,
        onchain_volume_24h=onchain.volume_24h,
        final_score=score.score,
        final_band=score.band,
        llm_tokens_used=llm_tokens,
        duration_ms=duration_ms,
    )

    if llm_tokens > 0:
        tracker.record_llm_call(
            symbol=symbol,
            prompt_tokens=llm_tokens // 2,
            completion_tokens=llm_tokens // 2,
            duration_ms=duration_ms,
        )

    return AnalysisReport(
        symbol=symbol,
        timestamp=start_ts,
        social=social,
        onchain=onchain,
        score=score,
        brief_markdown=brief_md,
        total_llm_tokens=llm_tokens,
    )


async def _synthesize_brief(
    symbol: str,
    score: SentimentScore,
    onchain,
    settings: Settings,
) -> tuple[str, int]:
    """Call MiMo for a brief synthesis (light usage, ~500-800 tokens)."""
    prompt = f"""Provide a 2-3 sentence sentiment brief for {symbol}.

Sentiment score: {score.score}/100 ({score.band})
Liquidity: ${onchain.liquidity_usd:,.0f}
24h volume: ${onchain.volume_24h:,.0f}
Key signals: {', '.join(score.flags) or 'none flagged'}

Brief (concise, no markdown):"""

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.llm_base_url}/chat/completions",
                json={
                    "model": settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 150,
                    "temperature": 0.7,
                },
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]
            brief = (msg.get("content") or msg.get("reasoning_content") or "").strip()
            if not brief:
                return "(no synthesis output)", 0
            usage = data.get("usage", {})
            total_tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            return brief, total_tokens
    except Exception as e:
        return f"(synthesis failed: {str(e)[:50]})", 0
