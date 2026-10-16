"""Run retrieval + generation on test questions and print the answers.

Run:  python -m scripts.check_generation
"""
import time

from backend.services.generation_service import generate_answer
from backend.services.retrieval_service import retrieve

QUESTIONS = [
    # Should be answered from the 5 test pages.
    "מה עושה שמאי רכב?",
    "האם צריך ביטוח חיים כשלוקחים משכנתא?",
    "איזה ניתוחים מכוסים בביטוח בריאות?",
    "איך מגישים תביעה על ניתוח?",
    "איך מזמינים שירותי גרירה לרכב?",
    # Should get the fixed "not on the website" reply.
    "מה מזג האוויר מחר בתל אביב?",
    "כמה עולה ביטוח לכלב?",
    # Edge cases: personal policy and professional advice.
    "מה הכיסוי בפוליסה שלי לניתוח?",
    "האם כדאי לי לעבור ניתוח ברך?",
]


def main() -> None:
    for question in QUESTIONS:
        result = retrieve(question)
        answer = generate_answer(question, result.chunks)
        print(f"\nQ: {question}")
        print(f"   best score: {result.best_score:.3f}, chunks used: {len(result.chunks)}")
        print(f"A: {answer.answer}")
        print(f"   source: {answer.source_url}  found: {answer.found}")
        time.sleep(2)  # stay inside the free-tier limits


if __name__ == "__main__":
    main()
