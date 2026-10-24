import builtins
import html
import io
import keyword
import re
import tokenize
from itertools import groupby

from django.utils.safestring import mark_safe


BUILTIN_NAMES = set(dir(builtins))
COLOURED_OPERATORS = {"+", "-", "*", "/", "//", "%", "**", "=", "+=", "-=", "*=", "/=", "==", "!=", "<", ">", "<=", ">=", ":="}
TRACEBACK_LINE = re.compile(r'File "[^"]*submission\.py", line (\d+)')


def _token_class(token):
    if token.type == tokenize.NAME:
        if keyword.iskeyword(token.string):
            return "review-token-keyword"
        if token.string in BUILTIN_NAMES:
            return "review-token-builtin"
    if token.type == tokenize.STRING:
        return "review-token-string"
    if token.type == tokenize.NUMBER:
        return "review-token-number"
    if token.type == tokenize.COMMENT:
        return "review-token-comment"
    if token.type == tokenize.OP and token.string in COLOURED_OPERATORS:
        return "review-token-operator"
    return None


def build_code_review(source, execution_status="", stderr=""):
    """Syntax-colour stored code; mark only lines identified by Python's traceback."""
    lines = source.splitlines() or [""]
    styles = [[None] * len(line) for line in lines]

    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            token_class = _token_class(token)
            if not token_class:
                continue
            start_line, start_col = token.start
            end_line, end_col = token.end
            for line_number in range(start_line, min(end_line, len(lines)) + 1):
                line_index = line_number - 1
                first_col = start_col if line_number == start_line else 0
                last_col = end_col if line_number == end_line else len(lines[line_index])
                for column in range(first_col, min(last_col, len(lines[line_index]))):
                    styles[line_index][column] = token_class
    except (tokenize.TokenError, IndentationError):
        pass

    runtime_line = None
    if execution_status not in {"success", "timeout", "empty_code", "system_error"}:
        reported_lines = [int(match) for match in TRACEBACK_LINE.findall(stderr)]
        runtime_line = next((number for number in reversed(reported_lines) if 1 <= number <= len(lines)), None)

    rendered_lines = []
    for number, (line, line_styles) in enumerate(zip(lines, styles), start=1):
        parts = []
        for token_class, positions in groupby(range(len(line)), key=lambda column: line_styles[column]):
            columns = list(positions)
            content = html.escape(line[columns[0]:columns[-1] + 1])
            parts.append(f'<span class="{token_class}">{content}</span>' if token_class else content)
        rendered_lines.append({
            "number": number,
            "html": mark_safe("".join(parts)),
            "runtime_error": number == runtime_line,
        })

    return {"lines": rendered_lines, "runtime_line": runtime_line}
