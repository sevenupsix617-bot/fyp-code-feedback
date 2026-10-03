import json
import re

from .feedback_schema import FEEDBACK_SCHEMA_VERSION, validate_feedback_payload


def extract_json_object(raw_text: str) -> str:
    text = (raw_text or "").strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1].strip()

    return text


def parse_ai_feedback_with_metadata(raw_text: str) -> dict:
    try:
        parsed = json.loads(extract_json_object(raw_text))
    except json.JSONDecodeError as exc:
        return {
            "feedback_json": None,
            "error": f"AI response was not valid JSON: {exc}",
            "schema_validation_status": "invalid_json",
            "schema_validation_notes": str(exc),
            "feedback_schema_version": FEEDBACK_SCHEMA_VERSION,
        }

    feedback_json, schema_status, schema_notes = validate_feedback_payload(parsed)
    if feedback_json is None:
        return {
            "feedback_json": None,
            "error": schema_notes,
            "schema_validation_status": schema_status,
            "schema_validation_notes": schema_notes,
            "feedback_schema_version": FEEDBACK_SCHEMA_VERSION,
        }

    return {
        "feedback_json": feedback_json,
        "error": None,
        "schema_validation_status": schema_status,
        "schema_validation_notes": schema_notes,
        "feedback_schema_version": FEEDBACK_SCHEMA_VERSION,
    }


def parse_ai_feedback(raw_text: str) -> tuple[dict | None, str | None]:
    result = parse_ai_feedback_with_metadata(raw_text)
    return result["feedback_json"], result["error"]


def detect_solution_leakage(raw_text: str, feedback_json: dict | None = None) -> bool:
    if feedback_json and feedback_json.get("does_reveal_solution") is True:
        return True

    text = raw_text or ""
    feedback = ""
    if feedback_json:
        feedback = str(feedback_json.get("feedback", ""))

    combined = f"{text}\n{feedback}".lower()
    leakage_patterns = [
        r"corrected code",
        r"full solution",
        r"complete solution",
        r"here is the solution",
        r"here is the corrected code",
        r"完整代码",
        r"正确代码",
        r"答案如下",
    ]
    return any(re.search(pattern, combined) for pattern in leakage_patterns)
