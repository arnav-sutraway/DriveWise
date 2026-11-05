from typing import Protocol


class LLMInference(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate a response using a future, explicitly configured local model."""
        ...
