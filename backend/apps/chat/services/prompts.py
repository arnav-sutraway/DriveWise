"""Prompt construction: tell the model to answer only from the retrieved passages.

The grounding rules are the same for every question. What changes per question type (US 8)
is the answer shape, the word limit, how many passages are retrieved, and the temperature:
see PROMPT_PROFILES and intents.classify_question.
"""

from dataclasses import dataclass

from apps.knowledge.services.vector_retrieval import RetrievedChunk

from . import intents

NO_ANSWER_TOKEN = "NO_ANSWER"

BASE_RULES = f"""You are Driver Ed Coach, a patient driving instructor for new and returning drivers.
Rules that always apply:
1. Answer ONLY with information found in the numbered manual passages provided. Never use outside knowledge.
2. Cite every rule you state with its passage number in square brackets, e.g. [1] or [1][3].
3. If the passages do not contain the answer, reply with exactly {NO_ANSWER_TOKEN} and nothing else.
4. Use plain, friendly language a 16-year-old or someone new to US roads can follow.
5. Do not invent numbers (speeds, distances, fines). Only state numbers that appear in the passages.
6. Write plain text. Do not use Markdown such as **bold**, headings, or bullet symbols."""


@dataclass(frozen=True)
class PromptProfile:
    label: str               # shown to the learner next to the answer
    instructions: str        # how to shape the answer for this question type
    max_words: int
    temperature: float
    extra_passages: int = 0  # retrieved on top of the configured top_k


PROMPT_PROFILES = {
    intents.FACTUAL: PromptProfile(
        label="Quick answer",
        instructions=("The learner wants a specific fact. Start with the direct answer (the rule, "
                      "the number, or yes/no), then add at most one sentence of context."),
        max_words=60,
        temperature=0.1,
    ),
    intents.EXPLANATION: PromptProfile(
        label="Explanation",
        instructions=("The learner wants to understand a rule. State the rule, then explain the "
                      "reason behind it or how it works in a short paragraph. Only give reasons the "
                      "passages state; if they give the rule without a reason, say so."),
        max_words=150,
        temperature=0.3,
    ),
    intents.PROCEDURE: PromptProfile(
        label="Step-by-step",
        instructions=("The learner wants to know how to do something. Give the steps in order, each "
                      "on its own line starting with its number (1., 2., 3.), with a citation on "
                      "every step. If the passages include a safety reminder, end with it."),
        max_words=200,
        temperature=0.2,
        extra_passages=3,
    ),
    intents.SCENARIO: PromptProfile(
        label="Your situation",
        instructions=("The learner describes a situation. First tell them what to do in that "
                      "situation, then the rule from the passages that requires it. If the passages "
                      "only cover part of their situation, answer that part and say what is not covered."),
        max_words=150,
        temperature=0.2,
    ),
    intents.CREATIVE: PromptProfile(
        label="Practice",
        instructions=("The learner wants practice material. Write three short practice questions, "
                      "each on its own line and followed by its answer, or a short memory aid if they "
                      "asked for one. Use only facts from the passages, cite each one, and do not "
                      "invent rules, numbers, or situations the passages do not support."),
        max_words=200,
        temperature=0.6,
        extra_passages=2,
    ),
    intents.GENERAL: PromptProfile(
        label="Answer",
        instructions="Answer the learner's question clearly and briefly.",
        max_words=150,
        temperature=0.2,
    ),
}


def profile_for(question_type: str) -> PromptProfile:
    return PROMPT_PROFILES.get(question_type, PROMPT_PROFILES[intents.GENERAL])


def build_system_prompt(question_type: str) -> str:
    profile = profile_for(question_type)
    return (f"{BASE_RULES}\n\n"
            f"Question type: {profile.label}\n"
            f"How to answer: {profile.instructions}\n"
            f"Keep the answer under {profile.max_words} words.")


def format_passages(retrieved: list[RetrievedChunk]) -> str:
    blocks = []
    for number, item in enumerate(retrieved, start=1):
        chunk = item.chunk
        label = chunk.document.title
        if chunk.page:
            label += f" (p. {chunk.page})"
        blocks.append(f"[{number}] {label}\n{chunk.text}")
    return "\n\n".join(blocks)


def build_prompt(question: str, retrieved: list[RetrievedChunk],
                 question_type: str = intents.GENERAL) -> tuple[str, str]:
    """Return (system_prompt, user_prompt) for the question, its type, and the retrieved passages."""
    user_prompt = (
        f"Manual passages:\n\n{format_passages(retrieved)}\n\n"
        f"Learner's question: {question}"
    )
    return build_system_prompt(question_type), user_prompt
