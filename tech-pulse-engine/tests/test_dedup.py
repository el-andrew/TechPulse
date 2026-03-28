from __future__ import annotations

import unittest

from app.parsers.models import CollectedItem
from app.rankers.dedup import Deduplicator, canonicalize_link


class DeduplicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.deduplicator = Deduplicator(similarity_threshold=0.9)

    def test_canonicalize_link_removes_tracking_parameters(self) -> None:
        raw = "https://example.com/opportunity/?utm_source=x&utm_campaign=y&id=42#fragment"
        self.assertEqual(canonicalize_link(raw), "https://example.com/opportunity?id=42")

    def test_filter_new_rejects_same_canonical_link(self) -> None:
        first = CollectedItem(
            title="Google Africa Developer Scholarship",
            description="Funding for developers in Africa",
            source_name="Source A",
            source_type="rss",
            source_url="https://example.com/feed",
            link="https://example.com/opportunity?utm_source=twitter",
            category_hint="scholarship",
            africa_relevance_weight=0.9,
        )
        second = CollectedItem(
            title="Google Africa Developer Scholarship 2026",
            description="Funding for developers in Africa",
            source_name="Source B",
            source_type="rss",
            source_url="https://example.com/feed",
            link="https://example.com/opportunity",
            category_hint="scholarship",
            africa_relevance_weight=0.9,
        )
        unique = self.deduplicator.filter_new([first, second], [])
        self.assertEqual(len(unique), 1)

    def test_filter_new_rejects_high_similarity_titles(self) -> None:
        first = CollectedItem(
            title="Cisco Networking Academy Free Certificate Program",
            description="Certificate program for African learners",
            source_name="Source A",
            source_type="html",
            source_url="https://example.com",
            link="https://example.com/cisco-free-certificate",
            category_hint="training",
            africa_relevance_weight=0.9,
        )
        second = CollectedItem(
            title="Cisco Networking Academy Free Certification Program",
            description="Certificate program for African learners",
            source_name="Source B",
            source_type="html",
            source_url="https://example.com",
            link="https://example.com/cisco-certification-program",
            category_hint="training",
            africa_relevance_weight=0.9,
        )
        unique = self.deduplicator.filter_new([first, second], [])
        self.assertEqual(len(unique), 1)


if __name__ == "__main__":
    unittest.main()
