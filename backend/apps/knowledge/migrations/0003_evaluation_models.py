from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("knowledge", "0002_developer_portal"),
    ]

    operations = [
        migrations.CreateModel(
            name="EvaluationTest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.TextField()),
                ("expected_answer", models.TextField()),
                ("expected_sources", models.TextField(blank=True)),
                ("category", models.CharField(blank=True, max_length=128)),
                ("required_concepts", models.TextField(blank=True)),
                ("description", models.TextField(blank=True)),
                ("expected_visualization", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="EvaluationRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(blank=True, max_length=255)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(null=True, blank=True)),
                ("total_tests", models.PositiveIntegerField(default=0)),
                ("passed_tests", models.PositiveIntegerField(default=0)),
                ("failed_tests", models.PositiveIntegerField(default=0)),
                ("pass_percentage", models.FloatField(default=0)),
                ("summary", models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name="EvaluationResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("question", models.TextField()),
                ("expected_answer", models.TextField()),
                ("actual_answer", models.TextField(blank=True)),
                ("retrieved_sources", models.JSONField(default=list)),
                ("retrieved_chunks", models.JSONField(default=list)),
                ("concepts_covered", models.JSONField(default=list)),
                ("concepts_missing", models.JSONField(default=list)),
                ("cited_relevant_source", models.BooleanField(default=False)),
                ("visualization_selected", models.CharField(blank=True, max_length=128)),
                ("execution_time_ms", models.PositiveIntegerField(default=0)),
                ("passed", models.BooleanField(default=False)),
                ("failure_categories", models.JSONField(default=list)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="knowledge.evaluationrun")),
                ("test", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="results", to="knowledge.evaluationtest")),
            ],
        ),
    ]
