from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from app.parsers.models import SourceConfig


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SOURCES_PATH = ROOT_DIR / "app" / "config" / "sources.yaml"


@dataclass(slots=True)
class Settings:
    database_url: str
    request_timeout: int
    user_agent: str
    log_level: str
    digest_path: Path
    scheduler_hour: int
    scheduler_minute: int
    min_africa_score: float
    dashboard_host: str
    dashboard_port: int
    dashboard_title: str
    dashboard_refresh_seconds: int


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        database_url=os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR / 'tech_pulse.db'}"),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "20")),
        user_agent=os.getenv("USER_AGENT", "tech-pulse-engine/2.0"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        digest_path=Path(os.getenv("DIGEST_PATH", ROOT_DIR / "daily_digest.md")),
        scheduler_hour=int(os.getenv("DAILY_RUN_HOUR", "7")),
        scheduler_minute=int(os.getenv("DAILY_RUN_MINUTE", "0")),
        min_africa_score=float(os.getenv("MIN_AFRICA_SCORE", "0.50")),
        dashboard_host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
        dashboard_port=int(os.getenv("DASHBOARD_PORT", "8080")),
        dashboard_title=os.getenv("DASHBOARD_TITLE", "Tech Pulse Command Center"),
        dashboard_refresh_seconds=int(os.getenv("DASHBOARD_REFRESH_SECONDS", "60")),
    )


def load_sources(path: Path | None = None) -> list[SourceConfig]:
    config_path = path or DEFAULT_SOURCES_PATH
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    items = payload.get("sources", [])
    return [SourceConfig.from_dict(item) for item in items]


def read_selector(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(entry) for entry in value]
    return []
