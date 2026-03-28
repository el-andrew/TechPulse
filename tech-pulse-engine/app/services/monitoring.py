from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Opportunity, PipelineRun, SourceRun


STATUS_SEVERITY = {
    "failed": 0,
    "partial_success": 1,
    "running": 2,
    "success": 3,
}


def build_dashboard_snapshot(
    session: Session,
    *,
    recent_runs_limit: int = 10,
    recent_opportunities_limit: int = 12,
) -> dict[str, object]:
    total_opportunities = _count(session, Opportunity)
    total_drafts = _count(session, Opportunity, Opportunity.status == "draft")
    total_approved = _count(session, Opportunity, Opportunity.status == "approved")
    total_posted = _count(session, Opportunity, Opportunity.status == "posted")

    recent_runs = session.execute(
        select(PipelineRun).order_by(PipelineRun.started_at.desc(), PipelineRun.id.desc()).limit(recent_runs_limit)
    ).scalars().all()
    latest_run = recent_runs[0] if recent_runs else None

    recent_opportunities = session.execute(
        select(Opportunity).order_by(Opportunity.date_found.desc(), Opportunity.id.desc()).limit(recent_opportunities_limit)
    ).scalars().all()
    source_runs = session.execute(
        select(SourceRun).order_by(SourceRun.started_at.desc(), SourceRun.id.desc())
    ).scalars().all()

    category_breakdown = _group_counts(session, Opportunity.category)
    status_breakdown = _group_counts(session, Opportunity.status)
    source_health = _build_source_health(source_runs)
    source_alerts = [row for row in source_health if row["status"] in {"failed", "partial_success"}][:6]

    successful_runs = sum(1 for run in recent_runs if run.status in {"success", "partial_success"})
    run_success_rate = round((successful_runs / len(recent_runs)) * 100, 1) if recent_runs else 0.0
    healthy_sources = sum(1 for item in source_health if item["status"] == "success")

    return {
        "generated_at": _serialize_datetime(datetime.utcnow()),
        "metrics": {
            "opportunities_total": total_opportunities,
            "drafts_total": total_drafts,
            "approved_total": total_approved,
            "posted_total": total_posted,
            "latest_run_saved": latest_run.total_items_saved if latest_run else 0,
            "latest_run_qualified": latest_run.total_items_qualified if latest_run else 0,
            "pipeline_success_rate": run_success_rate,
            "healthy_sources": healthy_sources,
            "sources_total": len(source_health),
        },
        "last_run": _serialize_pipeline_run(latest_run),
        "recent_runs": [_serialize_pipeline_run(run) for run in recent_runs],
        "run_series": _build_run_series(recent_runs),
        "category_breakdown": _with_percentages(category_breakdown),
        "status_breakdown": _with_percentages(status_breakdown),
        "source_health": source_health,
        "source_alerts": source_alerts,
        "recent_opportunities": [_serialize_opportunity(item) for item in recent_opportunities],
    }


def _count(session: Session, model, *conditions) -> int:
    query = select(func.count()).select_from(model)
    for condition in conditions:
        query = query.where(condition)
    value = session.execute(query).scalar_one()
    return int(value or 0)


def _group_counts(session: Session, column) -> list[dict[str, object]]:
    rows = session.execute(
        select(column, func.count(Opportunity.id))
        .select_from(Opportunity)
        .group_by(column)
        .order_by(func.count(Opportunity.id).desc(), column.asc())
    )
    return [{"label": label, "count": count} for label, count in rows]


def _build_source_health(source_runs: list[SourceRun]) -> list[dict[str, object]]:
    histories: dict[str, list[SourceRun]] = defaultdict(list)
    latest_by_source: dict[str, SourceRun] = {}
    for row in source_runs:
        histories[row.source_name].append(row)
        latest_by_source.setdefault(row.source_name, row)

    health_rows: list[dict[str, object]] = []
    for source_name, latest in latest_by_source.items():
        history = histories[source_name][:12]
        success_count = sum(1 for row in history if row.status == "success")
        avg_duration = _average([row.duration_ms for row in history if row.duration_ms is not None])
        avg_saved = _average([row.items_saved for row in history])
        latest_status = latest.status
        if latest_status == "success" and success_count < len(history):
            latest_status = "partial_success"

        health_rows.append(
            {
                "source_name": source_name,
                "source_type": latest.source_type,
                "strategy": latest.strategy or "generic",
                "status": latest_status,
                "success_rate": round((success_count / len(history)) * 100, 1) if history else 0.0,
                "last_collected": latest.items_collected,
                "last_saved": latest.items_saved,
                "average_saved": round(avg_saved, 1),
                "average_duration_ms": int(avg_duration),
                "last_completed_at": _serialize_datetime(latest.completed_at),
                "source_url": latest.source_url,
                "error_message": latest.error_message,
            }
        )

    health_rows.sort(key=lambda item: (STATUS_SEVERITY.get(str(item["status"]), 99), str(item["source_name"]).lower()))
    return health_rows


def _build_run_series(recent_runs: list[PipelineRun]) -> list[dict[str, object]]:
    ordered = list(reversed(recent_runs))
    max_saved = max((run.total_items_saved for run in ordered), default=1)
    series: list[dict[str, object]] = []
    for run in ordered:
        saved = run.total_items_saved
        bar_width = 12 if max_saved <= 0 else max(12, int((saved / max_saved) * 100))
        series.append(
            {
                "label": run.started_at.strftime("%m-%d %H:%M"),
                "saved": saved,
                "qualified": run.total_items_qualified,
                "failed_sources": run.sources_failed,
                "status": run.status,
                "bar_width": bar_width,
            }
        )
    return series


def _serialize_pipeline_run(run: PipelineRun | None) -> dict[str, object] | None:
    if run is None:
        return None
    return {
        "id": run.id,
        "trigger": run.trigger,
        "status": run.status,
        "total_sources": run.total_sources,
        "sources_succeeded": run.sources_succeeded,
        "sources_failed": run.sources_failed,
        "total_items_collected": run.total_items_collected,
        "total_items_qualified": run.total_items_qualified,
        "total_items_saved": run.total_items_saved,
        "digest_path": run.digest_path,
        "error_message": run.error_message,
        "started_at": _serialize_datetime(run.started_at),
        "completed_at": _serialize_datetime(run.completed_at),
        "duration_ms": run.duration_ms,
    }


def _serialize_opportunity(item: Opportunity) -> dict[str, object]:
    return {
        "id": item.id,
        "title": item.title,
        "category": item.category,
        "source_name": item.source_name,
        "status": item.status,
        "link": item.link,
        "total_score": item.total_score,
        "deadline": item.deadline.isoformat() if item.deadline else None,
        "date_found": _serialize_datetime(item.date_found),
    }


def _with_percentages(items: list[dict[str, object]]) -> list[dict[str, object]]:
    total = sum(int(item["count"]) for item in items) or 1
    return [
        {**item, "percentage": round((int(item["count"]) / total) * 100, 1)}
        for item in items
    ]


def _average(values: list[int | float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value else None
