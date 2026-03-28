from __future__ import annotations

from email.utils import parsedate_to_datetime

import feedparser
import requests

from app.collectors.base import BaseCollector
from app.parsers.dates import parse_date_text
from app.parsers.models import CollectedItem


class RSSCollector(BaseCollector):
    def collect(self) -> list[CollectedItem]:
        self.logger.info("Fetching RSS feed: %s", self.source.url)
        try:
            response = requests.get(
                self.source.url,
                headers={"User-Agent": self.settings.user_agent},
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            self.logger.error("Failed to fetch %s: %s", self.source.url, exc)
            return []

        feed = feedparser.parse(response.content)
        items: list[CollectedItem] = []
        entries = getattr(feed, "entries", []) or []
        max_entries = int(self.source.options.get("max_entries", 50))
        for entry in entries[:max_entries]:
            title = (entry.get("title") or "").strip()
            if not title:
                continue
            summary = (
                entry.get("summary")
                or entry.get("description")
                or self._read_content_value(entry.get("content"))
                or ""
            ).strip()
            link = (entry.get("link") or "").strip()
            published = entry.get("published") or entry.get("updated") or ""
            event_date = parse_date_text(published) if published else None
            if not event_date and published:
                try:
                    event_date = parsedate_to_datetime(published).date()
                except (TypeError, ValueError, IndexError):
                    event_date = None

            items.append(
                CollectedItem(
                    title=title,
                    description=summary,
                    source_name=self.source.name,
                    source_type=self.source.type,
                    source_url=self.source.url,
                    link=link,
                    category_hint=self.source.category_hint,
                    africa_relevance_weight=self.source.africa_relevance_weight,
                    deadline=parse_date_text(summary),
                    event_date=event_date,
                )
            )
        self.logger.info("Collected %s RSS entries", len(items))
        if getattr(feed, "bozo", False):
            self.logger.warning("Feed parsing reported malformed input for %s", self.source.url)
        return items

    @staticmethod
    def _read_content_value(content: object) -> str:
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                return str(first.get("value", ""))
        return ""
