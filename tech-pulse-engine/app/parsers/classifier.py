from __future__ import annotations

from app.parsers.models import CollectedItem


CATEGORY_KEYWORDS = {
    "Job": ["job", "hiring", "career", "vacancy", "internship", "role", "apply now"],
    "Training": ["training", "course", "bootcamp", "learn", "academy", "certificate", "certification"],
    "Scholarship": ["scholarship", "fellowship", "bursary", "tuition"],
    "Accelerator": ["accelerator", "incubator", "cohort", "startup program"],
    "Event": ["event", "summit", "webinar", "conference", "workshop", "meetup"],
    "Grant": ["grant", "funding", "stipend", "seed fund", "prize", "award"],
}

HINT_MAPPING = {
    "job": "Job",
    "training": "Training",
    "certification": "Training",
    "scholarship": "Scholarship",
    "accelerator": "Accelerator",
    "event": "Event",
    "grant": "Grant",
}

AFRICA_TERMS = [
    "africa",
    "african",
    "nigeria",
    "kenya",
    "ghana",
    "south africa",
    "uganda",
    "tanzania",
    "rwanda",
    "egypt",
    "ethiopia",
    "remote africa",
    "pan-african",
]


def classify_item(item: CollectedItem) -> str | None:
    haystack = f"{item.title} {item.description}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            return category
    return HINT_MAPPING.get(item.category_hint.lower())


def compute_africa_score(item: CollectedItem) -> float:
    score = item.africa_relevance_weight
    haystack = f"{item.title} {item.description}".lower()
    matches = sum(1 for term in AFRICA_TERMS if term in haystack)
    if matches:
        score += min(0.2, matches * 0.05)
    return min(score, 1.0)
