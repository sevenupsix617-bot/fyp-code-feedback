# Generated manually for the Semester 2 data model upgrade.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("feedback_app", "0002_codefeedbackrecord_llm_used"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Question",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("problem_statement", models.TextField()),
                ("lecture_objective", models.TextField(blank=True, default="")),
                ("sample_input", models.TextField(blank=True, default="")),
                ("expected_output", models.TextField(blank=True, default="")),
                ("test_harness", models.TextField(blank=True, default="")),
                ("difficulty", models.CharField(blank=True, default="", max_length=50)),
                ("topic_tags", models.CharField(blank=True, default="", max_length=255)),
                (
                    "default_llm_provider",
                    models.CharField(
                        choices=[("deepseek", "DeepSeek"), ("kimi", "Kimi")],
                        default="deepseek",
                        max_length=50,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["title"],
            },
        ),
        migrations.AlterModelOptions(
            name="codefeedbackrecord",
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="question",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="feedback_app.question",
            ),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="sample_input",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="expected_output",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="execution_return_code",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="execution_timed_out",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="execution_time_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="actual_output",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="output_comparison_status",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="uses_runtime_evidence",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="suggested_next_step",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="confidence",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="prompt_version",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="prompt_text",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="llm_model_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="llm_latency_ms",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="llm_token_usage",
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="estimated_cost",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="evaluation_sample_id",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="ground_truth_category",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="json_compliance",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="solution_leakage_flag",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
