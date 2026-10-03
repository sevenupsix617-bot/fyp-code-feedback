import csv
import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from feedback_app.evaluation_analysis import (
    MANUAL_REVIEW_COLUMNS,
    _bar_chart_svg,
    _confusion_matrix_svg,
    _result_to_dict,
    _write_json,
    render_day12_markdown,
    summarise_human_review,
)
from feedback_app.evaluation_runner import summarise_evaluation_results
from feedback_app.models import EvaluationResult, EvaluationRun


def _parse_ids(value):
    ids = []
    for item in str(value or "").split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError as exc:
            raise CommandError(f"Invalid run id: {item}") from exc
    if not ids:
        raise CommandError("--run-ids is required.")
    return ids


def _parse_csv(value):
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _slugify(value):
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value).strip()).strip("_")
    return slug or "aggregate_evaluation"


def _write_manual_review_csv(rows, path, *, limit=20):
    selected = rows[: int(limit)] if limit else rows
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANUAL_REVIEW_COLUMNS)
        writer.writeheader()
        for result in selected:
            writer.writerow(
                {
                    "database_id": result["database_id"],
                    "sample_id": result["sample_id"],
                    "source_record_path": result["source_record_path"],
                    "provider": result["provider"],
                    "prompt_version": result["prompt_version"],
                    "ground_truth_category": result["ground_truth_category"],
                    "predicted_category": result["predicted_category"],
                    "category_match": result["category_match"],
                    "feedback_text": result["feedback_text"],
                    "suggested_next_step": result["suggested_next_step"],
                    "helpfulness_score": result.get("helpfulness_score") or "",
                    "lecture_alignment_score": result.get("lecture_alignment_score") or "",
                    "actionability_score": result.get("actionability_score") or "",
                    "human_solution_leakage": ""
                    if result.get("human_solution_leakage") is None
                    else result["human_solution_leakage"],
                    "human_review_notes": result.get("human_review_notes", ""),
                }
            )


def _score_reference_review(result):
    if result.get("ai_error"):
        return 1, 1, 1, "Reference only: API/model error; review should be excluded or rerun."

    if result.get("solution_leakage_flag"):
        return 1, 2, 1, "Reference only: automatic leakage flag triggered; human must inspect."

    if result.get("category_match") is True:
        helpfulness = 4
    elif result.get("predicted_category"):
        helpfulness = 2
    else:
        helpfulness = 1

    lecture_alignment = 4 if result.get("concept_reference") else 3
    actionability = 4 if result.get("suggested_next_step") else 3
    if result.get("uses_runtime_evidence"):
        helpfulness = min(helpfulness + 1, 5)
        actionability = min(actionability + 1, 5)

    notes = (
        "Reference only: generated from automatic signals, not a human review. "
        "Replace these values after manual inspection before reporting human-review metrics."
    )
    return helpfulness, lecture_alignment, actionability, notes


def _write_reference_review_csv(rows, path, *, limit=20):
    selected = rows[: int(limit)] if limit else rows
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANUAL_REVIEW_COLUMNS)
        writer.writeheader()
        for result in selected:
            helpfulness, alignment, actionability, notes = _score_reference_review(result)
            writer.writerow(
                {
                    "database_id": result["database_id"],
                    "sample_id": result["sample_id"],
                    "source_record_path": result["source_record_path"],
                    "provider": result["provider"],
                    "prompt_version": result["prompt_version"],
                    "ground_truth_category": result["ground_truth_category"],
                    "predicted_category": result["predicted_category"],
                    "category_match": result["category_match"],
                    "feedback_text": result["feedback_text"],
                    "suggested_next_step": result["suggested_next_step"],
                    "helpfulness_score": helpfulness,
                    "lecture_alignment_score": alignment,
                    "actionability_score": actionability,
                    "human_solution_leakage": bool(result.get("solution_leakage_flag")),
                    "human_review_notes": notes,
                }
            )


def _duplicate_keys(rows):
    seen = set()
    duplicates = set()
    for result in rows:
        key = (
            result["sample_id"],
            result["provider"],
            result["prompt_version"],
        )
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return sorted(duplicates)


def _dedupe_latest(rows):
    deduped = {}
    for result in rows:
        key = (
            result["sample_id"],
            result["provider"],
            result["prompt_version"],
        )
        previous = deduped.get(key)
        if previous is None or result["evaluation_run_id"] > previous["evaluation_run_id"]:
            deduped[key] = result

    return sorted(
        deduped.values(),
        key=lambda item: (
            item["sample_id"],
            item["provider"],
            item["prompt_version"],
            item["evaluation_run_id"],
        ),
    )


class Command(BaseCommand):
    help = "Aggregate several batched EvaluationRun records into one Day 12 report."

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-ids",
            required=True,
            help="Comma-separated EvaluationRun ids to aggregate.",
        )
        parser.add_argument(
            "--providers",
            default="",
            help="Optional comma-separated provider filter, such as deepseek or kimi.",
        )
        parser.add_argument(
            "--prompt-versions",
            default="",
            help="Optional comma-separated prompt version filter.",
        )
        parser.add_argument(
            "--name",
            default="Day 12 aggregate evaluation",
            help="Human-readable name for the aggregate report.",
        )
        parser.add_argument(
            "--slug",
            default="",
            help="Optional filename prefix. Defaults to a timestamped slug from --name.",
        )
        parser.add_argument(
            "--output-dir",
            default="",
            help="Optional directory for aggregate report artifacts.",
        )
        parser.add_argument(
            "--review-limit",
            type=int,
            default=20,
            help="Number of rows to include in the manual review CSV template.",
        )
        parser.add_argument(
            "--dedupe-latest",
            action="store_true",
            help=(
                "When repeated sample/provider/prompt keys exist across reruns, "
                "keep only the row from the latest EvaluationRun id."
            ),
        )

    def handle(self, *args, **options):
        run_ids = _parse_ids(options["run_ids"])
        runs = list(EvaluationRun.objects.filter(id__in=run_ids).order_by("id"))
        found_ids = {run.id for run in runs}
        missing_ids = [run_id for run_id in run_ids if run_id not in found_ids]
        if missing_ids:
            raise CommandError(f"EvaluationRun id(s) not found: {missing_ids}")

        providers = _parse_csv(options["providers"])
        prompt_versions = _parse_csv(options["prompt_versions"])

        queryset = EvaluationResult.objects.filter(evaluation_run_id__in=run_ids)
        if providers:
            queryset = queryset.filter(provider__in=providers)
        if prompt_versions:
            queryset = queryset.filter(prompt_version__in=prompt_versions)
        queryset = queryset.order_by(
            "sample_id",
            "provider",
            "prompt_version",
            "evaluation_run_id",
        )

        rows = [_result_to_dict(result) for result in queryset]
        if not rows:
            raise CommandError("No EvaluationResult rows matched the selected filters.")

        duplicate_keys = _duplicate_keys(rows)
        duplicate_count = len(duplicate_keys)
        if duplicate_keys and not options["dedupe_latest"]:
            raise CommandError(
                "Duplicate sample/provider/prompt keys found across selected runs. "
                "Use --dedupe-latest for rerun-based aggregates."
            )
        if options["dedupe_latest"]:
            rows = _dedupe_latest(rows)

        automatic = summarise_evaluation_results(rows)
        human = summarise_human_review(rows)
        run_mode_values = sorted({run.run_mode for run in runs})
        dry_run_caveat = run_mode_values == [EvaluationRun.RUN_MODE_DRY_RUN]
        dataset_names = sorted({run.dataset_name for run in runs})
        dataset_paths = sorted({run.dataset_path for run in runs if run.dataset_path})
        selected_providers = sorted({row["provider"] for row in rows})
        selected_prompt_versions = sorted({row["prompt_version"] for row in rows})
        selected_sample_ids = sorted({row["sample_id"] for row in rows})
        now = timezone.localtime()
        started_at = min(run.started_at for run in runs)
        completed_values = [run.completed_at for run in runs if run.completed_at]
        completed_at = max(completed_values) if completed_values else None
        duplicate_note = (
            f" Duplicate result keys detected and deduplicated by latest run id: {duplicate_count}."
            if duplicate_count and options["dedupe_latest"]
            else f" Duplicate result keys detected: {duplicate_count}."
            if duplicate_count
            else " No duplicate sample/provider/prompt keys detected."
        )

        summary = {
            "run": {
                "id": f"aggregate:{','.join(str(run_id) for run_id in run_ids)}",
                "name": options["name"],
                "run_mode": "+".join(run_mode_values),
                "dataset_name": ", ".join(dataset_names),
                "dataset_size": len(selected_sample_ids),
                "providers": selected_providers,
                "prompt_versions": selected_prompt_versions,
                "notes": (
                    f"Aggregated EvaluationRun ids: {run_ids}. "
                    f"Result filters: providers={providers or 'all'}, "
                    f"prompt_versions={prompt_versions or 'all'}."
                    f"{duplicate_note}"
                ),
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat() if completed_at else None,
            },
            "source_run_ids": run_ids,
            "source_dataset_paths": dataset_paths,
            "automatic_metrics": automatic,
            "human_review_metrics": human,
            "reference_review_note": (
                "The reference review CSV is pre-filled from automatic signals only. "
                "It is a scoring aid and must not be reported as completed human review."
            ),
            "dry_run_caveat": dry_run_caveat,
        }

        output_dir = Path(options["output_dir"] or settings.BASE_DIR / "evaluation_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        slug = _slugify(options["slug"] or f"{timestamp}_{options['name']}")

        summary_path = output_dir / f"{slug}_summary.json"
        markdown_path = output_dir / f"{slug}_summary.md"
        results_path = output_dir / f"{slug}_results.json"
        manual_review_path = output_dir / f"{slug}_manual_review_template.csv"
        reference_review_path = output_dir / f"{slug}_reference_review_suggestions.csv"
        accuracy_chart = output_dir / f"{slug}_accuracy_by_condition.svg"
        quality_chart = output_dir / f"{slug}_quality_rates.svg"
        distribution_chart = output_dir / f"{slug}_ground_truth_distribution.svg"
        confusion_chart = output_dir / f"{slug}_confusion_matrix.svg"

        condition_rows = [
            (key, item["category_accuracy"] or 0)
            for key, item in sorted(automatic["by_provider_prompt"].items())
        ]
        quality_rows = [
            ("Category accuracy", automatic["category_accuracy"] or 0),
            ("JSON compliance", automatic["json_compliance_rate"] or 0),
            ("Usable schema", automatic["usable_schema_rate"] or 0),
            ("Runtime evidence", automatic["runtime_evidence_usage_rate"] or 0),
            ("Solution leakage", automatic["solution_leakage_rate"] or 0),
        ]
        ground_truth_rows = sorted(
            automatic["ground_truth_counts"].items(),
            key=lambda item: (-item[1], item[0]),
        )

        _bar_chart_svg(
            "Category Accuracy by Provider and Prompt",
            condition_rows,
            accuracy_chart,
            max_value=1,
        )
        _bar_chart_svg("Automatic Quality Rates", quality_rows, quality_chart, max_value=1)
        _bar_chart_svg(
            "Ground-Truth Category Distribution",
            ground_truth_rows,
            distribution_chart,
        )
        _confusion_matrix_svg(summary, confusion_chart)

        artifact_paths = {
            "summary_json": str(summary_path),
            "summary_markdown": str(markdown_path),
            "results_json": str(results_path),
            "manual_review_csv": str(manual_review_path),
            "reference_review_csv": str(reference_review_path),
            "accuracy_chart_svg": str(accuracy_chart),
            "quality_rates_svg": str(quality_chart),
            "ground_truth_distribution_svg": str(distribution_chart),
            "confusion_matrix_svg": str(confusion_chart),
        }
        summary["artifact_paths"] = artifact_paths

        _write_json(summary_path, summary)
        _write_json(
            results_path,
            {
                "aggregate": summary["run"],
                "source_run_ids": run_ids,
                "results": rows,
            },
        )
        _write_manual_review_csv(rows, manual_review_path, limit=options["review_limit"])
        _write_reference_review_csv(rows, reference_review_path, limit=options["review_limit"])
        markdown_path.write_text(
            render_day12_markdown(summary, artifact_paths),
            encoding="utf-8",
        )

        self.stdout.write(self.style.SUCCESS("Exported aggregate Day 12 artifacts"))
        self.stdout.write(f"Run ids: {run_ids}")
        self.stdout.write(f"Filtered providers: {selected_providers}")
        self.stdout.write(f"Dataset size: {len(selected_sample_ids)}")
        self.stdout.write(f"Total results: {automatic['total_results']}")
        self.stdout.write(f"Category accuracy: {automatic['category_accuracy']}")
        self.stdout.write(f"JSON compliance rate: {automatic['json_compliance_rate']}")
        self.stdout.write(f"Solution leakage rate: {automatic['solution_leakage_rate']}")
        self.stdout.write(f"Runtime evidence usage rate: {automatic['runtime_evidence_usage_rate']}")
        self.stdout.write(f"AI/API error count: {automatic['ai_error_count']}")
        for name, path in artifact_paths.items():
            self.stdout.write(f"{name}: {path}")
