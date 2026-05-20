"""DexScreener client — deterministic onchain signal fetcher (zero LLM tokens).

Free API, no key required. Provides liquidity, volume, price changes, and
transaction counts for any token across supported chains.
"""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .models import OnchainSignal


_BASE = "https://api.dexscreener.com/latest"
_TIMEOUT = 15.0


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def fetch_onchain(seed: str, *, client: httpx.AsyncClient | None = None) -> OnchainSignal | None:
    """Fetch onchain metrics for a token seed (address or symbol).

    Returns the top pair by liquidity, or None if not found.
    """
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=_TIMEOUT)

    try:
        if seed.startswith("0x") or len(seed) > 20:
            url = f"{_BASE}/dex/tokens/{seed}"
        else:
            url = f"{_BASE}/dex/search/?q={seed}"

        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()

        pairs = data.get("pairs") or []
        if not pairs:
            return None

        # Pick top pair by liquidity
        pairs.sort(key=lambda p: float(p.get("liquidity", {}).get("usd", 0) or 0), reverse=True)
        top = pairs[0]

        price_change = top.get("priceChange") or {}
        txns = top.get("txns", {}).get("h24") or {}
        pair_created = top.get("pairCreatedAt")
        pair_age = None
        if pair_created:
            import time
            age_s = time.time() - (pair_created / 1000)
            pair_age = max(0, int(age_s / 86400))

        return OnchainSignal(
            symbol=top.get("baseToken", {}).get("symbol", seed),
            chain=top.get("chainId"),
            address=top.get("baseToken", {}).get("address"),
            liquidity_usd=float(top.get("liquidity", {}).get("usd", 0) or 0),
            volume_24h=float(top.get("volume", {}).get("h24", 0) or 0),
            price_usd=float(top.get("priceUsd", 0) or 0),
            price_change_1h=float(price_change.get("h1", 0) or 0),
            price_change_24h=float(price_change.get("h24", 0) or 0),
            txns_buys_24h=int(txns.get("buys", 0) or 0),
            txns_sells_24h=int(txns.get("sells", 0) or 0),
            pair_age_days=pair_age,
            fdv_usd=float(top.get("fdv", 0) or 0) if top.get("fdv") else None,
        )
    finally:
        if own_client:
            await client.aclose()
