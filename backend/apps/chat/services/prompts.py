"""Prompt construction: tell the model to answer only from the retrieved passages."""

from apps.knowledge.services.vector_retrieval import RetrievedChunk

NO_ANSWER_TOKEN = "NO_ANSWER"

SYSTEM_PROMPT = f"""You are Driver Ed Coach, a patient driving instructor for new and returning drivers.
Rules:
1. Answer ONLY with information found in the numbered manual passages provided. Never use outside knowledge.
2. Cite every rule you state with its passage number in square brackets, e.g. [1] or [1][3].
3. If the passages do not contain the answer, reply with exactly {NO_ANSWER_TOKEN} and nothing else.
4. Use plain, friendly language a 16-year-old or someone new to US roads can follow. Keep it under 150 words.
5. Do not invent numbers (speeds, distances, fines). Only state numbers that appear in the passages."""


def format_passages(retrieved: list[RetrievedChunk]) -> str:
    blocks = []
    for number, item in enumerate(retrieved, start=1):
        chunk = item.chunk
        label = chunk.document.title
        if chunk.page:
            label += f" (p. {chunk.page})"
        blocks.append(f"[{number}] {label}\n{chunk.text}")
    return "\n\n".join(blocks)


def build_prompt(question: str, retrieved: list[RetrievedChunk]) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the given question and retrieved passages."""
    user_prompt = (
        f"Manual passages:\n\n{format_passages(retrieved)}\n\n"
        f"Learner's question: {question}"
    )
    return SYSTEM_PROMPT, user_prompt
