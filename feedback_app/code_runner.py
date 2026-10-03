import os
import subprocess
import tempfile
import time


ERROR_STATUS_MARKERS = [
    ("TabError", "indentation_error"),
    ("IndentationError", "indentation_error"),
    ("SyntaxError", "syntax_error"),
    ("UnboundLocalError", "name_error"),
    ("NameError", "name_error"),
    ("TypeError", "type_error"),
    ("ValueError", "value_error"),
    ("IndexError", "index_error"),
    ("KeyError", "key_error"),
    ("EOFError", "eof_error"),
    ("ModuleNotFoundError", "module_not_found"),
    ("ImportError", "import_error"),
]


def _safe_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _classify_error(stderr: str) -> str:
    for marker, status in ERROR_STATUS_MARKERS:
        if marker in stderr:
            return status
    return "runtime_error"


def _sandbox_env() -> dict:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def run_python_code(
    code: str,
    sample_input: str = "",
    timeout: int = 3,
    test_harness: str = "",
) -> dict:
    """
    Run submitted Python code in a temporary file and capture output.
    This is a simple prototype sandbox for FYP demonstration.
    It captures stdout, stderr, return code, timeout errors, and elapsed time.
    """

    if not code.strip():
        return {
            "execution_status": "empty_code",
            "stdout": "",
            "stderr": "No code was provided.",
            "return_code": None,
            "timed_out": False,
            "execution_time_ms": 0,
        }

    start_time = time.monotonic()
    sample_input = _safe_text(sample_input)
    timeout = max(int(timeout), 1)

    try:
        with tempfile.TemporaryDirectory(prefix="fyp_sandbox_") as temp_dir:
            temp_file_path = os.path.join(temp_dir, "submission.py")
            with open(temp_file_path, "w", encoding="utf-8") as temp_file:
                temp_file.write(code)
                if test_harness.strip():
                    temp_file.write("\n\n")
                    temp_file.write(test_harness)

            result = subprocess.run(
                ["python3", "-I", "-B", temp_file_path],
                input=sample_input,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=temp_dir,
                env=_sandbox_env(),
            )
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        if result.returncode == 0:
            status = "success"
        else:
            status = _classify_error(result.stderr)

        return {
            "execution_status": status,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
            "timed_out": False,
            "execution_time_ms": elapsed_ms,
        }

    except subprocess.TimeoutExpired as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return {
            "execution_status": "timeout",
            "stdout": _safe_text(e.stdout),
            "stderr": _safe_text(e.stderr) or f"Execution timed out after {timeout} seconds.",
            "return_code": None,
            "timed_out": True,
            "execution_time_ms": elapsed_ms,
        }

    except Exception as e:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        return {
            "execution_status": "system_error",
            "stdout": "",
            "stderr": str(e),
            "return_code": None,
            "timed_out": False,
            "execution_time_ms": elapsed_ms,
        }
