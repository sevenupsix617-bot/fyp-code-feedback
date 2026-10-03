import json

from django.core.management.base import BaseCommand, CommandError

from feedback_app.ai_response import extract_json_object
from feedback_app.llm_client import call_llm_with_metadata
from feedback_app.models import Question
from feedback_app.prompt_builder import build_topic_classification_prompt
from feedback_app.taxonomy import TOPIC_TAXONOMY, serialize_topic_tags


class Command(BaseCommand):
    help = (
        "Use an LLM to propose fixed taxonomy tags for untagged questions. "
        "Run with --dry-run for human review before saving."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--provider",
            choices=("deepseek", "kimi"),
            default="deepseek",
            help="LLM provider used to propose topic tags (default: deepseek).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Call the LLM and print validated proposals without saving them.",
        )

    def handle(self, *args, **options):
        provider = options["provider"]
        dry_run = options["dry_run"]
        questions = [
            question
            for question in Question.objects.order_by("id")
            if not question.topic_tags.strip()
        ]

        if not questions:
            self.stdout.write(self.style.SUCCESS("No untagged questions found."))
            return

        mode = "DRY RUN" if dry_run else "SAVE"
        self.stdout.write(
            f"{mode}: tagging {len(questions)} untagged question(s) with {provider}."
        )

        saved_count = 0
        failures = []
        for question in questions:
            try:
                prompt = build_topic_classification_prompt(
                    question.problem_statement,
                    question.lecture_objective,
                )
                response = call_llm_with_metadata(prompt, provider)
                topic_ids = self._validated_topic_ids(response.get("content", ""))
                serialized_tags = serialize_topic_tags(topic_ids)
            except (CommandError, ValueError, TypeError, json.JSONDecodeError) as exc:
                failures.append(f"Question #{question.pk} {question.title!r}: {exc}")
                self.stderr.write(self.style.ERROR(failures[-1]))
                continue
            except Exception as exc:
                failures.append(
                    f"Question #{question.pk} {question.title!r}: provider error: {exc}"
                )
                self.stderr.write(self.style.ERROR(failures[-1]))
                continue

            labels = [TOPIC_TAXONOMY[topic_id]["label"] for topic_id in topic_ids]
            action = "would save" if dry_run else "saved"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Question #{question.pk} {question.title!r}: {action} "
                    f"{serialized_tags} ({', '.join(labels)})"
                )
            )

            if not dry_run:
                question.topic_tags = serialized_tags
                question.save(update_fields=["topic_tags", "updated_at"])
                saved_count += 1

        if failures:
            raise CommandError(
                f"Topic tagging finished with {len(failures)} failure(s); "
                f"{saved_count} question(s) saved. Review the errors above."
            )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run complete: no database changes were made. "
                    "Review the proposals, then rerun without --dry-run to save."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Topic tagging complete: {saved_count} question(s) saved."
                )
            )

    @staticmethod
    def _validated_topic_ids(raw_response):
        payload = json.loads(extract_json_object(raw_response))
        if not isinstance(payload, dict):
            raise CommandError("response must be one JSON object")

        topic_ids = payload.get("topic_tags")
        if not isinstance(topic_ids, list) or not topic_ids:
            raise CommandError("topic_tags must be a non-empty JSON list")
        if not all(isinstance(topic_id, str) for topic_id in topic_ids):
            raise CommandError("every topic_tags value must be a string")

        unknown = sorted(set(topic_ids) - set(TOPIC_TAXONOMY))
        if unknown:
            raise CommandError(
                "unknown topic id(s): " + ", ".join(unknown)
            )

        return [topic_id for topic_id in TOPIC_TAXONOMY if topic_id in topic_ids]
