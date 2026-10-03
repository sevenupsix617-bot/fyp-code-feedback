from django.core.management.base import BaseCommand, CommandError

from feedback_app.evaluation_analysis import (
    export_day12_artifacts,
    import_manual_review_scores,
)
from feedback_app.models import EvaluationRun


class Command(BaseCommand):
    help = "Export Day 12 evaluation summaries, charts, and manual review templates."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-id",
            type=int,
            default=0,
            help="EvaluationRun id. Defaults to the latest run.",
        )
        parser.add_argument(
            "--output-dir",
            default="",
            help="Optional directory for report artifacts.",
        )
        parser.add_argument(
            "--review-limit",
            type=int,
            default=20,
            help="Number of rows to include in the manual review CSV template.",
        )
        parser.add_argument(
            "--import-review-csv",
            default="",
            help="Optional CSV with human scores to import before exporting analysis.",
        )

    def handle(self, *args, **options):
        if options["import_review_csv"]:
            updated = import_manual_review_scores(options["import_review_csv"])
            self.stdout.write(self.style.SUCCESS(f"Imported human review scores: {updated}"))

        if options["run_id"]:
            evaluation_run = EvaluationRun.objects.filter(pk=options["run_id"]).first()
        else:
            evaluation_run = EvaluationRun.objects.first()

        if not evaluation_run:
            raise CommandError("No EvaluationRun found. Run run_evaluation_dataset first.")

        summary = export_day12_artifacts(
            evaluation_run,
            output_dir=options["output_dir"] or None,
            review_limit=options["review_limit"],
        )
        automatic = summary["automatic_metrics"]
        human = summary["human_review_metrics"]

        self.stdout.write(self.style.SUCCESS(f"Exported Day 12 artifacts for run #{evaluation_run.id}"))
        self.stdout.write(f"Run mode: {evaluation_run.run_mode}")
        self.stdout.write(f"Total results: {automatic['total_results']}")
        self.stdout.write(f"Category accuracy: {automatic['category_accuracy']}")
        self.stdout.write(f"JSON compliance rate: {automatic['json_compliance_rate']}")
        self.stdout.write(f"Solution leakage rate: {automatic['solution_leakage_rate']}")
        self.stdout.write(f"Runtime evidence usage rate: {automatic['runtime_evidence_usage_rate']}")
        self.stdout.write(f"AI/API error count: {automatic['ai_error_count']}")
        self.stdout.write(f"Human review coverage: {human['review_coverage_rate']}")
        for name, path in summary["artifact_paths"].items():
            self.stdout.write(f"{name}: {path}")

        if summary["dry_run_caveat"]:
            self.stdout.write(
                self.style.WARNING(
                    "This is a dry-run analysis. Use it to verify reporting flow, not as real LLM evidence."
                )
            )
