import json
import os
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .ai_response import detect_solution_leakage, parse_ai_feedback_with_metadata
from .code_runner import run_python_code
from .evaluation_dataset import EVALUATION_DATASET_FILENAME
from .feedback_schema import FEEDBACK_SCHEMA_VERSION, canonicalize_error_category
from .llm_client import call_llm_with_metadata, get_llm_model_name
from .models import EvaluationResult, EvaluationRun
from .output_comparison import COMPARISON_MODE_NORMALIZED, compare_outputs
from .prompt_builder import (
    PROMPT_BASELINE,
    PROMPT_CONTEXT_AWARE,
    PROMPT_STRICT_SCAFFOLDED,
    build_feedback_prompt,
)


DEFAULT_EVALUATION_PROVIDERS = ["deepseek", "kimi"]
DEFAULT_EVALUATION_PROMPT_VERSIONS = [
    PROMPT_BASELINE,
    PROMPT_CONTEXT_AWARE,
    PROMPT_STRICT_SCAFFOLDED,
]


def load_evaluation_samples(dataset_path=None):
    path = Path(dataset_path or settings.BASE_DIR / EVALUATION_DATASET_FILENAME)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return path, payload.get("metadata", {}), payload["samples"]


def _combine_code(sample):
    return "\n\n".join(
        part.strip()
        for part in [sample.get("support_code", ""), sample.get("student_code", "")]
        if part and part.strip()
    )


def _build_runtime_evidence(sample, timeout):
    result = run_python_code(
        _combine_code(sample),
        sample_input=sample.get("sample_input", ""),
        timeout=timeout,
        test_harness=sample.get("test_harness", ""),
    )
    comparison_status = compare_outputs(
        result.get("stdout", ""),
        sample.get("expected_output", ""),
        result.get("execution_status", ""),
        mode=sample.get("comparison_mode") or COMPARISON_MODE_NORMALIZED,
    )
    return result, comparison_status


def _build_prompt(sample, prompt_version, runtime_result, comparison_status):
    return build_feedback_prompt(
        problem_statement=sample["problem_statement"],
        lecture_objective=sample.get("lecture_objective", ""),
        support_code=sample.get("support_code", ""),
        student_code=sample["student_code"],
        sample_input=sample.get("sample_input", ""),
        expected_output=sample.get("expected_output", ""),
        test_harness=sample.get("test_harness", ""),
        topic_tags=sample.get("topic_tags") or sample.get("taxonomy_group", ""),
        execution_result=runtime_result,
        output_comparison_status=comparison_status,
        comparison_mode=sample.get("comparison_mode") or COMPARISON_MODE_NORMALIZED,
        prompt_version=prompt_version,
    )


def _mock_llm_with_metadata(sample, prompt, provider):
    content = json.dumps(
        {
            "error_category": sample["ground_truth_category"],
            "feedback_level": "Level 2",
            "concept_reference": sample.get("taxonomy_group", "").replace("_", " "),
            "feedback": (
                "This dry-run feedback validates the evaluation pipeline only. "
                f"{sample['expected_feedback_focus']}"
            ),
            "does_reveal_solution": False,
            "uses_runtime_evidence": True,
            "suggested_next_step": sample["expected_feedback_focus"],
            "confidence": "high",
        }
    )
    return {
        "content": content,
        "model_name": f"{get_llm_model_name(provider)}-offline-oracle",
        "usage": {},
        "estimated_cost": None,
    }


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _is_retryable_llm_error(message):
    lowered = str(message or "").lower()
    if any(
        marker in lowered
        for marker in (
            "insufficient balance",
            "exceeded_current_quota",
            "current token quota",
            "please recharge",
            "account balance",
            "billing details",
            "is suspended",
        )
    ):
        return False

    return any(
        marker in lowered
        for marker in (
            "429",
            "rate limit",
            "timed out",
            "timeout",
            "network error",
            "ssl",
            "eof",
            "empty content",
            "incompleteread",
            "remote end closed",
            "closed connection",
        )
    )


def _call_model(sample, prompt, provider, run_llm, *, retry_attempts=2, retry_delay=3):
    llm_start = time.monotonic()
    max_attempts = max(int(retry_attempts or 1), 1) if run_llm else 1
    last_result = None
    last_error = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            time.sleep(max(float(retry_delay or 0), 0))

        try:
            if run_llm:
                result = call_llm_with_metadata(prompt, provider)
                last_result = result
                if not str(result.get("content", "")).strip():
                    raise RuntimeError("LLM returned empty content")
            else:
                result = _mock_llm_with_metadata(sample, prompt, provider)
            latency_ms = int((time.monotonic() - llm_start) * 1000)
            return result, latency_ms
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts or not _is_retryable_llm_error(str(exc)):
                break

    result = {
        "content": "",
        "model_name": get_llm_model_name(provider),
        "usage": {},
        "estimated_cost": None,
        "error": str(last_error),
    }
    if last_result:
        result.update(
            {
                "model_name": last_result.get("model_name") or result["model_name"],
                "usage": last_result.get("usage") or {},
                "estimated_cost": last_result.get("estimated_cost"),
            }
        )
    latency_ms = int((time.monotonic() - llm_start) * 1000)
    return result, latency_ms


def _wait_for_provider_interval(provider, last_call_at, provider_min_intervals):
    min_interval = float(provider_min_intervals.get(provider, 0) or 0)
    if min_interval <= 0:
        return

    previous_call_at = last_call_at.get(provider)
    if previous_call_at is None:
        return

    elapsed = time.monotonic() - previous_call_at
    remaining = min_interval - elapsed
    if remaining > 0:
        time.sleep(remaining)


def _decimal_to_string(value):
    if isinstance(value, Decimal):
        return str(value)
    return value


def _result_to_json(result):
    serializable = {}
    for key, value in result.items():
        serializable[key] = _decimal_to_string(value)
    return serializable


def _rate(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def summarise_evaluation_results(results):
    total = len(results)
    matched = sum(1 for item in results if item["category_match"] is True)
    json_ok = sum(1 for item in results if item["json_compliance"] is True)
    strict_schema_ok = sum(
        1 for item in results if item["schema_validation_status"] == "valid_schema"
    )
    usable_schema_ok = sum(
        1
        for item in results
        if item["schema_validation_status"] in {"valid_schema", "repaired_schema"}
    )
    leakage = sum(1 for item in results if item["solution_leakage_flag"] is True)
    runtime_evidence = sum(1 for item in results if item["uses_runtime_evidence"] is True)
    latency_values = [
        item["llm_latency_ms"] for item in results if item.get("llm_latency_ms") is not None
    ]

    token_totals = Counter()
    for item in results:
        for token_name, token_value in (item.get("llm_token_usage") or {}).items():
            token_totals[token_name] += token_value or 0

    total_cost = Decimal("0")
    cost_count = 0
    for item in results:
        estimated_cost = item.get("estimated_cost")
        if estimated_cost is not None:
            total_cost += Decimal(estimated_cost)
            cost_count += 1

    by_condition = {}
    grouped = defaultdict(list)
    for item in results:
        grouped[(item["provider"], item["prompt_version"])].append(item)

    for (provider, prompt_version), group in grouped.items():
        group_total = len(group)
        key = f"{provider}:{prompt_version}"
        by_condition[key] = {
            "total": group_total,
            "category_accuracy": _rate(
                sum(1 for item in group if item["category_match"] is True),
                group_total,
            ),
            "json_compliance_rate": _rate(
                sum(1 for item in group if item["json_compliance"] is True),
                group_total,
            ),
            "solution_leakage_rate": _rate(
                sum(1 for item in group if item["solution_leakage_flag"] is True),
                group_total,
            ),
            "runtime_evidence_usage_rate": _rate(
                sum(1 for item in group if item["uses_runtime_evidence"] is True),
                group_total,
            ),
        }

    confusion_counter = Counter(
        (item["ground_truth_category"], item["predicted_category"] or "N/A")
        for item in results
    )

    return {
        "total_results": total,
        "category_accuracy": _rate(matched, total),
        "json_compliance_rate": _rate(json_ok, total),
        "strict_schema_rate": _rate(strict_schema_ok, total),
        "usable_schema_rate": _rate(usable_schema_ok, total),
        "solution_leakage_rate": _rate(leakage, total),
        "runtime_evidence_usage_rate": _rate(runtime_evidence, total),
        "average_latency_ms": (
            round(sum(latency_values) / len(latency_values), 2) if latency_values else None
        ),
        "token_totals": dict(token_totals),
        "estimated_cost_total": str(total_cost.quantize(Decimal("0.000001")))
        if cost_count
        else None,
        "ai_error_count": sum(1 for item in results if item.get("ai_error")),
        "provider_counts": dict(Counter(item["provider"] for item in results)),
        "prompt_version_counts": dict(Counter(item["prompt_version"] for item in results)),
        "ground_truth_counts": dict(Counter(item["ground_truth_category"] for item in results)),
        "predicted_counts": dict(Counter(item["predicted_category"] or "N/A" for item in results)),
        "runtime_status_counts": dict(Counter(item["execution_status"] for item in results)),
        "comparison_counts": dict(Counter(item["output_comparison_status"] for item in results)),
        "schema_status_counts": dict(
            Counter(item["schema_validation_status"] for item in results)
        ),
        "by_provider_prompt": by_condition,
        "confusion_matrix": [
            {
                "ground_truth_category": truth,
                "predicted_category": prediction,
                "count": count,
            }
            for (truth, prediction), count in sorted(confusion_counter.items())
        ],
    }


def _render_markdown_summary(evaluation_run, summary, *, result_path, json_summary_path):
    mode_note = (
        "This is a real LLM API run."
        if evaluation_run.run_mode == EvaluationRun.RUN_MODE_LLM
        else "This is a dry run that validates the pipeline only; it is not real LLM performance."
    )
    lines = [
        "# Batch Evaluation Summary",
        "",
        f"- Run name: {evaluation_run.name}",
        f"- Run mode: {evaluation_run.run_mode}",
        f"- Note: {mode_note}",
        f"- Dataset: {evaluation_run.dataset_name}",
        f"- Dataset path: {evaluation_run.dataset_path}",
        f"- Dataset size: {evaluation_run.dataset_size}",
        f"- Providers: {', '.join(evaluation_run.providers)}",
        f"- Prompt versions: {', '.join(evaluation_run.prompt_versions)}",
        f"- Notes: {evaluation_run.notes}",
        f"- Started at: {evaluation_run.started_at}",
        f"- Completed at: {evaluation_run.completed_at}",
        f"- Result JSON: {result_path}",
        f"- Summary JSON: {json_summary_path}",
        "",
        "## Metrics",
        "",
        f"- Total results: {summary['total_results']}",
        f"- Category accuracy: {summary['category_accuracy']}",
        f"- JSON compliance rate: {summary['json_compliance_rate']}",
        f"- Strict schema rate: {summary['strict_schema_rate']}",
        f"- Usable schema rate: {summary['usable_schema_rate']}",
        f"- Solution leakage rate: {summary['solution_leakage_rate']}",
        f"- Runtime evidence usage rate: {summary['runtime_evidence_usage_rate']}",
        f"- Average latency ms: {summary['average_latency_ms']}",
        f"- Token totals: {json.dumps(summary['token_totals'], sort_keys=True)}",
        f"- Estimated total cost: {summary['estimated_cost_total']}",
        f"- AI/API error count: {summary['ai_error_count']}",
        f"- Schema status counts: {json.dumps(summary['schema_status_counts'], sort_keys=True)}",
        "",
        "## Provider / Prompt Breakdown",
        "",
        "| Provider and prompt | Results | Category accuracy | JSON compliance | Leakage | Runtime evidence |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for key, item in sorted(summary["by_provider_prompt"].items()):
        lines.append(
            "| {key} | {total} | {accuracy} | {json_rate} | {leakage_rate} | {runtime_rate} |".format(
                key=key,
                total=item["total"],
                accuracy=item["category_accuracy"],
                json_rate=item["json_compliance_rate"],
                leakage_rate=item["solution_leakage_rate"],
                runtime_rate=item["runtime_evidence_usage_rate"],
            )
        )

    return "\n".join(lines) + "\n"


def export_evaluation_run_files(evaluation_run, result_dicts, output_dir=None):
    base_dir = Path(output_dir or settings.BASE_DIR / "evaluation_runs")
    base_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timezone.localtime(evaluation_run.started_at).strftime("%Y%m%d_%H%M%S")
    slug = f"{timestamp}_{evaluation_run.run_mode}_{evaluation_run.id}"
    result_path = base_dir / f"{slug}_results.json"
    summary_path = base_dir / f"{slug}_summary.json"
    markdown_path = base_dir / f"{slug}_summary.md"

    result_payload = {
        "run": {
            "id": evaluation_run.id,
            "name": evaluation_run.name,
            "run_mode": evaluation_run.run_mode,
            "dataset_name": evaluation_run.dataset_name,
            "dataset_path": evaluation_run.dataset_path,
            "dataset_size": evaluation_run.dataset_size,
            "providers": evaluation_run.providers,
            "prompt_versions": evaluation_run.prompt_versions,
            "notes": evaluation_run.notes,
            "started_at": evaluation_run.started_at.isoformat(),
            "completed_at": evaluation_run.completed_at.isoformat()
            if evaluation_run.completed_at
            else None,
        },
        "results": [_result_to_json(item) for item in result_dicts],
    }
    result_path.write_text(json.dumps(result_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_payload = {
        "run": result_payload["run"],
        "summary": evaluation_run.summary,
    }
    summary_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    markdown_path.write_text(
        _render_markdown_summary(
            evaluation_run,
            evaluation_run.summary,
            result_path=result_path,
            json_summary_path=summary_path,
        ),
        encoding="utf-8",
    )

    return {
        "results": result_path,
        "summary_json": summary_path,
        "summary_md": markdown_path,
    }


def run_evaluation_dataset(
    *,
    dataset_path=None,
    providers=None,
    prompt_versions=None,
    offset=0,
    limit=None,
    run_llm=False,
    timeout=1,
    name="",
    output_dir=None,
    provider_min_intervals=None,
    retry_attempts=None,
    retry_delay=None,
):
    dataset_path, metadata, samples = load_evaluation_samples(dataset_path)
    offset = max(int(offset or 0), 0)
    if offset:
        samples = samples[offset:]
    if limit:
        samples = samples[: int(limit)]

    providers = providers or DEFAULT_EVALUATION_PROVIDERS
    prompt_versions = prompt_versions or DEFAULT_EVALUATION_PROMPT_VERSIONS
    run_mode = EvaluationRun.RUN_MODE_LLM if run_llm else EvaluationRun.RUN_MODE_DRY_RUN
    run_name = name or f"{metadata.get('dataset_name', 'Evaluation')} {run_mode}"
    provider_min_intervals = provider_min_intervals or {}
    provider_last_call_at = {}
    retry_attempts = retry_attempts or _get_int_env("LLM_RETRY_ATTEMPTS", 2)
    retry_delay = retry_delay if retry_delay is not None else _get_int_env("LLM_RETRY_DELAY", 3)
    sample_window_note = ""
    if offset or limit:
        sample_window_note = f" Sample window: offset={offset}, limit={limit or 'all'}."
    real_run_note = "Real LLM API run."
    real_run_note += sample_window_note
    if run_llm:
        real_run_note += f" Retry attempts: {retry_attempts}; retry delay: {retry_delay}s."
    if run_llm and any(float(value or 0) > 0 for value in provider_min_intervals.values()):
        real_run_note += f" Provider min intervals: {provider_min_intervals}."
    dry_run_note = (
        "Dry-run oracle mode validates storage, prompt construction, parsing, "
        "and metric export without calling paid APIs."
        f"{sample_window_note}"
    )

    evaluation_run = EvaluationRun.objects.create(
        name=run_name,
        dataset_name=metadata.get("dataset_name", "Refactory"),
        dataset_path=str(dataset_path),
        dataset_size=len(samples),
        providers=providers,
        prompt_versions=prompt_versions,
        run_mode=run_mode,
        notes=(
            dry_run_note
            if not run_llm
            else real_run_note
        ),
    )

    result_dicts = []
    for sample in samples:
        runtime_result, comparison_status = _build_runtime_evidence(sample, timeout)

        for provider in providers:
            for prompt_version in prompt_versions:
                prompt = _build_prompt(sample, prompt_version, runtime_result, comparison_status)
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
                    run_llm,
                    retry_attempts=retry_attempts,
                    retry_delay=provider_retry_delay,
                )
                if run_llm:
                    provider_last_call_at[provider] = time.monotonic()
                raw_ai_response = ai_result.get("content", "")
                parsed = parse_ai_feedback_with_metadata(raw_ai_response)
                feedback_json = parsed["feedback_json"]
                solution_leakage_flag = detect_solution_leakage(
                    raw_ai_response,
                    feedback_json,
                )

                predicted_category = ""
                if feedback_json:
                    predicted_category, _ = canonicalize_error_category(
                        feedback_json.get("error_category")
                    )

                category_match = (
                    predicted_category == sample["ground_truth_category"]
                    if predicted_category
                    else False
                )
                estimated_cost = ai_result.get("estimated_cost")

                result = EvaluationResult.objects.create(
                    evaluation_run=evaluation_run,
                    sample_id=sample["sample_id"],
                    source_dataset=sample.get("source_dataset", "Refactory"),
                    source_record_path=sample.get("source_record_path", ""),
                    source_test_input_path=sample.get("source_test_input_path", ""),
                    source_test_output_path=sample.get("source_test_output_path", ""),
                    provider=provider,
                    prompt_version=prompt_version,
                    ground_truth_category=sample["ground_truth_category"],
                    predicted_category=predicted_category,
                    category_match=category_match,
                    feedback_level=feedback_json.get("feedback_level", "") if feedback_json else "",
                    concept_reference=feedback_json.get("concept_reference", "")
                    if feedback_json
                    else "",
                    feedback_text=feedback_json.get("feedback", "") if feedback_json else "",
                    suggested_next_step=feedback_json.get("suggested_next_step", "")
                    if feedback_json
                    else "",
                    confidence=str(feedback_json.get("confidence", "")) if feedback_json else "",
                    json_compliance=feedback_json is not None,
                    schema_validation_status=parsed["schema_validation_status"],
                    schema_validation_notes=parsed["schema_validation_notes"],
                    solution_leakage_flag=solution_leakage_flag,
                    uses_runtime_evidence=feedback_json.get("uses_runtime_evidence")
                    if feedback_json
                    else None,
                    execution_status=runtime_result.get("execution_status", ""),
                    output_comparison_status=comparison_status,
                    actual_output=runtime_result.get("stdout", ""),
                    actual_stderr=runtime_result.get("stderr", ""),
                    prompt_text=prompt,
                    raw_ai_response=raw_ai_response,
                    ai_error=ai_result.get("error") or parsed["error"] or "",
                    llm_model_name=ai_result.get("model_name", ""),
                    llm_latency_ms=latency_ms,
                    llm_token_usage=ai_result.get("usage") or None,
                    estimated_cost=estimated_cost,
                )

                result_dicts.append(
                    {
                        "database_id": result.id,
                        "evaluation_run_id": evaluation_run.id,
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
                        "estimated_cost": result.estimated_cost,
                    }
                )

    summary = summarise_evaluation_results(result_dicts)
    evaluation_run.summary = summary
    evaluation_run.completed_at = timezone.now()
    evaluation_run.save(update_fields=["summary", "completed_at"])

    output_paths = export_evaluation_run_files(evaluation_run, result_dicts, output_dir)

    return {
        "run": evaluation_run,
        "summary": summary,
        "output_paths": output_paths,
        "results": result_dicts,
    }
