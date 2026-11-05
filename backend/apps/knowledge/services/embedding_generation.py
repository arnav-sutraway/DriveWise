from typing import Protocol


class EmbeddingGenerator(Protocol):
    def embed(self, text: str) -> list[float]:
        """Generate embeddings with a future, explicitly configured local model."""
        ...
