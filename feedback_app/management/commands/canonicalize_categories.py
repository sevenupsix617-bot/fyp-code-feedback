from django.core.management.base import BaseCommand

from feedback_app.feedback_schema import ERROR_CATEGORIES, canonicalize_error_category
from feedback_app.models import CodeFeedbackRecord
from feedback_app.taxonomy import canonicalize_topic_reference, peci_error_label


class Command(BaseCommand):
    help = "Canonicalize legacy v1/v2 error labels and stored concept wording."

    def handle(self, *args, **options):
        total = 0
        changed = 0
        unknown = 0
        concepts_changed = 0
        unknown_concepts = 0

        for record in CodeFeedbackRecord.objects.all().iterator():
            total += 1
            updates = {}

            if record.classification_outcome == "peci_error":
                display_label = record.peci_error_label or peci_error_label(
                    record.peci_error_code
                )
                if display_label and record.error_category != display_label:
                    updates["error_category"] = display_label
            elif not record.classification_outcome:
                for field_name in ("error_category", "ground_truth_category"):
                    value = getattr(record, field_name)
                    if not value:
                        continue

                    canonical_value, _ = canonicalize_error_category(value)
                    if canonical_value == "Unknown" and value not in ERROR_CATEGORIES:
                        unknown += 1
                    if canonical_value != value:
                        updates[field_name] = canonical_value
                if record.error_category and not record.legacy_error_category:
                    updates["legacy_error_category"] = record.error_category

            if record.concept_reference:
                canonical_concept, _ = canonicalize_topic_reference(
                    record.concept_reference
                )
                if canonical_concept == "Unknown" and record.concept_reference != "Unknown":
                    unknown_concepts += 1
                if canonical_concept != record.concept_reference:
                    updates["concept_reference"] = canonical_concept
                    concepts_changed += 1

            if updates:
                CodeFeedbackRecord.objects.filter(pk=record.pk).update(**updates)
                changed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Canonicalized categories for {changed}/{total} records. "
                f"Concept references changed: {concepts_changed}. "
                f"Unrecognized categories mapped to Unknown: {unknown}. "
                f"Unrecognized concepts mapped to Unknown: {unknown_concepts}."
            )
        )
