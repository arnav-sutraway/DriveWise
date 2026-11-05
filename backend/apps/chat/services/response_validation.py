from typing import Protocol


class ResponseValidator(Protocol):
    def validate(self, answer: str, retrieved_passages: list[str]) -> bool:
        """Validate a future response against the passages actually retrieved."""
        ...
