from .feedback_schema import (
    CONFIDENCE_LEVELS,
    ERROR_CATEGORIES,
    FEEDBACK_LEVELS,
    FEEDBACK_SCHEMA_VERSION,
    REQUIRED_FIELDS,
    schema_prompt_block,
)
from .taxonomy import (
    TAXONOMY_SOURCE,
    TAXONOMY_VERSION,
    error_classification_rules_prompt_block,
    error_taxonomy_prompt_block,
    topic_labels,
    topic_taxonomy_prompt_block,
)


PROMPT_BASELINE = "baseline"
PROMPT_CONTEXT_AWARE = "context_aware"
PROMPT_STRICT_SCAFFOLDED = "strict_scaffolded"


PROMPT_VERSION_CHOICES = [
    (PROMPT_BASELINE, "Baseline"),
    (PROMPT_CONTEXT_AWARE, "Context-aware"),
    (PROMPT_STRICT_SCAFFOLDED, "Strict scaffolded"),
]


JSON_STRING_ESCAPING_RULE = (
    "Never include an unescaped double quote or a raw newline inside a JSON "
    "string value. Escape every double quote inside text as \\\" and encode "
    "line breaks as \\n."
)

JSON_REPAIR_INSTRUCTION = (
    "Your previous output was not valid JSON. Re-emit it as a single valid JSON "
    "object, escaping every double quote inside string values as \\\" and "
    "encoding line breaks as \\n instead of using raw newlines inside strings. "
    "Return the JSON object only, with no markdown fences or commentary."
)


def build_json_repair_prompt(original_prompt: str) -> str:
    return f"{original_prompt.rstrip()}\n\nJSON REPAIR RETRY:\n{JSON_REPAIR_INSTRUCTION}\n"


def build_feedback_prompt(
    problem_statement: str,
    student_code: str,
    lecture_objective: str = "",
    support_code: str = "",
    execution_result: dict | None = None,
    sample_input: str = "",
    expected_output: str = "",
    test_harness: str = "",
    topic_tags: str = "",
    output_comparison_status: str = "",
    comparison_mode: str = "",
    prompt_version: str = PROMPT_STRICT_SCAFFOLDED,
) -> str:
    """
    Build the prompt sent to the LLM. Different prompt versions are kept so
    the final evaluation can compare baseline and context-aware designs.
    """
    execution_result = execution_result or {}
    selected_topic_labels = topic_labels(topic_tags)
    selected_topics_text = (
        ", ".join(selected_topic_labels)
        if selected_topic_labels
        else "No fixed topic tags have been assigned."
    )

    if prompt_version == PROMPT_BASELINE:
        context_block = f"""
Programming Question:
{problem_statement}

Instructor Support Code:
{support_code if support_code else "No instructor support code provided."}

Student Code:
{student_code}

Fixed Question Topic(s):
{selected_topics_text}
"""
        rule_block = """
Use only the programming question and submitted code to identify the most likely issue.
Do not rely on runtime output in this baseline prompt version.
"""
    else:
        context_block = f"""
Programming Question:
{problem_statement}

Lecture Objective / Course Concept:
{lecture_objective if lecture_objective else "No specific lecture objective provided."}

Instructor Support Code:
{support_code if support_code else "No instructor support code provided."}

Sample Input:
{sample_input if sample_input else "No sample input provided."}

Expected Output:
{expected_output if expected_output else "No expected output provided."}

Test Harness:
{test_harness if test_harness else "No test harness provided."}

Student Code:
{student_code}

Fixed Question Topic(s):
{selected_topics_text}

Execution Result:
Status: {execution_result.get("execution_status")}
Return Code: {execution_result.get("return_code")}
Timed Out: {execution_result.get("timed_out")}
Execution Time (ms): {execution_result.get("execution_time_ms")}

Actual Standard Output:
{execution_result.get("stdout")}

Error Output:
{execution_result.get("stderr")}

Output Comparison Status:
{output_comparison_status if output_comparison_status else "not_available"}

Output Comparison Mode:
{comparison_mode if comparison_mode else "not_available"}
"""
        rule_block = """
Use the runtime evidence and output comparison when relevant. If the code runs
but the output does not match the expected output, consider whether this is a
logic or conceptual error rather than a syntax/runtime error.
If the comparison mode is normalized, minor case, spacing, or blank-line
differences may be acceptable. If the comparison mode is strict, exact output
format matters.
"""

    scaffold_rules = f"""
Important rules:
1. Do NOT provide the full corrected code.
2. Do NOT directly reveal the final answer.
3. Give scaffolded hints that help the student reason about the bug.
4. Use beginner-friendly language.
5. Refer to the programming question and lecture objective when relevant.
6. Classify with the literature-derived PECI A-X inventory below. Set
   classification_outcome to peci_error and select exactly one A-X code only
   when its definition directly fits. Do not invent, merge, or rename a code.
7. Return ONLY valid JSON. Do not include markdown fences.
8. Use one feedback_level from: {", ".join(FEEDBACK_LEVELS)}.
9. Use one confidence value from: {", ".join(CONFIDENCE_LEVELS)}.
10. Set concept_reference to one fixed topic label listed for the question. If
    none is assigned or supported, use Unknown. Do not invent a new topic.
"""

    if prompt_version == PROMPT_STRICT_SCAFFOLDED:
        scaffold_rules += f"""
11. If you mention a fix, describe the idea without writing a complete corrected program.
12. If runtime evidence is useful, explicitly set uses_runtime_evidence to true.
13. Keep feedback short enough for a beginner to act on.
14. Do not include imports, function definitions, or multi-line corrected code unless they already appear in the student's submission.
15. If the submitted code is supported as correct, set classification_outcome
    to no_error and peci_error_code to an empty string.
16. If a real mistake does not fit A-X, set classification_outcome to
    outside_peci_scope and peci_error_code to an empty string. Keep the exact
    exception or runtime status in the feedback instead of fabricating a code.
17. Output a misconception field: one short sentence naming the student's most
    likely misunderstanding, grounded in the code and runtime evidence. Use an
    empty string when classification_outcome is no_error or unknown.
18. {JSON_STRING_ESCAPING_RULE}
"""

    prompt = f"""
You are an AI programming tutor for beginner Python students.

Your task is to generate educational feedback for an incorrect or incomplete Python submission.

Prompt Version:
{prompt_version}

Feedback Schema Version:
{FEEDBACK_SCHEMA_VERSION}

Human-defined Taxonomy Version:
{TAXONOMY_VERSION}

Taxonomy Basis:
{TAXONOMY_SOURCE}

Fixed Topic Taxonomy:
{topic_taxonomy_prompt_block()}

PECI Table 1 Error Taxonomy (A-X) With Researcher Operational Definitions:
{error_taxonomy_prompt_block()}

Error Classification Priority:
{error_classification_rules_prompt_block()}

{scaffold_rules}

{rule_block}

{context_block}

Return exactly one JSON object with these required fields:
{", ".join(REQUIRED_FIELDS)}

Formal JSON schema:
{schema_prompt_block()}
"""
    return prompt


def build_topic_classification_prompt(
    problem_statement: str,
    lecture_objective: str = "",
) -> str:
    """Build a no-API prompt for assigning a question to the fixed topic set."""
    return f"""
You are classifying an introductory Python programming question.

The topic set was fixed in advance from human domain knowledge. Select one or
more topic IDs from this list and do not create a new topic:

{topic_taxonomy_prompt_block()}

Question:
{problem_statement}

Lecture Objective:
{lecture_objective if lecture_objective else "No lecture objective provided."}

Return only JSON in this form:
{{"topic_tags": ["topic_id"]}}
""".strip()
