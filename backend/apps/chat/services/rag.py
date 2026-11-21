"""The RAG pipeline: question -> retrieve -> prompt -> generate -> validate."""

from dataclasses import dataclass

from django.conf import settings

from apps.knowledge.services.embedding_generation import get_embedder
from apps.knowledge.services.vector_retrieval import DatabaseVectorRetriever
from apps.monitoring.metrics import time_stage

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
    retrieved_chunks: list = None


def answer_question(question: str, embedder=None, llm=None, retriever=None) -> ChatResult:
    """Answer a learner question using only passages retrieved from the knowledge base."""
    try:
        from apps.knowledge.models import SystemConfiguration
        runtime = SystemConfiguration.objects.first()
        if runtime is not None:
            top_k = runtime.top_k
            min_score = runtime.similarity_threshold
        else:
            top_k = settings.RAG_TOP_K
            min_score = settings.RAG_MIN_SCORE
    except Exception:
        top_k = settings.RAG_TOP_K
        min_score = settings.RAG_MIN_SCORE
    with time_stage("embedding"):
        embedder = embedder or get_embedder()
        query_embedding = embedder.embed_query(question)
    with time_stage("retrieval"):
        retriever = retriever or DatabaseVectorRetriever()
        retrieved = retriever.search(query_embedding,
                                     top_k=top_k, min_score=min_score)
    if not retrieved:
        return ChatResult(NO_ANSWER_MESSAGE, grounded=False, retrieved_chunks=[])

    system_prompt, user_prompt = build_prompt(question, retrieved)
    with time_stage("generation"):
        raw_answer = (llm or get_llm()).generate(system_prompt, user_prompt)

    validation = CitationValidator().validate(raw_answer, len(retrieved))
    if not validation.grounded:
        return ChatResult(NO_ANSWER_MESSAGE, grounded=False, retrieved_chunks=retrieved)
    return ChatResult(validation.answer, grounded=True, retrieved_chunks=retrieved)
