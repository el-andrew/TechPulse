from __future__ import annotations

from app.parsers.models import CollectedItem


ACTIONABLE_KEYWORDS = {
    "apply",
    "application",
    "register",
    "sign up",
    "join",
    "cohort",
    "deadline",
    "scholarship",
    "grant",
    "funding",
    "stipend",
    "accelerator",
    "bootcamp",
    "training",
    "course",
    "certificate",
    "certification",
    "webinar",
    "workshop",
    "summit",
    "event",
    "free",
    "fellowship",
    "program",
    "call for",
    "open call",
}

NEWSY_SOURCE_HINTS = {"news", "startup"}


def is_actionable_opportunity(item: CollectedItem) -> bool:
    text = f"{item.title} {item.description}".lower()
    signal_count = sum(1 for keyword in ACTIONABLE_KEYWORDS if keyword in text)

    if item.source_type == "html":
        return signal_count >= 1 or (item.category or "") in {"Training", "Event"}

    if item.source_type == "rss":
        if item.category in {"Training", "Scholarship", "Job"}:
            return signal_count >= 1
        if item.category in {"Accelerator", "Grant", "Event"}:
            return signal_count >= 2 or "deadline" in text
        if item.category_hint.lower() in NEWSY_SOURCE_HINTS:
            return signal_count >= 2
    return signal_count >= 1
