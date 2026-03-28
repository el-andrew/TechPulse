from __future__ import annotations

import unittest

from app.collectors.html import HTMLCollector
from app.parsers.filtering import is_actionable_opportunity
from app.parsers.models import CollectedItem


class FilteringTests(unittest.TestCase):
    def test_news_article_without_actionable_signal_is_rejected(self) -> None:
        item = CollectedItem(
            title="Apple announces new iPhone release date",
            description="A report on device launches and company strategy.",
            source_name="TechCabal",
            source_type="rss",
            source_url="https://techcabal.com/feed",
            link="https://techcabal.com/article",
            category_hint="news",
            africa_relevance_weight=0.9,
            category="Event",
        )
        self.assertFalse(is_actionable_opportunity(item))

    def test_training_html_item_is_kept(self) -> None:
        item = CollectedItem(
            title="Free certificate training for cloud engineers",
            description="Join the free training course and earn a certificate.",
            source_name="Google Skills",
            source_type="html",
            source_url="https://www.skills.google/catalog",
            link="https://www.skills.google/course_templates/123",
            category_hint="training",
            africa_relevance_weight=0.85,
            category="Training",
        )
        self.assertTrue(is_actionable_opportunity(item))


class GoogleSkillsPayloadTests(unittest.TestCase):
    def test_parse_google_skills_payload(self) -> None:
        html = """
        <html>
          <body>
            <ql-search-result-container
              pagedSearchResults='{&quot;searchResults&quot;:[{&quot;title&quot;:&quot;Intro to Cloud&quot;,&quot;description&quot;:&quot;Free cloud training&quot;,&quot;path&quot;:&quot;/course_templates/123&quot;,&quot;duration&quot;:&quot;45 minutes&quot;,&quot;level&quot;:&quot;introductory&quot;,&quot;credentialType&quot;:&quot;skill_badge&quot;}]}'>
            </ql-search-result-container>
          </body>
        </html>
        """
        results = HTMLCollector.parse_google_skills_payload(html)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Intro to Cloud")
        self.assertEqual(results[0]["path"], "/course_templates/123")


if __name__ == "__main__":
    unittest.main()
