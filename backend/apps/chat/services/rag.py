"""The RAG pipeline: question -> retrieve -> prompt -> generate -> validate."""

from dataclasses import dataclass

from django.conf import settings

from apps.knowledge.services.embedding_generation import get_embedder
from apps.knowledge.services.vector_retrieval import DatabaseVectorRetriever

from .inference import get_llm
from .prompts import build_prompt
from .response_validation import CitationValidator

NO_ANSWER_MESSAGE = (
    "I couldn't find that in the driver's manuals. I only answer from the official "
    "manuals in my sources, so I won't guess. Try asking about a traffic law, road sign, "
    "or driving situation."
)


@dataclass
class ChatResult:
    answer: str
    grounded: bool


def answer_question(question: str, embedder=None, llm=None, retriever=None) -> ChatResult:
    """Answer a learner question using only passages retrieved from the knowledge base."""
    embedder = embedder or get_embedder()
    retriever = retriever or DatabaseVectorRetriever()
    retrieved = retriever.search(embedder.embed_query(question),
                                 top_k=settings.RAG_TOP_K, min_score=settings.RAG_MIN_SCORE)
    if not retrieved:
        return ChatResult(NO_ANSWER_MESSAGE, grounded=False)

    system_prompt, user_prompt = build_prompt(question, retrieved)
    raw_answer = (llm or get_llm()).generate(system_prompt, user_prompt)

    validation = CitationValidator().validate(raw_answer, len(retrieved))
    if not validation.grounded:
        return ChatResult(NO_ANSWER_MESSAGE, grounded=False)
    return ChatResult(validation.answer, grounded=True)
