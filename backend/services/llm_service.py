import time
from typing import Callable, TypeVar

import httpx
from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from backend.config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_COOLDOWN_SECONDS,
    LLM_PROVIDER_ORDER,
    LLM_TIMEOUT_SECONDS,
    OPENROUTER_API_KEY,
    OPENROUTER_MODEL,
)
from backend.utils.retry import call_with_retry

M = TypeVar("M", bound=BaseModel)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class AllProvidersFailed(RuntimeError):
    """Every LLM provider failed or has no key."""


# --- One function per provider. Each returns the reply text. ---
# `schema` is a pydantic class when we want a JSON reply, otherwise None.

_gemini_client: genai.Client | None = None


def _call_gemini(system_prompt: str, prompt: str, schema: type[BaseModel] | None) -> str:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    config = types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.0)
    if schema is not None:
        config.response_mime_type = "application/json"
        config.response_schema = schema
    response = call_with_retry(lambda: _gemini_client.models.generate_content(
        model=GEMINI_MODEL, contents=prompt, config=config,
    ))
    return response.text or ""


def _call_openai_style(url: str, api_key: str, model: str, system_prompt: str, prompt: str,
                       schema: type[BaseModel] | None) -> str:
    """Groq and OpenRouter use the same chat format."""
    if schema is not None:
        # These models have no schema option here, so we describe the JSON shape in the prompt.
        system_prompt += f"\n\nReply with one JSON object only, matching this JSON schema:\n{schema.model_json_schema()}"
    body = {
        "model": model,
        "temperature": 0.0,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
    }
    if schema is not None:
        body["response_format"] = {"type": "json_object"}

    def send() -> str:
        response = httpx.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=body,
                              timeout=LLM_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"] or ""

    return call_with_retry(send)


def _call_groq(system_prompt: str, prompt: str, schema: type[BaseModel] | None) -> str:
    return _call_openai_style(GROQ_URL, GROQ_API_KEY, GROQ_MODEL, system_prompt, prompt, schema)


def _call_openrouter(system_prompt: str, prompt: str, schema: type[BaseModel] | None) -> str:
    return _call_openai_style(OPENROUTER_URL, OPENROUTER_API_KEY, OPENROUTER_MODEL, system_prompt, prompt, schema)


# name -> (function, has a key?). The key check is a function so tests can change it.
_PROVIDERS: dict[str, tuple[Callable[..., str], Callable[[], bool]]] = {
    "gemini": (_call_gemini, lambda: bool(GEMINI_API_KEY)),
    "groq": (_call_groq, lambda: bool(GROQ_API_KEY)),
    "openrouter": (_call_openrouter, lambda: bool(OPENROUTER_API_KEY)),
}

# When a provider may be tried again (time.monotonic value). Missing = available now.
_blocked_until: dict[str, float] = {}


def _candidates() -> list[str]:
    """Providers to try, in priority order. Skips providers with no key or in cooldown."""
    with_key = [name for name in LLM_PROVIDER_ORDER if name in _PROVIDERS and _PROVIDERS[name][1]()]
    now = time.monotonic()
    ready = [name for name in with_key if _blocked_until.get(name, 0.0) <= now]
    # If everything is cooling down, still try them all rather than fail without trying.
    return ready or with_key


def _generate(system_prompt: str, prompt: str, schema: type[M] | None) -> str | M:
    errors_seen: list[str] = []
    for name in _candidates():
        function = _PROVIDERS[name][0]
        try:
            text = function(system_prompt, prompt, schema)
            result = text.strip() if schema is None else schema.model_validate_json(text)
        except ValidationError as error:
            # The provider answered but not in the right shape. Try the next one, no cooldown.
            errors_seen.append(f"{name}: bad JSON ({error.error_count()} errors)")
            print(f"LLM {name} returned bad JSON, trying the next provider.")
            continue
        except Exception as error:
            # Quota, overload, network, etc. Skip this provider for a while.
            _blocked_until[name] = time.monotonic() + LLM_COOLDOWN_SECONDS
            errors_seen.append(f"{name}: {type(error).__name__} {error}")
            print(f"LLM {name} failed ({type(error).__name__}), trying the next provider for {LLM_COOLDOWN_SECONDS:.0f}s.")
            continue
        _blocked_until.pop(name, None)
        return result
    raise AllProvidersFailed("; ".join(errors_seen) or "no LLM provider has a key")


def generate_text(system_prompt: str, prompt: str) -> str:
    """Plain text reply from the first provider that works."""
    return _generate(system_prompt, prompt, None)


def generate_json(system_prompt: str, prompt: str, schema: type[M]) -> M:
    """JSON reply, checked against the pydantic schema, from the first provider that works."""
    return _generate(system_prompt, prompt, schema)
