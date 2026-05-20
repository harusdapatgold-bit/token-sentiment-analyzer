"""Token Sentiment Analyzer — multi-source sentiment + onchain signals."""

from .config import load_settings, Settings
from .models import (
    SocialSignal,
    OnchainSignal,
    SentimentScore,
    AnalysisReport,
)
from .tracker import SignalTracker
from .pipeline import run_pipeline

__version__ = "1.0.0"

__all__ = [
    "load_settings",
    "Settings",
    "SocialSignal",
    "OnchainSignal",
    "SentimentScore",
    "AnalysisReport",
    "SignalTracker",
    "run_pipeline",
]
