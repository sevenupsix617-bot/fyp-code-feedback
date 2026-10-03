# Generated manually for the Day 4 output comparison upgrade.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("feedback_app", "0003_question_feedback_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="comparison_mode",
            field=models.CharField(
                choices=[
                    ("strict", "Strict exact output"),
                    ("normalized", "Normalized beginner-friendly output"),
                ],
                default="normalized",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="codefeedbackrecord",
            name="comparison_mode",
            field=models.CharField(
                choices=[
                    ("strict", "Strict exact output"),
                    ("normalized", "Normalized beginner-friendly output"),
                ],
                default="normalized",
                max_length=30,
            ),
        ),
    ]
