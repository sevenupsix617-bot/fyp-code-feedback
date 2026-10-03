"""Human-defined topic and novice-error taxonomies used by the feedback system.

The taxonomy is intentionally fixed before any LLM classification. It is
adapted to this project's introductory Python scope from the PECI concept and
error inventory described by Cooke, Hawwash, and Smith (SEFI 2019), then
refined using the supervisor's 2026-09-16 guidance and the project's observed
student-code cases.
"""

from collections import OrderedDict
import re


TAXONOMY_VERSION = "peci_taxonomy_v3_2026_09_17"
TAXONOMY_SOURCE = (
    "Cooke, Hawwash, and Smith (2019), Python for Engineers Concept Inventory "
    "(PECI), Table 1; supervisor review dated 2026-09-16."
)


TOPIC_TAXONOMY = OrderedDict(
    [
        (
            "program_structure",
            {
                "label": "Program Structure and Statements",
                "definition": (
                    "Program execution order, Python statements, block structure, "
                    "and how separate statements form a complete program."
                ),
                "peci_concepts": ("C1 The Program", "C4 Statements"),
            },
        ),
        (
            "variables_assignment",
            {
                "label": "Variables and Assignment",
                "definition": (
                    "Creating names, storing values, updating state, and tracing how "
                    "assignment changes a variable during execution."
                ),
                "peci_concepts": ("C2 Variables",),
            },
        ),
        (
            "expressions_operators",
            {
                "label": "Expressions and Operators",
                "definition": (
                    "Arithmetic, comparison, division, modulo, precedence, and the "
                    "evaluation of expressions."
                ),
                "peci_concepts": ("C3 Expressions",),
            },
        ),
        (
            "conditionals_boolean",
            {
                "label": "Conditionals and Boolean Logic",
                "definition": (
                    "Boolean conditions and if/elif/else branches used to select "
                    "which statements execute."
                ),
                "peci_concepts": ("C6 Conditionals",),
            },
        ),
        (
            "iteration_range",
            {
                "label": "Iteration and Range",
                "definition": (
                    "for/while loops, range boundaries, repeated state updates, "
                    "accumulator patterns, and loop termination."
                ),
                "peci_concepts": ("C9 Iteration",),
            },
        ),
        (
            "functions_returns",
            {
                "label": "Functions and Return Values",
                "definition": (
                    "Function definitions and calls, parameters, local scope, and "
                    "returning a value to the caller."
                ),
                "peci_concepts": ("C5 Functions", "C8 Fruitful functions"),
            },
        ),
        (
            "strings_io",
            {
                "label": "Strings, Input, and Output",
                "definition": (
                    "String values and quotation, reading user input, conversion at "
                    "the input boundary, and producing the required printed format."
                ),
                "peci_concepts": ("C10 Strings", "C4 Statements"),
            },
        ),
        (
            "collections_indexing",
            {
                "label": "Collections and Indexing",
                "definition": (
                    "Lists, dictionaries, and tuples, including element access, "
                    "indices, traversal, and collection operations."
                ),
                "peci_concepts": ("C11 Lists", "C12 Dictionaries", "C13 Tuples"),
            },
        ),
    ]
)


PECI_ERROR_TAXONOMY = OrderedDict(
    [
        ("A", {"label": "Invalid names", "definition": "An identifier is invalid for the role in which it is used, excluding the more specific misspelling and reserved-keyword cases N and O."}),
        ("B", {"label": "Left-to-right assignments", "definition": "The student treats assignment as if the value flows from the left side to the right side, reversing Python's target = value relationship."}),
        ("C", {"label": "Assignments in expressions", "definition": "An assignment is placed where an expression or Boolean test is required, or assignment and expression evaluation are confused."}),
        ("D", {"label": "Expressions as parameters", "definition": "An expression is supplied or structured incorrectly as a function argument or parameter, so the call does not represent the intended value or contract."}),
        ("E", {"label": "Literal values instead of variables", "definition": "A fixed literal is used where the task requires a variable or computed value, causing the program to work only for a particular case."}),
        ("F", {"label": "Extra or missing spaces", "definition": "Spaces are added or omitted where they change required program or output form, including exact-format output tasks."}),
        ("G", {"label": "Invalid else-statements", "definition": "An else or elif branch is attached, ordered, or structured incorrectly relative to its if statement."}),
        ("H", {"label": "Missing or extra quotation marks", "definition": "A string uses missing, extra, or mismatched quotation marks, changing or invalidating the intended string literal."}),
        ("I", {"label": "Division and modulo", "definition": "Division or modulo is selected, interpreted, or applied incorrectly for the required calculation or divisibility test."}),
        ("J", {"label": "Invalid use of the and-operator", "definition": "The Boolean and operator combines conditions incorrectly or is used where separate complete comparisons are required."}),
        ("K", {"label": "Wrong or extra keyword", "definition": "A Python keyword is incorrect, unnecessary, or placed where the language does not permit it."}),
        ("L", {"label": "Incorrect structure", "definition": "The program's statement, block, branch, loop, or function structure is arranged incorrectly and no more specific PECI category describes the primary cause."}),
        ("M", {"label": "Unbalanced parentheses and brackets", "definition": "Opening and closing parentheses, square brackets, or braces are missing, extra, or mismatched."}),
        ("N", {"label": "Misspelled names or keywords", "definition": "A variable, function, method, or keyword is spelled inconsistently with its definition or Python's required spelling."}),
        ("O", {"label": "Using keywords as names", "definition": "A reserved Python keyword is used as a variable, function, parameter, or other identifier."}),
        ("P", {"label": "Using assignment instead of comparison", "definition": "Assignment syntax is used where equality or another comparison is intended."}),
        ("Q", {"label": "Misspelled operators", "definition": "An operator is written in an invalid or unintended form, such as mistyping a comparison or arithmetic operator."}),
        ("R", {"label": "Unterminated string literal", "definition": "A string begins with a quotation mark but is not closed correctly before the line or file ends."}),
        ("S", {"label": "Missing colon, comma or operator", "definition": "Required punctuation or an operator is omitted, such as a missing colon after a compound statement or a missing comma between arguments."}),
        ("T", {"label": "Invalid indentation", "definition": "Indentation is missing, unexpected, or inconsistent, so Python block membership is invalid or differs from the intended control flow."}),
        ("U", {"label": "Code after a break statement", "definition": "Statements are placed after break in the same loop block and are therefore unreachable on that path."}),
        ("V", {"label": "Call without parentheses", "definition": "A function or method is referenced without the parentheses needed to call it when execution of that callable is intended."}),
        ("W", {"label": "Useless computations", "definition": "A computation is performed but its result is neither stored, returned, printed, nor otherwise used to affect the program."}),
        ("X", {"label": "Useless comparison", "definition": "A comparison is evaluated but its Boolean result is ignored and therefore does not influence control flow or output."}),
    ]
)


CLASSIFICATION_OUTCOMES = OrderedDict(
    [
        ("peci_error", "PECI error identified"),
        ("no_error", "No Error"),
        ("outside_peci_scope", "Outside PECI Scope"),
        ("unknown", "Unknown"),
    ]
)


# Retained only so the completed Day 12 v1/v2 evaluation remains reproducible.
# It is not the primary taxonomy for new feedback records.
LEGACY_ERROR_TAXONOMY = OrderedDict(
    [
        (
            "Syntax Error",
            {
                "definition": (
                    "Python cannot parse the program because required syntax is "
                    "missing, malformed, or misplaced. Use Indentation Error instead "
                    "when the parser specifically reports indentation or tab usage."
                ),
                "peci_errors": (
                    "K Wrong or extra keyword",
                    "M Unbalanced parentheses and brackets",
                    "R Unterminated string literal",
                    "S Missing colon, comma or operator",
                ),
            },
        ),
        (
            "Indentation Error",
            {
                "definition": (
                    "A block has missing, unexpected, or inconsistent indentation, "
                    "including IndentationError and TabError evidence."
                ),
                "peci_errors": ("T Invalid indentation",),
            },
        ),
        (
            "Name Error",
            {
                "definition": (
                    "The program refers to an undefined, misspelled, out-of-scope, "
                    "or otherwise invalid identifier, including NameError and "
                    "UnboundLocalError evidence."
                ),
                "peci_errors": (
                    "A Invalid names",
                    "N Misspelled names or keywords",
                    "O Using keywords as names",
                ),
            },
        ),
        (
            "Type Error",
            {
                "definition": (
                    "An operation or function receives an incompatible Python type, "
                    "such as combining a string and integer without conversion."
                ),
                "peci_errors": ("D Expressions as parameters",),
            },
        ),
        (
            "Value Error",
            {
                "definition": (
                    "The data has an acceptable type but an invalid value for the "
                    "requested conversion or operation, normally supported by a "
                    "ValueError."
                ),
                "peci_errors": (),
            },
        ),
        (
            "Input Error",
            {
                "definition": (
                    "The program reads the wrong number or order of inputs, omits a "
                    "required input, or interprets the supplied input incorrectly. "
                    "Prefer Type Error or Value Error when a more specific runtime "
                    "exception identifies the failure."
                ),
                "peci_errors": (),
            },
        ),
        (
            "Output Format Error",
            {
                "definition": (
                    "The computed result is substantively correct but the required "
                    "printed text, spacing, case, punctuation, or line structure is "
                    "wrong. Do not use this for an incorrect numeric or logical result."
                ),
                "peci_errors": (
                    "F Extra or missing spaces",
                    "H Missing or extra quotation marks",
                ),
            },
        ),
        (
            "Logic Error",
            {
                "definition": (
                    "The program runs but its general algorithm, calculation, or state "
                    "update is wrong. Use this only when the defect does not fit a more "
                    "specific loop, condition, function, index, or format category."
                ),
                "peci_errors": (
                    "B Left-to-right assignments",
                    "C Assignments in expressions",
                    "E Literal values instead of variables",
                    "W Useless computations",
                ),
            },
        ),
        (
            "Loop Boundary Error",
            {
                "definition": (
                    "A loop starts, stops, or repeats the wrong number of times, such "
                    "as an off-by-one range boundary. Use Timeout when non-termination "
                    "is the strongest observed evidence."
                ),
                "peci_errors": (),
            },
        ),
        (
            "Condition Error",
            {
                "definition": (
                    "A Boolean expression, comparison operator, or branch arrangement "
                    "selects the wrong path even though the code can execute."
                ),
                "peci_errors": (
                    "G Invalid else-statements",
                    "J Invalid use of the and-operator",
                    "P Using assignment instead of comparison",
                    "X Useless comparison",
                ),
            },
        ),
        (
            "Function Error",
            {
                "definition": (
                    "A function contract is incomplete or misused: the definition, "
                    "call, parameters, scope, return value, or return placement does "
                    "not satisfy the question."
                ),
                "peci_errors": ("V Call without parentheses",),
            },
        ),
        (
            "Index Error",
            {
                "definition": (
                    "The program accesses a collection position that does not exist or "
                    "uses the wrong index boundary, usually supported by IndexError "
                    "or clear collection-access evidence."
                ),
                "peci_errors": (),
            },
        ),
        (
            "Module Import Error",
            {
                "definition": (
                    "A required module or imported name cannot be found or is imported "
                    "incorrectly, including ImportError and ModuleNotFoundError."
                ),
                "peci_errors": (),
            },
        ),
        (
            "Timeout",
            {
                "definition": (
                    "Execution exceeds the sandbox time limit, normally because the "
                    "program does not terminate or performs unintended repeated work."
                ),
                "peci_errors": (),
            },
        ),
        (
            "Conceptual Error",
            {
                "definition": (
                    "The submission shows a broad misunderstanding of the task or a "
                    "programming concept that cannot be localised to one narrower "
                    "operational category. State the misconception in the feedback."
                ),
                "peci_errors": (),
            },
        ),
        (
            "No Error",
            {
                "definition": (
                    "Available runtime and task evidence supports that the submission "
                    "satisfies the question and no semantic defect is visible. Passing "
                    "one sample alone is not proof when the code is known to fail for "
                    "other valid inputs."
                ),
                "peci_errors": (),
            },
        ),
        (
            "Unknown",
            {
                "definition": (
                    "The available question, code, and runtime evidence are insufficient "
                    "or conflicting, so a reliable category cannot be assigned."
                ),
                "peci_errors": (),
            },
        ),
    ]
)


ERROR_TAXONOMY = LEGACY_ERROR_TAXONOMY


ERROR_CLASSIFICATION_RULES = (
    "Select peci_error only when one A-X definition directly describes the primary mistake; then return exactly one PECI code.",
    "Use deterministic runtime evidence to locate the defect, but do not convert an exception name into a PECI category unless the code pattern satisfies that category's definition.",
    "When several mistakes exist, choose the earliest root cause that prevents the intended program behaviour and explain the other evidence in the feedback.",
    "Use no_error only when the available task and runtime evidence supports correctness; one passing sample is not proof if another visible defect remains.",
    "Use outside_peci_scope for a real mistake not represented by A-X, such as a timeout, an out-of-range index, an unsupported import, or a type/value failure with no matching PECI pattern.",
    "Use unknown only when the evidence is insufficient or conflicting. Never invent, merge, or rename an A-X category.",
)


TOPIC_ALIASES = {
    "program": "program_structure",
    "program structure": "program_structure",
    "program structure and statements": "program_structure",
    "statements": "program_structure",
    "syntax indentation": "program_structure",
    "module import": "program_structure",
    "variables": "variables_assignment",
    "variable": "variables_assignment",
    "variables and assignment": "variables_assignment",
    "variable names": "variables_assignment",
    "assignment": "variables_assignment",
    "state": "variables_assignment",
    "name undefined variable": "variables_assignment",
    "operators": "expressions_operators",
    "operator": "expressions_operators",
    "expressions and operators": "expressions_operators",
    "modulo operator": "expressions_operators",
    "division": "expressions_operators",
    "modulo": "expressions_operators",
    "algorithm logic": "expressions_operators",
    "type operation": "expressions_operators",
    "conditionals": "conditionals_boolean",
    "conditional": "conditionals_boolean",
    "conditionals and boolean logic": "conditionals_boolean",
    "conditional boundary": "conditionals_boolean",
    "boolean": "conditionals_boolean",
    "loops": "iteration_range",
    "loop": "iteration_range",
    "iteration and range": "iteration_range",
    "loop accumulator": "iteration_range",
    "range boundary": "iteration_range",
    "range end boundary": "iteration_range",
    "for loop syntax": "iteration_range",
    "range": "iteration_range",
    "off by one": "iteration_range",
    "loop boundary off by one": "iteration_range",
    "timeout infinite loop": "iteration_range",
    "functions": "functions_returns",
    "function": "functions_returns",
    "functions and return values": "functions_returns",
    "function return expressions": "functions_returns",
    "multiple function definitions": "functions_returns",
    "return": "functions_returns",
    "scope": "functions_returns",
    "parameters": "functions_returns",
    "multiple functions": "functions_returns",
    "function return": "functions_returns",
    "strings": "strings_io",
    "string": "strings_io",
    "strings input and output": "strings_io",
    "string concatenation": "strings_io",
    "input()": "strings_io",
    "input and print": "strings_io",
    "input conversion": "strings_io",
    "input": "strings_io",
    "print": "strings_io",
    "input handling": "strings_io",
    "output formatting": "strings_io",
    "lists": "collections_indexing",
    "list": "collections_indexing",
    "collections and indexing": "collections_indexing",
    "len() and average": "collections_indexing",
    "list indexing": "collections_indexing",
    "indexing": "collections_indexing",
    "dictionaries": "collections_indexing",
    "tuples": "collections_indexing",
}


TOPIC_REFERENCE_KEYWORDS = (
    ("collections_indexing", ("list", "index", "dictionary", "tuple", "collection")),
    ("conditionals_boolean", ("condition", "boolean", "if/elif/else", "branch")),
    ("iteration_range", ("loop", "range", "iteration", "accumulator")),
    ("functions_returns", ("function", "return", "parameter", "scope")),
    ("strings_io", ("input", "print", "string", "conversion", "line break")),
    ("variables_assignment", ("variable", "assignment", "undefined name")),
    ("expressions_operators", ("expression", "operator", "division", "modulo", "arithmetic")),
    ("program_structure", ("statement", "indent", "syntax", "program structure")),
)


def _normalise_key(value: str) -> str:
    value = re.sub(r"[_\-/]+", " ", str(value or "").strip().lower())
    return re.sub(r"\s+", " ", value)


def canonicalize_topic_tag(value: str) -> str | None:
    raw = str(value or "").strip()
    if raw in TOPIC_TAXONOMY:
        return raw
    return TOPIC_ALIASES.get(_normalise_key(raw))


def parse_topic_tags(value) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_tags = value
    else:
        raw_tags = re.split(r"[,;]", str(value or ""))

    selected = set()
    for raw_tag in raw_tags:
        canonical = canonicalize_topic_tag(raw_tag)
        if canonical:
            selected.add(canonical)
    return [topic_id for topic_id in TOPIC_TAXONOMY if topic_id in selected]


def serialize_topic_tags(value) -> str:
    return ",".join(parse_topic_tags(value))


def topic_labels(value) -> list[str]:
    return [TOPIC_TAXONOMY[topic_id]["label"] for topic_id in parse_topic_tags(value)]


def canonicalize_topic_reference(value: str) -> tuple[str, str | None]:
    original = str(value or "").strip() or "Unknown"
    if original == "Unknown":
        return original, None

    canonical = canonicalize_topic_tag(original)
    if canonical:
        label = TOPIC_TAXONOMY[canonical]["label"]
        if original == label:
            return label, None
        return label, f"concept_reference normalised from {original!r} to {label!r}"

    normalised = _normalise_key(original)
    for topic_id, keywords in TOPIC_REFERENCE_KEYWORDS:
        if any(keyword in normalised for keyword in keywords):
            label = TOPIC_TAXONOMY[topic_id]["label"]
            return label, f"concept_reference normalised from {original!r} to {label!r}"

    return "Unknown", f"concept_reference {original!r} was not recognised"


def topic_choices() -> list[tuple[str, str]]:
    return [(topic_id, data["label"]) for topic_id, data in TOPIC_TAXONOMY.items()]


def topic_taxonomy_prompt_block() -> str:
    lines = []
    for topic_id, data in TOPIC_TAXONOMY.items():
        lines.append(f'- {topic_id}: {data["label"]} - {data["definition"]}')
    return "\n".join(lines)


def error_taxonomy_prompt_block() -> str:
    lines = []
    for code, data in PECI_ERROR_TAXONOMY.items():
        lines.append(f'- {code} - {data["label"]}: {data["definition"]}')
    return "\n".join(lines)


def canonicalize_peci_error_code(value: str) -> tuple[str, str | None]:
    original = str(value or "").strip().upper()
    if not original:
        return "", None
    match = re.match(r"^([A-X])(?:\b|\s*[-:])", original)
    code = match.group(1) if match else original
    if code in PECI_ERROR_TAXONOMY:
        note = None if original == code else f"peci_error_code normalised from {value!r} to {code!r}"
        return code, note
    return "", f"peci_error_code {value!r} was not recognised"


def peci_error_label(code: str) -> str:
    canonical, _ = canonicalize_peci_error_code(code)
    return PECI_ERROR_TAXONOMY.get(canonical, {}).get("label", "")


def peci_error_display(code: str) -> str:
    canonical, _ = canonicalize_peci_error_code(code)
    return peci_error_label(canonical)


def error_classification_rules_prompt_block() -> str:
    return "\n".join(
        f"{index}. {rule}" for index, rule in enumerate(ERROR_CLASSIFICATION_RULES, start=1)
    )
