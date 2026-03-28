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
    africa_score: float = 0.0
    relevance_score: float = 0.0
    total_score: float = 0.0
    whatsapp_short: str = ""
    whatsapp_detailed: str = ""
