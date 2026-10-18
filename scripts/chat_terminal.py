"""Chat with the bot in the terminal. Type "exit" to quit.

Run:  python -m scripts.chat_terminal
"""
from backend.controllers.chat_controller import BUSY_MESSAGE
from backend.models.schemas import ChatMessage
from backend.services.chat_service import answer_question
from backend.services.llm_service import AllProvidersFailed


def main() -> None:
    history: list[ChatMessage] = []
    print('Ask a question about Phoenix Insurance. Type "exit" to quit.')
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        try:
            answer = answer_question(question, history)
        except AllProvidersFailed:
            print(f"Bot: {BUSY_MESSAGE}")
            continue  # keep the chat going, and do not save this failed turn in the history
        except Exception as error:
            print(f"Bot: אירעה שגיאה בלתי צפויה, נסו שוב. ({type(error).__name__})")
            continue
        print(f"Bot: {answer.answer}")
        if answer.source_url:
            print(f"     source: {answer.source_url}")

        history.append(ChatMessage(role="user", content=question))
        history.append(ChatMessage(role="assistant", content=answer.answer))


if __name__ == "__main__":
    main()
