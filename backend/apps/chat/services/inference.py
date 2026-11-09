"""LLM providers. Pick one with the RAG_LLM setting ("gemini")."""

from typing import Protocol

from django.conf import settings

from apps.knowledge.services.embedding_generation import ConfigurationError


class LLMInference(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        ...


class GeminiInference:
    def __init__(self, api_key: str, model: str, timeout_seconds: int = 90):
        from google import genai
        from google.genai import types

        # Fail after timeout_seconds instead of hanging, and retry at most once.
        self.client = genai.Client(api_key=api_key, http_options=types.HttpOptions(
            timeout=timeout_seconds * 1000,
            retry_options=types.HttpRetryOptions(attempts=2),
        ))
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
                # Answers only restate manual passages, so little "thinking" is needed; keeps replies fast.
                thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
            ),
        )
        return (response.text or "").strip()


def get_llm() -> LLMInference:
    if settings.RAG_LLM == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ConfigurationError("GEMINI_API_KEY is not set (see backend/.env.example).")
        return GeminiInference(settings.GEMINI_API_KEY, settings.RAG_CHAT_MODEL)
    raise ConfigurationError(f"Unknown RAG_LLM: {settings.RAG_LLM!r}")
