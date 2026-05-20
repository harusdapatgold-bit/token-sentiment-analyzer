"""CLI entry point for token-sentiment-analyzer."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .config import load_settings
from .pipeline import run_pipeline
from .tracker import SignalTracker

console = Console()


@click.group()
def main() -> None:
    """Token Sentiment Analyzer — social + onchain signals powered by MiMo."""
    pass


@main.command()
@click.argument("symbol")
@click.option("--text", "-t", default="", help="Social text to analyze")
def analyze(symbol: str, text: str) -> None:
    """Run sentiment analysis on a single token."""
    settings = load_settings()
    tracker = SignalTracker(settings.db_path)
    report = asyncio.run(
        run_pipeline(symbol, settings=settings, tracker=tracker, social_text=text)
    )
    console.print(f"\n[bold]{report.symbol}[/] — [{_band_color(report.score.band)}]{report.score.band}[/] ({report.score.score}/100)")
    console.print(f"  Onchain: liq=${report.onchain.liquidity_usd:,.0f}  vol=${report.onchain.volume_24h:,.0f}")
    console.print(f"  Social: +{report.social.positive_keywords} / -{report.social.negative_keywords} keywords")
    if report.brief_markdown:
        console.print(f"  Brief: {report.brief_markdown}")
    console.print(f"  LLM tokens: {report.total_llm_tokens}")


@main.command()
@click.option("--seeds", "-s", type=click.Path(exists=True), default="seeds/default.txt")
@click.option("--cycle-sleep", default=60, help="Seconds between cycles")
@click.option("--max-cycles", default=0, help="Max cycles (0=infinite)")
def monitor(seeds: str, cycle_sleep: int, max_cycles: int) -> None:
    """Run continuous sentiment monitoring loop."""
    settings = load_settings()
    tracker = SignalTracker(settings.db_path)
    seed_list = Path(seeds).read_text().strip().splitlines()
    seed_list = [s.strip() for s in seed_list if s.strip() and not s.startswith("#")]

    console.print(f"[bold cyan]Monitor starting[/] | seeds={len(seed_list)} cycle_sleep={cycle_sleep}s")
    asyncio.run(_monitor_loop(seed_list, settings, tracker, cycle_sleep, max_cycles))


async def _monitor_loop(
    seeds: list[str],
    settings,
    tracker: SignalTracker,
    cycle_sleep: int,
    max_cycles: int,
) -> None:
    cycle = 0
    while True:
        cycle += 1
        console.print(f"\n[bold]=== cycle {cycle} ===[/]")
        for seed in seeds:
            try:
                report = await run_pipeline(seed, settings=settings, tracker=tracker)
                color = _band_color(report.score.band)
                console.print(
                    f"  [{color}]{report.symbol}[/] "
                    f"score={report.score.score} band={report.score.band} "
                    f"llm_tok={report.total_llm_tokens}"
                )
            except Exception as e:
                console.print(f"  [red]ERR[/] {seed}: {e}")
            await asyncio.sleep(2)

        if max_cycles and cycle >= max_cycles:
            break
        await asyncio.sleep(cycle_sleep)

    console.print(f"\n[bold green]Monitor complete[/] | runs={tracker.total_runs()} llm_tokens={tracker.total_llm_tokens()}")


@main.command()
def stats() -> None:
    """Show usage statistics from SQLite tracker."""
    settings = load_settings()
    tracker = SignalTracker(settings.db_path)

    t = Table(title="Sentiment Analyzer Stats", header_style="bold cyan")
    t.add_column("Metric", style="dim")
    t.add_column("Value", justify="right", style="bold")
    t.add_row("Total runs", f"{tracker.total_runs():,}")
    t.add_row("Total LLM tokens", f"{tracker.total_llm_tokens():,}")
    t.add_row("Model", settings.llm_model)
    console.print(t)

    runs = tracker.recent_runs(limit=10)
    if runs:
        rt = Table(title="Recent Runs", header_style="bold cyan")
        rt.add_column("Time")
        rt.add_column("Symbol")
        rt.add_column("Score", justify="right")
        rt.add_column("Band")
        rt.add_column("LLM Tok", justify="right")
        for r in runs:
            ts = (r.get("ts") or "")[:19].replace("T", " ")
            band = r.get("final_band") or "?"
            rt.add_row(ts, r["symbol"], str(r["final_score"]), band, str(r["llm_tokens_used"]))
        console.print(rt)


def _band_color(band: str) -> str:
    return {
        "panic": "bold red",
        "bearish": "red",
        "neutral": "white",
        "bullish": "green",
        "euphoric": "bold green",
    }.get(band, "white")
