"""Configuration loaded from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    dexscreener_base: str = "https://api.dexscreener.com/latest"
    cryptopanic_token: str | None = None
    db_path: str = "data/sentiment.sqlite"
    reports_dir: str = "data/reports"


def load_settings(env_file: str | Path | None = None) -> Settings:
    """Load settings from .env file or environment variables.

    Raises RuntimeError if required LLM config is missing.
    """
    if env_file is not None:
        load_dotenv(env_file)
    else:
        load_dotenv()

    base_url = os.getenv("LLM_BASE_URL", "").strip()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()

    if not (base_url and api_key and model):
        raise RuntimeError(
            "Missing LLM config. Set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL "
            "(see .env.example)."
        )

    return Settings(
        llm_base_url=base_url,
        llm_api_key=api_key,
        llm_model=model,
        cryptopanic_token=os.getenv("CRYPTOPANIC_TOKEN") or None,
        db_path=os.getenv("DB_PATH", "data/sentiment.sqlite"),
        reports_dir=os.getenv("REPORTS_DIR", "data/reports"),
    )
