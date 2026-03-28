from __future__ import annotations

from app.parsers.models import CollectedItem


def format_whatsapp_short(item: CollectedItem) -> str:
    deadline = f" Deadline: {item.deadline.isoformat()}." if item.deadline else ""
    return f"[{item.category}] {item.title} | {item.source_name}.{deadline} {item.link}".strip()


def format_whatsapp_detailed(item: CollectedItem) -> str:
    description = " ".join(item.description.split())[:280]
    deadline = item.deadline.isoformat() if item.deadline else "Not stated"
    event_date = item.event_date.isoformat() if item.event_date else "Not stated"
    return (
        f"{item.title}\n"
        f"Category: {item.category}\n"
        f"Source: {item.source_name}\n"
        f"Deadline: {deadline}\n"
        f"Event Date: {event_date}\n"
        f"Africa Score: {item.africa_score:.2f}\n"
        f"Relevance Score: {item.relevance_score:.2f}\n"
        f"Why it matters: {description}\n"
        f"Apply: {item.link}"
    )
