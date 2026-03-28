from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.db.models import Opportunity
from app.parsers.models import CollectedItem


TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}


def canonicalize_link(link: str) -> str:
    if not link:
        return ""
    split = urlsplit(link.strip())
    query = urlencode(
        [(key, value) for key, value in parse_qsl(split.query, keep_blank_values=True) if key not in TRACKING_PARAMS]
    )
    path = split.path.rstrip("/") or "/"
    return urlunsplit((split.scheme.lower(), split.netloc.lower(), path, query, ""))


def title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left.lower().strip(), right.lower().strip()).ratio()


@dataclass(slots=True)
class DuplicateCheckResult:
    is_duplicate: bool
    reason: str | None = None


class Deduplicator:
    def __init__(self, similarity_threshold: float = 0.92) -> None:
        self.similarity_threshold = similarity_threshold

    def check(self, candidate: CollectedItem, existing: Opportunity | CollectedItem) -> DuplicateCheckResult:
        candidate_link = canonicalize_link(candidate.link)
        existing_link = canonicalize_link(existing.link)
        if candidate_link and existing_link and candidate_link == existing_link:
            return DuplicateCheckResult(True, "canonical_link")

        similarity = title_similarity(candidate.title, existing.title)
        if similarity >= self.similarity_threshold:
            return DuplicateCheckResult(True, "title_similarity")
        return DuplicateCheckResult(False)

    def filter_new(
        self,
        candidates: Iterable[CollectedItem],
        existing_items: Iterable[Opportunity | CollectedItem],
    ) -> list[CollectedItem]:
        uniques: list[CollectedItem] = []
        prior = list(existing_items)
        for candidate in candidates:
            if any(self.check(candidate, item).is_duplicate for item in prior):
                continue
            uniques.append(candidate)
            prior.append(candidate)
        return uniques
