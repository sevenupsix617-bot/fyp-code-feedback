import subprocess
import tempfile
import os

def run_python_code(code: str, timeout: int = 3) -> dict:
    """
    Run submitted Python code in a temporary file and capture output.
    This is a simple prototype sandbox for FYP demonstration.
    It captures stdout, stderr, return code, and timeout errors.
    """

    if not code.strip():
        return {
            "execution_status": "empty_code",
            "stdout": "",
            "stderr": "No code was provided.",
            "return_code": None,
        }

    temp_file_path = None

    try:
        # 创建一个临时的 Python 文件
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        # Mac 系统使用 python3 来执行临时文件
        result = subprocess.run(
            ["python3", temp_file_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            status = "success"
        else:
            status = "runtime_error"

        return {
            "execution_status": status,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }

    except subprocess.TimeoutExpired:
        return {
            "execution_status": "timeout",
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "return_code": None,
        }

    except Exception as e:
        return {
            "execution_status": "system_error",
            "stdout": "",
            "stderr": str(e),
            "return_code": None,
        }

    finally:
        # 运行完之后，清理掉临时文件
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)