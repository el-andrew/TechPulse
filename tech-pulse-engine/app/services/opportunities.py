from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Opportunity
from app.formatters.whatsapp import (
    build_location_label,
    build_scope_label,
    format_whatsapp_channel,
    format_whatsapp_detailed,
    format_whatsapp_short,
)


VALID_STATUSES = {"draft", "approved", "posted"}


def get_opportunity(session: Session, opportunity_id: int) -> Opportunity | None:
    return session.get(Opportunity, opportunity_id)


def refresh_templates(opportunity: Opportunity) -> Opportunity:
    opportunity.whatsapp_short = format_whatsapp_short(opportunity)
    opportunity.whatsapp_detailed = format_whatsapp_detailed(opportunity)
    opportunity.whatsapp_channel = format_whatsapp_channel(opportunity)
    return opportunity


def set_status(opportunity: Opportunity, status: str) -> Opportunity:
    normalized = status.lower().strip()
    if normalized not in VALID_STATUSES:
        raise ValueError(f"Unsupported status: {status}")
    opportunity.status = normalized
    return opportunity


def serialize_opportunity_detail(opportunity: Opportunity) -> dict[str, object]:
    return {
        "id": opportunity.id,
        "title": opportunity.title,
        "description": opportunity.description,
        "category": opportunity.category,
        "source_name": opportunity.source_name,
        "link": opportunity.link,
        "application_url": opportunity.application_url or opportunity.link,
        "deadline": opportunity.deadline.isoformat() if opportunity.deadline else None,
        "event_date": opportunity.event_date.isoformat() if opportunity.event_date else None,
        "country": opportunity.country,
        "region": opportunity.region,
        "city": opportunity.city,
        "audience_scope": opportunity.audience_scope,
        "issuer_name": opportunity.issuer_name,
        "issuer_type": opportunity.issuer_type,
        "location_text": opportunity.location_text,
        "language": opportunity.language,
        "source_priority": opportunity.source_priority,
        "africa_score": opportunity.africa_score,
        "locality_score": opportunity.locality_score,
        "relevance_score": opportunity.relevance_score,
        "total_score": opportunity.total_score,
        "status": opportunity.status,
        "whatsapp_short": opportunity.whatsapp_short,
        "whatsapp_detailed": opportunity.whatsapp_detailed,
        "whatsapp_channel": opportunity.whatsapp_channel,
        "location_label": build_location_label(opportunity),
        "scope_label": build_scope_label(opportunity),
    }
