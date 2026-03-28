from __future__ import annotations

import unittest
from datetime import datetime, timedelta

from app.db.models import Opportunity, PipelineRun, SourceRun
from app.db.session import create_session_factory, session_scope
from app.services.monitoring import build_dashboard_snapshot


class MonitoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session_factory = create_session_factory("sqlite:///:memory:")
        now = datetime.utcnow()
        with session_scope(self.session_factory) as session:
            run_one = PipelineRun(
                trigger="scheduled",
                status="success",
                total_sources=2,
                sources_succeeded=2,
                sources_failed=0,
                total_items_collected=30,
                total_items_qualified=12,
                total_items_saved=8,
                started_at=now - timedelta(hours=3),
                completed_at=now - timedelta(hours=2, minutes=59),
                duration_ms=60000,
            )
            run_two = PipelineRun(
                trigger="manual",
                status="partial_success",
                total_sources=2,
                sources_succeeded=1,
                sources_failed=1,
                total_items_collected=25,
                total_items_qualified=10,
                total_items_saved=6,
                started_at=now - timedelta(hours=1),
                completed_at=now - timedelta(minutes=59),
                duration_ms=70000,
            )
            session.add_all([run_one, run_two])
            session.flush()

            session.add_all(
                [
                    SourceRun(
                        pipeline_run_id=run_one.id,
                        source_name="TechCabal",
                        source_type="rss",
                        source_url="https://techcabal.com/feed/",
                        strategy="generic",
                        status="success",
                        items_collected=10,
                        items_qualified=4,
                        items_saved=3,
                        started_at=now - timedelta(hours=3),
                        completed_at=now - timedelta(hours=2, minutes=59),
                        duration_ms=1200,
                    ),
                    SourceRun(
                        pipeline_run_id=run_two.id,
                        source_name="TechCabal",
                        source_type="rss",
                        source_url="https://techcabal.com/feed/",
                        strategy="generic",
                        status="failed",
                        items_collected=0,
                        items_qualified=0,
                        items_saved=0,
                        started_at=now - timedelta(hours=1),
                        completed_at=now - timedelta(minutes=59),
                        duration_ms=900,
                        error_message="timeout",
                    ),
                ]
            )

            session.add_all(
                [
                    Opportunity(
                        title="Africa Cloud Fellowship",
                        description="Training program",
                        category="Training",
                        source_name="TechCabal",
                        link="https://example.com/1",
                        africa_score=0.9,
                        relevance_score=0.8,
                        total_score=0.85,
                        status="draft",
                    ),
                    Opportunity(
                        title="Startup Demo Day",
                        description="Event program",
                        category="Event",
                        source_name="Disrupt Africa",
                        link="https://example.com/2",
                        africa_score=0.85,
                        relevance_score=0.7,
                        total_score=0.78,
                        status="approved",
                    ),
                ]
            )

    def test_build_dashboard_snapshot(self) -> None:
        with session_scope(self.session_factory) as session:
            snapshot = build_dashboard_snapshot(session)

        self.assertEqual(snapshot["metrics"]["opportunities_total"], 2)
        self.assertEqual(snapshot["metrics"]["drafts_total"], 1)
        self.assertEqual(snapshot["last_run"]["status"], "partial_success")
        self.assertEqual(snapshot["source_health"][0]["source_name"], "TechCabal")
        self.assertEqual(snapshot["source_health"][0]["status"], "failed")
        self.assertEqual(snapshot["source_alerts"][0]["error_message"], "timeout")
        self.assertEqual(snapshot["recent_opportunities"][0]["title"], "Startup Demo Day")
        self.assertEqual(snapshot["run_series"][-1]["saved"], 6)


if __name__ == "__main__":
    unittest.main()
