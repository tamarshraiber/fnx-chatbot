"""Check the /chat safeguards with a fake chat service (no LLM, no database).

Run:  python -m scripts.check_safeguards
"""
from fastapi.testclient import TestClient

from backend.config import MAX_HISTORY_ITEMS, MAX_MESSAGE_CHARS, MAX_QUESTION_CHARS, RATE_LIMIT_REQUESTS
from backend.controllers import chat_controller
from backend.main import app
from backend.models.schemas import ChatAnswer
from backend.services.llm_service import AllProvidersFailed
from backend.utils import rate_limit

client = TestClient(app)
mode = {"value": "ok"}


def fake_answer(question, history):
    if mode["value"] == "down":
        raise AllProvidersFailed("all down")
    if mode["value"] == "crash":
        raise ValueError("bug")
    return ChatAnswer(answer="ok", source_url=None, found=False)


chat_controller.answer_question = fake_answer


def check(label: str, got: int, expected: int) -> None:
    print(f"{label}: status {got} -> {'OK' if got == expected else f'WRONG, expected {expected}'}")


def post(body: dict) -> int:
    rate_limit._recent.clear()  # each case starts with a fresh rate limit
    return client.post("/chat", json=body).status_code


def main() -> None:
    check("1. Normal question          ", post({"question": "שלום"}), 200)
    check("2. Question too long        ", post({"question": "א" * (MAX_QUESTION_CHARS + 1)}), 422)
    check("3. Too many history items   ", post({"question": "שלום", "history": [{"role": "user", "content": "x"}] * (MAX_HISTORY_ITEMS + 1)}), 422)
    check("4. History message too long ", post({"question": "שלום", "history": [{"role": "user", "content": "x" * (MAX_MESSAGE_CHARS + 1)}]}), 422)

    mode["value"] = "down"
    check("5. All LLMs down (friendly) ", post({"question": "שלום"}), 503)
    mode["value"] = "crash"
    check("6. Unexpected error         ", post({"question": "שלום"}), 500)
    mode["value"] = "ok"

    rate_limit._recent.clear()
    codes = [client.post("/chat", json={"question": "שלום"}).status_code for _ in range(RATE_LIMIT_REQUESTS + 1)]
    check(f"7. Request {RATE_LIMIT_REQUESTS + 1} in one minute   ", codes[-1], 429)
    check(f"   first {RATE_LIMIT_REQUESTS} allowed          ", max(codes[:-1]), 200)


if __name__ == "__main__":
    main()
