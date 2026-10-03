from django.core.management.base import BaseCommand, CommandError

from feedback_app.feedback_schema import FEEDBACK_SCHEMA_VERSION
from feedback_app.evaluation_runner import (
    DEFAULT_EVALUATION_PROMPT_VERSIONS,
    DEFAULT_EVALUATION_PROVIDERS,
    run_evaluation_dataset,
)
from feedback_app.prompt_builder import PROMPT_VERSION_CHOICES


VALID_PROMPT_VERSIONS = {value for value, _label in PROMPT_VERSION_CHOICES}
VALID_PROVIDERS = {"deepseek", "kimi"}


def _parse_csv(value, default):
    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


class Command(BaseCommand):
    help = (
        "Run the FYP batch evaluation dataset. By default this is a safe dry run; "
        "add --run-llm only after confirming API usage."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-path",
            default="",
            help="Path to evaluation_samples.json. Defaults to the project root export.",
        )
        parser.add_argument(
            "--providers",
            default=",".join(DEFAULT_EVALUATION_PROVIDERS),
            help="Comma-separated providers: deepseek,kimi.",
        )
        parser.add_argument(
            "--prompt-versions",
            default=",".join(DEFAULT_EVALUATION_PROMPT_VERSIONS),
            help="Comma-separated prompt versions: baseline,context_aware,strict_scaffolded.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Optional sample limit for pilot runs. 0 means all samples.",
        )
        parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Optional zero-based sample offset for slow batched API runs.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=1,
            help="Sandbox timeout in seconds.",
        )
        parser.add_argument(
            "--run-llm",
            action="store_true",
            help="Actually call LLM APIs. Omit this flag for the free offline dry run.",
        )
        parser.add_argument(
            "--kimi-min-interval",
            type=float,
            default=0,
            help="Minimum seconds between Kimi API calls, useful for low-RPM pilot runs.",
        )
        parser.add_argument(
            "--retry-attempts",
            type=int,
            default=2,
            help="Maximum attempts for retryable LLM API failures.",
        )
        parser.add_argument(
            "--retry-delay",
            type=float,
            default=3,
            help="Seconds to wait before retrying retryable LLM API failures.",
        )
        parser.add_argument(
            "--name",
            default="",
            help="Optional name for this evaluation run.",
        )
        parser.add_argument(
            "--output-dir",
            default="",
            help="Optional directory for exported result JSON and summary files.",
        )

    def handle(self, *args, **options):
        providers = _parse_csv(options["providers"], DEFAULT_EVALUATION_PROVIDERS)
        prompt_versions = _parse_csv(
            options["prompt_versions"],
            DEFAULT_EVALUATION_PROMPT_VERSIONS,
        )

        unknown_providers = sorted(set(providers) - VALID_PROVIDERS)
        if unknown_providers:
            raise CommandError(f"Unknown providers: {', '.join(unknown_providers)}")

        unknown_prompt_versions = sorted(set(prompt_versions) - VALID_PROMPT_VERSIONS)
        if unknown_prompt_versions:
            raise CommandError(
                f"Unknown prompt versions: {', '.join(unknown_prompt_versions)}"
            )

        if options["run_llm"] and FEEDBACK_SCHEMA_VERSION == "feedback_schema_v3_peci":
            raise CommandError(
                "Real LLM evaluation is blocked because evaluation_samples.json "
                "contains legacy v1/v2 ground-truth labels, not PECI A-X codes. "
                "Create and review a separate v3 A-X annotation file before running "
                "new API evaluation. The offline dry run remains available."
            )

        try:
            result = run_evaluation_dataset(
                dataset_path=options["dataset_path"] or None,
                providers=providers,
                prompt_versions=prompt_versions,
                offset=options["offset"],
                limit=options["limit"] or None,
                run_llm=options["run_llm"],
                timeout=options["timeout"],
                name=options["name"],
                output_dir=options["output_dir"] or None,
                provider_min_intervals={
                    "kimi": options["kimi_min_interval"],
                },
                retry_attempts=options["retry_attempts"],
                retry_delay=options["retry_delay"],
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        run = result["run"]
        summary = result["summary"]
        self.stdout.write(self.style.SUCCESS(f"Created evaluation run #{run.id}: {run.name}"))
        self.stdout.write(f"Run mode: {run.run_mode}")
        self.stdout.write(f"Dataset size: {run.dataset_size}")
        self.stdout.write(f"Total results: {summary['total_results']}")
        self.stdout.write(f"Category accuracy: {summary['category_accuracy']}")
        self.stdout.write(f"JSON compliance rate: {summary['json_compliance_rate']}")
        self.stdout.write(f"Strict schema rate: {summary['strict_schema_rate']}")
        self.stdout.write(f"Solution leakage rate: {summary['solution_leakage_rate']}")
        self.stdout.write(f"Runtime evidence usage rate: {summary['runtime_evidence_usage_rate']}")
        self.stdout.write(f"Average latency ms: {summary['average_latency_ms']}")
        self.stdout.write(f"AI/API error count: {summary['ai_error_count']}")
        self.stdout.write(f"Results JSON: {result['output_paths']['results']}")
        self.stdout.write(f"Summary JSON: {result['output_paths']['summary_json']}")
        self.stdout.write(f"Summary MD: {result['output_paths']['summary_md']}")

        if not options["run_llm"]:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run oracle mode only validates the pipeline. "
                    "Use --run-llm after explicit API-cost confirmation for real model metrics."
                )
            )
