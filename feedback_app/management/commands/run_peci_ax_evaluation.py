from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from feedback_app.peci_ax_evaluation import (
    DEFAULT_CONFIRMED_FILENAME,
    run_peci_ax_evaluation,
)


class Command(BaseCommand):
    help = (
        "Run the independent PECI A-X evaluation: 55 confirmed Refactory samples x "
        "DeepSeek and Kimi x strict_scaffolded."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirmed-csv",
            default="",
            help=(
                "Researcher-confirmed A-X CSV. Defaults to "
                "evaluation_reports/peci_ax_ground_truth_confirmed.csv."
            ),
        )
        parser.add_argument(
            "--dataset-path",
            default="",
            help="Path to evaluation_samples.json. Defaults to the project root file.",
        )
        parser.add_argument(
            "--output-dir",
            default="",
            help="Report directory. Defaults to evaluation_reports/.",
        )
        parser.add_argument(
            "--run-llm",
            action="store_true",
            help="Required acknowledgement that this command makes 110 paid API calls.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=1,
            help="Student-code sandbox timeout in seconds.",
        )
        parser.add_argument(
            "--kimi-min-interval",
            type=float,
            default=0,
            help="Optional minimum seconds between Kimi calls.",
        )
        parser.add_argument(
            "--retry-attempts",
            type=int,
            default=2,
            help="Maximum attempts for retryable provider errors.",
        )
        parser.add_argument(
            "--retry-delay",
            type=float,
            default=3,
            help="Seconds to wait before retrying a retryable provider error.",
        )

    def handle(self, *args, **options):
        if not options["run_llm"]:
            raise CommandError(
                "This command is the real 110-call A-X evaluation. Review and complete "
                "the confirmed CSV first, then rerun with --run-llm."
            )

        confirmed_csv = Path(
            options["confirmed_csv"]
            or settings.BASE_DIR / "evaluation_reports" / DEFAULT_CONFIRMED_FILENAME
        )
        try:
            result = run_peci_ax_evaluation(
                confirmed_csv_path=confirmed_csv,
                dataset_path=options["dataset_path"] or None,
                output_dir=options["output_dir"] or None,
                timeout=options["timeout"],
                provider_min_intervals={"kimi": options["kimi_min_interval"]},
                retry_attempts=options["retry_attempts"],
                retry_delay=options["retry_delay"],
                progress_callback=self.stdout.write,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        summary = result["summary"]
        self.stdout.write(
            self.style.SUCCESS(
                f"Created PECI A-X evaluation run #{result['run'].id}."
            )
        )
        self.stdout.write(f"Samples: {summary['sample_count']}")
        self.stdout.write(f"Total results: {summary['total_results']}")
        self.stdout.write(f"Overall accuracy: {summary['overall_accuracy']}")
        self.stdout.write(f"AI/API error count: {summary['ai_error_count']}")
        self.stdout.write(f"Leakage rate: {summary['solution_leakage_rate']}")
        self.stdout.write(f"Summary JSON: {result['output_paths']['summary_json']}")
        self.stdout.write(f"Summary MD: {result['output_paths']['summary_md']}")
        self.stdout.write(
            f"Confusion matrix CSV: {result['output_paths']['confusion_matrix_csv']}"
        )
