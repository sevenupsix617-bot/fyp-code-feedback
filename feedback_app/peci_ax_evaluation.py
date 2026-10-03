import csv
import json
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .ai_response import (
    detect_solution_leakage,
    extract_json_object,
    parse_ai_feedback_with_metadata,
)
from .evaluation_runner import (
    _build_prompt,
    _build_runtime_evidence,
    _call_model,
    _is_retryable_llm_error,
    _wait_for_provider_interval,
    load_evaluation_samples,
)
from .feedback_schema import canonicalize_classification_outcome
from .json_repair import (
    combine_json_repair_responses,
    json_repair_schema_notes,
    merge_llm_call_metadata,
    should_retry_invalid_json,
)
from .llm_client import call_llm_with_metadata, get_llm_model_name
from .models import EvaluationResult, EvaluationRun
from .prompt_builder import (
    JSON_STRING_ESCAPING_RULE,
    PROMPT_STRICT_SCAFFOLDED,
    build_json_repair_prompt,
)
from .taxonomy import (
    CLASSIFICATION_OUTCOMES,
    PECI_ERROR_TAXONOMY,
    canonicalize_peci_error_code,
    error_classification_rules_prompt_block,
    error_taxonomy_prompt_block,
)


REFACTORY_SAMPLE_ORIGIN = "real_student_submission_refactory"
EXPECTED_REFACTORY_SAMPLE_COUNT = 55
DEFAULT_PROPOSAL_FILENAME = "peci_ax_ground_truth_proposals.csv"
DEFAULT_CONFIRMED_FILENAME = "peci_ax_ground_truth_confirmed.csv"
DEFAULT_SUMMARY_JSON_FILENAME = "peci_ax_evaluation_summary.json"
DEFAULT_SUMMARY_MARKDOWN_FILENAME = "peci_ax_evaluation_summary.md"
DEFAULT_CONFUSION_MATRIX_FILENAME = "peci_ax_evaluation_confusion_matrix.csv"
PECI_EVALUATION_PROVIDERS = ["deepseek", "kimi"]

PROPOSAL_COLUMNS = [
    "sample_id",
    "old_ground_truth_category",
    "expected_feedback_focus",
    "proposed_outcome",
    "proposed_peci_code",
    "proposed_rationale",
    "confirmed_outcome",
    "confirmed_peci_code",
]


def load_refactory_evaluation_samples(dataset_path=None):
    path, metadata, samples = load_evaluation_samples(dataset_path)
    refactory_samples = [
        sample
        for sample in samples
        if sample.get("sample_origin") == REFACTORY_SAMPLE_ORIGIN
    ]
    if len(refactory_samples) != EXPECTED_REFACTORY_SAMPLE_COUNT:
        raise ValueError(
            "Expected exactly "
            f"{EXPECTED_REFACTORY_SAMPLE_COUNT} Refactory samples with "
            f"sample_origin={REFACTORY_SAMPLE_ORIGIN!r}, found {len(refactory_samples)}."
        )
    return path, metadata, refactory_samples


def build_peci_ground_truth_prompt(sample):
    runtime_evidence = {
        "sample_input": sample.get("sample_input", ""),
        "expected_output": sample.get("expected_output", ""),
        "actual_output": sample.get("actual_output", ""),
        "actual_stderr": sample.get("actual_stderr", ""),
        "output_comparison_status": sample.get("output_comparison_status", ""),
        "expected_execution_status": sample.get("expected_execution_status", ""),
    }
    program_context = {
        "problem_statement": sample.get("problem_statement", ""),
        "lecture_objective": sample.get("lecture_objective", ""),
        "support_code": sample.get("support_code", ""),
        "student_code": sample.get("student_code", ""),
        "test_harness": sample.get("test_harness", ""),
    }
    return f"""You are proposing an annotation for researcher review. This is not final ground truth.

Classify the primary issue in this beginner Python submission using only the fixed PECI A-X inventory below. Do not invent, merge, or rename categories. The legacy FYP category is intentionally withheld because it is not a valid mapping to PECI A-X.

PECI A-X error inventory:
{error_taxonomy_prompt_block()}

Classification rules:
{error_classification_rules_prompt_block()}

Program context:
{json.dumps(program_context, indent=2, ensure_ascii=False)}

Stored runtime evidence:
{json.dumps(runtime_evidence, indent=2, ensure_ascii=False)}

Return JSON only, with exactly these fields:
{{
  "classification_outcome": "peci_error|no_error|outside_peci_scope|unknown",
  "peci_error_code": "A-X or empty",
  "rationale": "one sentence grounded in the code and runtime evidence"
}}

Use peci_error only with exactly one valid A-X code. Use an empty code for every other outcome.
JSON string safety rule: {JSON_STRING_ESCAPING_RULE}
"""


def parse_peci_ground_truth_proposal(raw_response):
    try:
        payload = json.loads(extract_json_object(raw_response))
    except (TypeError, json.JSONDecodeError) as exc:
        return None, f"invalid JSON: {exc}"

    if not isinstance(payload, dict):
        return None, "proposal response must be one JSON object"

    raw_outcome = str(payload.get("classification_outcome", "")).strip()
    outcome, outcome_note = canonicalize_classification_outcome(raw_outcome)
    if outcome_note and "not recognised" in outcome_note:
        return None, outcome_note

    raw_code = str(payload.get("peci_error_code", "")).strip()
    code, code_note = canonicalize_peci_error_code(raw_code)
    if outcome == "peci_error" and not code:
        return None, code_note or "peci_error requires one valid A-X code"
    if outcome != "peci_error" and raw_code:
        return None, "peci_error_code must be empty when outcome is not peci_error"

    rationale = " ".join(str(payload.get("rationale", "")).split())[:600]
    if not rationale:
        return None, "proposal rationale is missing"

    return {
        "classification_outcome": outcome,
        "peci_error_code": code if outcome == "peci_error" else "",
        "rationale": rationale,
    }, None


def _request_ground_truth_proposal(sample, provider, retry_attempts=2, retry_delay=3):
    prompt = build_peci_ground_truth_prompt(sample)
    last_error = ""
    max_attempts = max(int(retry_attempts or 1), 1)

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            time.sleep(max(float(retry_delay or 0), 0))
        try:
            result = call_llm_with_metadata(prompt, provider)
            raw_response = result.get("content", "")
            proposal, parse_error = parse_peci_ground_truth_proposal(raw_response)
            if proposal:
                return proposal
            last_error = parse_error or "invalid proposal response"
        except Exception as exc:
            last_error = str(exc)
            if not _is_retryable_llm_error(last_error):
                break

    return {
        "classification_outcome": "unknown",
        "peci_error_code": "",
        "rationale": f"AI proposal unavailable after validation: {last_error}"[:600],
    }


def propose_peci_ground_truth(
    *,
    dataset_path=None,
    provider="deepseek",
    output_path=None,
    dry_run=False,
    retry_attempts=2,
    retry_delay=3,
    progress_callback=None,
):
    dataset_path, _metadata, samples = load_refactory_evaluation_samples(dataset_path)
    proposals = []

    for index, sample in enumerate(samples, start=1):
        proposal = _request_ground_truth_proposal(
            sample,
            provider,
            retry_attempts=retry_attempts,
            retry_delay=retry_delay,
        )
        row = {
            "sample_id": sample["sample_id"],
            "old_ground_truth_category": sample.get("ground_truth_category", ""),
            "expected_feedback_focus": sample.get("expected_feedback_focus", ""),
            "proposed_outcome": proposal["classification_outcome"],
            "proposed_peci_code": proposal["peci_error_code"],
            "proposed_rationale": proposal["rationale"],
            "confirmed_outcome": "",
            "confirmed_peci_code": "",
        }
        proposals.append(row)
        if progress_callback:
            code_display = row["proposed_peci_code"] or "-"
            progress_callback(
                f"[{index}/{len(samples)}] {row['sample_id']}: "
                f"{row['proposed_outcome']} / {code_display} - "
                f"{row['proposed_rationale']}"
            )

    resolved_output_path = Path(
        output_path
        or settings.BASE_DIR / "evaluation_reports" / DEFAULT_PROPOSAL_FILENAME
    )
    if not dry_run:
        resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
        with resolved_output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=PROPOSAL_COLUMNS)
            writer.writeheader()
            writer.writerows(proposals)

    return {
        "dataset_path": dataset_path,
        "output_path": resolved_output_path,
        "provider": provider,
        "dry_run": dry_run,
        "proposals": proposals,
    }


def load_confirmed_peci_ground_truth(confirmed_csv_path, samples):
    path = Path(confirmed_csv_path)
    if not path.exists():
        raise ValueError(f"Confirmed A-X ground-truth CSV does not exist: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required_columns = {
            "sample_id",
            "confirmed_outcome",
            "confirmed_peci_code",
        }
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                "Confirmed CSV is missing required column(s): "
                + ", ".join(sorted(missing_columns))
            )
        rows = list(reader)

    expected_ids = {sample["sample_id"] for sample in samples}
    seen_ids = set()
    confirmed = {}
    for row_number, row in enumerate(rows, start=2):
        sample_id = str(row.get("sample_id", "")).strip()
        if not sample_id:
            raise ValueError(f"Confirmed CSV row {row_number} has an empty sample_id.")
        if sample_id in seen_ids:
            raise ValueError(f"Confirmed CSV contains duplicate sample_id {sample_id!r}.")
        seen_ids.add(sample_id)

        outcome = str(row.get("confirmed_outcome", "")).strip()
        if outcome not in CLASSIFICATION_OUTCOMES:
            raise ValueError(
                f"Sample {sample_id!r} has invalid or empty confirmed_outcome {outcome!r}."
            )

        raw_code = str(row.get("confirmed_peci_code", "")).strip()
        code, code_note = canonicalize_peci_error_code(raw_code)
        if outcome == "peci_error" and not code:
            raise ValueError(
                f"Sample {sample_id!r} requires one confirmed A-X code: "
                f"{code_note or raw_code!r}."
            )
        if outcome != "peci_error" and raw_code:
            raise ValueError(
                f"Sample {sample_id!r} must have an empty confirmed_peci_code "
                f"when confirmed_outcome is {outcome!r}."
            )
        confirmed[sample_id] = {
            "classification_outcome": outcome,
            "peci_error_code": code if outcome == "peci_error" else "",
        }

    missing_ids = sorted(expected_ids - seen_ids)
    extra_ids = sorted(seen_ids - expected_ids)
    if missing_ids or extra_ids:
        details = []
        if missing_ids:
            details.append(f"missing {len(missing_ids)} sample(s): {', '.join(missing_ids[:5])}")
        if extra_ids:
            details.append(f"unexpected {len(extra_ids)} sample(s): {', '.join(extra_ids[:5])}")
        raise ValueError("Confirmed CSV does not exactly match the 55 Refactory samples; " + "; ".join(details))

    return confirmed


def _classification_key(outcome, code):
    if outcome == "peci_error" and code:
        return code
    return outcome or "invalid_output"


def _rate(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def _build_peci_summary(results, sample_count):
    total = len(results)
    correct = sum(1 for item in results if item["classification_match"])
    leakage_count = sum(1 for item in results if item["solution_leakage_flag"] is True)
    provider_summary = {}
    for provider in PECI_EVALUATION_PROVIDERS:
        group = [item for item in results if item["provider"] == provider]
        group_cost = Decimal("0")
        cost_items = 0
        for item in group:
            if item.get("estimated_cost") is not None:
                group_cost += Decimal(str(item["estimated_cost"]))
                cost_items += 1
        latency_values = [
            item["llm_latency_ms"]
            for item in group
            if item.get("llm_latency_ms") is not None
        ]
        provider_summary[provider] = {
            "results": len(group),
            "correct": sum(1 for item in group if item["classification_match"]),
            "accuracy": _rate(
                sum(1 for item in group if item["classification_match"]),
                len(group),
            ),
            "ai_error_count": sum(1 for item in group if item.get("ai_error")),
            "json_repair_attempt_count": sum(
                1 for item in group if item.get("json_repair_attempted")
            ),
            "json_repair_success_count": sum(
                1 for item in group if item.get("json_repair_succeeded")
            ),
            "solution_leakage_count": sum(
                1 for item in group if item["solution_leakage_flag"] is True
            ),
            "solution_leakage_rate": _rate(
                sum(1 for item in group if item["solution_leakage_flag"] is True),
                len(group),
            ),
            "average_latency_ms": (
                round(sum(latency_values) / len(latency_values), 2)
                if latency_values
                else None
            ),
            "estimated_cost_total": (
                str(group_cost.quantize(Decimal("0.000001"))) if cost_items else None
            ),
        }

    confusion = Counter(
        (item["ground_truth_key"], item["predicted_key"])
        for item in results
    )
    return {
        "evaluation_name": "PECI A-X independent strict-scaffolded evaluation",
        "ground_truth_source": "researcher-confirmed AI-assisted A-X annotation",
        "scope_note": (
            "This evaluation uses only strict_scaffolded and is separate from the "
            "Day 12 legacy-taxonomy three-prompt evaluation."
        ),
        "sample_count": sample_count,
        "providers": PECI_EVALUATION_PROVIDERS,
        "prompt_versions": [PROMPT_STRICT_SCAFFOLDED],
        "total_results": total,
        "correct_results": correct,
        "overall_accuracy": _rate(correct, total),
        "ai_error_count": sum(1 for item in results if item.get("ai_error")),
        "json_repair_attempt_count": sum(
            1 for item in results if item.get("json_repair_attempted")
        ),
        "json_repair_success_count": sum(
            1 for item in results if item.get("json_repair_succeeded")
        ),
        "solution_leakage_count": leakage_count,
        "solution_leakage_rate": _rate(leakage_count, total),
        "per_provider": provider_summary,
        "ground_truth_counts": dict(Counter(item["ground_truth_key"] for item in results)),
        "predicted_counts": dict(Counter(item["predicted_key"] for item in results)),
        "confusion_matrix": [
            {"ground_truth": truth, "predicted": predicted, "count": count}
            for (truth, predicted), count in sorted(confusion.items())
        ],
    }


def _ordered_matrix_labels(labels):
    peci_codes = list(PECI_ERROR_TAXONOMY)
    special_order = ["no_error", "outside_peci_scope", "unknown", "invalid_output"]
    label_set = set(labels)
    return [label for label in peci_codes + special_order if label in label_set]


def _write_confusion_matrix_csv(path, results):
    counter = Counter(
        (item["ground_truth_key"], item["predicted_key"])
        for item in results
    )
    truth_labels = _ordered_matrix_labels(item["ground_truth_key"] for item in results)
    predicted_labels = _ordered_matrix_labels(item["predicted_key"] for item in results)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["ground_truth\\predicted", *predicted_labels])
        for truth in truth_labels:
            writer.writerow(
                [truth, *[counter[(truth, predicted)] for predicted in predicted_labels]]
            )
    return truth_labels, predicted_labels, counter


def _render_peci_markdown(summary, truth_labels, predicted_labels, counter):
    lines = [
        "# PECI A-X Independent Evaluation",
        "",
        "## Scope and Ground Truth",
        "",
        "- Ground truth source: researcher-confirmed AI-assisted A-X annotation.",
        "- Scope: 55 Refactory samples x 2 providers x 1 strict_scaffolded prompt.",
        "- This is separate from the Day 12 legacy-taxonomy three-prompt evaluation; the 77.88% Day 12 figure must not be reused as an A-X result.",
        "- Proposed labels were produced by an LLM, but only the researcher-confirmed outcome and A-X code were used as ground truth.",
        "",
        "## Metrics",
        "",
        f"- Samples: {summary['sample_count']}",
        f"- Total model outputs: {summary['total_results']}",
        f"- Overall accuracy: {summary['overall_accuracy']}",
        f"- AI/API error count: {summary['ai_error_count']}",
        f"- JSON repair retries: {summary['json_repair_attempt_count']}",
        f"- Successful JSON repairs: {summary['json_repair_success_count']}",
        f"- Solution leakage rate: {summary['solution_leakage_rate']}",
        "",
        "| Provider | Results | Correct | Accuracy | AI errors | Repair retries | Repaired | Leakage rate | Average latency ms | Estimated cost |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for provider in PECI_EVALUATION_PROVIDERS:
        item = summary["per_provider"][provider]
        lines.append(
            f"| {provider} | {item['results']} | {item['correct']} | "
            f"{item['accuracy']} | {item['ai_error_count']} | "
            f"{item['json_repair_attempt_count']} | "
            f"{item['json_repair_success_count']} | "
            f"{item['solution_leakage_rate']} | {item['average_latency_ms']} | "
            f"{item['estimated_cost_total']} |"
        )

    lines.extend(
        [
            "",
            "## Confusion Matrix",
            "",
            "Rows are researcher-confirmed ground-truth A-X labels; columns are predicted A-X labels or explicit non-PECI outcomes.",
            "",
            "| Ground truth \\ Predicted | " + " | ".join(predicted_labels) + " |",
            "| --- | " + " | ".join("---:" for _ in predicted_labels) + " |",
        ]
    )
    for truth in truth_labels:
        values = [str(counter[(truth, predicted)]) for predicted in predicted_labels]
        lines.append(f"| {truth} | " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def run_peci_ax_evaluation(
    *,
    confirmed_csv_path,
    dataset_path=None,
    output_dir=None,
    timeout=1,
    provider_min_intervals=None,
    retry_attempts=2,
    retry_delay=3,
    progress_callback=None,
):
    dataset_path, metadata, samples = load_refactory_evaluation_samples(dataset_path)
    confirmed = load_confirmed_peci_ground_truth(confirmed_csv_path, samples)
    provider_min_intervals = provider_min_intervals or {}
    provider_last_call_at = {}

    evaluation_run = EvaluationRun.objects.create(
        name="PECI A-X strict-scaffolded independent evaluation",
        dataset_name=metadata.get("dataset_name", "Refactory"),
        dataset_path=str(dataset_path),
        dataset_size=len(samples),
        providers=PECI_EVALUATION_PROVIDERS,
        prompt_versions=[PROMPT_STRICT_SCAFFOLDED],
        run_mode=EvaluationRun.RUN_MODE_LLM,
        notes=(
            "Ground truth: researcher-confirmed AI-assisted A-X annotation. "
            "Strict-scaffolded only; separate from the Day 12 legacy-taxonomy run."
        ),
    )

    result_dicts = []
    total_calls = len(samples) * len(PECI_EVALUATION_PROVIDERS)
    call_index = 0
    for sample in samples:
        runtime_result, comparison_status = _build_runtime_evidence(sample, timeout)
        truth = confirmed[sample["sample_id"]]
        ground_truth_key = _classification_key(
            truth["classification_outcome"],
            truth["peci_error_code"],
        )

        for provider in PECI_EVALUATION_PROVIDERS:
            call_index += 1
            prompt = _build_prompt(
                sample,
                PROMPT_STRICT_SCAFFOLDED,
                runtime_result,
                comparison_status,
            )
            _wait_for_provider_interval(
                provider,
                provider_last_call_at,
                provider_min_intervals,
            )
            provider_retry_delay = max(
                float(retry_delay or 0),
                float(provider_min_intervals.get(provider, 0) or 0),
            )
            ai_result, latency_ms = _call_model(
                sample,
                prompt,
                provider,
                True,
                retry_attempts=retry_attempts,
                retry_delay=provider_retry_delay,
            )
            provider_last_call_at[provider] = time.monotonic()
            raw_response = ai_result.get("content", "")
            parsed = parse_ai_feedback_with_metadata(raw_response)
            feedback_json = parsed["feedback_json"]
            stored_prompt = prompt
            stored_raw_response = raw_response
            schema_validation_notes = parsed["schema_validation_notes"]
            json_repair_attempted = False
            json_repair_succeeded = False

            if should_retry_invalid_json(parsed, ai_result):
                json_repair_attempted = True
                initial_parse_error = parsed["error"]
                repair_prompt = build_json_repair_prompt(prompt)
                _wait_for_provider_interval(
                    provider,
                    provider_last_call_at,
                    provider_min_intervals,
                )
                repair_result, repair_latency_ms = _call_model(
                    sample,
                    repair_prompt,
                    provider,
                    True,
                    retry_attempts=retry_attempts,
                    retry_delay=provider_retry_delay,
                )
                provider_last_call_at[provider] = time.monotonic()
                repair_raw_response = repair_result.get("content", "")
                repair_parsed = parse_ai_feedback_with_metadata(repair_raw_response)
                ai_result = merge_llm_call_metadata(ai_result, repair_result)
                latency_ms += repair_latency_ms
                parsed = repair_parsed
                feedback_json = parsed["feedback_json"]
                json_repair_succeeded = feedback_json is not None
                stored_prompt = repair_prompt
                stored_raw_response = combine_json_repair_responses(
                    raw_response,
                    repair_raw_response,
                )
                schema_validation_notes = json_repair_schema_notes(
                    initial_parse_error,
                    parsed["schema_validation_notes"],
                    json_repair_succeeded,
                )

            predicted_outcome = ""
            predicted_code = ""
            if feedback_json:
                predicted_outcome = feedback_json.get("classification_outcome", "")
                predicted_code = feedback_json.get("peci_error_code", "")
            predicted_key = _classification_key(predicted_outcome, predicted_code)
            classification_match = bool(
                feedback_json
                and predicted_outcome == truth["classification_outcome"]
                and predicted_code == truth["peci_error_code"]
            )
            leakage = detect_solution_leakage(stored_raw_response, feedback_json)
            ai_error = ai_result.get("error") or parsed["error"] or ""

            database_result = EvaluationResult.objects.create(
                evaluation_run=evaluation_run,
                sample_id=sample["sample_id"],
                source_dataset=sample.get("source_dataset", "Refactory"),
                source_record_path=sample.get("source_record_path", ""),
                source_test_input_path=sample.get("source_test_input_path", ""),
                source_test_output_path=sample.get("source_test_output_path", ""),
                provider=provider,
                prompt_version=PROMPT_STRICT_SCAFFOLDED,
                ground_truth_category=ground_truth_key,
                predicted_category=predicted_key,
                category_match=classification_match,
                feedback_level=feedback_json.get("feedback_level", "")
                if feedback_json
                else "",
                concept_reference=feedback_json.get("concept_reference", "")
                if feedback_json
                else "",
                feedback_text=feedback_json.get("feedback", "")
                if feedback_json
                else "",
                suggested_next_step=feedback_json.get("suggested_next_step", "")
                if feedback_json
                else "",
                confidence=str(feedback_json.get("confidence", ""))
                if feedback_json
                else "",
                json_compliance=feedback_json is not None,
                schema_validation_status=parsed["schema_validation_status"],
                schema_validation_notes=schema_validation_notes,
                solution_leakage_flag=leakage,
                uses_runtime_evidence=feedback_json.get("uses_runtime_evidence")
                if feedback_json
                else None,
                execution_status=runtime_result.get("execution_status", ""),
                output_comparison_status=comparison_status,
                actual_output=runtime_result.get("stdout", ""),
                actual_stderr=runtime_result.get("stderr", ""),
                prompt_text=stored_prompt,
                raw_ai_response=stored_raw_response,
                ai_error=ai_error,
                llm_model_name=ai_result.get("model_name") or get_llm_model_name(provider),
                llm_latency_ms=latency_ms,
                llm_token_usage=ai_result.get("usage") or None,
                estimated_cost=ai_result.get("estimated_cost"),
            )
            result_dicts.append(
                {
                    "database_id": database_result.id,
                    "sample_id": sample["sample_id"],
                    "provider": provider,
                    "ground_truth_outcome": truth["classification_outcome"],
                    "ground_truth_peci_code": truth["peci_error_code"],
                    "ground_truth_key": ground_truth_key,
                    "predicted_outcome": predicted_outcome,
                    "predicted_peci_code": predicted_code,
                    "predicted_key": predicted_key,
                    "classification_match": classification_match,
                    "solution_leakage_flag": leakage,
                    "ai_error": ai_error,
                    "json_repair_attempted": json_repair_attempted,
                    "json_repair_succeeded": json_repair_succeeded,
                    "llm_latency_ms": latency_ms,
                    "llm_token_usage": ai_result.get("usage") or {},
                    "estimated_cost": ai_result.get("estimated_cost"),
                }
            )
            if progress_callback:
                progress_callback(
                    f"[{call_index}/{total_calls}] {sample['sample_id']} / {provider}: "
                    f"truth={ground_truth_key}, predicted={predicted_key}, "
                    f"match={classification_match}"
                )

    summary = _build_peci_summary(result_dicts, len(samples))
    evaluation_run.summary = summary
    evaluation_run.completed_at = timezone.now()
    evaluation_run.save(update_fields=["summary", "completed_at"])

    report_dir = Path(output_dir or settings.BASE_DIR / "evaluation_reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    summary_json_path = report_dir / DEFAULT_SUMMARY_JSON_FILENAME
    summary_markdown_path = report_dir / DEFAULT_SUMMARY_MARKDOWN_FILENAME
    confusion_matrix_path = report_dir / DEFAULT_CONFUSION_MATRIX_FILENAME

    truth_labels, predicted_labels, counter = _write_confusion_matrix_csv(
        confusion_matrix_path,
        result_dicts,
    )
    summary_payload = {
        "run": {
            "database_id": evaluation_run.id,
            "name": evaluation_run.name,
            "dataset_path": str(dataset_path),
            "confirmed_ground_truth_path": str(Path(confirmed_csv_path)),
            "completed_at": evaluation_run.completed_at.isoformat(),
        },
        "summary": summary,
    }
    summary_json_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    summary_markdown_path.write_text(
        _render_peci_markdown(summary, truth_labels, predicted_labels, counter),
        encoding="utf-8",
    )

    return {
        "run": evaluation_run,
        "summary": summary,
        "results": result_dicts,
        "output_paths": {
            "summary_json": summary_json_path,
            "summary_md": summary_markdown_path,
            "confusion_matrix_csv": confusion_matrix_path,
        },
    }
