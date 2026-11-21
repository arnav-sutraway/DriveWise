from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="category",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="document",
            name="description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="document",
            name="jurisdiction",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.AddField(
            model_name="document",
            name="last_processed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="document",
            name="processing_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="document",
            name="processing_status",
            field=models.CharField(choices=[("pending", "Pending"), ("processing", "Processing"), ("indexed", "Indexed"), ("error", "Error")], default="pending", max_length=16),
        ),
        migrations.AddField(
            model_name="document",
            name="raw_text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="document",
            name="source_organization",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="document",
            name="source_url",
            field=models.URLField(blank=True, max_length=2000),
        ),
        migrations.CreateModel(
            name="SystemConfiguration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chunk_size", models.PositiveIntegerField(default=220)),
                ("chunk_overlap", models.PositiveIntegerField(default=40)),
                ("top_k", models.PositiveIntegerField(default=5)),
                ("similarity_threshold", models.FloatField(default=0.55)),
                ("embedding_model", models.CharField(blank=True, max_length=255)),
                ("llm_model", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
