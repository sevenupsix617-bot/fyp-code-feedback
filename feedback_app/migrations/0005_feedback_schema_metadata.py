# Generated manually for the Day 5 prompt and schema validation upgrade.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("feedback_app", "0004_comparison_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="feedback_schema_version",
            field=models.CharField(blank=True, default="feedback_schema_v1", max_length=50),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="schema_validation_status",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="schema_validation_notes",
            field=models.TextField(blank=True, default=""),
        ),
    ]
