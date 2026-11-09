"""Check that a generated answer is actually grounded in the retrieved passages (US 3)."""

import re
from dataclasses import dataclass, field

from .prompts import NO_ANSWER_TOKEN

_CITATION = re.compile(r"\[(\d+)\]")


@dataclass
class ValidationResult:
    grounded: bool
    answer: str
    cited: list[int] = field(default_factory=list)  # 1-based passage numbers


class CitationValidator:
    """An answer counts as grounded only if it cites at least one passage that was retrieved.

    Citations to passage numbers that don't exist are removed from the text.
    """

    def validate(self, answer: str, passage_count: int) -> ValidationResult:
        text = answer.strip()
        if not text or text.upper().startswith(NO_ANSWER_TOKEN):
            return ValidationResult(False, "")

        valid = {n for n in map(int, _CITATION.findall(text)) if 1 <= n <= passage_count}
        text = _CITATION.sub(lambda m: m.group(0) if int(m.group(1)) in valid else "", text)
        if not valid:
            return ValidationResult(False, "")
        return ValidationResult(True, re.sub(r"[ \t]{2,}", " ", text).strip(), sorted(valid))
