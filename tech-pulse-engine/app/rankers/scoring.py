from __future__ import annotations

from datetime import date

from app.parsers.classifier import compute_africa_score
from app.parsers.models import CollectedItem


BOOST_KEYWORDS = {
    "free": 0.15,
    "certificate": 0.10,
    "funding": 0.18,
    "stipend": 0.18,
    "scholarship": 0.18,
    "tangazo": 0.10,
    "vacancy": 0.12,
}

AUDIENCE_SCOPE_BOOST = {
    "tanzania": 0.62,
    "east_africa": 0.42,
    "africa": 0.22,
    "global": 0.08,
}

TANZANIA_TERMS = [
    "tanzania",
    "dar es salaam",
    "dodoma",
    "arusha",
    "zanzibar",
    "mwanza",
    "mbeya",
    "morogoro",
    "ajira",
    "costech",
    "veta",
]

EAST_AFRICA_TERMS = [
    "east africa",
    "east african",
    "eac",
    "kenya",
    "uganda",
    "rwanda",
    "burundi",
    "south sudan",
]


def apply_ranking(item: CollectedItem, today: date | None = None) -> CollectedItem:
    current_day = today or date.today()
    item.africa_score = compute_africa_score(item)
    item.locality_score = round(_locality_score(item), 3)
    item.relevance_score = round(_keyword_score(item) + _deadline_score(item, current_day) + _priority_score(item), 3)
    item.total_score = round((item.africa_score * 0.30) + (item.relevance_score * 0.35) + (item.locality_score * 0.35), 3)
    return item


def _keyword_score(item: CollectedItem) -> float:
    text = f"{item.title} {item.description}".lower()
    score = 0.0
    for keyword, weight in BOOST_KEYWORDS.items():
        if keyword in text:
            score += weight
    return min(score, 0.55)


def _deadline_score(item: CollectedItem, today: date) -> float:
    if not item.deadline:
        return 0.12
    days_until_deadline = (item.deadline - today).days
    if days_until_deadline < 0:
        return 0.0
    if days_until_deadline <= 3:
        return 0.5
    if days_until_deadline <= 7:
        return 0.35
    if days_until_deadline <= 14:
        return 0.25
    return 0.1


def _priority_score(item: CollectedItem) -> float:
    return min(0.18, max(0.0, item.source_priority) * 0.18)


def _locality_score(item: CollectedItem) -> float:
    text = " ".join(
        part for part in (
            item.title,
            item.description,
            item.location_text or "",
            item.country or "",
            item.region or "",
            item.city or "",
        )
    ).lower()
    score = AUDIENCE_SCOPE_BOOST.get(item.audience_scope, 0.12)
    if item.country and item.country.lower() == "tanzania":
        score += 0.18
    elif item.country and item.country.lower() in {"kenya", "uganda", "rwanda", "burundi", "south sudan"}:
        score += 0.08

    if item.region:
        score += 0.08
    if item.city:
        score += 0.06

    score += min(0.16, sum(0.04 for term in TANZANIA_TERMS if term in text))
    score += min(0.10, sum(0.03 for term in EAST_AFRICA_TERMS if term in text))
    score += min(0.14, max(0.0, item.source_priority) * 0.14)
    return min(score, 1.0)
