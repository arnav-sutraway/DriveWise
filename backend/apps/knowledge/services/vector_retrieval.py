"""Cosine-similarity search over the Chunk table.

The driver's manual is a few hundred chunks, so an in-memory numpy search is
fast enough and avoids running a separate vector database.
"""

from dataclasses import dataclass

import numpy as np

from ..models import Chunk


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float


class DatabaseVectorRetriever:
    def search(self, query_embedding: list[float], top_k: int = 5,
               min_score: float = 0.0) -> list[RetrievedChunk]:
        chunks = list(Chunk.objects.select_related("document"))
        if not chunks:
            return []
        query = np.asarray(query_embedding, dtype=np.float32)
        matrix = np.asarray([c.embedding for c in chunks], dtype=np.float32)
        if matrix.shape[1] != query.shape[0]:
            raise ValueError(
                "Stored embeddings have a different size than the query embedding. "
                "Re-run `python manage.py ingest_documents` after changing the embedder."
            )
        norms = np.linalg.norm(matrix, axis=1) * (np.linalg.norm(query) or 1.0)
        scores = matrix @ query / np.where(norms == 0, 1.0, norms)
        best = np.argsort(-scores)[:top_k]
        return [
            RetrievedChunk(chunks[i], float(scores[i]))
            for i in best
            if scores[i] >= min_score
        ]
