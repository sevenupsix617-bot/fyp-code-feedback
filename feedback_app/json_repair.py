from decimal import Decimal


def should_retry_invalid_json(parsed_response, llm_result=None):
    llm_result = llm_result or {}
    error = str(parsed_response.get("error") or "")
    return bool(
        parsed_response.get("feedback_json") is None
        and not llm_result.get("error")
        and "not valid JSON" in error
    )


def merge_llm_call_metadata(initial_result, repair_result):
    merged = dict(repair_result)
    usage = {}
    for result in (initial_result, repair_result):
        for key, value in (result.get("usage") or {}).items():
            if isinstance(value, (int, float)):
                usage[key] = usage.get(key, 0) + value
    merged["usage"] = usage

    costs = [
        Decimal(str(result["estimated_cost"]))
        for result in (initial_result, repair_result)
        if result.get("estimated_cost") is not None
    ]
    merged["estimated_cost"] = sum(costs, Decimal("0")) if costs else None
    return merged


def combine_json_repair_responses(initial_raw, repair_raw):
    return (
        "INITIAL INVALID JSON RESPONSE:\n"
        f"{initial_raw}\n\n"
        "JSON REPAIR RETRY RESPONSE:\n"
        f"{repair_raw}"
    )


def json_repair_schema_notes(initial_error, final_notes, succeeded):
    outcome = "succeeded" if succeeded else "failed"
    notes = f"JSON repair retry {outcome} after initial parse error: {initial_error}"
    if final_notes:
        notes += f"; final parser notes: {final_notes}"
    return notes
