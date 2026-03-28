from __future__ import annotations

import re
from datetime import date, datetime


DATE_PATTERNS = (
    "%Y-%m-%d",
    "%d %B %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %b %Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
)

DATE_REGEXES = (
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}\s+[A-Z][a-z]+\s+\d{4}\b",
    r"\b[A-Z][a-z]+\s+\d{1,2},\s+\d{4}\b",
    r"\b[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\b",
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
)


def parse_date_text(text: str | None) -> date | None:
    if not text:
        return None

    cleaned = re.sub(r"\s+", " ", text).strip()
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(cleaned, pattern).date()
        except ValueError:
            continue

    for regex in DATE_REGEXES:
        match = re.search(regex, cleaned)
        if not match:
            continue
        token = match.group(0)
        for pattern in DATE_PATTERNS:
            try:
                return datetime.strptime(token, pattern).date()
            except ValueError:
                continue
    return None
