import json
import re

from .taxonomy import (
    CLASSIFICATION_OUTCOMES,
    ERROR_TAXONOMY,
    PECI_ERROR_TAXONOMY,
    TOPIC_TAXONOMY,
    canonicalize_peci_error_code,
    canonicalize_topic_reference,
    peci_error_display,
    peci_error_label,
)

FEEDBACK_SCHEMA_VERSION = "feedback_schema_v3_peci"

# Legacy v1/v2 categories remain available only for reproducing the completed
# Day 12 evaluation. New feedback classification uses PECI_ERROR_CODES.
ERROR_CATEGORIES = list(ERROR_TAXONOMY)
PECI_ERROR_CODES = list(PECI_ERROR_TAXONOMY)
CLASSIFICATION_OUTCOME_VALUES = list(CLASSIFICATION_OUTCOMES)

FEEDBACK_LEVELS = ["Level 1", "Level 2", "Level 3"]
CONFIDENCE_LEVELS = ["low", "medium", "high"]
TOPIC_REFERENCE_CHOICES = [
    data["label"] for data in TOPIC_TAXONOMY.values()
] + ["Unknown"]

REQUIRED_FIELDS = [
    "classification_outcome",
    "peci_error_code",
    "feedback_level",
    "concept_reference",
    "misconception",
    "feedback",
    "does_reveal_solution",
    "uses_runtime_evidence",
    "suggested_next_step",
    "confidence",
]

FIELD_DEFAULTS = {
    "classification_outcome": "unknown",
    "peci_error_code": "",
    "feedback_level": "Level 2",
    "concept_reference": "Unknown",
    "misconception": "",
    "feedback": "The AI response was incomplete. Please review the runtime evidence and try again.",
    "does_reveal_solution": False,
    "uses_runtime_evidence": False,
    "suggested_next_step": "Compare the actual output with the expected output and inspect the related code line.",
    "confidence": "low",
}

FEEDBACK_JSON_SCHEMA = {
    "schema_version": FEEDBACK_SCHEMA_VERSION,
    "type": "object",
    "required": REQUIRED_FIELDS,
    "properties": {
        "classification_outcome": {
            "type": "string",
            "enum": CLASSIFICATION_OUTCOME_VALUES,
            "description": (
                "Whether the result is one PECI error, no error, a genuine issue "
                "outside the PECI A-X inventory, or unknown."
            ),
        },
        "peci_error_code": {
            "type": "string",
            "enum": [""] + PECI_ERROR_CODES,
            "description": (
                "Exactly one literature-derived PECI code A-X when "
                "classification_outcome is peci_error; otherwise an empty string."
            ),
        },
        "feedback_level": {
            "type": "string",
            "enum": FEEDBACK_LEVELS,
            "description": "Level 1 general hint, Level 2 targeted hint, Level 3 explicit debugging step.",
        },
        "concept_reference": {
            "type": "string",
            "enum": TOPIC_REFERENCE_CHOICES,
            "description": (
                "The most relevant fixed topic label supplied in the question "
                "context, or Unknown when no topic can be supported."
            ),
        },
        "misconception": {
            "type": "string",
            "description": (
                "One short sentence describing the student's most likely misunderstanding, "
                "grounded in the code and runtime evidence. Return an empty string when "
                "classification_outcome is no_error or unknown."
            ),
        },
        "feedback": {
            "type": "string",
            "description": "Short scaffolded feedback without full corrected code.",
        },
        "does_reveal_solution": {
            "type": "boolean",
            "description": "True only if the response gives away the full answer or corrected program.",
        },
        "uses_runtime_evidence": {
            "type": "boolean",
            "description": "True if the feedback uses stdout, stderr, timeout, or comparison evidence.",
        },
        "suggested_next_step": {
            "type": "string",
            "description": "One concrete next debugging action for the student.",
        },
        "confidence": {
            "type": "string",
            "enum": CONFIDENCE_LEVELS,
        },
    },
    "additionalProperties": False,
}

ERROR_CATEGORY_ALIASES = {
    "syntax": "Syntax Error",
    "syntax error": "Syntax Error",
    "syntax indentation": "Indentation Error",
    "syntax indentation error": "Indentation Error",
    "syntax error indentation error": "Indentation Error",
    "indentation": "Indentation Error",
    "indentation error": "Indentation Error",
    "indentationerror": "Indentation Error",
    "indentation_error": "Indentation Error",
    "tab error": "Indentation Error",
    "taberror": "Indentation Error",
    "tab_error": "Indentation Error",
    "name": "Name Error",
    "name error": "Name Error",
    "type": "Type Error",
    "type error": "Type Error",
    "value": "Value Error",
    "value error": "Value Error",
    "input": "Input Error",
    "input error": "Input Error",
    "eof error": "Input Error",
    "eoferror": "Input Error",
    "output": "Output Format Error",
    "output format": "Output Format Error",
    "output_format": "Output Format Error",
    "formatting": "Output Format Error",
    "string formatting": "Output Format Error",
    "string_formatting": "Output Format Error",
    "logic": "Logic Error",
    "logic error": "Logic Error",
    "loop": "Loop Boundary Error",
    "loop boundary": "Loop Boundary Error",
    "off by one": "Loop Boundary Error",
    "off-by-one": "Loop Boundary Error",
    "off_by_one": "Loop Boundary Error",
    "condition": "Condition Error",
    "condition error": "Condition Error",
    "operator misuse": "Condition Error",
    "operator_misuse": "Condition Error",
    "function": "Function Error",
    "function error": "Function Error",
    "function logic": "Function Error",
    "index": "Index Error",
    "index error": "Index Error",
    "indexerror": "Index Error",
    "index_error": "Index Error",
    "list index": "Index Error",
    "list indexing": "Index Error",
    "module": "Module Import Error",
    "module import": "Module Import Error",
    "module not found": "Module Import Error",
    "module_not_found": "Module Import Error",
    "import error": "Module Import Error",
    "timeout": "Timeout",
    "concept": "Conceptual Error",
    "conceptual": "Conceptual Error",
    "conceptual error": "Conceptual Error",
    "no error": "No Error",
    "no_error": "No Error",
    "unknown": "Unknown",
}


def _normalise_key(value: str) -> str:
    value = re.sub(r"[_\-/]+", " ", str(value or "").strip().lower())
    value = re.sub(r"\s+", " ", value)
    return value


def _coerce_text(value, default: str) -> str:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip() or default


def _coerce_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalised = value.strip().lower()
        if normalised in {"true", "yes", "1"}:
            return True
        if normalised in {"false", "no", "0"}:
            return False
    return default


def canonicalize_error_category(value: str) -> tuple[str, str | None]:
    original = _coerce_text(value, "Unknown")
    if original in ERROR_CATEGORIES:
        return original, None

    alias = ERROR_CATEGORY_ALIASES.get(_normalise_key(original))
    if alias:
        return alias, f"error_category normalised from {original!r} to {alias!r}"

    return "Unknown", f"error_category {original!r} was not recognised"


def canonicalize_classification_outcome(value: str) -> tuple[str, str | None]:
    original = _coerce_text(value, FIELD_DEFAULTS["classification_outcome"])
    normalised = _normalise_key(original)
    aliases = {
        "peci error": "peci_error",
        "peci_error": "peci_error",
        "error": "peci_error",
        "no error": "no_error",
        "no_error": "no_error",
        "correct": "no_error",
        "outside peci scope": "outside_peci_scope",
        "outside_peci_scope": "outside_peci_scope",
        "outside scope": "outside_peci_scope",
        "unknown": "unknown",
    }
    canonical = aliases.get(normalised)
    if canonical:
        note = None if original == canonical else f"classification_outcome normalised from {original!r} to {canonical!r}"
        return canonical, note
    return "unknown", f"classification_outcome {original!r} was not recognised"


def canonicalize_feedback_level(value: str) -> tuple[str, str | None]:
    original = _coerce_text(value, FIELD_DEFAULTS["feedback_level"])
    if original in FEEDBACK_LEVELS:
        return original, None

    normalised = _normalise_key(original)
    level_match = re.search(r"\b([123])\b", normalised)
    if level_match:
        level = f"Level {level_match.group(1)}"
        return level, f"feedback_level normalised from {original!r} to {level!r}"

    hint_aliases = {
        "general": "Level 1",
        "general hint": "Level 1",
        "hint": "Level 2",
        "targeted hint": "Level 2",
        "debugging step": "Level 3",
        "explicit debugging step": "Level 3",
    }
    alias = hint_aliases.get(normalised)
    if alias:
        return alias, f"feedback_level normalised from {original!r} to {alias!r}"

    return "Level 2", f"feedback_level {original!r} was not recognised"


def canonicalize_confidence(value: str) -> tuple[str, str | None]:
    original = _coerce_text(value, FIELD_DEFAULTS["confidence"]).lower()
    if original in CONFIDENCE_LEVELS:
        return original, None

    return "low", f"confidence {original!r} was not recognised"


def _limit_text(field_name: str, value: str, max_length: int) -> tuple[str, str | None]:
    if len(value) <= max_length:
        return value, None
    return value[:max_length].rstrip(), f"{field_name} was trimmed to {max_length} characters"


def validate_feedback_payload(payload) -> tuple[dict | None, str, str]:
    """
    Validate and normalise an LLM feedback JSON object.
    Returns (payload, status, notes). The payload is None only when the JSON
    value is not an object and cannot be repaired.
    """
    if not isinstance(payload, dict):
        return None, "invalid_schema", "Top-level AI response JSON must be an object."

    notes = []
    is_legacy_payload = "error_category" in payload and not any(
        field_name in payload
        for field_name in ("classification_outcome", "peci_error_code")
    )
    normalised_payload = {}

    for field_name in REQUIRED_FIELDS:
        if field_name not in payload:
            notes.append(f"missing field {field_name!r}; default inserted")
        normalised_payload[field_name] = payload.get(field_name, FIELD_DEFAULTS[field_name])

    # v1/v2 payloads may contain error_category. Preserve it as legacy metadata,
    # but never translate it into a PECI code because that would invent evidence.
    legacy_error_category = ""
    if "error_category" in payload:
        legacy_error_category, legacy_note = canonicalize_error_category(payload["error_category"])
        notes.append("legacy error_category retained but not treated as a PECI A-X classification")
        if legacy_note:
            notes.append(legacy_note)

    for field_name in set(payload.keys()) - set(REQUIRED_FIELDS) - {"error_category"}:
        notes.append(f"ignored unexpected field {field_name!r}")

    normalised_payload["classification_outcome"], note = canonicalize_classification_outcome(
        normalised_payload["classification_outcome"]
    )
    if note:
        notes.append(note)

    normalised_payload["peci_error_code"], note = canonicalize_peci_error_code(
        normalised_payload["peci_error_code"]
    )
    if note:
        notes.append(note)

    if normalised_payload["classification_outcome"] == "peci_error":
        if not normalised_payload["peci_error_code"]:
            normalised_payload["classification_outcome"] = "unknown"
            notes.append("peci_error requires one valid A-X code; outcome changed to unknown")
    elif normalised_payload["peci_error_code"]:
        normalised_payload["peci_error_code"] = ""
        notes.append("peci_error_code cleared because outcome is not peci_error")

    code = normalised_payload["peci_error_code"]
    outcome = normalised_payload["classification_outcome"]
    outcome_display = dict(CLASSIFICATION_OUTCOMES)[outcome]
    normalised_payload["peci_error_label"] = peci_error_label(code)
    normalised_payload["error_category"] = (
        legacy_error_category
        if is_legacy_payload and legacy_error_category
        else peci_error_display(code) or outcome_display
    )
    normalised_payload["legacy_error_category"] = legacy_error_category

    normalised_payload["feedback_level"], note = canonicalize_feedback_level(
        normalised_payload["feedback_level"]
    )
    if note:
        notes.append(note)

    normalised_payload["confidence"], note = canonicalize_confidence(
        normalised_payload["confidence"]
    )
    if note:
        notes.append(note)

    for field_name in ("concept_reference", "misconception", "feedback", "suggested_next_step"):
        normalised_payload[field_name] = _coerce_text(
            normalised_payload[field_name],
            FIELD_DEFAULTS[field_name],
        )

    normalised_payload["concept_reference"], note = canonicalize_topic_reference(
        normalised_payload["concept_reference"]
    )
    if note:
        notes.append(note)

    normalised_payload["misconception"], note = _limit_text(
        "misconception",
        normalised_payload["misconception"],
        400,
    )
    if note:
        notes.append(note)
    if outcome in {"no_error", "unknown"} and normalised_payload["misconception"]:
        normalised_payload["misconception"] = ""
        notes.append("misconception cleared for no_error or unknown outcome")

    normalised_payload["feedback"], note = _limit_text(
        "feedback",
        normalised_payload["feedback"],
        1200,
    )
    if note:
        notes.append(note)

    normalised_payload["suggested_next_step"], note = _limit_text(
        "suggested_next_step",
        normalised_payload["suggested_next_step"],
        400,
    )
    if note:
        notes.append(note)

    for field_name in ("does_reveal_solution", "uses_runtime_evidence"):
        original = normalised_payload[field_name]
        coerced = _coerce_bool(original, FIELD_DEFAULTS[field_name])
        if not isinstance(original, bool):
            notes.append(f"{field_name} coerced to boolean")
        normalised_payload[field_name] = coerced

    status = "valid_schema" if not notes else "repaired_schema"
    return normalised_payload, status, "; ".join(notes)


def schema_prompt_block() -> str:
    return json.dumps(FEEDBACK_JSON_SCHEMA, indent=2)
