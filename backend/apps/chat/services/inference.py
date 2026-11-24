"""LLM providers. Pick one with the RAG_LLM setting ("gemini" or "claude_code")."""

import shutil
import subprocess
import tempfile
from typing import Protocol

from django.conf import settings

from apps.knowledge.services.embedding_generation import ConfigurationError


DEFAULT_TEMPERATURE = 0.2


class LLMInference(Protocol):
    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = DEFAULT_TEMPERATURE) -> str:
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

    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = DEFAULT_TEMPERATURE) -> str:
        from google.genai import types

        response = self.client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                # Answers only restate manual passages, so little "thinking" is needed; keeps replies fast.
                thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL),
            ),
        )
        return (response.text or "").strip()


class ClaudeCodeInference:
    """Local-testing provider: answers with the developer's Claude Code login via `claude -p`.

    No API key or Gemini quota is used. Every tool, customization (CLAUDE.md, hooks, plugins),
    MCP server and saved session is disabled, and the CLI runs outside the project, so it only
    turns the prompt into text: a learner's question cannot make it run commands or read files.
    """

    # The chat bubble renders plain text (line breaks are kept, Markdown is not), and Claude
    # otherwise tends to answer with bold text and bullet lists.
    PLAIN_TEXT_RULE = ("\n\nFormatting reminder: plain text only. Do not use Markdown (no bold, "
                       "headings, or bullet symbols). Numbered steps, when asked for, go one per line.")

    def __init__(self, binary: str = "claude", model: str = "", timeout_seconds: int = 120):
        executable = shutil.which(binary)
        if not executable:
            raise ConfigurationError(
                f"Claude Code CLI {binary!r} was not found on PATH "
                "(install Claude Code or set CLAUDE_CODE_BIN; see backend/.env.local.example)."
            )
        self.executable = executable
        self.model = model
        self.timeout_seconds = timeout_seconds

    def generate(self, system_prompt: str, user_prompt: str,
                 temperature: float = DEFAULT_TEMPERATURE) -> str:
        # The Claude Code CLI has no temperature option, so local testing ignores it;
        # the per-type instructions in the system prompt still apply.
        command = [
            self.executable, "-p",
            "--tools", "",
            "--safe-mode",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--output-format", "text",
            "--system-prompt", system_prompt + self.PLAIN_TEXT_RULE,
        ]
        if self.model:
            command += ["--model", self.model]
        # The prompt goes over stdin, which avoids command-line length limits.
        completed = subprocess.run(
            command, input=user_prompt, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=self.timeout_seconds, cwd=tempfile.gettempdir(), check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[:500]
            raise RuntimeError(f"Claude Code exited with status {completed.returncode}: {detail}")
        return completed.stdout.strip()


def get_llm() -> LLMInference:
    if settings.RAG_LLM == "gemini":
        if not settings.GEMINI_API_KEY:
            raise ConfigurationError("GEMINI_API_KEY is not set (see backend/.env.example).")
        return GeminiInference(settings.GEMINI_API_KEY, settings.RAG_CHAT_MODEL)
    if settings.RAG_LLM == "claude_code":
        return ClaudeCodeInference(settings.CLAUDE_CODE_BIN, settings.CLAUDE_CODE_MODEL,
                                   settings.CLAUDE_CODE_TIMEOUT_SECONDS)
    raise ConfigurationError(f"Unknown RAG_LLM: {settings.RAG_LLM!r}")
