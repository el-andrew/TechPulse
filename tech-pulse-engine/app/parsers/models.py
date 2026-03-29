from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(slots=True)
class SourceConfig:
    name: str
    type: str
    url: str
    category_hint: str
    africa_relevance_weight: float
    strategy: str | None = None
    selectors: dict[str, list[str]] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    country: str | None = None
    region: str | None = None
    city: str | None = None
    audience_scope: str = "africa"
    issuer_name: str | None = None
    issuer_type: str | None = None
    language: str = "en"
    source_priority: float = 0.5
    location_text: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SourceConfig":
        selectors = payload.get("selectors") or {}
        normalized_selectors = {
            key: value if isinstance(value, list) else [value]
            for key, value in selectors.items()
        }
        return cls(
            name=str(payload["name"]),
            type=str(payload["type"]).lower(),
            url=str(payload["url"]),
            category_hint=str(payload.get("category_hint", "")),
            africa_relevance_weight=float(payload.get("africa_relevance_weight", 0.5)),
            strategy=str(payload.get("strategy")) if payload.get("strategy") else None,
            selectors=normalized_selectors,
            options=dict(payload.get("options") or {}),
            country=_optional_string(payload.get("country")),
            region=_optional_string(payload.get("region")),
            city=_optional_string(payload.get("city")),
            audience_scope=str(payload.get("audience_scope", "africa")).lower(),
            issuer_name=_optional_string(payload.get("issuer_name")),
            issuer_type=_optional_string(payload.get("issuer_type")),
            language=str(payload.get("language", "en")).lower(),
            source_priority=float(payload.get("source_priority", 0.5)),
            location_text=_optional_string(payload.get("location_text")),
        )


@dataclass(slots=True)
class CollectedItem:
    title: str
    description: str
    source_name: str
    source_type: str
    source_url: str
    link: str
    category_hint: str
    africa_relevance_weight: float
    deadline: date | None = None
    event_date: date | None = None
    category: str | None = None
    country: str | None = None
    region: str | None = None
    city: str | None = None
    audience_scope: str = "africa"
    issuer_name: str | None = None
    issuer_type: str | None = None
    application_url: str | None = None
    location_text: str | None = None
    language: str = "en"
    source_priority: float = 0.5
    africa_score: float = 0.0
    locality_score: float = 0.0
    relevance_score: float = 0.0
    total_score: float = 0.0
    whatsapp_short: str = ""
    whatsapp_detailed: str = ""
    whatsapp_channel: str = ""


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
