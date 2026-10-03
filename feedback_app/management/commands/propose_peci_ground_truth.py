from django.core.management.base import BaseCommand, CommandError

from feedback_app.peci_ax_evaluation import propose_peci_ground_truth


VALID_PROVIDERS = {"deepseek", "kimi"}


class Command(BaseCommand):
    help = (
        "Ask one LLM to propose PECI A-X labels for the 55 Refactory samples. "
        "The proposals are not ground truth until a researcher fills the confirmed columns."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dataset-path",
            default="",
            help="Path to evaluation_samples.json. Defaults to the project root file.",
        )
        parser.add_argument(
            "--provider",
            default="deepseek",
            help="Proposal provider: deepseek (default) or kimi.",
        )
        parser.add_argument(
            "--output-path",
            default="",
            help=(
                "Proposal CSV path. Defaults to "
                "evaluation_reports/peci_ax_ground_truth_proposals.csv."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Print all 55 proposals without writing a CSV or database rows. "
                "This still calls the selected paid LLM API."
            ),
        )
        parser.add_argument(
            "--retry-attempts",
            type=int,
            default=2,
            help="Maximum attempts for invalid JSON, invalid A-X codes, or retryable API errors.",
        )
        parser.add_argument(
            "--retry-delay",
            type=float,
            default=3,
            help="Seconds to wait between retry attempts.",
        )

    def handle(self, *args, **options):
        provider = options["provider"].strip().lower()
        if provider not in VALID_PROVIDERS:
            raise CommandError(f"Unknown provider {provider!r}; use deepseek or kimi.")

        try:
            result = propose_peci_ground_truth(
                dataset_path=options["dataset_path"] or None,
                provider=provider,
                output_path=options["output_path"] or None,
                dry_run=options["dry_run"],
                retry_attempts=options["retry_attempts"],
                retry_delay=options["retry_delay"],
                progress_callback=self.stdout.write,
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(f"Dataset: {result['dataset_path']}")
        self.stdout.write(f"Provider: {result['provider']}")
        self.stdout.write(f"Proposal count: {len(result['proposals'])}")
        if result["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run complete: no proposal CSV and no database rows were written."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Proposal CSV: {result['output_path']}")
            )
            self.stdout.write(
                self.style.WARNING(
                    "The proposed labels are not final ground truth. Review every row, "
                    "fill confirmed_outcome and confirmed_peci_code, and save the reviewed "
                    "file as evaluation_reports/peci_ax_ground_truth_confirmed.csv."
                )
            )
