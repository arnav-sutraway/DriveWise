from typing import Protocol


class DocumentIngestor(Protocol):
    def ingest(self, source: object) -> object:
        """Convert a future document source into the application's internal format."""
        ...
