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
            response = self.http.get(self.source.url, timeout=self.settings.request_timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            message = f"Failed to fetch {self.source.url}: {exc}"
            self._record_error(message)
            self.logger.error(message)
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
            link = (entry.get("link") or self.source.url).strip()
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
                    deadline=parse_date_text(summary),
                    event_date=event_date,
                    **self._base_item_fields(link),
                )
            )
        self.logger.info("Collected %s RSS entries", len(items))
        if getattr(feed, "bozo", False):
            message = f"Feed parsing reported malformed input for {self.source.url}"
            self._record_error(message)
            self.logger.warning(message)
        return items

    @staticmethod
    def _read_content_value(content: object) -> str:
        if isinstance(content, list) and content:
            first = content[0]
            if isinstance(first, dict):
                return str(first.get("value", ""))
        return ""
