import json
import logging
import tempfile
import time
import uuid
from functools import wraps
from pathlib import Path

from django.contrib.auth import authenticate, login, logout
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from django.conf import settings

from apps.chat.services.rag import answer_question
from apps.chat.services.visualizations import visualization_for_question
from apps.knowledge.models import Document
from apps.knowledge.services.embedding_generation import ConfigurationError
from apps.knowledge.services.sources import LOCAL_CONTENT_TYPES, local_file
from apps.monitoring.metrics import monitor_chat, note_failure

from .ratelimit import rate_limit

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 1000


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@csrf_exempt
@rate_limit
@monitor_chat
@require_POST
def chat(request):
    """POST {"message": "..."} -> {"answer": str, "grounded": bool}."""
    try:
        payload = json.loads(request.body or b"{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"detail": "Request body must be JSON."}, status=400)

    message = payload.get("message") if isinstance(payload, dict) else None
    if not isinstance(message, str) or not message.strip():
        return JsonResponse({"detail": "Send a non-empty \"message\" string."}, status=400)
    message = message.strip()
    if len(message) > MAX_QUESTION_LENGTH:
        return JsonResponse(
            {"detail": f"Questions must be under {MAX_QUESTION_LENGTH} characters."}, status=400)

    try:
        result = answer_question(message)
    except ConfigurationError as error:
        note_failure(error)
        return JsonResponse({"detail": f"Chatbot is not configured: {error}"}, status=503)
    except Exception as error:  # noqa: BLE001 - provider/network failure
        note_failure(error)
        logger.exception("Chat request failed")
        return JsonResponse(
            {"detail": "The coach couldn't answer right now. Please try again."}, status=502)

    return JsonResponse({
        "answer": result.answer,
        "grounded": result.grounded,
        "sources": result.sources,
        "visualization": visualization_for_question(message, grounded=result.grounded),
    })


@require_GET
def document_file(request, document_id):
    """Serve the ingested copy for citations, limited to supported files under KNOWLEDGE_DATA_DIR."""
    document = get_object_or_404(Document, pk=document_id)
    path = local_file(document)
    if path is None:
        raise Http404("This document has no local copy.")
    return FileResponse(
        path.open("rb"),
        filename=path.name,
        content_type=LOCAL_CONTENT_TYPES[path.suffix.lower()],
    )


def _developer_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Developer authentication required."}, status=401)
        if not request.user.is_active or not request.user.is_staff:
            return JsonResponse({"detail": "You are not authorized to access the Developer Portal."},
                                 status=403)
        return view(request, *args, **kwargs)
    return wrapped


def _payload(request):
    try:
        return json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _document_json(document):
    return {
        "id": document.id,
        "title": document.title,
        "name": document.title,
        "source_url": document.source_url,
        "source_organization": document.source_organization,
        "category": document.category,
        "jurisdiction": document.jurisdiction,
        "description": document.description,
        "state": document.state,
        "edition": document.edition,
        "source_path": document.source_path,
        "created_at": document.created_at.isoformat(),
        "date_uploaded": document.created_at.isoformat(),
        "last_processed": document.last_processed_at.isoformat() if document.last_processed_at else None,
        "processing_status": document.processing_status,
        "processing_error": document.processing_error,
        "chunk_count": document.chunks.count(),
    }


@ensure_csrf_cookie
@require_GET
def developer_csrf(request):
    return JsonResponse({"detail": "CSRF cookie ready."})


def developer_session(request):
    if request.method == "GET":
        if request.user.is_authenticated and request.user.is_active and request.user.is_staff:
            return JsonResponse({
                "authenticated": True,
                "username": request.user.username,
                "is_developer": True,
            })
        return JsonResponse({"authenticated": False, "is_developer": False}, status=200)
    if request.method == "DELETE":
        logout(request)
        return JsonResponse({"authenticated": False})
    if request.method != "POST":
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    payload = _payload(request)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "Request body must be JSON."}, status=400)
    user = authenticate(request, username=payload.get("username"),
                         password=payload.get("password"))
    if user is None or not user.is_active:
        return JsonResponse({"detail": "Invalid username or password."}, status=401)
    if not user.is_staff:
        return JsonResponse({"detail": "This account is not authorized for the Developer Portal."},
                            status=403)
    login(request, user)
    return JsonResponse({"authenticated": True, "username": user.username, "is_developer": True})


@_developer_required
@require_GET
def developer_dashboard(request):
    from apps.knowledge.models import Chunk, Document
    documents = Document.objects.all()
    recent = documents.order_by("-created_at").first()
    errors = list(documents.filter(processing_status="error").order_by("-last_processed_at")
                  .values("id", "title", "processing_error")[:10])
    return JsonResponse({
        "document_count": documents.count(),
        "chunk_count": Chunk.objects.count(),
        "source_count": documents.exclude(source_organization="").values("source_organization").distinct().count()
        + documents.exclude(source_url="").values("source_url").distinct().count(),
        "recent_ingestion": _document_json(recent) if recent else None,
        "vector_index_status": "ready" if Chunk.objects.exists() else "empty",
        "embedding_model": settings.RAG_EMBEDDING_MODEL,
        "recent_errors": errors,
    })


@_developer_required
def developer_documents(request):
    from apps.knowledge.models import Document
    if request.method == "GET":
        search = request.GET.get("search", "").strip()
        category = request.GET.get("category", "").strip()
        status = request.GET.get("status", "").strip()
        queryset = Document.objects.all()
        if search:
            queryset = queryset.filter(title__icontains=search)
        if category:
            queryset = queryset.filter(category=category)
        if status:
            queryset = queryset.filter(processing_status=status)
        return JsonResponse({"documents": [_document_json(item) for item in queryset]})
    return JsonResponse({"detail": "Method not allowed."}, status=405)


@_developer_required
def developer_document_detail(request, document_id):
    from apps.knowledge.models import Document
    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return JsonResponse({"detail": "Document not found."}, status=404)

    if request.method == "GET":
        payload = _document_json(document)
        payload["chunks"] = [
            {"id": chunk.id, "position": chunk.position, "page": chunk.page, "text": chunk.text}
            for chunk in document.chunks.all()
        ]
        return JsonResponse(payload)
    if request.method == "DELETE":
        document.delete()
        return JsonResponse({"deleted": True, "id": document_id})
    if request.method in ("PUT", "PATCH"):
        payload = _payload(request)
        if not isinstance(payload, dict):
            return JsonResponse({"detail": "Request body must be JSON."}, status=400)
        fields = (
            "title", "state", "edition", "source_url", "description", "category",
            "source_organization", "jurisdiction",
        )
        for field in fields:
            if field in payload:
                setattr(document, field, payload[field])
        document.save()
        return JsonResponse(_document_json(document))
    return JsonResponse({"detail": "Method not allowed."}, status=405)


@_developer_required
@require_POST
def developer_ingest_upload(request):
    from apps.knowledge.models import Document
    from apps.knowledge.services.document_ingestion import RawPage, ingest_pages, read_pdf
    from apps.knowledge.services.file_ingestion import ingest_text_upload

    uploads = request.FILES.getlist("files") or request.FILES.getlist("file")
    if not uploads:
        return JsonResponse({"detail": "Upload one or more files."}, status=400)

    metadata = {
        "state": request.POST.get("state", ""),
        "edition": request.POST.get("edition", ""),
        "source_url": request.POST.get("source_url", ""),
        "description": request.POST.get("description", ""),
        "category": request.POST.get("category", ""),
        "source_organization": request.POST.get("source_organization", ""),
        "jurisdiction": request.POST.get("jurisdiction", ""),
    }
    results = []
    for upload in uploads:
        suffix = Path(upload.name).suffix.lower()
        try:
            if suffix == ".pdf":
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp:
                    for chunk in upload.chunks():
                        temp.write(chunk)
                    temp_path = Path(temp.name)
                document = ingest_pages(
                    read_pdf(temp_path),
                    title=Path(upload.name).stem,
                    source_path=f"upload:{upload.name}",
                    state=metadata["state"],
                    edition=metadata["edition"],
                    metadata=metadata,
                )
                temp_path.unlink(missing_ok=True)
            elif suffix in (".txt", ".md"):
                document = ingest_text_upload(
                    upload,
                    upload.name,
                    title=Path(upload.name).stem,
                    state=metadata["state"],
                    edition=metadata["edition"],
                )
                for key, value in metadata.items():
                    if key not in ("state", "edition"):
                        setattr(document, key, value)
                document.save(update_fields=list(metadata.keys()) + ["processing_status"])
            else:
                results.append({"name": upload.name, "status": "skipped",
                                "error": "Unsupported file type."})
                continue
            results.append({"name": upload.name, "status": "success",
                            "document": _document_json(document)})
        except Exception as error:
            logger.exception("Developer upload failed for %s", upload.name)
            results.append({"name": upload.name, "status": "error", "error": str(error)})
    return JsonResponse({"results": results})


@_developer_required
@require_POST
def developer_ingest_text(request):
    from apps.knowledge.services.document_ingestion import RawPage, ingest_pages
    payload = _payload(request)
    if not isinstance(payload, dict) or not str(payload.get("text", "")).strip():
        return JsonResponse({"detail": "Provide non-empty text."}, status=400)
    title = str(payload.get("title", "")).strip() or "Custom text"
    source_path = f"text:{uuid.uuid4()}"
    try:
        document = ingest_pages(
            [RawPage(str(payload["text"]))],
            title=title,
            source_path=source_path,
            state=str(payload.get("state", "")),
            edition=str(payload.get("edition", "")),
            metadata={key: payload.get(key, "") for key in (
                "source_url", "description", "category", "source_organization", "jurisdiction",
            )},
        )
        return JsonResponse({"status": "success", "document": _document_json(document)})
    except Exception as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=502)


@_developer_required
@require_POST
def developer_url_preview(request):
    from apps.knowledge.services.web_ingestion import fetch_web_page
    payload = _payload(request)
    url = str(payload.get("url", "")).strip() if isinstance(payload, dict) else ""
    if not url:
        return JsonResponse({"detail": "Provide a URL."}, status=400)
    try:
        page = fetch_web_page(url, settings.KNOWLEDGE_ALLOWED_HOSTS)
        return JsonResponse({"url": page.url, "title": page.title, "text": page.text})
    except (ValueError, OSError) as error:
        return JsonResponse({"detail": str(error)}, status=400)


@_developer_required
@require_POST
def developer_ingest_url(request):
    from apps.knowledge.services.document_ingestion import RawPage, ingest_pages
    from apps.knowledge.services.web_ingestion import fetch_web_page
    payload = _payload(request)
    url = str(payload.get("url", "")).strip() if isinstance(payload, dict) else ""
    if not url:
        return JsonResponse({"detail": "Provide a URL."}, status=400)
    try:
        page = fetch_web_page(url, settings.KNOWLEDGE_ALLOWED_HOSTS)
        title = str(payload.get("title", "")).strip() or page.title
        document = ingest_pages(
            [RawPage(page.text)],
            title=title,
            source_path=page.url,
            state=str(payload.get("state", "")),
            edition=str(payload.get("edition", "")),
            metadata={
                "source_url": page.url,
                "description": str(payload.get("description", "")),
                "category": str(payload.get("category", "")),
                "source_organization": str(payload.get("source_organization", "")),
                "jurisdiction": str(payload.get("jurisdiction", "")),
            },
        )
        return JsonResponse({"status": "success", "document": _document_json(document)})
    except Exception as error:
        return JsonResponse({"status": "error", "error": str(error)}, status=400)


@_developer_required
@require_POST
def developer_preprocess_preview(request):
    from apps.knowledge.services.preprocessing import clean_text, chunk_pages
    from apps.knowledge.services.document_ingestion import RawPage
    payload = _payload(request)
    text = str(payload.get("text", "")).strip() if isinstance(payload, dict) else ""
    chunk_size = int(payload.get("chunk_size", 220)) if isinstance(payload, dict) else 220
    overlap = int(payload.get("chunk_overlap", 40)) if isinstance(payload, dict) else 40
    if chunk_size < 15 or chunk_size > 2000:
        return JsonResponse({"detail": "Chunk size must be between 15 and 2000 words."}, status=400)
    if overlap < 0 or overlap >= chunk_size:
        return JsonResponse({"detail": "Chunk overlap must be non-negative and smaller than chunk size."},
                            status=400)
    cleaned = clean_text(text)
    if not cleaned:
        return JsonResponse({"detail": "The document is empty or unusable."}, status=400)
    chunks = chunk_pages([RawPage(cleaned)], chunk_words=chunk_size, overlap_words=overlap)
    lines = cleaned.splitlines()
    duplicate_lines = len(lines) - len(set(lines))
    return JsonResponse({
        "cleaned_text": cleaned,
        "empty": not bool(cleaned),
        "duplicate_line_count": max(0, duplicate_lines),
        "chunks": [{"position": index, "page": chunk.page, "text": chunk.text}
                   for index, chunk in enumerate(chunks)],
    })


@_developer_required
@require_POST
def developer_reprocess(request, document_id):
    from apps.knowledge.models import Document
    from apps.knowledge.services.document_ingestion import RawPage, ingest_pages
    try:
        original = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return JsonResponse({"detail": "Document not found."}, status=404)
    payload = _payload(request) if request.body else {}
    chunk_size = int(payload.get("chunk_size", 220)) if isinstance(payload, dict) else 220
    overlap = int(payload.get("chunk_overlap", 40)) if isinstance(payload, dict) else 40
    if not original.raw_text:
        return JsonResponse({"detail": "No preserved source text is available for reprocessing."},
                            status=400)
    if chunk_size < 15 or chunk_size > 2000 or overlap < 0 or overlap >= chunk_size:
        return JsonResponse({"detail": "Invalid chunk size or overlap."}, status=400)
    try:
        original.processing_status = "processing"
        original.save(update_fields=["processing_status"])
        replacement = ingest_pages(
            [RawPage(original.raw_text)],
            title=original.title,
            source_path=original.source_path,
            state=original.state,
            edition=original.edition,
            chunk_words=chunk_size,
            overlap_words=overlap,
            metadata={
                "source_url": original.source_url,
                "description": original.description,
                "category": original.category,
                "source_organization": original.source_organization,
                "jurisdiction": original.jurisdiction,
            },
        )
        return JsonResponse(_document_json(replacement))
    except Exception as error:
        original.processing_status = "error"
        original.processing_error = str(error)
        original.save(update_fields=["processing_status", "processing_error"])
        return JsonResponse({"detail": str(error)}, status=502)


@_developer_required
def developer_config(request):
    from apps.knowledge.models import SystemConfiguration
    config = SystemConfiguration.current()
    if request.method == "GET":
        return JsonResponse({
            "chunk_size": config.chunk_size,
            "chunk_overlap": config.chunk_overlap,
            "top_k": config.top_k,
            "similarity_threshold": config.similarity_threshold,
            "embedding_model": config.embedding_model or settings.RAG_EMBEDDING_MODEL,
            "llm_model": config.llm_model or settings.RAG_CHAT_MODEL,
            "provider": settings.RAG_EMBEDDER,
        })
    if request.method not in ("PUT", "PATCH", "POST"):
        return JsonResponse({"detail": "Method not allowed."}, status=405)
    payload = _payload(request)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "Request body must be JSON."}, status=400)
    chunk_size = int(payload.get("chunk_size", config.chunk_size))
    chunk_overlap = int(payload.get("chunk_overlap", config.chunk_overlap))
    top_k = int(payload.get("top_k", config.top_k))
    threshold = float(payload.get("similarity_threshold", config.similarity_threshold))
    if chunk_size < 15 or chunk_size > 2000:
        return JsonResponse({"detail": "Chunk size must be between 15 and 2000 words."}, status=400)
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        return JsonResponse({"detail": "Chunk overlap must be smaller than chunk size."}, status=400)
    if top_k < 1 or top_k > 100:
        return JsonResponse({"detail": "Top-k must be between 1 and 100."}, status=400)
    if threshold < 0 or threshold > 1:
        return JsonResponse({"detail": "Similarity threshold must be between 0 and 1."}, status=400)
    config.chunk_size = chunk_size
    config.chunk_overlap = chunk_overlap
    config.top_k = top_k
    config.similarity_threshold = threshold
    if "embedding_model" in payload:
        config.embedding_model = str(payload["embedding_model"]).strip()
    if "llm_model" in payload:
        config.llm_model = str(payload["llm_model"]).strip()
    config.save()
    return JsonResponse({
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
        "top_k": config.top_k,
        "similarity_threshold": config.similarity_threshold,
        "embedding_model": config.embedding_model or settings.RAG_EMBEDDING_MODEL,
        "llm_model": config.llm_model or settings.RAG_CHAT_MODEL,
        "provider": settings.RAG_EMBEDDER,
    })


def _test_json(test):
    return {
        "id": test.id,
        "question": test.question,
        "expected_answer": test.expected_answer,
        "expected_sources": test.expected_sources,
        "category": test.category,
        "required_concepts": test.required_concepts,
        "description": test.description,
        "expected_visualization": test.expected_visualization,
    }


@_developer_required
def developer_tests(request):
    from apps.knowledge.models import EvaluationTest
    if request.method == "GET":
        queryset = EvaluationTest.objects.all()
        category = request.GET.get("category", "").strip()
        if category:
            queryset = queryset.filter(category=category)
        return JsonResponse({"tests": [_test_json(item) for item in queryset]})
    if request.method == "POST":
        payload = _payload(request)
        if not isinstance(payload, dict) or not str(payload.get("question", "")).strip():
            return JsonResponse({"detail": "A test question is required."}, status=400)
        test = EvaluationTest.objects.create(
            question=str(payload.get("question", "")).strip(),
            expected_answer=str(payload.get("expected_answer", "")),
            expected_sources=str(payload.get("expected_sources", "")),
            category=str(payload.get("category", "")),
            required_concepts=str(payload.get("required_concepts", "")),
            description=str(payload.get("description", "")),
            expected_visualization=str(payload.get("expected_visualization", "")),
        )
        return JsonResponse(_test_json(test), status=201)
    return JsonResponse({"detail": "Method not allowed."}, status=405)


@_developer_required
def developer_test_detail(request, test_id):
    from apps.knowledge.models import EvaluationTest
    try:
        test = EvaluationTest.objects.get(pk=test_id)
    except EvaluationTest.DoesNotExist:
        return JsonResponse({"detail": "Test case not found."}, status=404)
    if request.method == "GET":
        return JsonResponse(_test_json(test))
    if request.method == "DELETE":
        test.delete()
        return JsonResponse({"deleted": True, "id": test_id})
    if request.method in ("PUT", "PATCH"):
        payload = _payload(request)
        if not isinstance(payload, dict):
            return JsonResponse({"detail": "Request body must be JSON."}, status=400)
        for field in ("question", "expected_answer", "expected_sources", "category",
                      "required_concepts", "description", "expected_visualization"):
            if field in payload:
                setattr(test, field, payload[field])
        test.save()
        return JsonResponse(_test_json(test))
    return JsonResponse({"detail": "Method not allowed."}, status=405)


@_developer_required
@require_POST
def developer_evaluation_run(request):
    from apps.chat.services.rag import answer_question
    from apps.chat.services.visualizations import visualization_for_question
    from apps.knowledge.models import EvaluationRun, EvaluationResult, EvaluationTest
    payload = _payload(request)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "Request body must be JSON."}, status=400)
    test_ids = payload.get("test_ids")
    if test_ids:
        queryset = EvaluationTest.objects.filter(id__in=test_ids)
    else:
        queryset = EvaluationTest.objects.all()
    run = EvaluationRun.objects.create(name=str(payload.get("name", "Evaluation run")).strip())
    for test in queryset:
        started = time.perf_counter()
        try:
            chat_result = answer_question(test.question)
            actual = chat_result.answer
            grounded = chat_result.grounded
            retrieved = chat_result.retrieved_chunks or []
            answer_error = None
        except Exception as error:
            actual = ""
            grounded = False
            retrieved = []
            answer_error = str(error)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        lower_actual = actual.lower()
        concepts = [item.strip() for item in test.required_concepts.split(",") if item.strip()]
        covered = [item for item in concepts if item.lower() in lower_actual]
        missing = [item for item in concepts if item.lower() not in lower_actual]

        source_names = [
            item.chunk.document.title
            for item in retrieved
            if getattr(item, "chunk", None) is not None
        ]
        source_refs = [
            {
                "document_id": item.chunk.document_id,
                "title": item.chunk.document.title,
                "page": item.chunk.page,
                "score": round(item.score, 6),
            }
            for item in retrieved
            if getattr(item, "chunk", None) is not None
        ]
        chunk_refs = [
            {
                "document_id": item.chunk.document_id,
                "title": item.chunk.document.title,
                "position": item.chunk.position,
                "page": item.chunk.page,
                "text": item.chunk.text,
                "score": round(item.score, 6),
            }
            for item in retrieved
            if getattr(item, "chunk", None) is not None
        ]
        expected_sources = [
            item.strip().lower()
            for item in test.expected_sources.split(",")
            if item.strip()
        ]
        cited_relevant = bool(expected_sources) and any(
            name.lower() in expected or expected in name.lower()
            for name in source_names
            for expected in expected_sources
        )
        if not expected_sources:
            cited_relevant = bool(source_names)
        selected_visualization = visualization_for_question(test.question, grounded=grounded)
        selected_id = selected_visualization.get("scenario_id", "") if selected_visualization else ""
        failure_categories = []
        if answer_error:
            failure_categories.append("execution_error")
        if missing:
            failure_categories.append("missing_concepts")
        if expected_sources and not cited_relevant:
            failure_categories.append("missing_or_irrelevant_source")
        if test.expected_visualization and selected_id != test.expected_visualization:
            failure_categories.append("incorrect_visualization")
        if not retrieved:
            failure_categories.append("missing_retrieved_context")
        if not grounded:
            failure_categories.append("unsupported_answer")
        passed = not failure_categories
        EvaluationResult.objects.create(
            run=run,
            test=test,
            question=test.question,
            expected_answer=test.expected_answer,
            actual_answer=actual,
            retrieved_sources=source_refs,
            retrieved_chunks=chunk_refs,
            concepts_covered=covered,
            concepts_missing=missing,
            cited_relevant_source=cited_relevant,
            visualization_selected=selected_id,
            execution_time_ms=elapsed_ms,
            passed=passed,
            failure_categories=failure_categories,
        )

    total = run.results.count()
    passed = run.results.filter(passed=True).count()
    failed = total - passed
    categories = {}
    for result in run.results.all():
        for category in result.failure_categories:
            categories[category] = categories.get(category, 0) + 1
    run.completed_at = timezone.now()
    run.total_tests = total
    run.passed_tests = passed
    run.failed_tests = failed
    run.pass_percentage = round((passed / total * 100) if total else 0, 2)
    run.summary = {
        "common_failure_categories": [
            {"category": key, "count": value}
            for key, value in sorted(categories.items(), key=lambda item: (-item[1], item[0]))
        ],
    }
    run.save()
    return JsonResponse(developer_evaluation_json(run), status=201)


def developer_evaluation_json(run):
    return {
        "id": run.id,
        "name": run.name,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "total_tests": run.total_tests,
        "passed_tests": run.passed_tests,
        "failed_tests": run.failed_tests,
        "pass_percentage": run.pass_percentage,
        "summary": run.summary,
        "results": [
            {
                "id": result.id,
                "test_id": result.test_id,
                "question": result.question,
                "expected_answer": result.expected_answer,
                "actual_answer": result.actual_answer,
                "retrieved_sources": result.retrieved_sources,
                "retrieved_chunks": result.retrieved_chunks,
                "concepts_covered": result.concepts_covered,
                "concepts_missing": result.concepts_missing,
                "cited_relevant_source": result.cited_relevant_source,
                "visualization_selected": result.visualization_selected,
                "execution_time_ms": result.execution_time_ms,
                "passed": result.passed,
                "failure_categories": result.failure_categories,
            }
            for result in run.results.all()
        ],
    }


@_developer_required
@require_GET
def developer_evaluations(request):
    from apps.knowledge.models import EvaluationRun
    run_id = request.GET.get("run")
    if run_id:
        try:
            return JsonResponse(developer_evaluation_json(
                EvaluationRun.objects.get(pk=int(run_id))
            ))
        except (EvaluationRun.DoesNotExist, ValueError):
            return JsonResponse({"detail": "Evaluation run not found."}, status=404)
    return JsonResponse({"runs": [
        {
            "id": run.id,
            "name": run.name,
            "started_at": run.started_at.isoformat(),
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "total_tests": run.total_tests,
            "passed_tests": run.passed_tests,
            "failed_tests": run.failed_tests,
            "pass_percentage": run.pass_percentage,
            "summary": run.summary,
        }
        for run in EvaluationRun.objects.order_by("-started_at")
    ]})
