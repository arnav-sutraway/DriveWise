from datetime import timedelta
from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from google.genai.errors import APIError

from apps.chat.services.rag import ChatResult, NO_ANSWER_MESSAGE, answer_question
from apps.knowledge.services.document_ingestion import RawPage, ingest_pages
from apps.knowledge.services.embedding_generation import ConfigurationError, HashingEmbedder

from .checks import check_thresholds
from .metrics import failure_kind, save_observations
from .models import PerformanceBucket, UsageLog
from .reporting import performance_report, usage_report


@override_settings(PERFORMANCE_LATENCY_WARNING_MS=0, PERFORMANCE_FAILURE_WARNING_PERCENT=0)
class RequestMonitoringTests(TestCase):
    def post(self, message="Who goes first?"):
        return self.client.post("/api/v1/chat/", {"message": message}, content_type="application/json")

    def test_successful_requests_are_aggregated_without_changing_response(self):
        with mock.patch("apps.api.views.answer_question", return_value=ChatResult("Yield [1].", True)), \
                mock.patch("apps.monitoring.metrics.perf_counter", side_effect=[1, 1.05, 2, 2.08]):
            for message in ("private question one", "private question two"):
                response = self.post(message)
                self.assertEqual(response.json(), {
                    "answer": "Yield [1].",
                    "grounded": True,
                    "visualization": None,
                })
        bucket = PerformanceBucket.objects.get()
        self.assertEqual((bucket.stage, bucket.outcome, bucket.samples), ("request", "success", 2))
        self.assertAlmostEqual(bucket.total_ms, 130)
        self.assertAlmostEqual(bucket.max_ms, 80)
        self.assertNotIn("private question", str(list(PerformanceBucket.objects.values())))

    def test_invalid_requests_are_excluded_from_latency_and_failure_rate(self):
        for message in ("", "x" * 1001):
            self.assertEqual(self.post(message).status_code, 400)
        self.assertEqual(self.client.post("/api/v1/chat/", b"\xff", content_type="application/json").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/chat/").status_code, 405)
        self.assertEqual(sum(PerformanceBucket.objects.values_list("samples", flat=True)), 4)
        self.assertEqual(set(PerformanceBucket.objects.values_list("outcome", flat=True)), {"invalid"})
        report = performance_report(15)
        self.assertEqual(report["status"], "No data")
        self.assertEqual(report["failure_rate"], "—")

    def test_no_answer_is_success(self):
        with mock.patch("apps.api.views.answer_question", return_value=ChatResult(NO_ANSWER_MESSAGE, False)):
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(PerformanceBucket.objects.get().outcome, "success")
        self.assertEqual(performance_report(15)["failure_rate"], "0.0%")

    def test_configuration_provider_timeout_and_unexpected_errors_are_distinct(self):
        cases = [
            (ConfigurationError("not set"), "configuration", 503),
            (APIError(429, {"error": {"message": "quota"}}), "provider", 502),
            (TimeoutError("provider took too long"), "timeout", 502),
            (RuntimeError("unexpected"), "unexpected", 502),
        ]
        for error, outcome, status in cases:
            with self.subTest(outcome=outcome), \
                    mock.patch("apps.api.views.answer_question", side_effect=error), \
                    mock.patch("apps.api.views.logger.exception"):
                self.assertEqual(self.post().status_code, status)
                self.assertEqual(PerformanceBucket.objects.filter(stage="request", outcome=outcome).count(), 1)
        self.assertEqual(performance_report(15)["failure_rate"], "100.0%")

    def test_sdk_timeouts_and_connection_errors(self):
        self.assertEqual(failure_kind(APIError(504, {})), "timeout")
        # Exercise whichever transport(s) the installed SDK supports.
        from .metrics import _transport_errors
        timeouts, requests = _transport_errors()
        for error_type in timeouts:
            self.assertEqual(failure_kind(error_type("timeout")), "timeout")
        for error_type in requests:
            self.assertEqual(failure_kind(error_type("connection")), "provider")

    def test_failed_metric_write_preserves_response_and_next_request(self):
        with mock.patch("apps.api.views.answer_question", return_value=ChatResult("Answer [1].", True)):
            with mock.patch("apps.monitoring.metrics.save_observations", side_effect=DatabaseError("unavailable")), \
                    self.assertLogs("apps.monitoring.metrics", "WARNING"):
                self.assertEqual(self.post().status_code, 200)
            self.assertEqual(self.post().status_code, 200)
        self.assertEqual(sum(PerformanceBucket.objects.values_list("samples", flat=True)), 1)

    def test_health_and_dashboard_do_not_generate_chat_samples(self):
        self.client.get("/api/v1/health/")
        self.client.get(reverse("performance"))
        self.assertFalse(PerformanceBucket.objects.exists())


@override_settings(RAG_EMBEDDER="hashing", RAG_MIN_SCORE=0.01)
class StageTimingTests(TestCase):
    def setUp(self):
        ingest_pages([RawPage("At a four way stop the first vehicle to stop goes first. Yield to pedestrians before proceeding through the intersection.", 1)],
                     title="Test manual", embedder=HashingEmbedder())

    def post(self):
        return self.client.post("/api/v1/chat/", {"message": "Who goes first at a four way stop?"}, content_type="application/json")

    def test_stages_are_measured_once_and_retries_are_inside_stage_duration(self):
        llm = mock.Mock()
        llm.generate.return_value = "The first vehicle goes first [1]."
        # request start; embedding start/end; retrieval start/end; generation start/end; request end
        with mock.patch("apps.chat.services.rag.get_llm", return_value=llm), \
                mock.patch("apps.monitoring.metrics.perf_counter", side_effect=[0, 0.1, 0.3, 0.3, 0.4, 0.4, 2.4, 2.5]):
            self.assertEqual(self.post().status_code, 200)
        durations = dict(PerformanceBucket.objects.values_list("stage", "total_ms"))
        for stage, expected in {"embedding": 200, "retrieval": 100, "generation": 2000, "request": 2500}.items():
            self.assertAlmostEqual(durations[stage], expected)
        self.assertEqual(PerformanceBucket.objects.count(), 4)

    def test_failed_generation_has_timing_and_one_request_failure(self):
        llm = mock.Mock()
        llm.generate.side_effect = TimeoutError()
        with mock.patch("apps.chat.services.rag.get_llm", return_value=llm), mock.patch("apps.api.views.logger.exception"):
            self.assertEqual(self.post().status_code, 502)
        self.assertEqual(PerformanceBucket.objects.get(stage="generation").outcome, "timeout")
        report = performance_report(15)
        self.assertEqual(report["overall"]["samples"], 1)
        self.assertEqual(next(row["count"] for row in report["failures"] if row["label"] == "Timeout"), 1)

    @override_settings(RAG_MIN_SCORE=1.1)
    def test_skipped_generation_has_no_sample(self):
        self.assertEqual(self.post().status_code, 200)
        self.assertFalse(PerformanceBucket.objects.filter(stage="generation").exists())
        self.assertEqual(PerformanceBucket.objects.get(stage="request").outcome, "success")

    def test_direct_pipeline_calls_do_not_record_request_metrics(self):
        answer_question("four way stop", llm=mock.Mock(generate=mock.Mock(return_value="Go first [1].")))
        self.assertFalse(PerformanceBucket.objects.exists())


@override_settings(PERFORMANCE_LATENCY_WARNING_MS=0, PERFORMANCE_FAILURE_WARNING_PERCENT=0)
class ReportingTests(TestCase):
    def setUp(self):
        self.now = timezone.now().replace(second=30, microsecond=0)

    def add(self, duration, outcome="success", ago=0):
        save_observations([("request", outcome, duration)], self.now - timedelta(minutes=ago))

    def test_weighted_average_percentile_and_failure_denominator(self):
        for _ in range(19):
            self.add(100)
        self.add(1000, "provider")
        self.add(100000, "invalid")
        report = performance_report(15, self.now)
        self.assertEqual(report["overall"]["average"], "145 ms")
        self.assertEqual(report["overall"]["p95"], "≤ 100 ms")
        self.assertEqual(report["overall"]["maximum"], "1.00 s")
        self.assertEqual(report["failure_rate"], "5.0%")
        self.assertEqual(report["status"], "Failures observed")

    def test_window_edges_and_future_buckets(self):
        for ago in (0, 14, 15, 59, 60, -2):
            self.add(100, ago=ago)
        self.assertEqual(performance_report(15, self.now)["overall"]["samples"], 2)
        self.assertEqual(performance_report(60, self.now)["overall"]["samples"], 4)

    def test_overflow_is_not_reported_as_a_finite_percentile(self):
        self.add(400000)
        self.assertEqual(performance_report(15, self.now)["overall"]["p95"], "> 300.00 s")

    def test_baseline_is_not_claimed_to_meet_an_unset_target(self):
        self.add(500)
        self.assertEqual(performance_report(15, self.now)["status"], "Collecting baseline")

    @override_settings(PERFORMANCE_LATENCY_WARNING_MS=1000, PERFORMANCE_FAILURE_WARNING_PERCENT=5)
    def test_thresholds_and_no_data_state(self):
        self.assertEqual(performance_report(15, self.now)["status"], "No data")
        self.add(100)
        self.assertEqual(performance_report(15, self.now)["status"], "Within configured thresholds")
        self.add(10000, "timeout")
        report = performance_report(15, self.now)
        self.assertEqual(report["status"], "Threshold exceeded")
        self.assertEqual(len(report["warnings"]), 2)

    def test_retention_only_removes_old_aggregates(self):
        self.add(100, ago=8 * 24 * 60)
        self.add(200)
        call_command("prune_performance_metrics", stdout=StringIO())
        self.assertEqual(PerformanceBucket.objects.get().total_ms, 200)

    @override_settings(PERFORMANCE_LATENCY_WARNING_MS=float("nan"), PERFORMANCE_FAILURE_WARNING_PERCENT=101)
    def test_invalid_thresholds_are_reported(self):
        self.assertEqual({error.id for error in check_thresholds(None)}, {"monitoring.E001", "monitoring.E002"})


class DashboardTests(TestCase):
    def setUp(self):
        self.url = reverse("performance")
        self.staff = get_user_model().objects.create_user(username="staff", is_staff=True)

    def test_anonymous_nonstaff_and_inactive_users_cannot_view_metrics(self):
        self.assertRedirects(self.client.get(self.url), "/admin/login/?next=/admin/performance/")
        for name, is_staff, is_active in [("learner", False, True), ("inactive", True, False)]:
            user = get_user_model().objects.create_user(username=name, is_staff=is_staff, is_active=is_active)
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_staff_can_view_both_windows_and_dashboard_is_not_cached(self):
        self.client.force_login(self.staff)
        for window in ("15", "60", "invalid"):
            response = self.client.get(self.url, {"window": window})
            self.assertContains(response, "Chatbot performance")
            self.assertContains(response, "No data")
            self.assertContains(response, "No individual questions")
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(response.context["minutes"], 60 if window == "60" else 15)

    def test_admin_home_links_to_performance(self):
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(reverse("admin:index")), self.url)

    def test_dashboard_renders_actual_summary(self):
        self.client.force_login(self.staff)
        save_observations([("request", "timeout", 12000)], timezone.now())
        response = self.client.get(self.url)
        self.assertContains(response, "100.0%")
        self.assertContains(response, "12.00 s")
        self.assertContains(response, "Failures observed")

    def test_storage_outage_is_not_rendered_as_healthy(self):
        self.client.force_login(self.staff)
        with mock.patch("apps.monitoring.views.performance_report", side_effect=DatabaseError()), \
                self.assertLogs("apps.monitoring.views", "WARNING"):
            response = self.client.get(self.url)
        self.assertContains(response, "Metrics unavailable", status_code=503)
        self.assertNotContains(response, "Within configured thresholds", status_code=503)


class UsageLogTests(TestCase):
    def test_valid_requests_are_logged_without_question_text(self):
        with mock.patch("apps.api.views.answer_question", return_value=ChatResult("Yield [1].", True)):
            self.client.post("/api/v1/chat/", {"message": "private question"}, content_type="application/json")
        self.client.post("/api/v1/chat/", {"message": ""}, content_type="application/json")
        log = UsageLog.objects.get()
        self.assertEqual(log.outcome, "success")
        self.assertNotIn("private question", str(list(UsageLog.objects.values())))

    def test_report_counts_requests_in_window(self):
        now = timezone.now()
        for hours_ago, ms, outcome in [(0.5, 100, "success"), (0.5, 300, "timeout"), (2, 100, "success")]:
            UsageLog.objects.create(created_at=now - timedelta(hours=hours_ago), response_ms=ms, outcome=outcome)
        report = usage_report(1, now)
        self.assertEqual((report["total_queries"], report["average"]), (2, "200 ms"))
        self.assertEqual(usage_report(24, now)["total_queries"], 3)
        self.assertIn("Timeout", [log["outcome"] for log in report["logs"]])

    def test_only_staff_can_view_usage_page(self):
        url = reverse("usage")
        self.assertRedirects(self.client.get(url), "/admin/login/?next=/admin/usage/")
        UsageLog.objects.create(created_at=timezone.now(), response_ms=1500, outcome="success")
        self.client.force_login(get_user_model().objects.create_user(username="staff", is_staff=True))
        response = self.client.get(url)
        self.assertContains(response, "1.50 s")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertContains(self.client.get(reverse("admin:index")), url)
