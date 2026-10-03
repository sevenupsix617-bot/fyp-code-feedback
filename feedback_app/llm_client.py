import json
import os
import re
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv

load_dotenv()


def get_llm_model_name(model_choice: str = "deepseek") -> str:
    if model_choice == "kimi":
        return os.getenv("KIMI_MODEL_NAME") or "kimi-k2.7-code-highspeed"
    return os.getenv("DEEPSEEK_MODEL_NAME") or "deepseek-chat"


def _get_llm_base_url(model_choice: str) -> str:
    if model_choice == "kimi":
        return os.getenv("KIMI_BASE_URL") or "https://api.moonshot.cn/v1"
    return os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if not value:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _get_temperature(model_choice: str) -> float:
    if model_choice == "kimi":
        return _get_float_env("KIMI_TEMPERATURE", 1.0)

    return _get_float_env(
        "DEEPSEEK_TEMPERATURE",
        _get_float_env("LLM_TEMPERATURE", 0.2),
    )


def _get_max_output_tokens(model_choice: str) -> int:
    if model_choice == "kimi":
        return _get_int_env(
            "KIMI_MAX_OUTPUT_TOKENS",
            _get_int_env("LLM_MAX_OUTPUT_TOKENS", 2000),
        )

    return _get_int_env(
        "DEEPSEEK_MAX_OUTPUT_TOKENS",
        _get_int_env("LLM_MAX_OUTPUT_TOKENS", 1200),
    )


def _extract_usage(response) -> dict:
    if isinstance(response, dict):
        usage = response.get("usage")
    else:
        usage = getattr(response, "usage", None)

    if not usage:
        return {}

    extracted = {}
    for field_name in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if isinstance(usage, dict):
            value = usage.get(field_name)
        else:
            value = getattr(usage, field_name, None)
        if value is not None:
            extracted[field_name] = value
    return extracted


def _get_decimal_env(name: str) -> Decimal | None:
    value = os.getenv(name)
    if not value:
        return None

    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def estimate_llm_cost(model_choice: str, usage: dict) -> Decimal | None:
    """Estimate cost only when per-1M-token rates are configured in .env."""
    if not usage:
        return None

    prefix = "KIMI" if model_choice == "kimi" else "DEEPSEEK"
    input_rate = _get_decimal_env(f"{prefix}_INPUT_COST_PER_1M")
    output_rate = _get_decimal_env(f"{prefix}_OUTPUT_COST_PER_1M")
    if input_rate is None or output_rate is None:
        return None

    prompt_tokens = Decimal(usage.get("prompt_tokens") or 0)
    completion_tokens = Decimal(usage.get("completion_tokens") or 0)
    cost = (
        prompt_tokens / Decimal(1_000_000) * input_rate
        + completion_tokens / Decimal(1_000_000) * output_rate
    )
    return cost.quantize(Decimal("0.000001"))


def _sanitize_provider_error(error_body: str) -> str:
    error_body = re.sub(r"org-[A-Za-z0-9]+", "org-<redacted>", error_body)
    error_body = re.sub(r"ak-[A-Za-z0-9]+", "ak-<redacted>", error_body)
    error_body = re.sub(r"sk-[A-Za-z0-9]+", "sk-<redacted>", error_body)
    error_body = re.sub(
        r"Bearer\s+[A-Za-z0-9._\-]+",
        "Bearer <redacted>",
        error_body,
        flags=re.IGNORECASE,
    )
    return error_body


def _post_chat_completion(base_url: str, api_key: str, payload: dict, timeout: int) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = _sanitize_provider_error(
            exc.read().decode("utf-8", errors="replace")
        )[:800]
        raise RuntimeError(f"HTTP {exc.code} from LLM provider: {error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error from LLM provider: {exc.reason}") from exc

    return json.loads(body)


def _extract_chat_content(response_payload: dict) -> str:
    choices = response_payload.get("choices") or []
    if not choices:
        return ""

    message = choices[0].get("message") or {}
    return message.get("content") or ""


def call_llm_with_metadata(prompt: str, model_choice: str = "deepseek") -> dict:
    """Call the selected LLM and return the response text plus evaluation metadata."""
    if model_choice == "kimi":
        api_key = os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
    else:
        api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise ValueError(f"Missing API key for {model_choice}.")

    base_url = _get_llm_base_url(model_choice)
    model_name = get_llm_model_name(model_choice)
    max_tokens = _get_max_output_tokens(model_choice)
    temperature = _get_temperature(model_choice)
    request_timeout = _get_int_env("LLM_REQUEST_TIMEOUT", 45)

    response_payload = _post_chat_completion(
        base_url,
        api_key,
        {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a programming tutor for beginner Python students. "
                        "You generate educational hints, not full solutions."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        },
        timeout=request_timeout,
    )

    usage = _extract_usage(response_payload)
    content = _extract_chat_content(response_payload)

    return {
        "content": content,
        "model_name": model_name,
        "usage": usage,
        "estimated_cost": estimate_llm_cost(model_choice, usage),
    }


def call_llm(prompt: str, model_choice: str = "deepseek") -> str:
    """Backward-compatible wrapper for older code paths and quick scripts."""
    return call_llm_with_metadata(prompt, model_choice)["content"]
