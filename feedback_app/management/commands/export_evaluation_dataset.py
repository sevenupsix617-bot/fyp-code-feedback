from django.core.management.base import BaseCommand, CommandError

from feedback_app.evaluation_dataset import (
    DEFAULT_REFACTORY_DATA_DIR,
    HAND_CRAFTED_BOUNDARY_RECORDS,
    SELECTED_REFACTORY_RECORDS,
    build_evaluation_samples,
    export_evaluation_files,
    summarise_evaluation_samples,
    validate_evaluation_samples,
)


class Command(BaseCommand):
    help = (
        "Export and validate the real Refactory student-code evaluation dataset, "
        "plus clearly marked hand-crafted boundary samples."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--refactory-data-dir",
            default=str(DEFAULT_REFACTORY_DATA_DIR),
            help="Path to the extracted Refactory data directory that contains question_1 ... question_5.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=1,
            help="Sandbox timeout in seconds when locating each source record's first failing test case.",
        )
        parser.add_argument(
            "--refactory-only",
            action="store_true",
            help="Export only the real Refactory records and exclude supplemental boundary samples.",
        )

    def handle(self, *args, **options):
        refactory_data_dir = options["refactory_data_dir"]

        try:
            samples = build_evaluation_samples(
                refactory_data_dir,
                timeout=options["timeout"],
                include_hand_crafted=not options["refactory_only"],
            )
            errors = validate_evaluation_samples(samples)
            if errors:
                raise CommandError("\n".join(errors))
            dataset_path, source_report_path, samples = export_evaluation_files(
                refactory_data_dir,
                timeout=options["timeout"],
                include_hand_crafted=not options["refactory_only"],
            )
        except (FileNotFoundError, ValueError) as exc:
            raise CommandError(str(exc)) from exc

        summary = summarise_evaluation_samples(samples)

        self.stdout.write(self.style.SUCCESS(f"Exported dataset: {dataset_path}"))
        self.stdout.write(self.style.SUCCESS(f"Exported source report: {source_report_path}"))
        self.stdout.write(f"Total samples: {summary['total']}")
        self.stdout.write(f"Curated records: {len(SELECTED_REFACTORY_RECORDS)}")
        self.stdout.write(f"Real Refactory records: {summary['real_refactory_records']}")
        self.stdout.write(f"Hand-crafted boundary cases: {summary['hand_crafted_boundary_cases']}")
        self.stdout.write(f"Available boundary cases: {len(HAND_CRAFTED_BOUNDARY_RECORDS)}")
        self.stdout.write(f"Question distribution: {summary['question_counts']}")
        self.stdout.write(f"Ground-truth categories: {summary['category_counts']}")
        self.stdout.write(f"Runtime statuses: {summary['runtime_status_counts']}")
