# Generated manually for Day 5 legacy record classification.

from django.db import migrations, models


def mark_legacy_unvalidated_records(apps, schema_editor):
    CodeFeedbackRecord = apps.get_model("feedback_app", "CodeFeedbackRecord")
    CodeFeedbackRecord.objects.filter(schema_validation_status="").update(
        schema_validation_status="legacy_unvalidated"
    )


def unmark_legacy_unvalidated_records(apps, schema_editor):
    CodeFeedbackRecord = apps.get_model("feedback_app", "CodeFeedbackRecord")
    CodeFeedbackRecord.objects.filter(schema_validation_status="legacy_unvalidated").update(
        schema_validation_status=""
    )


class Migration(migrations.Migration):

    dependencies = [
        ("feedback_app", "0005_feedback_schema_metadata"),
    ]

    operations = [
        migrations.AlterField(
            model_name="codefeedbackrecord",
            name="schema_validation_status",
            field=models.CharField(blank=True, default="not_validated", max_length=50),
        ),
        migrations.RunPython(
            mark_legacy_unvalidated_records,
            unmark_legacy_unvalidated_records,
        ),
    ]
