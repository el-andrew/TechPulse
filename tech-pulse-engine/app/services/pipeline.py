from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.collectors.html import HTMLCollector
from app.collectors.rss import RSSCollector
from app.config.settings import DEFAULT_SOURCES_PATH, Settings, load_sources
from app.db.models import Opportunity, PipelineRun, SourceRun
from app.db.session import session_scope
from app.formatters.whatsapp import format_whatsapp_detailed, format_whatsapp_short
from app.parsers.classifier import classify_item
from app.parsers.filtering import is_actionable_opportunity
from app.parsers.models import CollectedItem, SourceConfig
from app.rankers.dedup import Deduplicator, canonicalize_link
from app.rankers.scoring import apply_ranking


COLLECTOR_MAP = {
    "rss": RSSCollector,
    "html": HTMLCollector,
}

logger = logging.getLogger("tech_pulse.pipeline")


@dataclass(slots=True)
class PipelineExecutionSummary:
    run_id: int
    status: str
    processed_items: int
    qualified_items: int
    saved_items: int
    failed_sources: int
    total_sources: int
    digest_path: Path
    error_message: str | None = None


class PipelineService:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        sources_path: Path | None = None,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.sources_path = sources_path or DEFAULT_SOURCES_PATH
        self.deduplicator = Deduplicator()

    def run_daily(self, trigger: str = "manual") -> PipelineExecutionSummary:
        sources = load_sources(self.sources_path)
        started_at = _utcnow()

        with session_scope(self.session_factory) as session:
            pipeline_run = PipelineRun(
                trigger=trigger,
                status="running",
                started_at=started_at,
                total_sources=len(sources),
            )
            session.add(pipeline_run)
            session.flush()

            source_runs: dict[str, SourceRun] = {}
            processed_items = 0
            qualified_items = 0
            failed_sources = 0
            candidate_items: list[CollectedItem] = []

            try:
                existing = session.execute(select(Opportunity)).scalars().all()

                for source in sources:
                    source_run = self._start_source_run(session, pipeline_run.id, source)
                    source_runs[source.name] = source_run
                    try:
                        raw_items = self._collect_source(source)
                        processed_items += len(raw_items)
                        source_run.items_collected = len(raw_items)

                        qualified = self._qualify_items(raw_items)
                        qualified_items += len(qualified)
                        source_run.items_qualified = len(qualified)
                        candidate_items.extend(qualified)
                        source_run.status = "success"
                    except Exception as exc:
                        failed_sources += 1
                        source_run.status = "failed"
                        source_run.error_message = _trim_error(exc)
                        logger.exception("Source processing failed for %s", source.name)
                    finally:
                        self._finish_source_run(session, source_run)

                unique_items = self.deduplicator.filter_new(candidate_items, existing)
                saved = self._persist_items(session, unique_items)
                saved_by_source = Counter(item.source_name for item in unique_items)
                for source_name, source_run in source_runs.items():
                    source_run.items_saved = saved_by_source.get(source_name, 0)

                digest_path = self._write_daily_digest(saved)
                completed_at = _utcnow()
                pipeline_run.sources_failed = failed_sources
                pipeline_run.sources_succeeded = len(sources) - failed_sources
                pipeline_run.total_items_collected = processed_items
                pipeline_run.total_items_qualified = qualified_items
                pipeline_run.total_items_saved = len(saved)
                pipeline_run.digest_path = str(digest_path)
                pipeline_run.completed_at = completed_at
                pipeline_run.duration_ms = _duration_ms(started_at, completed_at)
                pipeline_run.status = "partial_success" if failed_sources else "success"
                session.flush()

                return PipelineExecutionSummary(
                    run_id=pipeline_run.id,
                    status=pipeline_run.status,
                    processed_items=processed_items,
                    qualified_items=qualified_items,
                    saved_items=len(saved),
                    failed_sources=failed_sources,
                    total_sources=len(sources),
                    digest_path=digest_path,
                )
            except Exception as exc:
                completed_at = _utcnow()
                for source_run in source_runs.values():
                    if source_run.status == "running":
                        source_run.status = "failed"
                        source_run.error_message = _trim_error(exc)
                        self._finish_source_run(session, source_run)

                pipeline_run.status = "failed"
                pipeline_run.error_message = _trim_error(exc)
                pipeline_run.sources_failed = max(failed_sources, len(sources) - pipeline_run.sources_succeeded)
                pipeline_run.total_items_collected = processed_items
                pipeline_run.total_items_qualified = qualified_items
                pipeline_run.completed_at = completed_at
                pipeline_run.duration_ms = _duration_ms(started_at, completed_at)
                logger.exception("Pipeline run failed")
                session.flush()

                return PipelineExecutionSummary(
                    run_id=pipeline_run.id,
                    status="failed",
                    processed_items=processed_items,
                    qualified_items=qualified_items,
                    saved_items=0,
                    failed_sources=pipeline_run.sources_failed,
                    total_sources=len(sources),
                    digest_path=self.settings.digest_path,
                    error_message=_trim_error(exc),
                )

    def _start_source_run(self, session: Session, pipeline_run_id: int, source: SourceConfig) -> SourceRun:
        source_run = SourceRun(
            pipeline_run_id=pipeline_run_id,
            source_name=source.name,
            source_type=source.type,
            source_url=source.url,
            strategy=source.strategy,
            status="running",
            started_at=_utcnow(),
        )
        session.add(source_run)
        session.flush()
        return source_run

    def _finish_source_run(self, session: Session, source_run: SourceRun) -> None:
        completed_at = _utcnow()
        source_run.completed_at = completed_at
        source_run.duration_ms = _duration_ms(source_run.started_at, completed_at)
        session.flush()

    def _collect_source(self, source: SourceConfig) -> list[CollectedItem]:
        collector_cls = COLLECTOR_MAP.get(source.type)
        if collector_cls is None:
            raise ValueError(f"Unsupported source type: {source.type}")
        collector = collector_cls(self.settings, source)
        return collector.collect()

    def _qualify_items(self, items: list[CollectedItem]) -> list[CollectedItem]:
        qualified: list[CollectedItem] = []
        for item in items:
            item.category = classify_item(item)
            if not item.category:
                continue

            if item.source_type == "html" and item.category == "Job":
                hint = item.category_hint.lower()
                if hint in {"training", "certification"}:
                    item.category = "Training"

            if not is_actionable_opportunity(item):
                continue

            ranked = apply_ranking(item, today=date.today())
            if ranked.africa_score < self.settings.min_africa_score:
                continue

            ranked.link = canonicalize_link(ranked.link)
            ranked.whatsapp_short = format_whatsapp_short(ranked)
            ranked.whatsapp_detailed = format_whatsapp_detailed(ranked)
            qualified.append(ranked)
        return qualified

    def _persist_items(self, session: Session, items: list[CollectedItem]) -> list[Opportunity]:
        saved: list[Opportunity] = []
        for item in sorted(items, key=lambda current: current.total_score, reverse=True):
            opportunity = Opportunity(
                title=item.title,
                description=item.description,
                category=item.category or "Event",
                source_name=item.source_name,
                link=item.link,
                deadline=item.deadline,
                event_date=item.event_date,
                africa_score=item.africa_score,
                relevance_score=item.relevance_score,
                total_score=item.total_score,
                status="draft",
                whatsapp_short=item.whatsapp_short,
                whatsapp_detailed=item.whatsapp_detailed,
            )
            session.add(opportunity)
            saved.append(opportunity)
        session.flush()
        return saved

    def _write_daily_digest(self, items: list[Opportunity]) -> Path:
        output_path = self.settings.digest_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        grouped: dict[str, list[Opportunity]] = defaultdict(list)
        for item in items:
            grouped[item.category].append(item)

        lines = ["# Daily Tech Pulse Digest", ""]
        if not items:
            lines.append("_No new opportunities found today._")
        else:
            for category in sorted(grouped):
                lines.append(f"## {category}")
                lines.append("")
                for item in sorted(grouped[category], key=lambda current: current.total_score, reverse=True):
                    deadline = item.deadline.isoformat() if item.deadline else "N/A"
                    lines.append(
                        f"- **{item.title}** ({item.source_name}) | Score: {item.total_score:.2f} | Deadline: {deadline}"
                    )
                    lines.append(f"  - {item.link}")
                lines.append("")

        output_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return output_path


def _utcnow() -> datetime:
    return datetime.utcnow()


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    return max(0, int((completed_at - started_at).total_seconds() * 1000))


def _trim_error(exc: Exception) -> str:
    return str(exc)[:2000]
