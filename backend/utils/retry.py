import random
import time
from typing import Callable, TypeVar

import httpx
from google.genai import errors

from backend.config import RETRY_BASE_DELAY_SECONDS, RETRY_MAX_ATTEMPTS

T = TypeVar("T")

# 429 = too many requests, 503 = service overloaded. Both are temporary.
RETRYABLE_CODES = {429, 503}


def _error_code(error: Exception) -> int | None:
    """The HTTP status code of a Gemini, Groq or OpenRouter error."""
    if isinstance(error, errors.APIError):
        return error.code
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code
    return None


def call_with_retry(function: Callable[[], T]) -> T:
    """Call the function. On a 429/503 error, wait and try again (the wait doubles each time)."""
    for attempt in range(1, RETRY_MAX_ATTEMPTS + 1):
        try:
            return function()
        except (errors.APIError, httpx.HTTPStatusError) as error:
            code = _error_code(error)
            if code not in RETRYABLE_CODES or attempt == RETRY_MAX_ATTEMPTS:
                raise  # not temporary, or we are out of attempts
            delay = RETRY_BASE_DELAY_SECONDS * 2 ** (attempt - 1) + random.uniform(0, 0.5)
            print(f"LLM error {code}. Retry {attempt} of {RETRY_MAX_ATTEMPTS - 1} in {delay:.1f}s")
            time.sleep(delay)
