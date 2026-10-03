import re


EXACT_MATCH = "exact_match"
NORMALIZED_MATCH = "normalized_match"
MISMATCH = "mismatch"
NOT_APPLICABLE = "not_applicable"
EXECUTION_ERROR = "execution_error"
TIMEOUT = "timeout"

COMPARISON_MODE_STRICT = "strict"
COMPARISON_MODE_NORMALIZED = "normalized"

COMPARISON_MODE_CHOICES = [
    (COMPARISON_MODE_STRICT, "Strict exact output"),
    (COMPARISON_MODE_NORMALIZED, "Normalized beginner-friendly output"),
]


def normalize_output(
    text: str,
    *,
    ignore_case: bool = True,
    collapse_whitespace: bool = True,
    drop_blank_lines: bool = True,
) -> str:
    text = text or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = []
    for line in text.split("\n"):
        normalized_line = line.strip()
        if collapse_whitespace:
            normalized_line = re.sub(r"[ \t]+", " ", normalized_line)
        if drop_blank_lines and normalized_line == "":
            continue
        lines.append(normalized_line)

    normalized = "\n".join(lines)
    if ignore_case:
        normalized = normalized.lower()
    return normalized


def compare_outputs(
    actual_output: str,
    expected_output: str,
    execution_status: str = "",
    mode: str = COMPARISON_MODE_NORMALIZED,
) -> str:
    if not expected_output.strip():
        return NOT_APPLICABLE

    if execution_status == "timeout":
        return TIMEOUT

    if execution_status and execution_status != "success":
        return EXECUTION_ERROR

    if actual_output == expected_output:
        return EXACT_MATCH

    if mode == COMPARISON_MODE_STRICT:
        return MISMATCH

    if normalize_output(actual_output) == normalize_output(expected_output):
        return NORMALIZED_MATCH

    return MISMATCH
