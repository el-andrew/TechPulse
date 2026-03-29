from __future__ import annotations

import json
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup, Tag

from app.collectors.base import BaseCollector
from app.parsers.dates import parse_date_text
from app.parsers.models import CollectedItem


DEFAULT_SELECTORS = {
    "container": ["article", ".card", ".post", ".entry", ".views-row", "li"],
    "title": ["h1 a", "h2 a", "h3 a", ".title a", "a"],
    "link": ["h1 a", "h2 a", "h3 a", "a"],
    "description": ["p", ".summary", ".description", ".card-text"],
    "date": ["time", ".date", ".deadline", ".event-date"],
}

STRATEGY_MAP = {
    "google_skills_catalog": "_collect_google_skills_catalog",
    "sitemap_detail": "_collect_sitemap_detail",
    "microsoft_events": "_collect_microsoft_events",
    "isc2_programs": "_collect_isc2_programs",
    "single_page_detail": "_collect_single_page_detail",
    "generic": "_collect_generic",
}


class HTMLCollector(BaseCollector):
    def collect(self) -> list[CollectedItem]:
        strategy = (self.source.strategy or "generic").lower()
        collector_name = STRATEGY_MAP.get(strategy, "_collect_generic")
        self.logger.info("Fetching HTML source with strategy=%s: %s", strategy, self.source.url)
        items = getattr(self, collector_name)()
        deduped = self._dedupe_items(items)
        self.logger.info("Collected %s HTML entries", len(deduped))
        return deduped

    def _collect_google_skills_catalog(self) -> list[CollectedItem]:
        html = self._fetch_text(self.source.url)
        if not html:
            return []

        results = self.parse_google_skills_payload(html)
        max_items = int(self.source.options.get("max_items", 12))
        items: list[CollectedItem] = []
        for result in results[:max_items]:
            title = str(result.get("title", "")).strip()
            path = str(result.get("path", "")).strip()
            description = str(result.get("description", "")).strip()
            if not title or not path:
                continue

            detail_bits = [description]
            if result.get("duration"):
                detail_bits.append(f"Duration: {result['duration']}.")
            if result.get("level"):
                detail_bits.append(f"Level: {result['level']}.")
            if result.get("credentialType"):
                detail_bits.append(f"Credential: {result['credentialType']}.")

            items.append(
                self._build_item(
                    title=title,
                    description=" ".join(bit for bit in detail_bits if bit).strip(),
                    link=urljoin(self.source.url, path),
                )
            )
        return items

    def _collect_sitemap_detail(self) -> list[CollectedItem]:
        sitemap_url = str(self.source.options.get("sitemap_url", self.source.url))
        include_patterns = [str(item) for item in self.source.options.get("include_patterns", [])]
        exclude_patterns = [str(item) for item in self.source.options.get("exclude_patterns", [])]
        max_items = int(self.source.options.get("max_items", 12))

        urls = self._extract_sitemap_urls(sitemap_url, include_patterns, exclude_patterns)
        items: list[CollectedItem] = []
        for url in urls[:max_items]:
            item = self._extract_meta_item(url)
            if item:
                items.append(item)
        return items

    def _collect_microsoft_events(self) -> list[CollectedItem]:
        seed_urls = [str(url) for url in self.source.options.get("seed_urls", [])]
        items: list[CollectedItem] = []
        for url in seed_urls:
            item = self._extract_meta_item(url)
            if item:
                items.append(item)
        return items

    def _collect_isc2_programs(self) -> list[CollectedItem]:
        seed_urls = [str(url) for url in self.source.options.get("seed_urls", [])]
        max_items = int(self.source.options.get("max_items", 10))
        items: list[CollectedItem] = []

        for url in seed_urls:
            soup = self._fetch_soup(url)
            if not soup:
                continue
            if "online-instructor-led" in url:
                items.extend(self._collect_isc2_training_items(soup, url))
            else:
                items.extend(self._collect_isc2_event_items(soup, url))

        return items[:max_items]

    def _collect_single_page_detail(self) -> list[CollectedItem]:
        item = self._extract_meta_item(self.source.url)
        return [item] if item else []

    def _collect_generic(self) -> list[CollectedItem]:
        soup = self._fetch_soup(self.source.url)
        if not soup:
            return []
        containers = self._find_containers(soup)
        max_items = int(self.source.options.get("max_items", 30))
        include_patterns = [str(item).lower() for item in self.source.options.get("include_patterns", [])]
        exclude_patterns = [str(item).lower() for item in self.source.options.get("exclude_patterns", [])]
        text_include_patterns = [str(item).lower() for item in self.source.options.get("text_include_patterns", [])]
        items: list[CollectedItem] = []
        for container in containers[:100]:
            title = self._extract_text(container, "title")
            link = self._extract_link(container)
            if not title or not link:
                continue
            description = self._extract_text(container, "description")
            date_text = self._extract_text(container, "date")
            link_lower = link.lower()
            text_blob = f"{title} {description}".lower()
            if include_patterns and not any(pattern in link_lower for pattern in include_patterns):
                continue
            if exclude_patterns and any(pattern in link_lower for pattern in exclude_patterns):
                continue
            if text_include_patterns and not any(pattern in text_blob for pattern in text_include_patterns):
                continue
            items.append(
                self._build_item(
                    title=title,
                    description=description,
                    link=link,
                    deadline_text=date_text or description,
                    event_date_text=date_text,
                )
            )
            if len(items) >= max_items:
                break
        return items

    def _collect_isc2_training_items(self, soup: BeautifulSoup, page_url: str) -> list[CollectedItem]:
        seen: set[str] = set()
        detail_urls: list[str] = []
        for anchor in soup.find_all("a", href=True):
            href = urljoin(page_url, str(anchor.get("href")).strip())
            if "/training/online-instructor-led/" not in href or href == page_url:
                continue
            if href in seen:
                continue
            seen.add(href)
            detail_urls.append(href)

        items: list[CollectedItem] = []
        for url in detail_urls[:6]:
            item = self._extract_meta_item(url)
            if item:
                items.append(item)
        return items

    def _collect_isc2_event_items(self, soup: BeautifulSoup, page_url: str) -> list[CollectedItem]:
        items: list[CollectedItem] = []
        seen: set[str] = set()
        for anchor in soup.find_all("a", href=True):
            text = self._anchor_text(anchor)
            href = urljoin(page_url, str(anchor.get("href")).strip())
            text_lower = text.lower()
            if not text:
                continue
            if "event" not in text_lower and "workshop" not in text_lower:
                continue
            if href in seen:
                continue
            seen.add(href)
            items.append(
                self._build_item(
                    title=self._isc2_anchor_title(text),
                    description=text,
                    link=href,
                    deadline_text=text,
                    event_date_text=text,
                )
            )
        return items

    def _extract_meta_item(self, url: str) -> CollectedItem | None:
        soup = self._fetch_soup(url)
        if not soup:
            return None

        title = (
            self._meta_content(soup, "og:title")
            or self._title_tag_text(soup)
            or self._heading_text(soup)
            or self._slug_to_title(url)
        )
        description = self._meta_content(soup, "og:description") or self._meta_content(soup, "description")

        if self._is_generic_title(title):
            title = self._slug_to_title(url)
        else:
            title = self._clean_title(title)

        if not description or self._is_generic_description(description):
            description = self._fallback_description(title, url)

        return self._build_item(
            title=title,
            description=description,
            link=url,
            deadline_text=description,
            event_date_text=f"{title} {description}",
        )

    def _extract_sitemap_urls(
        self,
        sitemap_url: str,
        include_patterns: list[str],
        exclude_patterns: list[str],
    ) -> list[str]:
        xml_text = self._fetch_text(sitemap_url)
        if not xml_text:
            return []

        matches = re.findall(r"<loc>(.*?)</loc>", xml_text)
        seen: set[str] = set()
        urls: list[str] = []
        for raw_url in matches:
            url = self._normalize_seed_url(raw_url)
            if include_patterns and not any(pattern in url for pattern in include_patterns):
                continue
            if any(pattern in url for pattern in exclude_patterns):
                continue
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def _find_containers(self, soup: BeautifulSoup) -> list[Tag]:
        selectors = self._selectors("container")
        found: list[Tag] = []
        for selector in selectors:
            found = [tag for tag in soup.select(selector) if isinstance(tag, Tag)]
            if found:
                break
        return found

    def _extract_text(self, container: Tag, key: str) -> str:
        for selector in self._selectors(key):
            match = container.select_one(selector)
            if not match:
                continue
            text = match.get_text(" ", strip=True)
            if text:
                return text
        return ""

    def _extract_link(self, container: Tag) -> str:
        for selector in self._selectors("link"):
            match = container.select_one(selector)
            if not match:
                continue
            href = match.get("href")
            if href:
                return urljoin(self.source.url, href.strip())
        anchor = container.find("a", href=True)
        if anchor:
            return urljoin(self.source.url, str(anchor.get("href")).strip())
        return ""

    def _selectors(self, key: str) -> list[str]:
        custom = self.source.selectors.get(key, [])
        return custom or DEFAULT_SELECTORS[key]

    def _request(self, url: str) -> requests.Response | None:
        try:
            response = self.http.get(url, timeout=self.settings.request_timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            message = f"Failed to fetch {url}: {exc}"
            self._record_error(message)
            self.logger.error(message)
            return None
        return response

    def _fetch_text(self, url: str) -> str | None:
        response = self._request(url)
        return response.text if response else None

    def _fetch_soup(self, url: str) -> BeautifulSoup | None:
        text = self._fetch_text(url)
        if not text:
            return None
        return BeautifulSoup(text, "html.parser")

    def _build_item(
        self,
        title: str,
        description: str,
        link: str,
        deadline_text: str | None = None,
        event_date_text: str | None = None,
    ) -> CollectedItem:
        normalized_link = self._normalize_seed_url(link)
        cleaned_title = self._clean_title(title)
        cleaned_description = " ".join(description.split())
        return CollectedItem(
            title=cleaned_title,
            description=cleaned_description,
            deadline=parse_date_text(deadline_text or cleaned_description),
            event_date=parse_date_text(event_date_text or cleaned_description),
            **self._base_item_fields(normalized_link),
        )

    def _dedupe_items(self, items: list[CollectedItem]) -> list[CollectedItem]:
        deduped: list[CollectedItem] = []
        seen_links: set[str] = set()
        for item in items:
            if not item.title or not item.link:
                continue
            if item.link in seen_links:
                continue
            seen_links.add(item.link)
            deduped.append(item)
        return deduped

    def _normalize_seed_url(self, url: str) -> str:
        split = urlsplit(url.strip())
        path = split.path.rstrip("/") or "/"
        return urlunsplit((split.scheme, split.netloc, path, "", ""))

    def _meta_content(self, soup: BeautifulSoup, key: str) -> str:
        node = soup.find("meta", attrs={"name": key}) or soup.find("meta", attrs={"property": key})
        return str(node.get("content", "")).strip() if node else ""

    def _title_tag_text(self, soup: BeautifulSoup) -> str:
        return soup.title.get_text(" ", strip=True) if soup.title else ""

    def _heading_text(self, soup: BeautifulSoup) -> str:
        heading = soup.find("h1")
        return heading.get_text(" ", strip=True) if heading else ""

    def _clean_title(self, title: str) -> str:
        cleaned = title.replace("’", "'").strip()
        for separator in ("|", " - "):
            if separator in cleaned:
                cleaned = cleaned.split(separator)[0].strip()
        return cleaned

    def _is_generic_title(self, title: str) -> bool:
        if not title:
            return True
        generic_titles = {str(value).lower() for value in self.source.options.get("generic_titles", [])}
        title_lower = title.lower().strip()
        return title_lower in generic_titles

    def _is_generic_description(self, description: str) -> bool:
        generic_descriptions = {
            str(value).lower() for value in self.source.options.get("generic_descriptions", [])
        }
        return description.lower().strip() in generic_descriptions

    def _fallback_description(self, title: str, url: str) -> str:
        domain = urlsplit(url).netloc.replace("www.", "")
        return f"{title} from {domain}. See the source page for full program details."

    def _slug_to_title(self, url: str) -> str:
        slug = urlsplit(url).path.rstrip("/").split("/")[-1]
        tokens = re.sub(r"[-_]+", " ", slug).split()
        acronym_map = {
            "ai": "AI",
            "api": "API",
            "aks": "AKS",
            "cla": "CLA",
            "llms": "LLMs",
            "lfx": "LFX",
            "sd": "SD",
            "ssl": "SSL",
            "tls": "TLS",
            "wan": "WAN",
            "wasmcloud": "WasmCloud",
            "webassembly": "WebAssembly",
            "ajira": "Ajira",
            "costech": "COSTECH",
            "veta": "VETA",
        }
        code_prefixes = ("lfs", "lfd", "lfc", "lfel", "lfws", "kcna", "cka", "ckad", "cks")
        small_words = {"and", "for", "in", "of", "on", "the", "to", "with"}

        formatted: list[str] = []
        for index, token in enumerate(tokens):
            lowered = token.lower()
            if lowered in acronym_map:
                formatted.append(acronym_map[lowered])
                continue
            code_match = re.fullmatch(r"([a-z]+)(\d+[a-z]*)", lowered)
            if code_match and code_match.group(1) in code_prefixes:
                formatted.append(f"{code_match.group(1).upper()}{code_match.group(2).upper()}")
                continue
            if lowered in small_words and index > 0:
                formatted.append(lowered)
                continue
            formatted.append(lowered.capitalize())
        return " ".join(formatted)

    def _anchor_text(self, anchor: Tag) -> str:
        return " ".join(anchor.get_text(" ", strip=True).split())

    def _isc2_anchor_title(self, text: str) -> str:
        match = re.match(r"^(Event|Workshop)\s+(.*?)(?:\s+Event Type|\s+Event Location|\s+Date\s+)", text)
        if match:
            return match.group(2).strip()
        return text[:120]

    @staticmethod
    def parse_google_skills_payload(html_text: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html_text, "html.parser")
        container = soup.find("ql-search-result-container")
        if not container:
            return []
        raw_payload = container.get("pagedsearchresults") or container.get("pagedSearchResults")
        if not raw_payload:
            return []
        payload = json.loads(unescape(str(raw_payload)))
        results = payload.get("searchResults", [])
        return [result for result in results if isinstance(result, dict)]
