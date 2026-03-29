from __future__ import annotations

from typing import Any


def build_location_label(item: Any) -> str:
    if getattr(item, "location_text", None):
        return str(item.location_text)
    parts = [getattr(item, field, None) for field in ("city", "region", "country")]
    values = [str(part) for part in parts if part]
    return ", ".join(values) if values else "Not stated"


def build_scope_label(item: Any) -> str:
    scope = str(getattr(item, "audience_scope", "africa") or "africa").replace("_", " ")
    return scope.title()


def format_whatsapp_short(item: Any) -> str:
    deadline = f" Deadline: {item.deadline.isoformat()}." if getattr(item, "deadline", None) else ""
    location = build_location_label(item)
    return (
        f"[{getattr(item, 'category', 'Opportunity')}] {item.title} | {location} | "
        f"{getattr(item, 'issuer_name', None) or item.source_name}.{deadline} "
        f"{getattr(item, 'application_url', None) or item.link}"
    ).strip()


def format_whatsapp_detailed(item: Any) -> str:
    description = " ".join(str(item.description).split())[:320]
    deadline = item.deadline.isoformat() if getattr(item, "deadline", None) else "Not stated"
    event_date = item.event_date.isoformat() if getattr(item, "event_date", None) else "Not stated"
    issuer_name = getattr(item, "issuer_name", None) or item.source_name
    issuer_type = getattr(item, "issuer_type", None) or "Not stated"
    location = build_location_label(item)
    scope = build_scope_label(item)
    application_url = getattr(item, "application_url", None) or item.link
    return (
        f"{item.title}\n"
        f"Category: {getattr(item, 'category', 'Opportunity')}\n"
        f"Issuer: {issuer_name} ({issuer_type})\n"
        f"Location: {location}\n"
        f"Audience: {scope}\n"
        f"Deadline: {deadline}\n"
        f"Event Date: {event_date}\n"
        f"Why it matters: {description}\n"
        f"Apply: {application_url}"
    )


def format_whatsapp_channel(item: Any) -> str:
    description = " ".join(str(item.description).split())[:240]
    deadline = item.deadline.isoformat() if getattr(item, "deadline", None) else "Not stated"
    issuer_name = getattr(item, "issuer_name", None) or item.source_name
    location = build_location_label(item)
    scope = build_scope_label(item)
    application_url = getattr(item, "application_url", None) or item.link
    hashtag = "#TechPulseTanzania" if str(getattr(item, "country", "")).lower() == "tanzania" else "#TechPulseAfrica"
    return (
        f"{item.title}\n\n"
        f"What it is: {getattr(item, 'category', 'Opportunity')}\n"
        f"Who should care: {scope}\n"
        f"Where: {location}\n"
        f"Issuer: {issuer_name}\n"
        f"Deadline: {deadline}\n\n"
        f"{description}\n\n"
        f"Apply here: {application_url}\n"
        f"{hashtag}"
    )
