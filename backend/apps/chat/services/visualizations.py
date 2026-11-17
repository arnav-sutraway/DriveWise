"""Map grounded learner questions to the application's predefined demonstrations."""

import re
from typing import TypedDict


class Visualization(TypedDict):
    scene: str
    scenario_id: str


_PARKING_PATTERNS = (
    (re.compile(r"\bparallel\s+park(?:ing)?\b"), "parallel"),
    (
        re.compile(
            r"\b(?:reverse|back[- ]in)\s+park(?:ing)?\b"
            r"|\b(?:back(?:ing)?|reverse)\s+into\s+(?:a\s+)?(?:parking\s+)?space\b"
        ),
        "reverse",
    ),
    (re.compile(r"\bangle(?:d)?\s+park(?:ing)?\b|\bdiagonal(?:ly)?\s+park(?:ing)?\b"), "angle"),
    (re.compile(r"\b(?:perpendicular|straight(?:[- ]in)?)\s+park(?:ing)?\b|\b90[- ]degree\s+(?:park(?:ing)?|space)\b"), "perpendicular"),
)
_FOUR_WAY_STOP = re.compile(r"\b(?:four|4)[- ]way\s+stop\b")


def visualization_for_question(question: str, *, grounded: bool) -> Visualization | None:
    """Return a known demo only for a grounded answer and a clearly named topic."""
    if not grounded:
        return None

    for pattern, scenario_id in _PARKING_PATTERNS:
        if pattern.search(question):
            return {"scene": "parking", "scenario_id": scenario_id}

    if _FOUR_WAY_STOP.search(question):
        return {"scene": "intersection", "scenario_id": "four_way_stop"}

    return None
