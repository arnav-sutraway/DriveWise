from typing import Protocol


class VectorRetriever(Protocol):
    def search(self, query_embedding: list[float]) -> list[object]:
        """Retrieve relevant passages from a future, locally hosted vector store."""
        ...
