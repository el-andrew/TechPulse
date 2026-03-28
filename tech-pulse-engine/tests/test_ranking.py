from __future__ import annotations

import unittest
from datetime import date, timedelta

from app.parsers.models import CollectedItem
from app.rankers.scoring import apply_ranking


class RankingTests(unittest.TestCase):
    def test_urgent_deadline_scores_higher(self) -> None:
        today = date(2026, 3, 3)
        urgent = CollectedItem(
            title="Pan-African grant with funding support",
            description="Funding for startups across Africa",
            source_name="Grant Source",
            source_type="rss",
            source_url="https://example.com/feed",
            link="https://example.com/grant-urgent",
            category_hint="grant",
            africa_relevance_weight=0.9,
            deadline=today + timedelta(days=2),
        )
        later = CollectedItem(
            title="Pan-African grant with funding support",
            description="Funding for startups across Africa",
            source_name="Grant Source",
            source_type="rss",
            source_url="https://example.com/feed",
            link="https://example.com/grant-later",
            category_hint="grant",
            africa_relevance_weight=0.9,
            deadline=today + timedelta(days=20),
        )
        apply_ranking(urgent, today=today)
        apply_ranking(later, today=today)
        self.assertGreater(urgent.total_score, later.total_score)

    def test_keyword_bonus_improves_relevance_score(self) -> None:
        today = date(2026, 3, 3)
        boosted = CollectedItem(
            title="Free certificate training for African engineers",
            description="A free course with certificate for Africa-based learners",
            source_name="Training Source",
            source_type="html",
            source_url="https://example.com",
            link="https://example.com/boosted",
            category_hint="training",
            africa_relevance_weight=0.8,
        )
        baseline = CollectedItem(
            title="Training for engineers",
            description="Course for software engineers",
            source_name="Training Source",
            source_type="html",
            source_url="https://example.com",
            link="https://example.com/baseline",
            category_hint="training",
            africa_relevance_weight=0.8,
        )
        apply_ranking(boosted, today=today)
        apply_ranking(baseline, today=today)
        self.assertGreater(boosted.relevance_score, baseline.relevance_score)
        self.assertGreater(boosted.total_score, baseline.total_score)


if __name__ == "__main__":
    unittest.main()
