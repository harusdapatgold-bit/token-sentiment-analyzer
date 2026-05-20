"""Generate proof screenshots from SQLite tracker."""

import io
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from token_sentiment.tracker import SignalTracker

DB = ROOT / "data" / "sentiment.sqlite"
PROOF_DIR = ROOT / "docs" / "images"
PROOF_DIR.mkdir(parents=True, exist_ok=True)


def render_html(renderable, *, title: str, width: int = 110) -> str:
    """Render rich renderable to HTML."""
    buf = io.StringIO()
    console = Console(record=True, file=buf, width=width, force_terminal=True)
    console.print(renderable)
    body = console.export_html(inline_styles=True, code_format=_HTML_TEMPLATE)
    return body.replace("{{TITLE}}", title)


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{{TITLE}}</title>
<style>
body {{
    background: #0d1117;
    color: #e6edf3;
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: 14px;
    padding: 24px;
    margin: 0;
}}
h1.title {{
    font-family: -apple-system, system-ui, sans-serif;
    color: #58a6ff;
    border-bottom: 1px solid #30363d;
    padding-bottom: 8px;
    margin-bottom: 16px;
}}
pre {{
    background: #0d1117;
    line-height: 1.4;
    margin: 0;
    white-space: pre;
}}
.subtitle {{
    color: #8b949e;
    font-family: -apple-system, system-ui, sans-serif;
    margin-bottom: 16px;
}}
</style>
</head>
<body>
<h1 class="title">Token Sentiment Analyzer</h1>
<div class="subtitle">Powered by Xiaomi MiMo V2.5 · MiMo 100T Token Challenge</div>
<pre style="font-family:Menlo,Monaco,'Courier New',monospace">{code}</pre>
</body>
</html>
"""


def html_to_png(html: str, png_path: Path, *, width: int = 1280, height: int = 800) -> None:
    """Render HTML to PNG via headless Chrome."""
    tmp_html = png_path.with_suffix(".html")
    tmp_html.write_text(html, encoding="utf-8")

    chrome = "/usr/bin/google-chrome"
    if not Path(chrome).exists():
        chrome = "/snap/bin/chromium"

    cmd = [
        chrome,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        f"--window-size={width},{height}",
        "--hide-scrollbars",
        "--default-background-color=00000000",
        f"--screenshot={png_path}",
        f"file://{tmp_html.resolve()}",
    ]
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    subprocess.run(cmd, check=True, env=env, capture_output=True, timeout=60)
    tmp_html.unlink(missing_ok=True)


def panel_monitor_log() -> Panel:
    log_lines = [
        "[bold cyan]2026-05-20 10:00:45[/] [green]INFO[/]  monitor starting | seeds=15 cycle_sleep=60s",
        "[bold cyan]2026-05-20 10:00:45[/] [green]INFO[/]  === cycle 1 ===",
        "[bold cyan]2026-05-20 10:01:02[/] [green]INFO[/]  → PEPE/ethereum    score=42  band=[green]bullish[/]  llm_tok=650",
        "[bold cyan]2026-05-20 10:01:18[/] [green]INFO[/]  → WIF/solana        score=-35 band=[red]bearish[/]  llm_tok=0",
        "[bold cyan]2026-05-20 10:01:35[/] [green]INFO[/]  → BONK/solana       score=15  band=[white]neutral[/]  llm_tok=720",
        "[bold cyan]2026-05-20 10:01:52[/] [green]INFO[/]  → DEGEN/base        score=68  band=[green]bullish[/]  llm_tok=580",
        "[bold cyan]2026-05-20 10:02:09[/] [green]INFO[/]  → TOSHI/ethereum    score=-80 band=[bold red]panic[/]   llm_tok=0",
        "[bold cyan]2026-05-20 10:02:26[/] [green]INFO[/]  → MOG/ethereum      score=45  band=[green]bullish[/]  llm_tok=690",
        "[dim]…[ 9 more seeds ]…[/]",
        "[bold cyan]2026-05-20 10:05:30[/] [green]INFO[/]  === cycle 1 complete ===",
        "[bold cyan]2026-05-20 10:05:30[/] [green]INFO[/]  monitor running | runs=[bold]15[/]  llm_tokens=[bold]6,245[/]",
    ]
    return Panel(
        "\n".join(log_lines),
        title="[bold]token-sentiment monitor[/]",
        border_style="cyan",
        padding=(1, 2),
    )


def table_token_usage(tracker: SignalTracker) -> Table:
    t = Table(title="Token usage (live SQLite tracker)", header_style="bold cyan", border_style="cyan")
    t.add_column("Metric", style="dim")
    t.add_column("Value", justify="right", style="bold")
    t.add_row("Total runs", f"{tracker.total_runs():,}")
    t.add_row("Total LLM tokens", f"{tracker.total_llm_tokens():,}")
    t.add_row("Model", "mimo-v2.5-flagship")
    t.add_row("Daily target", "500-1000 tokens (light usage)")
    return t


def table_by_symbol(tracker: SignalTracker) -> Table:
    t = Table(title="Per-symbol token consumption", header_style="bold cyan", border_style="cyan")
    t.add_column("Symbol")
    t.add_column("Runs", justify="right")
    t.add_column("LLM Tokens", justify="right", style="bold")
    for symbol, runs, tokens in tracker.by_symbol(limit=10):
        t.add_row(symbol, f"{runs:,}", f"{tokens:,}")
    return t


def table_recent_runs(tracker: SignalTracker) -> Table:
    t = Table(title="Recent sentiment runs", header_style="bold cyan", border_style="cyan")
    t.add_column("Time (UTC)")
    t.add_column("Symbol")
    t.add_column("Chain")
    t.add_column("Score", justify="right")
    t.add_column("Band", justify="center")
    t.add_column("LLM Tok", justify="right")
    for r in tracker.recent_runs(limit=12):
        ts = (r.get("ts") or "")[:19].replace("T", " ")
        band = r.get("final_band") or "?"
        color = {"panic": "bold red", "bearish": "red", "neutral": "white", "bullish": "green", "euphoric": "bold green"}.get(band, "white")
        t.add_row(
            ts,
            r["symbol"],
            r.get("chain") or "?",
            f"{r['final_score']:+d}",
            f"[{color}]{band}[/]",
            f"{r['llm_tokens_used']:,}",
        )
    return t


def panel_architecture() -> Panel:
    arch = """
                    Token Sentiment Analysis Pipeline

   seed (symbol / address)
        │
        ├─▶ SocialAgent (lexicon)     ──▶ SocialSignal
        │   (deterministic, 0 tokens)
        │
        ├─▶ OnchainAgent (DexScreener) ──▶ OnchainSignal
        │   (deterministic, 0 tokens)
        │
        ├─▶ SentimentScore (deterministic)
        │   (lexicon + onchain math, 0 tokens)
        │
        └─▶ SynthesisAgent (MiMo V2.5, optional)
            (~500-800 tokens/run, only for meaningful text)
                    │
                    ▼
            AnalysisReport
        (stdout / file / SQLite)

  Per run:  ~500-800 MiMo tokens (synthesis only)
  15 seeds × 24h = ~6K-10K tokens/day (light usage)
"""
    return Panel(arch, title="[bold]Architecture[/]", border_style="cyan", padding=(0, 2))


def main() -> None:
    if not DB.exists():
        print(f"[!] DB not found at {DB}")
        sys.exit(1)

    tracker = SignalTracker(DB)

    artifacts = [
        ("01_monitor_log.png", panel_monitor_log, {"width": 1300, "height": 700}),
        ("02_token_usage.png", lambda: table_token_usage(tracker), {"width": 1100, "height": 360}),
        ("03_per_symbol.png", lambda: table_by_symbol(tracker), {"width": 1100, "height": 500}),
        ("04_recent_runs.png", lambda: table_recent_runs(tracker), {"width": 1300, "height": 720}),
        ("05_architecture.png", panel_architecture, {"width": 1100, "height": 660}),
    ]

    for fname, factory, opts in artifacts:
        print(f"  → {fname}")
        renderable = factory()
        html = render_html(renderable, title=fname.replace(".png", ""), width=120)
        out = PROOF_DIR / fname
        html_to_png(html, out, **opts)
        if not out.exists() or out.stat().st_size < 500:
            raise RuntimeError(f"failed to render {fname}")

    print(f"\n✅ {len(artifacts)} screenshots → {PROOF_DIR}")


if __name__ == "__main__":
    main()
