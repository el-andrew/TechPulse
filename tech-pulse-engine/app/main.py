from __future__ import annotations

import argparse
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config.settings import DEFAULT_SOURCES_PATH, load_settings
from app.dashboard.app import serve_dashboard
from app.db.session import create_session_factory
from app.notify.logging import configure_logging
from app.services.pipeline import PipelineService


def run_daily_command(sources_path: Path = DEFAULT_SOURCES_PATH, trigger: str = "manual") -> int:
    settings = load_settings()
    configure_logging(settings.log_level)
    session_factory = create_session_factory(settings.database_url)
    service = PipelineService(settings, session_factory, sources_path)
    summary = service.run_daily(trigger=trigger)
    print(
        f"Run {summary.run_id} finished with status={summary.status}. "
        f"Processed {summary.processed_items}, qualified {summary.qualified_items}, "
        f"saved {summary.saved_items}, failed_sources {summary.failed_sources}. "
        f"Digest: {summary.digest_path}"
    )
    return 0 if summary.status in {"success", "partial_success"} else 1


def schedule_daily(sources_path: Path = DEFAULT_SOURCES_PATH) -> None:
    settings = load_settings()
    configure_logging(settings.log_level)
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_daily_command,
        trigger="cron",
        hour=settings.scheduler_hour,
        minute=settings.scheduler_minute,
        kwargs={"sources_path": sources_path, "trigger": "scheduled"},
        id="tech-pulse-daily",
        replace_existing=True,
    )
    print(
        f"Scheduler running daily at {settings.scheduler_hour:02d}:{settings.scheduler_minute:02d} "
        f"using {settings.database_url}"
    )
    scheduler.start()


def build_parser() -> argparse.ArgumentParser:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="tech-pulse-engine automation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run-daily", help="Run the daily collection pipeline")
    run_parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES_PATH)
    run_parser.add_argument("--trigger", default="manual")

    schedule_parser = subparsers.add_parser("schedule-daily", help="Run the scheduler loop")
    schedule_parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES_PATH)

    dashboard_parser = subparsers.add_parser("serve-dashboard", help="Serve the operations dashboard")
    dashboard_parser.add_argument("--host", default=settings.dashboard_host)
    dashboard_parser.add_argument("--port", type=int, default=settings.dashboard_port)

    subparsers.add_parser("init-db", help="Initialize the configured database")
    return parser


def init_db() -> int:
    settings = load_settings()
    configure_logging(settings.log_level)
    create_session_factory(settings.database_url)
    print(f"Database initialized at {settings.database_url}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "run-daily":
        return run_daily_command(args.sources, trigger=args.trigger)
    if args.command == "schedule-daily":
        schedule_daily(args.sources)
        return 0
    if args.command == "serve-dashboard":
        settings = load_settings()
        configure_logging(settings.log_level)
        serve_dashboard(settings, host=args.host, port=args.port)
        return 0
    if args.command == "init-db":
        return init_db()
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
