import json
import time
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Case, Count, IntegerField, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .ai_response import detect_solution_leakage, parse_ai_feedback_with_metadata
from .analytics import build_class_analytics, build_skill_timeline, build_student_profile
from .code_runner import run_python_code
from .feedback_schema import FEEDBACK_SCHEMA_VERSION
from .forms import CodeSubmitForm, StudentCodeSubmitForm
from .json_repair import (
    combine_json_repair_responses,
    json_repair_schema_notes,
    merge_llm_call_metadata,
    should_retry_invalid_json,
)
from .llm_client import call_llm_with_metadata, get_llm_model_name
from .models import CodeFeedbackRecord, EvaluationRun, Question
from .output_comparison import (
    COMPARISON_MODE_NORMALIZED,
    COMPARISON_MODE_STRICT,
    EXACT_MATCH,
    NORMALIZED_MATCH,
    compare_outputs,
)
from .prompt_builder import (
    PROMPT_STRICT_SCAFFOLDED,
    build_feedback_prompt,
    build_json_repair_prompt,
)


FINAL_EVALUATION_REPORTS = [
    {
        "title": "Current PECI A-X Independent Evaluation",
        "badge": "Current taxonomy evidence",
        "filename": "peci_ax_evaluation_summary.json",
        "summary_filename": "peci_ax_evaluation_summary.md",
        "description": (
            "55 Refactory submissions re-annotated for the current PECI A-X taxonomy, "
            "tested with 2 providers and the live strict-scaffolded prompt."
        ),
    },
    {
        "title": "Day 12 Refactory Main Evaluation",
        "badge": "Main evidence",
        "filename": "day12_deepseek_kimi_refactory_55_final_real_llm_summary.json",
        "summary_filename": "day12_deepseek_kimi_refactory_55_final_real_llm_summary.md",
        "description": "55 real Refactory student submissions, 2 providers, and 3 prompt versions.",
    },
    {
        "title": "Day 14 Boundary Evaluation",
        "badge": "Supplemental check",
        "filename": "day14_boundary_cases_real_llm_final_summary.json",
        "summary_filename": "day14_boundary_cases_real_llm_final_summary.md",
        "description": "12 hand-crafted boundary cases for syntax, input, timeout, and related edge cases.",
    },
]


def _require_staff(user):
    if not user.is_staff:
        raise PermissionDenied("This page is only available to instructor accounts.")


def _latest_record_is_solved(record):
    if record.solved:
        return True
    return bool(
        record.classification_outcome == "no_error"
        and record.execution_status == "success"
        and record.output_comparison_status in {EXACT_MATCH, NORMALIZED_MATCH}
    )


def _build_student_question_status(user, questions):
    question_list = list(questions)
    question_ids = [question.pk for question in question_list]
    attempt_counts = defaultdict(int)
    latest_records = {}

    records = CodeFeedbackRecord.objects.filter(
        user=user,
        question_id__in=question_ids,
    ).order_by("question_id", "-created_at", "-id")
    for record in records:
        attempt_counts[record.question_id] += 1
        latest_records.setdefault(record.question_id, record)

    status_map = {}
    for question in question_list:
        attempts = attempt_counts[question.pk]
        latest_record = latest_records.get(question.pk)
        if latest_record is None:
            status = "not_started"
            status_badge = "Not started"
        elif _latest_record_is_solved(latest_record):
            status = "solved"
            status_badge = "Solved"
        else:
            status = "in_progress"
            attempt_label = "attempt" if attempts == 1 else "attempts"
            status_badge = f"In progress - {attempts} {attempt_label}"

        status_map[question.pk] = {"status": status, "attempts": attempts}
        question.status = status
        question.attempts = attempts
        question.status_badge = status_badge

    status_priority = {"in_progress": 0, "not_started": 1, "solved": 2}
    sorted_questions = sorted(
        question_list,
        key=lambda question: (
            status_priority[question.status],
            question.title.casefold(),
        ),
    )
    ordered_ids = [question.pk for question in sorted_questions]
    if not ordered_ids:
        return sorted_questions, Question.objects.none(), status_map

    status_order = Case(
        *[
            When(pk=question_id, then=position)
            for position, question_id in enumerate(ordered_ids)
        ],
        default=len(ordered_ids),
        output_field=IntegerField(),
    )
    question_queryset = (
        Question.objects.filter(pk__in=ordered_ids)
        .annotate(_status_order=status_order)
        .order_by("_status_order")
    )
    return sorted_questions, question_queryset, status_map


def _format_percent(value):
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.2f}%"


def _format_percent_1(value):
    if value is None:
        return "N/A"
    return f"{float(value) * 100:.1f}%"


def _format_number(value):
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}"
    return value


def _load_json_file(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return None


def _aggregate_by_prompt(by_provider_prompt):
    totals = defaultdict(lambda: {"correct": 0.0, "total": 0})
    for key, item in (by_provider_prompt or {}).items():
        try:
            _provider, prompt_version = key.split(":", 1)
        except ValueError:
            prompt_version = key
        total = item.get("total") or 0
        accuracy = item.get("category_accuracy")
        if accuracy is None:
            continue
        totals[prompt_version]["correct"] += float(accuracy) * total
        totals[prompt_version]["total"] += total

    return {
        prompt: values["correct"] / values["total"]
        for prompt, values in totals.items()
        if values["total"]
    }


def _aggregate_by_provider_from_conditions(by_provider_prompt):
    totals = defaultdict(lambda: {"correct": 0.0, "total": 0})
    for key, item in (by_provider_prompt or {}).items():
        try:
            provider, _prompt_version = key.split(":", 1)
        except ValueError:
            provider = key
        total = item.get("total") or 0
        accuracy = item.get("category_accuracy")
        if accuracy is None:
            continue
        totals[provider]["correct"] += float(accuracy) * total
        totals[provider]["total"] += total

    return {
        provider: values["correct"] / values["total"]
        for provider, values in totals.items()
        if values["total"]
    }


def _aggregate_latency_by_provider(results_rows):
    latency = defaultdict(list)
    for row in results_rows:
        provider = row.get("provider")
        value = row.get("llm_latency_ms")
        if provider and value is not None:
            latency[provider].append(float(value))

    return {
        provider: sum(values) / len(values)
        for provider, values in latency.items()
        if values
    }


def _category_recall(results_rows, category):
    rows = [row for row in results_rows if row.get("ground_truth_category") == category]
    if not rows:
        return None
    correct = sum(1 for row in rows if row.get("category_match"))
    predicted_counts = defaultdict(int)
    for row in rows:
        predicted_counts[row.get("predicted_category") or "N/A"] += 1
    confusions = ", ".join(
        f"{label} {count}"
        for label, count in sorted(predicted_counts.items(), key=lambda item: (-item[1], item[0]))
        if label != category
    )
    return {
        "total": len(rows),
        "correct": correct,
        "recall": correct / len(rows),
        "confusions": confusions,
    }


def _build_day12_display(payload):
    automatic = payload.get("automatic_metrics", {}) or {}
    artifact_paths = payload.get("artifact_paths", {}) or {}
    by_provider_prompt = automatic.get("by_provider_prompt", {}) or {}
    by_prompt = _aggregate_by_prompt(by_provider_prompt)
    by_provider = _aggregate_by_provider_from_conditions(by_provider_prompt)

    results_payload = _load_json_file(artifact_paths.get("results_json"))
    results_rows = (results_payload or {}).get("results", [])
    latency_by_provider = _aggregate_latency_by_provider(results_rows)
    function_recall = _category_recall(results_rows, "Function Error")
    logic_recall = _category_recall(results_rows, "Logic Error")

    baseline = by_prompt.get("baseline")
    context_aware = by_prompt.get("context_aware")
    strict_scaffolded = by_prompt.get("strict_scaffolded")
    runtime_gain = (
        (context_aware - baseline) * 100
        if context_aware is not None and baseline is not None
        else None
    )

    provider_rows = []
    for provider in sorted(by_provider):
        provider_rows.append(
            {
                "provider": provider.title(),
                "accuracy": _format_percent_1(by_provider.get(provider)),
                "latency": f"{latency_by_provider[provider] / 1000:.1f}s"
                if provider in latency_by_provider
                else "N/A",
            }
        )

    prompt_rows = [
        {
            "prompt": "Baseline",
            "accuracy": _format_percent_1(baseline),
            "note": "Question + code only; no runtime evidence.",
        },
        {
            "prompt": "Context-aware",
            "accuracy": _format_percent_1(context_aware),
            "note": "Adds execution status, actual output, expected output, and comparison.",
        },
        {
            "prompt": "Strict-scaffolded",
            "accuracy": _format_percent_1(strict_scaffolded),
            "note": "Adds stricter anti-leakage and schema rules.",
        },
    ]

    key_findings = []
    if baseline is not None and context_aware is not None:
        key_findings.append(
            {
                "title": "Runtime evidence is the main improvement",
                "metric": f"{_format_percent_1(baseline)} -> {_format_percent_1(context_aware)}",
                "body": (
                    "Context-aware prompting substantially improved error-category recognition "
                    f"over baseline ({runtime_gain:.1f} percentage points)."
                ),
            }
        )

    if by_provider:
        best_provider = max(by_provider, key=by_provider.get)
        other_providers = [provider for provider in by_provider if provider != best_provider]
        comparison_text = ""
        if other_providers:
            other = other_providers[0]
            comparison_text = (
                f"{best_provider.title()} reached {_format_percent_1(by_provider[best_provider])} "
                f"vs {other.title()} {_format_percent_1(by_provider[other])}."
            )
        latency_text = ""
        if "kimi" in latency_by_provider and "deepseek" in latency_by_provider:
            latency_text = (
                f" Average latency was about {latency_by_provider['kimi'] / 1000:.1f}s for Kimi "
                f"vs {latency_by_provider['deepseek'] / 1000:.1f}s for DeepSeek."
            )
        key_findings.append(
            {
                "title": "Kimi was more accurate but slower and more costly",
                "metric": _format_percent_1(by_provider.get(best_provider)),
                "body": (
                    f"{comparison_text}{latency_text} Cost notes are kept in the Day 12 API cost estimate."
                ).strip(),
            }
        )

    if context_aware is not None and strict_scaffolded is not None:
        strict_delta = (strict_scaffolded - context_aware) * 100
        key_findings.append(
            {
                "title": "Strict scaffolding did not improve accuracy further",
                "metric": f"{_format_percent_1(strict_scaffolded)}",
                "body": (
                    "Strict-scaffolded prompting was slightly below context-aware prompting "
                    f"({strict_delta:.1f} percentage points), suggesting a small accuracy trade-off "
                    "from extra anti-leakage constraints."
                ),
            }
        )

    if function_recall:
        logic_text = (
            f" Logic Error recall was {_format_percent_1(logic_recall['recall'])}."
            if logic_recall
            else ""
        )
        key_findings.append(
            {
                "title": "Function vs Logic boundaries need refinement",
                "metric": f"{function_recall['correct']}/{function_recall['total']} Function Error",
                "body": (
                    f"Function Error recall was {_format_percent_1(function_recall['recall'])}; "
                    f"misclassifications often went to {function_recall['confusions'] or 'nearby categories'}."
                    f"{logic_text}"
                ),
            }
        )

    return {
        "findings_intro": (
            "These conclusions summarise what the Day 12 real LLM run shows, "
            "so the page is not just a raw metric table."
        ),
        "key_findings": key_findings,
        "prompt_rows": prompt_rows,
        "provider_rows": provider_rows,
        "cost_note": "Estimated retained Day 12 API spend: about USD 1.38-1.72; see day12_api_cost_estimate.md.",
    }


def _build_peci_ax_report(payload, report_config, markdown_path, summary_path):
    summary = payload.get("summary", {}) or {}
    providers = summary.get("providers", []) or []
    per_provider = summary.get("per_provider", {}) or {}
    total_results = summary.get("total_results") or 0
    ai_error_count = summary.get("ai_error_count") or 0
    valid_output_rate = (
        (total_results - ai_error_count) / total_results if total_results else None
    )

    provider_rows = []
    for provider in providers:
        provider_summary = per_provider.get(provider, {}) or {}
        latency_ms = provider_summary.get("average_latency_ms")
        provider_rows.append(
            {
                "provider": provider.title(),
                "accuracy": _format_percent_1(provider_summary.get("accuracy")),
                "latency": f"{float(latency_ms) / 1000:.1f}s"
                if latency_ms is not None
                else "N/A",
            }
        )

    ground_truth_counts = summary.get("ground_truth_counts", {}) or {}
    confusion_rows = summary.get("confusion_matrix", []) or []
    outside_total = ground_truth_counts.get("outside_peci_scope", 0) or 0
    outside_correct = sum(
        row.get("count", 0) or 0
        for row in confusion_rows
        if row.get("ground_truth") == "outside_peci_scope"
        and row.get("predicted") == "outside_peci_scope"
    )
    in_scope_total = sum(
        count
        for label, count in ground_truth_counts.items()
        if label != "outside_peci_scope"
    )
    in_scope_correct = sum(
        row.get("count", 0) or 0
        for row in confusion_rows
        if row.get("ground_truth") != "outside_peci_scope"
        and row.get("ground_truth") == row.get("predicted")
    )
    provider_count = len(providers) or 1
    outside_sample_count = outside_total // provider_count
    sample_count = summary.get("sample_count") or 0

    key_findings = [
        {
            "title": "Current taxonomy result",
            "metric": _format_percent_1(summary.get("overall_accuracy")),
            "body": (
                "This is the first independent evaluation of the current PECI A-X taxonomy. "
                "It is separate from the Day 12 legacy-taxonomy result."
            ),
        },
        {
            "title": "PECI scope is the main limitation",
            "metric": f"{outside_sample_count}/{sample_count} outside scope",
            "body": (
                f"In-scope accuracy was {_format_percent_1(in_scope_correct / in_scope_total) if in_scope_total else 'N/A'}, "
                f"while outside-scope recognition was {_format_percent_1(outside_correct / outside_total) if outside_total else 'N/A'}."
            ),
        },
        {
            "title": "Provider comparison",
            "metric": _format_percent_1((per_provider.get("kimi") or {}).get("accuracy")),
            "body": (
                f"Kimi reached {_format_percent_1((per_provider.get('kimi') or {}).get('accuracy'))}; "
                f"DeepSeek reached {_format_percent_1((per_provider.get('deepseek') or {}).get('accuracy'))}."
            ),
        },
        {
            "title": "Structured-output repair",
            "metric": f"{summary.get('json_repair_success_count', 0)} repaired",
            "body": (
                f"One malformed JSON response was repaired successfully. "
                f"The remaining {ai_error_count} errors were empty responses or provider timeouts."
            ),
        },
    ]

    return {
        **report_config,
        "findings_intro": (
            "This card reports the current PECI A-X classifier only. Its 50.0% result "
            "must not be mixed with the Day 12 legacy-taxonomy accuracy."
        ),
        "key_findings": key_findings,
        "prompt_rows": [
            {
                "prompt": "Strict-scaffolded",
                "accuracy": _format_percent_1(summary.get("overall_accuracy")),
                "note": "The current live prompt; this run is not a three-prompt comparison.",
            }
        ],
        "provider_rows": provider_rows,
        "cost_note": "Cost was not configured for this run; no A-X cost figure is reported.",
        "summary_path": str(markdown_path if markdown_path.exists() else summary_path),
        "summary_label": report_config["summary_filename"]
        if markdown_path.exists()
        else report_config["filename"],
        "dataset_size": summary.get("sample_count"),
        "providers": ", ".join(providers),
        "prompt_versions": ", ".join(summary.get("prompt_versions", []) or []),
        "total_results": total_results,
        "category_accuracy": _format_percent(summary.get("overall_accuracy")),
        "quality_metric_label": "Valid output",
        "json_compliance_rate": _format_percent(valid_output_rate),
        "solution_leakage_rate": _format_percent(summary.get("solution_leakage_rate")),
        "runtime_evidence_usage_rate": "N/A",
        "average_latency_ms": "N/A",
        "ai_error_count": ai_error_count,
        "reviewed_count": None,
        "review_coverage_rate": "N/A",
        "average_helpfulness_score": "N/A",
        "average_actionability_score": "N/A",
    }


def _load_final_evaluation_reports():
    reports = []
    report_dir = Path(settings.BASE_DIR) / "evaluation_reports"

    for report_config in FINAL_EVALUATION_REPORTS:
        summary_path = report_dir / report_config["filename"]
        markdown_path = report_dir / report_config["summary_filename"]
        if not summary_path.exists():
            continue

        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if report_config["filename"] == "peci_ax_evaluation_summary.json":
            reports.append(
                _build_peci_ax_report(
                    payload,
                    report_config,
                    markdown_path,
                    summary_path,
                )
            )
            continue

        automatic = payload.get("automatic_metrics", {}) or {}
        human = payload.get("human_review_metrics", {}) or {}
        run = payload.get("run", {}) or {}
        report_display = (
            _build_day12_display(payload)
            if report_config["filename"].startswith("day12_deepseek_kimi")
            else {}
        )
        reports.append(
            {
                **report_config,
                **report_display,
                "summary_path": str(markdown_path if markdown_path.exists() else summary_path),
                "summary_label": report_config["summary_filename"]
                if markdown_path.exists()
                else report_config["filename"],
                "dataset_size": run.get("dataset_size"),
                "providers": ", ".join(run.get("providers", [])),
                "prompt_versions": ", ".join(run.get("prompt_versions", [])),
                "total_results": automatic.get("total_results"),
                "category_accuracy": _format_percent(automatic.get("category_accuracy")),
                "json_compliance_rate": _format_percent(automatic.get("json_compliance_rate")),
                "solution_leakage_rate": _format_percent(automatic.get("solution_leakage_rate")),
                "runtime_evidence_usage_rate": _format_percent(
                    automatic.get("runtime_evidence_usage_rate")
                ),
                "average_latency_ms": _format_number(automatic.get("average_latency_ms")),
                "ai_error_count": automatic.get("ai_error_count"),
                "reviewed_count": human.get("reviewed_count"),
                "review_coverage_rate": _format_percent(human.get("review_coverage_rate")),
                "average_helpfulness_score": _format_number(
                    human.get("average_helpfulness_score")
                ),
                "average_actionability_score": _format_number(
                    human.get("average_actionability_score")
                ),
            }
        )

    return reports


def _latest_run_summary_for_display(evaluation_run):
    summary = dict(evaluation_run.summary or {})
    if summary.get("overall_accuracy") is None:
        return summary

    total_results = summary.get("total_results") or 0
    ai_error_count = summary.get("ai_error_count") or 0
    per_provider = summary.get("per_provider", {}) or {}
    latency_total = 0.0
    latency_count = 0
    for provider_summary in per_provider.values():
        result_count = provider_summary.get("results") or 0
        average_latency = provider_summary.get("average_latency_ms")
        if result_count and average_latency is not None:
            latency_total += float(average_latency) * result_count
            latency_count += result_count

    summary["category_accuracy"] = _format_percent(summary.get("overall_accuracy"))
    summary["solution_leakage_rate"] = _format_percent(
        summary.get("solution_leakage_rate")
    )
    summary["json_compliance_rate"] = _format_percent(
        (total_results - ai_error_count) / total_results if total_results else None
    )
    summary["runtime_evidence_usage_rate"] = "Included in prompt"
    summary["average_latency_ms"] = (
        f"{latency_total / latency_count / 1000:.1f}s" if latency_count else "N/A"
    )
    return summary


@login_required
def home(request):
    if request.user.is_staff:
        return redirect("instructor_dashboard")
    return redirect("student_submit")


def _generate_feedback_record(
    *,
    user=None,
    question=None,
    problem_statement: str,
    lecture_objective: str,
    student_code: str,
    topic_tags: str = "",
    sample_input: str = "",
    expected_output: str = "",
    comparison_mode: str = COMPARISON_MODE_NORMALIZED,
    llm_choice: str = "deepseek",
    prompt_version: str = PROMPT_STRICT_SCAFFOLDED,
    test_harness: str = "",
    trajectory_id: str = "",
    trajectory_attempt_number: int | None = None,
):
    comparison_mode = comparison_mode or COMPARISON_MODE_NORMALIZED

    execution_result = run_python_code(
        student_code,
        sample_input=sample_input,
        test_harness=test_harness,
    )
    output_comparison_status = compare_outputs(
        actual_output=execution_result.get("stdout", ""),
        expected_output=expected_output,
        execution_status=execution_result.get("execution_status", ""),
        mode=comparison_mode,
    )

    prompt = build_feedback_prompt(
        problem_statement=problem_statement,
        student_code=student_code,
        lecture_objective=lecture_objective,
        execution_result=execution_result,
        sample_input=sample_input,
        expected_output=expected_output,
        test_harness=test_harness,
        topic_tags=topic_tags,
        output_comparison_status=output_comparison_status,
        comparison_mode=comparison_mode,
        prompt_version=prompt_version,
    )

    ai_feedback_raw = ""
    ai_feedback_json = None
    ai_error = None
    llm_latency_ms = None
    llm_model_name = get_llm_model_name(llm_choice)
    llm_token_usage = {}
    estimated_cost = None
    feedback_schema_version = FEEDBACK_SCHEMA_VERSION
    schema_validation_status = ""
    schema_validation_notes = ""
    solution_leakage_flag = False
    prompt_for_record = prompt

    try:
        llm_start = time.monotonic()
        llm_result = call_llm_with_metadata(prompt, llm_choice)
        llm_latency_ms = int((time.monotonic() - llm_start) * 1000)
        ai_feedback_raw = llm_result["content"]
        parsed_feedback = parse_ai_feedback_with_metadata(ai_feedback_raw)
        ai_feedback_json = parsed_feedback["feedback_json"]
        ai_error = parsed_feedback["error"]
        feedback_schema_version = parsed_feedback["feedback_schema_version"]
        schema_validation_status = parsed_feedback["schema_validation_status"]
        schema_validation_notes = parsed_feedback["schema_validation_notes"]

        if should_retry_invalid_json(parsed_feedback, llm_result):
            initial_parse_error = parsed_feedback["error"]
            initial_raw_response = ai_feedback_raw
            repair_prompt = build_json_repair_prompt(prompt)
            prompt_for_record = repair_prompt
            try:
                repair_start = time.monotonic()
                repair_result = call_llm_with_metadata(repair_prompt, llm_choice)
                repair_latency_ms = int((time.monotonic() - repair_start) * 1000)
                repair_raw_response = repair_result["content"]
                repair_parsed = parse_ai_feedback_with_metadata(repair_raw_response)
                llm_result = merge_llm_call_metadata(llm_result, repair_result)
                llm_latency_ms += repair_latency_ms
                ai_feedback_raw = combine_json_repair_responses(
                    initial_raw_response,
                    repair_raw_response,
                )
                parsed_feedback = repair_parsed
                ai_feedback_json = parsed_feedback["feedback_json"]
                ai_error = parsed_feedback["error"]
                feedback_schema_version = parsed_feedback["feedback_schema_version"]
                schema_validation_status = parsed_feedback["schema_validation_status"]
                schema_validation_notes = json_repair_schema_notes(
                    initial_parse_error,
                    parsed_feedback["schema_validation_notes"],
                    ai_feedback_json is not None,
                )
            except Exception as repair_exc:
                ai_error = f"AI JSON repair call failed: {str(repair_exc)}"
                schema_validation_notes = json_repair_schema_notes(
                    initial_parse_error,
                    ai_error,
                    False,
                )

        llm_model_name = llm_result.get("model_name") or llm_model_name
        llm_token_usage = llm_result.get("usage") or {}
        estimated_cost = llm_result.get("estimated_cost")
        solution_leakage_flag = detect_solution_leakage(ai_feedback_raw, ai_feedback_json)
    except Exception as e:
        ai_error = f"AI call failed: {str(e)}"
        schema_validation_status = schema_validation_status or "llm_call_failed"
        schema_validation_notes = ai_error

    solved = bool(
        ai_feedback_json
        and ai_feedback_json.get("classification_outcome") == "no_error"
        and execution_result.get("execution_status") == "success"
        and output_comparison_status in {EXACT_MATCH, NORMALIZED_MATCH}
    )

    record = CodeFeedbackRecord.objects.create(
        user=user,
        question=question,
        problem_statement=problem_statement,
        lecture_objective=lecture_objective,
        student_code=student_code,
        sample_input=sample_input,
        expected_output=expected_output,
        execution_status=execution_result.get("execution_status", ""),
        execution_stdout=execution_result.get("stdout", ""),
        execution_stderr=execution_result.get("stderr", ""),
        execution_return_code=execution_result.get("return_code"),
        execution_timed_out=execution_result.get("timed_out", False),
        execution_time_ms=execution_result.get("execution_time_ms"),
        actual_output=execution_result.get("stdout", ""),
        output_comparison_status=output_comparison_status,
        comparison_mode=comparison_mode,
        error_category=ai_feedback_json.get("error_category", "") if ai_feedback_json else "",
        classification_outcome=ai_feedback_json.get("classification_outcome", "") if ai_feedback_json else "",
        solved=solved,
        peci_error_code=ai_feedback_json.get("peci_error_code", "") if ai_feedback_json else "",
        peci_error_label=ai_feedback_json.get("peci_error_label", "") if ai_feedback_json else "",
        legacy_error_category=ai_feedback_json.get("legacy_error_category", "") if ai_feedback_json else "",
        feedback_level=ai_feedback_json.get("feedback_level", "") if ai_feedback_json else "",
        concept_reference=ai_feedback_json.get("concept_reference", "") if ai_feedback_json else "",
        misconception=ai_feedback_json.get("misconception", "") if ai_feedback_json else "",
        feedback_text=ai_feedback_json.get("feedback", "") if ai_feedback_json else "",
        does_reveal_solution=ai_feedback_json.get("does_reveal_solution", False) if ai_feedback_json else False,
        uses_runtime_evidence=ai_feedback_json.get("uses_runtime_evidence", False) if ai_feedback_json else False,
        suggested_next_step=ai_feedback_json.get("suggested_next_step", "") if ai_feedback_json else "",
        confidence=str(ai_feedback_json.get("confidence", "")) if ai_feedback_json else "",
        prompt_version=prompt_version,
        prompt_text=prompt_for_record,
        feedback_schema_version=feedback_schema_version,
        raw_ai_response=ai_feedback_raw,
        ai_error=ai_error or "",
        llm_model_name=llm_model_name,
        llm_latency_ms=llm_latency_ms,
        llm_token_usage=llm_token_usage or None,
        estimated_cost=estimated_cost,
        json_compliance=ai_feedback_json is not None,
        schema_validation_status=schema_validation_status,
        schema_validation_notes=schema_validation_notes,
        solution_leakage_flag=solution_leakage_flag,
        llm_used=llm_choice,
        trajectory_id=trajectory_id,
        trajectory_attempt_number=trajectory_attempt_number,
    )

    return {
        "record": record,
        "problem_statement": problem_statement,
        "lecture_objective": lecture_objective,
        "student_code": student_code,
        "topic_tags": topic_tags,
        "sample_input": sample_input,
        "expected_output": expected_output,
        "comparison_mode": comparison_mode,
        "execution_result": execution_result,
        "output_comparison_status": output_comparison_status,
        "ai_feedback_raw": ai_feedback_raw,
        "ai_feedback_json": ai_feedback_json,
        "ai_error": ai_error,
        "llm_choice": llm_choice,
        "prompt_version": prompt_version,
        "llm_latency_ms": llm_latency_ms,
        "llm_model_name": llm_model_name,
        "llm_token_usage": llm_token_usage,
        "estimated_cost": estimated_cost,
        "feedback_schema_version": feedback_schema_version,
        "schema_validation_status": schema_validation_status,
        "schema_validation_notes": schema_validation_notes,
        "solution_leakage_flag": solution_leakage_flag,
    }


@login_required
def submit_code(request):
    _require_staff(request.user)

    if request.method == "POST":
        form = CodeSubmitForm(request.POST)

        if form.is_valid():
            context = _generate_feedback_record(
                user=request.user if request.user.is_authenticated else None,
                problem_statement=form.cleaned_data["problem_statement"],
                lecture_objective=form.cleaned_data["lecture_objective"],
                student_code=form.cleaned_data["student_code"],
                sample_input=form.cleaned_data["sample_input"],
                expected_output=form.cleaned_data["expected_output"],
                comparison_mode=form.cleaned_data["comparison_mode"],
                llm_choice=form.cleaned_data["llm_choice"],
                prompt_version=form.cleaned_data["prompt_version"],
            )
            return render(request, "feedback_app/result.html", context)
    else:
        form = CodeSubmitForm()

    return render(request, "feedback_app/submit.html", {"form": form})


@login_required
def student_submit(request):
    if request.user.is_staff:
        return redirect("instructor_dashboard")

    questions = Question.objects.filter(is_active=True)
    sorted_questions, question_queryset, status_map = _build_student_question_status(
        request.user,
        questions,
    )

    retry_record = None
    if request.method == "POST":
        form = StudentCodeSubmitForm(request.POST)

        if form.is_valid():
            question = form.cleaned_data["question"]
            previous = (
                CodeFeedbackRecord.objects.filter(user=request.user, question=question)
                .order_by("-created_at", "-id")
                .first()
            )
            if previous and previous.trajectory_id:
                trajectory_id = previous.trajectory_id
                trajectory_attempt_number = (previous.trajectory_attempt_number or 0) + 1
            else:
                trajectory_id = f"{request.user.pk}-{question.pk}-{time.time_ns()}"
                trajectory_attempt_number = 1
            context = _generate_feedback_record(
                user=request.user,
                question=question,
                problem_statement=question.problem_statement,
                lecture_objective=question.lecture_objective,
                student_code=form.cleaned_data["student_code"],
                topic_tags=question.topic_tags,
                sample_input=question.sample_input,
                expected_output=question.expected_output,
                comparison_mode=question.comparison_mode,
                llm_choice=question.default_llm_provider,
                prompt_version=PROMPT_STRICT_SCAFFOLDED,
                test_harness=question.test_harness,
                trajectory_id=trajectory_id,
                trajectory_attempt_number=trajectory_attempt_number,
            )
            context["question"] = question
            return render(request, "feedback_app/result.html", context)
    else:
        initial = {}
        retry_record_id = request.GET.get("retry")
        if retry_record_id:
            retry_record = get_object_or_404(
                CodeFeedbackRecord.objects.select_related("question"),
                pk=retry_record_id,
                user=request.user,
                question__is_active=True,
            )
            initial = {
                "question": retry_record.question,
                "student_code": retry_record.student_code,
            }
        form = StudentCodeSubmitForm(
            initial=initial,
            question_queryset=question_queryset,
            question_status=status_map,
        )

    return render(
        request,
        "feedback_app/student_submit.html",
        {
            "form": form,
            "questions": sorted_questions,
            "retry_record": retry_record,
        },
    )


@login_required
def instructor_dashboard(request):
    _require_staff(request.user)

    User = get_user_model()
    question_count = Question.objects.count()
    active_question_count = Question.objects.filter(is_active=True).count()
    inactive_question_count = question_count - active_question_count
    strict_question_count = Question.objects.filter(comparison_mode=COMPARISON_MODE_STRICT).count()
    normalized_question_count = Question.objects.filter(
        comparison_mode=COMPARISON_MODE_NORMALIZED
    ).count()
    student_count = User.objects.filter(is_staff=False, is_active=True).count()
    submission_count = CodeFeedbackRecord.objects.count()
    common_errors = (
        CodeFeedbackRecord.objects.filter(classification_outcome="peci_error")
        .exclude(peci_error_code="")
        .values("peci_error_code", "peci_error_label")
        .annotate(total=Count("id"))
        .order_by("-total", "peci_error_code")[:10]
    )
    for item in common_errors:
        item["error_category"] = item["peci_error_label"]
    provider_breakdown = (
        Question.objects.values("default_llm_provider")
        .annotate(total=Count("id"))
        .order_by("default_llm_provider")
    )
    output_breakdown = (
        CodeFeedbackRecord.objects.exclude(output_comparison_status="")
        .values("output_comparison_status")
        .annotate(total=Count("id"))
        .order_by("-total")[:8]
    )
    questions = Question.objects.annotate(
        submission_total=Count("codefeedbackrecord")
    ).order_by("title")
    recent_records = CodeFeedbackRecord.objects.select_related("user", "question")[:8]

    return render(
        request,
        "feedback_app/instructor_dashboard.html",
        {
            "question_count": question_count,
            "active_question_count": active_question_count,
            "inactive_question_count": inactive_question_count,
            "strict_question_count": strict_question_count,
            "normalized_question_count": normalized_question_count,
            "student_count": student_count,
            "submission_count": submission_count,
            "common_errors": common_errors,
            "provider_breakdown": provider_breakdown,
            "output_breakdown": output_breakdown,
            "questions": questions,
            "recent_records": recent_records,
        },
    )


@login_required
def analytics_dashboard(request):
    _require_staff(request.user)

    return render(request, "feedback_app/analytics.html", build_class_analytics())


@login_required
def evaluation_dashboard(request):
    _require_staff(request.user)

    latest_run = EvaluationRun.objects.prefetch_related("results").first()
    runs = EvaluationRun.objects.all()[:10]
    latest_results = []
    if latest_run:
        latest_results = latest_run.results.all()[:12]

    return render(
        request,
        "feedback_app/evaluation_dashboard.html",
        {
            "latest_run": latest_run,
            "final_reports": _load_final_evaluation_reports(),
            "runs": runs,
            "latest_results": latest_results,
            "summary": _latest_run_summary_for_display(latest_run) if latest_run else {},
        },
    )


@login_required
def student_profile(request, user_id):
    _require_staff(request.user)

    User = get_user_model()
    student = get_object_or_404(User, pk=user_id, is_staff=False)
    return render(
        request,
        "feedback_app/student_profile.html",
        {
            "profile": build_student_profile(student),
            "is_own_profile": False,
        },
    )


@login_required
def my_profile(request):
    if request.user.is_staff:
        return redirect("analytics_dashboard")

    return render(
        request,
        "feedback_app/student_profile.html",
        {
            "profile": build_student_profile(request.user),
            "is_own_profile": True,
        },
    )


@login_required
def student_skill_detail(request, user_id, topic_id):
    User = get_user_model()
    student = get_object_or_404(User, pk=user_id, is_staff=False)
    if not request.user.is_staff and request.user.id != student.id:
        raise PermissionDenied("You can only view your own skill evidence.")

    try:
        skill = build_skill_timeline(student, topic_id)
    except KeyError as exc:
        raise Http404("Unknown fixed topic.") from exc

    return render(
        request,
        "feedback_app/student_skill_detail.html",
        {
            "skill": skill,
            "is_own_profile": request.user.id == student.id,
        },
    )


@login_required
def history(request):
    records = CodeFeedbackRecord.objects.select_related("user", "question")
    students = []
    questions = []
    selected_student_id = None
    selected_question_id = None

    if not request.user.is_staff:
        records = records.filter(user=request.user)
    else:
        User = get_user_model()
        students = User.objects.filter(is_staff=False).order_by("username")
        questions = Question.objects.order_by("title")

        try:
            selected_student_id = int(request.GET.get("student", ""))
        except ValueError:
            selected_student_id = None

        try:
            selected_question_id = int(request.GET.get("question", ""))
        except ValueError:
            selected_question_id = None

        if selected_student_id:
            records = records.filter(user_id=selected_student_id)
        if selected_question_id:
            records = records.filter(question_id=selected_question_id)

    records = records[:20]
    return render(
        request,
        "feedback_app/history.html",
        {
            "records": records,
            "students": students,
            "questions": questions,
            "selected_student_id": selected_student_id,
            "selected_question_id": selected_question_id,
        },
    )


@login_required
def history_detail(request, record_id):
    record = get_object_or_404(
        CodeFeedbackRecord.objects.select_related("user", "question"),
        id=record_id,
    )
    if not request.user.is_staff and record.user_id != request.user.id:
        raise PermissionDenied("You can only view your own submission records.")

    return render(request, "feedback_app/history_detail.html", {"record": record})
