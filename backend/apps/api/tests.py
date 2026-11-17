from io import BytesIO
from unittest import mock

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.chat.services.rag import NO_ANSWER_MESSAGE, answer_question
from apps.chat.services.response_validation import CitationValidator
from apps.chat.services.visualizations import visualization_for_question
from apps.knowledge.models import Chunk, Document
from apps.knowledge.services.document_ingestion import RawPage, ingest_pages
from apps.knowledge.services.embedding_generation import HashingEmbedder
from apps.knowledge.services.file_ingestion import ingest_text_upload
from apps.knowledge.services.preprocessing import chunk_pages
from apps.knowledge.services.web_ingestion import WebPage, ingest_web_url

RIGHT_OF_WAY_PAGE = """At a four-way stop, the first vehicle to stop at the intersection goes first.
When two vehicles stop at the same time, the driver on the left yields to the
driver on the right. Always yield to pedestrians in the crosswalk before you
proceed through the intersection, even when it is otherwise your turn to go."""


class FakeLLM:
    def __init__(self, reply):
        self.reply = reply
        self.prompts = []

    def generate(self, system_prompt, user_prompt):
        self.prompts.append(user_prompt)
        return self.reply


@override_settings(RAG_EMBEDDER="hashing", RAG_MIN_SCORE=0.1, RAG_TOP_K=3)
class RagTestCase(TestCase):
    def setUp(self):
        self.document = ingest_pages([RawPage(RIGHT_OF_WAY_PAGE, 34)], title="Georgia Driver's Manual",
                                     source_path="georgia.pdf", state="Georgia", edition="2026",
                                     embedder=HashingEmbedder())


class IngestionTests(RagTestCase):
    def test_pages_are_chunked_and_embedded(self):
        chunk = self.document.chunks.get()
        self.assertEqual(chunk.page, 34)
        self.assertEqual(len(chunk.embedding), 512)

    def test_reingesting_the_same_file_replaces_it(self):
        ingest_pages([RawPage(RIGHT_OF_WAY_PAGE, 1)], title="Georgia Driver's Manual",
                     source_path="georgia.pdf", embedder=HashingEmbedder())
        self.assertEqual(Document.objects.count(), 1)

    def test_long_text_is_split_with_overlap(self):
        words = " ".join(f"word{i}" for i in range(500))
        chunks = chunk_pages([RawPage(words, 3)], chunk_words=200, overlap_words=40)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[1].text.split()[0], "word160")
        self.assertEqual(chunks[0].page, 3)

    def test_text_upload_is_cleaned_embedded_and_saved(self):
        source = (
            "The first vehicle\u0000 to stop goes first. "
            "Yield to pedestrians before proceeding through the intersection."
        )
        document = ingest_text_upload(
            BytesIO(source.encode("utf-8")),
            "uploaded_manual.txt",
            embedder=HashingEmbedder(),
        )

        chunk = document.chunks.get()
        self.assertNotIn("\u0000", chunk.text)
        self.assertNotIn("  ", chunk.text)
        self.assertEqual(len(chunk.embedding), 512)

    def test_web_page_is_embedded_and_saved(self):
        page = WebPage(
            url="https://manuals.example.org/rules",
            title="Online Manual",
            text="The first vehicle to stop goes first. Yield to pedestrians before proceeding through the intersection.",
        )
        with mock.patch(
            "apps.knowledge.services.web_ingestion.fetch_web_page",
            return_value=page,
        ):
            document = ingest_web_url(
                page.url,
                allowed_hosts=["manuals.example.org"],
                embedder=HashingEmbedder(),
            )

        chunk = document.chunks.get()
        self.assertEqual(document.title, "Online Manual")
        self.assertEqual(document.source_path, page.url)
        self.assertEqual(len(chunk.embedding), 512)


class CitationValidatorTests(TestCase):
    def test_answer_with_valid_citation_is_grounded(self):
        result = CitationValidator().validate("Yield to the right [1].", 3)
        self.assertTrue(result.grounded)
        self.assertEqual(result.cited, [1])

    def test_invalid_citations_are_removed(self):
        result = CitationValidator().validate("Yield [1][7].", 3)
        self.assertEqual(result.answer, "Yield [1].")

    def test_no_citations_or_no_answer_token_is_not_grounded(self):
        self.assertFalse(CitationValidator().validate("Yield to the right.", 3).grounded)
        self.assertFalse(CitationValidator().validate("NO_ANSWER", 3).grounded)


class VisualizationIntentTests(TestCase):
    def test_selects_only_predefined_grounded_demonstrations(self):
        self.assertEqual(
            visualization_for_question("How do I parallel park?", grounded=True),
            {"scene": "parking", "scenario_id": "parallel"},
        )
        self.assertEqual(
            visualization_for_question("How do I reverse park?", grounded=True),
            {"scene": "parking", "scenario_id": "reverse"},
        )
        self.assertEqual(
            visualization_for_question("How do I angle park?", grounded=True),
            {"scene": "parking", "scenario_id": "angle"},
        )
        self.assertEqual(
            visualization_for_question("How do I park in a 90-degree space?", grounded=True),
            {"scene": "parking", "scenario_id": "perpendicular"},
        )
        self.assertEqual(
            visualization_for_question("How does a four-way stop work?", grounded=True),
            {"scene": "intersection", "scenario_id": "four_way_stop"},
        )

    def test_does_not_select_a_demo_for_ungrounded_or_ambiguous_questions(self):
        self.assertIsNone(
            visualization_for_question("How do I parallel park?", grounded=False)
        )
        self.assertIsNone(
            visualization_for_question("What does parking mean?", grounded=True)
        )


class RagPipelineTests(RagTestCase):
    def test_grounded_answer_uses_retrieved_passages(self):
        llm = FakeLLM("If you stop at the same time, yield to the car on your right [1].")
        result = answer_question("Who goes first at a four-way stop?", llm=llm)

        self.assertTrue(result.grounded)
        self.assertIn("[1]", result.answer)
        self.assertIn("four-way stop", llm.prompts[0])
        self.assertIn("(p. 34)", llm.prompts[0])

    def test_model_refusal_returns_no_answer_message(self):
        result = answer_question("Who goes first at a four-way stop?", llm=FakeLLM("NO_ANSWER"))
        self.assertFalse(result.grounded)
        self.assertEqual(result.answer, NO_ANSWER_MESSAGE)

    def test_uncited_answer_is_rejected(self):
        result = answer_question("Who goes first?", llm=FakeLLM("Just go whenever you feel like it."))
        self.assertFalse(result.grounded)
        self.assertEqual(result.answer, NO_ANSWER_MESSAGE)

    @override_settings(RAG_MIN_SCORE=0.99)
    def test_nothing_relevant_skips_the_llm(self):
        llm = FakeLLM("should not be called [1]")
        result = answer_question("What is the cheapest car insurance?", llm=llm)
        self.assertFalse(result.grounded)
        self.assertEqual(llm.prompts, [])


@override_settings(CHAT_RATE_LIMIT=0)
class ApiEndpointTests(RagTestCase):
    def post(self, data):
        return self.client.post("/api/v1/chat/", data=data, content_type="application/json")

    def test_django_uses_frontend_build_directory(self):
        self.assertEqual(settings.FRONTEND_BUILD_DIR, settings.BASE_DIR.parent / "frontend" / "dist")

    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_chat_endpoint_returns_grounded_answer(self):
        llm = FakeLLM("Yield to the driver on your right [1].")
        with mock.patch("apps.chat.services.rag.get_llm", return_value=llm):
            response = self.post({"message": "Who goes first at a four-way stop?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "answer": "Yield to the driver on your right [1].",
            "grounded": True,
            # The test document's source_path is not a real file and has no official link.
            "sources": [{"number": 1, "title": "Georgia Driver's Manual", "page": 34,
                         "url": None, "official_url": None}],
            "visualization": {"scene": "intersection", "scenario_id": "four_way_stop"},
        })

    def test_grounded_parking_question_returns_predefined_visualization(self):
        from apps.chat.services.rag import ChatResult

        with mock.patch(
            "apps.api.views.answer_question",
            return_value=ChatResult("Use the manual's parking steps [1].", grounded=True),
        ):
            response = self.post({"message": "How do I parallel park?"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["visualization"],
            {"scene": "parking", "scenario_id": "parallel"},
        )

    def test_ungrounded_parking_question_does_not_trigger_a_visualization(self):
        from apps.chat.services.rag import ChatResult

        with mock.patch(
            "apps.api.views.answer_question",
            return_value=ChatResult(NO_ANSWER_MESSAGE, grounded=False),
        ):
            response = self.post({"message": "How do I parallel park?"})

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["visualization"])

    def test_chat_endpoint_validates_input(self):
        for data in ({}, {"message": "   "}, {"message": 5}, {"message": "x" * 1001}):
            self.assertEqual(self.post(data).status_code, 400, data)
        self.assertEqual(self.post("not json").status_code, 400)

    @override_settings(RAG_EMBEDDER="gemini", GEMINI_API_KEY="")
    def test_missing_api_key_returns_503(self):
        response = self.post({"message": "Who goes first?"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("GEMINI_API_KEY", response.json()["detail"])

    def test_provider_failure_returns_502(self):
        class BrokenLLM:
            def generate(self, *_):
                raise RuntimeError("quota exceeded")

        with mock.patch("apps.chat.services.rag.get_llm", return_value=BrokenLLM()), \
                self.assertLogs("apps.api.views", level="ERROR"):
            response = self.post({"message": "Who goes first at a four-way stop?"})
        self.assertEqual(response.status_code, 502)

    def test_chat_endpoint_only_accepts_post(self):
        self.assertEqual(self.client.get("/api/v1/chat/").status_code, 405)

    def test_empty_knowledge_base_says_no_answer(self):
        Chunk.objects.all().delete()
        with mock.patch("apps.chat.services.rag.get_llm", return_value=FakeLLM("x [1]")):
            response = self.post({"message": "Who goes first?"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["grounded"])


@override_settings(CHAT_RATE_LIMIT=2, CHAT_RATE_LIMIT_WINDOW_SECONDS=60)
class RateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def post(self, ip):
        return self.client.post("/api/v1/chat/", data={}, content_type="application/json",
                                HTTP_X_FORWARDED_FOR=f"{ip}, 10.0.0.1")

    def test_requests_over_the_limit_get_429(self):
        self.assertEqual([self.post("1.1.1.1").status_code for _ in range(3)], [400, 400, 429])
        self.assertEqual(self.post("1.1.1.1")["Retry-After"], "60")

    def test_limit_is_per_visitor(self):
        for _ in range(3):
            self.post("1.1.1.1")
        self.assertEqual(self.post("2.2.2.2").status_code, 400)

    @override_settings(CHAT_RATE_LIMIT=0)
    def test_zero_disables_the_limit(self):
        self.assertEqual({self.post("1.1.1.1").status_code for _ in range(5)}, {400})


class ClaudeCodeInferenceTests(TestCase):
    """Local-testing provider that shells out to `claude -p` instead of calling Gemini."""

    def make(self, **kwargs):
        from apps.chat.services.inference import ClaudeCodeInference

        with mock.patch("apps.chat.services.inference.shutil.which", return_value="/bin/claude"):
            return ClaudeCodeInference(**kwargs)

    @override_settings(RAG_LLM="claude_code", CLAUDE_CODE_BIN="claude", CLAUDE_CODE_MODEL="haiku",
                       CLAUDE_CODE_TIMEOUT_SECONDS=30)
    def test_get_llm_selects_claude_code(self):
        from apps.chat.services.inference import ClaudeCodeInference, get_llm

        with mock.patch("apps.chat.services.inference.shutil.which", return_value="/bin/claude"):
            llm = get_llm()
        self.assertIsInstance(llm, ClaudeCodeInference)
        self.assertEqual((llm.model, llm.timeout_seconds), ("haiku", 30))

    @override_settings(RAG_LLM="claude_code", CLAUDE_CODE_BIN="missing-claude")
    def test_missing_cli_is_a_configuration_error(self):
        from apps.chat.services.inference import get_llm
        from apps.knowledge.services.embedding_generation import ConfigurationError

        with mock.patch("apps.chat.services.inference.shutil.which", return_value=None):
            with self.assertRaises(ConfigurationError):
                get_llm()

    def test_runs_headless_with_tools_disabled_and_prompt_on_stdin(self):
        llm = self.make(model="haiku", timeout_seconds=30)
        completed = mock.Mock(returncode=0, stdout="  Stop first [1].\n", stderr="")
        with mock.patch("apps.chat.services.inference.subprocess.run", return_value=completed) as run:
            answer = llm.generate("SYSTEM RULES", "Manual passages: ...")
        self.assertEqual(answer, "Stop first [1].")
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ["/bin/claude", "-p"])
        self.assertEqual(command[command.index("--tools") + 1], "")
        for flag in ("--safe-mode", "--strict-mcp-config", "--no-session-persistence"):
            self.assertIn(flag, command)
        system_prompt = command[command.index("--system-prompt") + 1]
        self.assertTrue(system_prompt.startswith("SYSTEM RULES"))
        self.assertIn("Do not use Markdown", system_prompt)
        self.assertEqual(command[command.index("--model") + 1], "haiku")
        self.assertNotIn("Manual passages: ...", command)
        self.assertEqual(run.call_args.kwargs["input"], "Manual passages: ...")
        self.assertEqual(run.call_args.kwargs["timeout"], 30)

    def test_blank_model_uses_cli_default(self):
        llm = self.make(model="")
        completed = mock.Mock(returncode=0, stdout="ok [1]", stderr="")
        with mock.patch("apps.chat.services.inference.subprocess.run", return_value=completed) as run:
            llm.generate("s", "u")
        self.assertNotIn("--model", run.call_args.args[0])

    def test_cli_failure_raises(self):
        llm = self.make()
        completed = mock.Mock(returncode=1, stdout="", stderr="Not logged in")
        with mock.patch("apps.chat.services.inference.subprocess.run", return_value=completed):
            with self.assertRaisesRegex(RuntimeError, "Not logged in"):
                llm.generate("s", "u")


class SourceLinkTests(TestCase):
    """Cited passages link to the served local copy and, when known, the official original."""

    def setUp(self):
        import json
        import tempfile
        from pathlib import Path

        self.data_dir = Path(tempfile.mkdtemp())
        self.outside_dir = Path(tempfile.mkdtemp())
        (self.data_dir / "manual.pdf").write_bytes(b"%PDF-1.4 test manual")
        (self.data_dir / "rules.md").write_text("# Scooter rules\nNever ride on sidewalks.", encoding="utf-8")
        (self.data_dir / "notes.json").write_text("{}", encoding="utf-8")
        (self.outside_dir / "secret.md").write_text("not part of the knowledge base", encoding="utf-8")
        (self.data_dir / "source_links.json").write_text(json.dumps({
            "rules.md": "https://example.gov/scooter-rules",
            "manual.pdf": "javascript:alert(1)",  # Only https links are trusted.
        }), encoding="utf-8")
        self.settings_override = override_settings(KNOWLEDGE_DATA_DIR=self.data_dir)
        self.settings_override.enable()

    def tearDown(self):
        import shutil

        self.settings_override.disable()
        shutil.rmtree(self.data_dir, ignore_errors=True)
        shutil.rmtree(self.outside_dir, ignore_errors=True)

    def passage(self, source_path, title, page=None):
        from apps.knowledge.services.vector_retrieval import RetrievedChunk

        document = Document.objects.create(title=title, source_path=str(source_path))
        chunk = Chunk.objects.create(document=document, position=0, page=page, text="x", embedding=[1.0])
        return RetrievedChunk(chunk, 0.9)

    def test_cited_passages_get_local_and_official_links(self):
        from apps.knowledge.services.sources import describe_sources

        manual = self.passage(self.data_dir / "manual.pdf", "Driver's Manual", page=7)
        rules = self.passage(self.data_dir / "rules.md", "Scooter Rules")
        web = self.passage("https://dds.georgia.gov/page", "DDS Page")
        uncited = self.passage(self.data_dir / "rules.md", "Not cited")

        sources = describe_sources([manual, rules, web, uncited], cited=[3, 1, 2, 9, 1])

        self.assertEqual([source["number"] for source in sources], [1, 2, 3])
        self.assertEqual(sources[0], {
            "number": 1, "title": "Driver's Manual", "page": 7,
            "url": f"/api/v1/documents/{manual.chunk.document.pk}/file/#page=7", "official_url": None,
        })
        self.assertEqual(sources[1]["url"], f"/api/v1/documents/{rules.chunk.document.pk}/file/")
        self.assertEqual(sources[1]["official_url"], "https://example.gov/scooter-rules")
        self.assertEqual((sources[2]["url"], sources[2]["official_url"]),
                         ("https://dds.georgia.gov/page", "https://dds.georgia.gov/page"))

    def test_document_file_serves_local_copy_inline(self):
        pdf = self.passage(self.data_dir / "manual.pdf", "Driver's Manual").chunk.document
        rules = self.passage(self.data_dir / "rules.md", "Scooter Rules").chunk.document

        response = self.client.get(f"/api/v1/documents/{pdf.pk}/file/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response["Content-Disposition"].startswith("inline"))
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 test manual")

        response = self.client.get(f"/api/v1/documents/{rules.pk}/file/")
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn("Never ride on sidewalks.", b"".join(response.streaming_content).decode())

    def test_document_file_refuses_anything_outside_the_knowledge_folder(self):
        outside = self.passage(self.outside_dir / "secret.md", "Outside").chunk.document
        unsupported = self.passage(self.data_dir / "notes.json", "Unsupported").chunk.document
        missing = self.passage(self.data_dir / "deleted.pdf", "Deleted").chunk.document
        web = self.passage("https://dds.georgia.gov/page", "Web").chunk.document

        for document in (outside, unsupported, missing, web):
            self.assertEqual(self.client.get(f"/api/v1/documents/{document.pk}/file/").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/documents/999999/file/").status_code, 404)
        self.assertEqual(self.client.post(f"/api/v1/documents/{outside.pk}/file/").status_code, 405)
