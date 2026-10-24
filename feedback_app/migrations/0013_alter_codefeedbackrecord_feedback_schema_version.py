from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("feedback_app", "0012_codefeedbackrecord_solved"),
    ]

    operations = [
        migrations.AlterField(
            model_name="codefeedbackrecord",
            name="feedback_schema_version",
            field=models.CharField(
                blank=True, default="feedback_schema_v4_revised_taxonomy", max_length=50,
            ),
        ),
    ]
