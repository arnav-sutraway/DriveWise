from django.db import models


class Document(models.Model):
    """One source in the knowledge base, e.g. the Georgia Driver's Manual PDF."""

    title = models.CharField(max_length=255)
    state = models.CharField(max_length=64, blank=True)
    edition = models.CharField(max_length=32, blank=True)
    source_path = models.CharField(max_length=500, blank=True)
    source_url = models.URLField(max_length=2000, blank=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=128, blank=True)
    source_organization = models.CharField(max_length=255, blank=True)
    jurisdiction = models.CharField(max_length=128, blank=True)
    raw_text = models.TextField(blank=True)
    processing_status = models.CharField(
        max_length=16,
        choices=[("pending", "Pending"), ("processing", "Processing"),
                 ("indexed", "Indexed"), ("error", "Error")],
        default="pending",
    )
    processing_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Chunk(models.Model):
    """A retrievable passage of a document plus its embedding vector."""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    position = models.PositiveIntegerField()
    page = models.PositiveIntegerField(null=True, blank=True)
    text = models.TextField()
    embedding = models.JSONField()

    class Meta:
        ordering = ["document_id", "position"]

    def __str__(self):
        return f"{self.document.title} #{self.position}"


class SystemConfiguration(models.Model):
    """Persisted runtime settings for the RAG pipeline."""

    chunk_size = models.PositiveIntegerField(default=220)
    chunk_overlap = models.PositiveIntegerField(default=40)
    top_k = models.PositiveIntegerField(default=5)
    similarity_threshold = models.FloatField(default=0.55)
    embedding_model = models.CharField(max_length=255, blank=True)
    llm_model = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def current(cls):
        return cls.objects.first() or cls.objects.create(pk=1)


class EvaluationTest(models.Model):
    question = models.TextField()
    expected_answer = models.TextField()
    expected_sources = models.TextField(blank=True)
    category = models.CharField(max_length=128, blank=True)
    required_concepts = models.TextField(blank=True)
    description = models.TextField(blank=True)
    expected_visualization = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EvaluationRun(models.Model):
    name = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_tests = models.PositiveIntegerField(default=0)
    passed_tests = models.PositiveIntegerField(default=0)
    failed_tests = models.PositiveIntegerField(default=0)
    pass_percentage = models.FloatField(default=0)
    summary = models.JSONField(default=dict)


class EvaluationResult(models.Model):
    run = models.ForeignKey(EvaluationRun, on_delete=models.CASCADE, related_name="results")
    test = models.ForeignKey(EvaluationTest, on_delete=models.SET_NULL, null=True,
                             related_name="results")
    question = models.TextField()
    expected_answer = models.TextField()
    actual_answer = models.TextField(blank=True)
    retrieved_sources = models.JSONField(default=list)
    retrieved_chunks = models.JSONField(default=list)
    concepts_covered = models.JSONField(default=list)
    concepts_missing = models.JSONField(default=list)
    cited_relevant_source = models.BooleanField(default=False)
    visualization_selected = models.CharField(max_length=128, blank=True)
    execution_time_ms = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    failure_categories = models.JSONField(default=list)
