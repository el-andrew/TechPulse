from __future__ import annotations

from datetime import date

from app.parsers.classifier import compute_africa_score
from app.parsers.models import CollectedItem


BOOST_KEYWORDS = {
    "free": 0.15,
    "certificate": 0.10,
    "funding": 0.18,
    "stipend": 0.18,
}


def apply_ranking(item: CollectedItem, today: date | None = None) -> CollectedItem:
    current_day = today or date.today()
    item.africa_score = compute_africa_score(item)
    item.relevance_score = round(_keyword_score(item) + _deadline_score(item, current_day), 3)
    item.total_score = round((item.africa_score * 0.45) + (item.relevance_score * 0.55), 3)
    return item


def _keyword_score(item: CollectedItem) -> float:
    text = f"{item.title} {item.description}".lower()
    score = 0.0
    for keyword, weight in BOOST_KEYWORDS.items():
        if keyword in text:
            score += weight
    return min(score, 0.5)


def _deadline_score(item: CollectedItem, today: date) -> float:
    if not item.deadline:
        return 0.15
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
