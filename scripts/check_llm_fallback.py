"""Check the LLM fallback order with fake providers (no real API calls).

Run:  python -m scripts.check_llm_fallback
"""
from backend.models.schemas import LLMAnswer
from backend.services import llm_service

GOOD_JSON = '{"answerable": true, "answer": "ok", "source_url": "https://x"}'
calls: list[str] = []
state = {"gemini_down": True, "groq_down": True}


def fake(name: str, down_key: str | None):
    def call(system_prompt, prompt, schema):
        calls.append(name)
        if down_key and state[down_key]:
            raise RuntimeError(f"{name} out of quota")
        return GOOD_JSON
    return call


def setup() -> None:
    llm_service._PROVIDERS = {
        "gemini": (fake("gemini", "gemini_down"), lambda: True),
        "groq": (fake("groq", "groq_down"), lambda: True),
        "openrouter": (fake("openrouter", None), lambda: True),
    }
    llm_service._blocked_until.clear()


def run(label: str, expected: list[str]) -> None:
    calls.clear()
    llm_service.generate_json("sys", "question", LLMAnswer)
    print(f"{label}: tried {calls} -> {'OK' if calls == expected else f'WRONG, expected {expected}'}")


def main() -> None:
    setup()
    run("1. Gemini and Groq down   ", ["gemini", "groq", "openrouter"])
    run("2. Next call (cooldown)   ", ["openrouter"])  # Gemini and Groq are skipped for a while

    state["gemini_down"] = False
    llm_service._blocked_until["gemini"] = 0  # pretend the Gemini cooldown ended
    run("3. Gemini quota is back   ", ["gemini"])

    state["gemini_down"] = True
    llm_service._blocked_until.clear()
    state["groq_down"] = False
    run("4. Only Gemini down       ", ["gemini", "groq"])

    llm_service._PROVIDERS["openrouter"] = (fake("openrouter", "groq_down"), lambda: True)
    state["groq_down"] = True
    llm_service._blocked_until.clear()
    calls.clear()
    try:
        llm_service.generate_json("sys", "question", LLMAnswer)
    except llm_service.AllProvidersFailed as error:
        print(f"5. All providers down     : raised AllProvidersFailed after {calls} -> OK")


if __name__ == "__main__":
    main()
