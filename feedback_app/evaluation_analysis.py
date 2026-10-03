import csv
import html
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .evaluation_runner import summarise_evaluation_results
from .models import EvaluationResult, EvaluationRun


REPORT_DIR_NAME = "evaluation_reports"
MANUAL_REVIEW_COLUMNS = [
    "database_id",
    "sample_id",
    "source_record_path",
    "provider",
    "prompt_version",
    "ground_truth_category",
    "predicted_category",
    "category_match",
    "feedback_text",
    "suggested_next_step",
    "helpfulness_score",
    "lecture_alignment_score",
    "actionability_score",
    "human_solution_leakage",
    "human_review_notes",
]


def _decimal_to_string(value):
    if isinstance(value, Decimal):
        return str(value)
    return value


def _result_to_dict(result):
    return {
        "database_id": result.id,
        "evaluation_run_id": result.evaluation_run_id,
        "sample_id": result.sample_id,
        "source_dataset": result.source_dataset,
        "source_record_path": result.source_record_path,
        "source_test_input_path": result.source_test_input_path,
        "source_test_output_path": result.source_test_output_path,
        "provider": result.provider,
        "prompt_version": result.prompt_version,
        "ground_truth_category": result.ground_truth_category,
        "predicted_category": result.predicted_category,
        "category_match": result.category_match,
        "feedback_level": result.feedback_level,
        "concept_reference": result.concept_reference,
        "feedback_text": result.feedback_text,
        "suggested_next_step": result.suggested_next_step,
        "confidence": result.confidence,
        "json_compliance": result.json_compliance,
        "schema_validation_status": result.schema_validation_status,
        "schema_validation_notes": result.schema_validation_notes,
        "solution_leakage_flag": result.solution_leakage_flag,
        "uses_runtime_evidence": result.uses_runtime_evidence,
        "execution_status": result.execution_status,
        "output_comparison_status": result.output_comparison_status,
        "actual_output": result.actual_output,
        "actual_stderr": result.actual_stderr,
        "prompt_text": result.prompt_text,
        "raw_ai_response": result.raw_ai_response,
        "ai_error": result.ai_error,
        "llm_model_name": result.llm_model_name,
        "llm_latency_ms": result.llm_latency_ms,
        "llm_token_usage": result.llm_token_usage,
        "estimated_cost": _decimal_to_string(result.estimated_cost),
        "helpfulness_score": result.helpfulness_score,
        "lecture_alignment_score": result.lecture_alignment_score,
        "actionability_score": result.actionability_score,
        "human_solution_leakage": result.human_solution_leakage,
        "human_review_notes": result.human_review_notes,
        "reviewed_at": result.reviewed_at.isoformat() if result.reviewed_at else None,
    }


def evaluation_results_to_dicts(evaluation_run):
    queryset = evaluation_run.results.all().order_by("sample_id", "provider", "prompt_version")
    return [_result_to_dict(result) for result in queryset]


def _rate(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _average(values):
    values = [value for value in values if value is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def summarise_human_review(results):
    reviewed = [
        item
        for item in results
        if any(
            item.get(field) is not None
            for field in (
                "helpfulness_score",
                "lecture_alignment_score",
                "actionability_score",
                "human_solution_leakage",
            )
        )
    ]

    return {
        "reviewed_count": len(reviewed),
        "review_coverage_rate": _rate(len(reviewed), len(results)),
        "average_helpfulness_score": _average(
            [item.get("helpfulness_score") for item in reviewed]
        ),
        "average_lecture_alignment_score": _average(
            [item.get("lecture_alignment_score") for item in reviewed]
        ),
        "average_actionability_score": _average(
            [item.get("actionability_score") for item in reviewed]
        ),
        "human_solution_leakage_rate": _rate(
            sum(1 for item in reviewed if item.get("human_solution_leakage") is True),
            len(reviewed),
        ),
    }


def build_day12_summary(evaluation_run):
    results = evaluation_results_to_dicts(evaluation_run)
    automatic_summary = summarise_evaluation_results(results)
    human_summary = summarise_human_review(results)
    dry_run_caveat = evaluation_run.run_mode == EvaluationRun.RUN_MODE_DRY_RUN

    return {
        "run": {
            "id": evaluation_run.id,
            "name": evaluation_run.name,
            "run_mode": evaluation_run.run_mode,
            "dataset_name": evaluation_run.dataset_name,
            "dataset_size": evaluation_run.dataset_size,
            "providers": evaluation_run.providers,
            "prompt_versions": evaluation_run.prompt_versions,
            "notes": evaluation_run.notes,
            "started_at": evaluation_run.started_at.isoformat(),
            "completed_at": evaluation_run.completed_at.isoformat()
            if evaluation_run.completed_at
            else None,
        },
        "automatic_metrics": automatic_summary,
        "human_review_metrics": human_summary,
        "dry_run_caveat": dry_run_caveat,
    }


def _format_metric(value):
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _safe_svg_text(value):
    return html.escape(str(value), quote=False)


def _bar_chart_svg(title, rows, path, *, width=920, row_height=34, max_value=None):
    rows = list(rows)
    max_value = max_value if max_value is not None else max([value for _label, value in rows] + [1])
    chart_left = 250
    chart_right = 40
    top = 54
    height = top + row_height * max(len(rows), 1) + 36
    bar_width = width - chart_left - chart_right

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="24" y="32" fill="#1f2937" font-family="Arial" font-size="20" font-weight="700">{_safe_svg_text(title)}</text>',
    ]

    if not rows:
        parts.append(
            '<text x="24" y="80" fill="#667085" font-family="Arial" font-size="14">No data available.</text>'
        )
    else:
        for index, (label, value) in enumerate(rows):
            y = top + index * row_height
            ratio = 0 if max_value == 0 else value / max_value
            width_px = max(2, int(bar_width * ratio))
            parts.extend(
                [
                    f'<text x="24" y="{y + 19}" fill="#344054" font-family="Arial" font-size="13">{_safe_svg_text(label)}</text>',
                    f'<rect x="{chart_left}" y="{y + 5}" width="{bar_width}" height="18" rx="4" fill="#eef2f7"/>',
                    f'<rect x="{chart_left}" y="{y + 5}" width="{width_px}" height="18" rx="4" fill="#2563eb"/>',
                    f'<text x="{chart_left + bar_width + 10}" y="{y + 19}" fill="#344054" font-family="Arial" font-size="13">{_safe_svg_text(_format_metric(value))}</text>',
                ]
            )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def _confusion_matrix_svg(summary, path):
    items = summary["automatic_metrics"].get("confusion_matrix", [])
    labels = sorted(
        {
            item["ground_truth_category"]
            for item in items
        }
        | {item["predicted_category"] for item in items}
    )
    counts = {
        (item["ground_truth_category"], item["predicted_category"]): item["count"]
        for item in items
    }
    max_count = max(counts.values() or [1])
    cell = 52
    left = 170
    top = 92
    width = left + cell * len(labels) + 50
    height = top + cell * len(labels) + 60

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="24" y="32" fill="#1f2937" font-family="Arial" font-size="20" font-weight="700">Confusion Matrix</text>',
        '<text x="24" y="58" fill="#667085" font-family="Arial" font-size="13">Rows are ground truth; columns are predicted categories.</text>',
    ]

    short_labels = {
        "Condition Error": "Cond",
        "Function Error": "Func",
        "Index Error": "Index",
        "Logic Error": "Logic",
        "Loop Boundary Error": "Loop",
        "Name Error": "Name",
        "Type Error": "Type",
        "Value Error": "Value",
    }

    for col, label in enumerate(labels):
        x = left + col * cell
        parts.append(
            f'<text x="{x + 5}" y="{top - 12}" fill="#344054" font-family="Arial" font-size="12">{_safe_svg_text(short_labels.get(label, label[:6]))}</text>'
        )

    for row, truth in enumerate(labels):
        y = top + row * cell
        parts.append(
            f'<text x="24" y="{y + 31}" fill="#344054" font-family="Arial" font-size="12">{_safe_svg_text(truth)}</text>'
        )
        for col, predicted in enumerate(labels):
            x = left + col * cell
            count = counts.get((truth, predicted), 0)
            opacity = 0.12 + (0.76 * count / max_count if max_count else 0)
            color = "#2563eb" if truth == predicted else "#b45309"
            parts.extend(
                [
                    f'<rect x="{x}" y="{y}" width="{cell - 4}" height="{cell - 4}" rx="6" fill="{color}" fill-opacity="{opacity:.3f}"/>',
                    f'<text x="{x + 18}" y="{y + 30}" fill="#1f2937" font-family="Arial" font-size="13" font-weight="700">{count}</text>',
                ]
            )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def export_manual_review_template(evaluation_run, output_dir, *, limit=20):
    rows = evaluation_run.results.all().order_by(
        "sample_id",
        "provider",
        "prompt_version",
    )
    if limit:
        rows = rows[: int(limit)]

    path = Path(output_dir) / f"run_{evaluation_run.id}_manual_review_template.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANUAL_REVIEW_COLUMNS)
        writer.writeheader()
        for result in rows:
            writer.writerow(
                {
                    "database_id": result.id,
                    "sample_id": result.sample_id,
                    "source_record_path": result.source_record_path,
                    "provider": result.provider,
                    "prompt_version": result.prompt_version,
                    "ground_truth_category": result.ground_truth_category,
                    "predicted_category": result.predicted_category,
                    "category_match": result.category_match,
                    "feedback_text": result.feedback_text,
                    "suggested_next_step": result.suggested_next_step,
                    "helpfulness_score": result.helpfulness_score or "",
                    "lecture_alignment_score": result.lecture_alignment_score or "",
                    "actionability_score": result.actionability_score or "",
                    "human_solution_leakage": ""
                    if result.human_solution_leakage is None
                    else result.human_solution_leakage,
                    "human_review_notes": result.human_review_notes,
                }
            )
    return path


def _parse_optional_score(value, field_name):
    value = str(value or "").strip()
    if not value:
        return None
    score = int(value)
    if score < 1 or score > 5:
        raise ValueError(f"{field_name} must be blank or an integer from 1 to 5.")
    return score


def _parse_optional_bool(value):
    value = str(value or "").strip().lower()
    if not value:
        return None
    if value in {"true", "1", "yes", "y"}:
        return True
    if value in {"false", "0", "no", "n"}:
        return False
    raise ValueError("human_solution_leakage must be blank, true, or false.")


def import_manual_review_scores(csv_path):
    updated = 0
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            result_id = row.get("database_id") or row.get("id")
            if not result_id:
                continue

            updates = {
                "helpfulness_score": _parse_optional_score(
                    row.get("helpfulness_score"),
                    "helpfulness_score",
                ),
                "lecture_alignment_score": _parse_optional_score(
                    row.get("lecture_alignment_score"),
                    "lecture_alignment_score",
                ),
                "actionability_score": _parse_optional_score(
                    row.get("actionability_score"),
                    "actionability_score",
                ),
                "human_solution_leakage": _parse_optional_bool(
                    row.get("human_solution_leakage")
                ),
                "human_review_notes": row.get("human_review_notes", ""),
                "reviewed_at": timezone.now(),
            }
            EvaluationResult.objects.filter(pk=result_id).update(**updates)
            updated += 1

    return updated


def render_day12_markdown(summary, artifact_paths):
    run = summary["run"]
    automatic = summary["automatic_metrics"]
    human_review = summary["human_review_metrics"]
    caveat = (
        "This run is a dry-run pipeline validation and must not be reported as real model performance."
        if summary["dry_run_caveat"]
        else "This run contains real LLM API results."
    )
    lines = [
        "# Day 12 Evaluation Analysis",
        "",
        f"- Run: {run['name']} (#{run['id']})",
        f"- Mode: {run['run_mode']}",
        f"- Dataset: {run['dataset_name']} ({run['dataset_size']} samples)",
        f"- Providers: {', '.join(run['providers'])}",
        f"- Prompt versions: {', '.join(run['prompt_versions'])}",
        f"- Notes: {run['notes']}",
        f"- Caveat: {caveat}",
        "",
        "## Automatic Metrics",
        "",
        f"- Total results: {automatic['total_results']}",
        f"- Category accuracy: {automatic['category_accuracy']}",
        f"- JSON compliance rate: {automatic['json_compliance_rate']}",
        f"- Usable schema rate: {automatic['usable_schema_rate']}",
        f"- Solution leakage rate: {automatic['solution_leakage_rate']}",
        f"- Runtime evidence usage rate: {automatic['runtime_evidence_usage_rate']}",
        f"- Average latency ms: {automatic['average_latency_ms']}",
        f"- Estimated total cost: {automatic['estimated_cost_total']}",
        f"- AI/API error count: {automatic['ai_error_count']}",
        f"- Schema status counts: {json.dumps(automatic['schema_status_counts'], sort_keys=True)}",
        "",
        "## Human Review Metrics",
        "",
        f"- Reviewed count: {human_review['reviewed_count']}",
        f"- Review coverage rate: {human_review['review_coverage_rate']}",
        f"- Average helpfulness score: {human_review['average_helpfulness_score']}",
        f"- Average lecture alignment score: {human_review['average_lecture_alignment_score']}",
        f"- Average actionability score: {human_review['average_actionability_score']}",
        f"- Human-marked solution leakage rate: {human_review['human_solution_leakage_rate']}",
        "",
        "## Artifacts",
        "",
    ]
    for name, path in artifact_paths.items():
        lines.append(f"- {name}: {path}")
    return "\n".join(lines) + "\n"


def export_day12_artifacts(evaluation_run, *, output_dir=None, review_limit=20):
    output_dir = Path(output_dir or settings.BASE_DIR / REPORT_DIR_NAME)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = build_day12_summary(evaluation_run)
    run_id = evaluation_run.id
    summary_path = output_dir / f"run_{run_id}_day12_summary.json"
    markdown_path = output_dir / f"run_{run_id}_day12_summary.md"
    manual_review_path = export_manual_review_template(
        evaluation_run,
        output_dir,
        limit=review_limit,
    )

    automatic = summary["automatic_metrics"]
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

    accuracy_chart = output_dir / f"run_{run_id}_accuracy_by_condition.svg"
    quality_chart = output_dir / f"run_{run_id}_quality_rates.svg"
    distribution_chart = output_dir / f"run_{run_id}_ground_truth_distribution.svg"
    confusion_chart = output_dir / f"run_{run_id}_confusion_matrix.svg"

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
        "manual_review_csv": str(manual_review_path),
        "accuracy_chart_svg": str(accuracy_chart),
        "quality_rates_svg": str(quality_chart),
        "ground_truth_distribution_svg": str(distribution_chart),
        "confusion_matrix_svg": str(confusion_chart),
    }
    summary["artifact_paths"] = artifact_paths

    _write_json(summary_path, summary)
    markdown_path.write_text(render_day12_markdown(summary, artifact_paths), encoding="utf-8")

    updated_run_summary = dict(evaluation_run.summary or {})
    updated_run_summary["day12_analysis"] = {
        "automatic_metrics": automatic,
        "human_review_metrics": summary["human_review_metrics"],
        "artifact_paths": artifact_paths,
        "dry_run_caveat": summary["dry_run_caveat"],
    }
    evaluation_run.summary = updated_run_summary
    evaluation_run.save(update_fields=["summary"])

    return summary
