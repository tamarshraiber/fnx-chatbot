"""Chat with the bot in the terminal. Type "exit" to quit.

Run:  python -m scripts.chat_terminal
"""
from backend.models.schemas import ChatMessage
from backend.services.chat_service import answer_question


def main() -> None:
    history: list[ChatMessage] = []
    print('Ask a question about Phoenix Insurance. Type "exit" to quit.')
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        answer = answer_question(question, history)
        print(f"Bot: {answer.answer}")
        if answer.source_url:
            print(f"     source: {answer.source_url}")

        history.append(ChatMessage(role="user", content=question))
        history.append(ChatMessage(role="assistant", content=answer.answer))


if __name__ == "__main__":
    main()
