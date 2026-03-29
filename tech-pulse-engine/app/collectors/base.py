from __future__ import annotations

from abc import ABC, abstractmethod
from logging import Logger
from urllib.parse import urlsplit, urlunsplit

import requests
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config.settings import Settings
from app.notify.logging import get_source_logger
from app.parsers.models import CollectedItem, SourceConfig


class BaseCollector(ABC):
    def __init__(self, settings: Settings, source: SourceConfig) -> None:
        self.settings = settings
        self.source = source
        self.logger: Logger = get_source_logger(source.name, settings.log_level)
        self.errors: list[str] = []
        self.http = self._build_http_session()

    @abstractmethod
    def collect(self) -> list[CollectedItem]:
        raise NotImplementedError

    def _build_http_session(self) -> Session:
        session = requests.Session()
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            status=2,
            allowed_methods=frozenset({"GET"}),
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({"User-Agent": self.settings.user_agent})
        return session

    def _record_error(self, message: str) -> None:
        self.errors.append(message)

    def _base_item_fields(self, link: str) -> dict[str, object]:
        normalized_link = self._normalize_url(link)
        location_text = self.source.location_text or self._compose_location_text(
            self.source.city,
            self.source.region,
            self.source.country,
        )
        return {
            "source_name": self.source.name,
            "source_type": self.source.type,
            "source_url": self.source.url,
            "link": normalized_link,
            "category_hint": self.source.category_hint,
            "africa_relevance_weight": self.source.africa_relevance_weight,
            "country": self.source.country,
            "region": self.source.region,
            "city": self.source.city,
            "audience_scope": self.source.audience_scope,
            "issuer_name": self.source.issuer_name or self.source.name,
            "issuer_type": self.source.issuer_type,
            "application_url": normalized_link,
            "location_text": location_text,
            "language": self.source.language,
            "source_priority": self.source.source_priority,
        }

    @staticmethod
    def _compose_location_text(city: str | None, region: str | None, country: str | None) -> str | None:
        parts = [part for part in (city, region, country) if part]
        return ", ".join(parts) if parts else None

    @staticmethod
    def _normalize_url(url: str) -> str:
        split = urlsplit(url.strip())
        path = split.path.rstrip("/") or "/"
        return urlunsplit((split.scheme, split.netloc, path, split.query, ""))
