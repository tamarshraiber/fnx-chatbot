"""Ask test questions and show the top matches with scores. Helps us pick the relevance cutoff.

Run:  python -m scripts.check_retrieval
"""
import time

from backend.config import RELEVANCE_THRESHOLD
from backend.repositories import vector_repository
from backend.services.embedding_service import embed_question

# The 5 test pages: car appraiser, mortgage life insurance, health surgeries,
# surgery claims, car towing.
ANSWERABLE = [
    "מה עושה שמאי רכב?",
    "האם צריך ביטוח חיים כשלוקחים משכנתא?",
    "איזה ניתוחים מכוסים בביטוח בריאות?",
    "איך מגישים תביעה על ניתוח?",
    "איך מזמינים שירותי גרירה לרכב?",
]
UNANSWERABLE = [
    "מה מזג האוויר מחר בתל אביב?",
    "איך מכינים פסטה בולונז?",
    "כמה עולה ביטוח לכלב?",
    "מי זכה באליפות הכדורגל?",
]


def show(question: str) -> None:
    matches = vector_repository.search(embed_question(question), top_k=3)
    print(f"\n{question}")
    for match in matches:
        mark = "KEEP" if match["similarity"] >= RELEVANCE_THRESHOLD else "drop"
        print(f"  {match['similarity']:.3f} [{mark}] {match['url']}")


def main() -> None:
    print(f"Cutoff: {RELEVANCE_THRESHOLD}")
    for title, questions in (("ANSWERABLE", ANSWERABLE), ("UNANSWERABLE", UNANSWERABLE)):
        print(f"\n===== {title} =====")
        for question in questions:
            show(question)
            time.sleep(1)  # stay inside the free-tier limits


if __name__ == "__main__":
    main()
