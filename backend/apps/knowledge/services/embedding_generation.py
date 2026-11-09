"""Embedding providers. Pick one with the RAG_EMBEDDER setting ("gemini" or "hashing")."""

import hashlib
import math
import re
import time
from typing import Protocol

from django.conf import settings


class EmbeddingGenerator(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class ConfigurationError(RuntimeError):
    """Raised when a provider is selected but its API key/settings are missing."""


class GeminiEmbedder:
    batch_size = 50

    def __init__(self, api_key: str, model: str, dimensions: int):
        from google import genai

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.dimensions = dimensions

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        from google.genai import errors, types

        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self.dimensions)
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start:start + self.batch_size]
            for attempt in range(5):
                try:
                    result = self.client.models.embed_content(model=self.model, contents=batch, config=config)
                    break
                except errors.APIError as error:
                    # Free tier rate limits: back off and retry.
                    if getattr(error, "code", None) != 429 or attempt == 4:
                        raise
                    time.sleep(2 ** attempt * 5)
            vectors.extend(_normalize(e.values) for e in result.embeddings)
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]


class HashingEmbedder:
    """Offline bag-of-words embedder. No API key needed; used by tests and as a fallback."""

    def __init__(self, dimensions: int = 512):
        self.dimensions = dimensions

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            if len(token) < 3:
                continue
            index = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dimensions
            vector[index] += 1.0
        return _normalize(vector)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


def _normalize(vector) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [float(v) / norm for v in vector]


def get_embedder() -> EmbeddingGenerator:
    provider = settings.RAG_EMBEDDER
    if provider == "hashing":
        return HashingEmbedder()
    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ConfigurationError("GEMINI_API_KEY is not set (see backend/.env.example).")
        return GeminiEmbedder(settings.GEMINI_API_KEY, settings.RAG_EMBEDDING_MODEL,
                              settings.RAG_EMBEDDING_DIMENSIONS)
    raise ConfigurationError(f"Unknown RAG_EMBEDDER: {provider!r}")
