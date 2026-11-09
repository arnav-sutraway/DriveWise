from django.db import models


class Document(models.Model):
    """One source in the knowledge base, e.g. the Georgia Driver's Manual PDF."""

    title = models.CharField(max_length=255)
    state = models.CharField(max_length=64, blank=True)
    edition = models.CharField(max_length=32, blank=True)
    source_path = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
