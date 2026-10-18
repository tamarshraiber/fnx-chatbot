"""Test the local embedding model on real Hebrew questions. No database, nothing is saved.

It embeds the chunks of about 150 pages in memory, asks the questions below and shows the 3 closest
chunks for each. "Expected" questions must show a page whose URL contains the given text at the top.
The last questions are NOT on the website: look at how high their best score is, because
the relevance cutoff must sit above those scores and below the scores of the answerable questions.

Run:  python -m scripts.check_local_quality
"""
import json
import random

from backend.ingestion import config
from backend.ingestion.chunker import chunk_page
from backend.services.embedding_service import embed_chunks, embed_question

SAMPLE_PAGES = 150

# (question, text that must appear in the top URL, or None when we only want to look at the result)
ANSWERABLE = [
    ("איך בוחרים שמאי רכב?", "appraiser"),
    ("מה כולל הכיסוי לניתוחים בביטוח בריאות?", "surger"),
    ("מהו ביטוח חיים למשכנתא?", "mortgage-life-insurance"),
    ("איך מזמינים שירות גרירה לרכב?", "towing"),
    ("איך מגישים תביעה בביטוח בריאות?", None),
    ("מה זה קופת גמל?", None),
    ("איך עושים ביטוח נסיעות לחו\"ל?", None),
    ("מה הכיסוי של ביטוח דירה?", None),
]
NOT_ON_SITE = [
    "מה מתכון לעוגת שוקולד?",
    "מי ניצח במשחק הכדורגל אתמול?",
    "מה מזג האוויר מחר בתל אביב?",
    "מה המחיר של ביטוח רכב עבור אדם בן 25 עם תאונה אחת?",
]


def similarity(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def main() -> None:
    pages = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(config.RAW_DIR.glob("*.json"))]
    must_have = [page for page in pages if any(key and key in page["url"] for _, key in ANSWERABLE)]
    others = [page for page in pages if page not in must_have]
    random.Random(1).shuffle(others)
    chosen = must_have + others[:SAMPLE_PAGES]

    chunks = [chunk for page in chosen for chunk in chunk_page(page)]
    print(f"Embedding {len(chunks)} chunks from {len(chosen)} pages (this takes a few minutes)...")
    vectors = embed_chunks([chunk["text"] for chunk in chunks])

    def top3(question: str):
        query = embed_question(question)
        ranked = sorted(((similarity(query, vector), chunk) for vector, chunk in zip(vectors, chunks)), key=lambda p: p[0], reverse=True)
        return ranked[:3]

    passed = 0
    checked = 0
    print("\n=== Answerable questions ===")
    for question, expected in ANSWERABLE:
        results = top3(question)
        verdict = ""
        if expected:
            checked += 1
            ok = expected in results[0][1]["url"]
            passed += ok
            verdict = "  [PASS]" if ok else "  [FAIL]"
        print(f"\n{question}{verdict}")
        for score, chunk in results:
            print(f"  {score:.3f}  {chunk['url']}")

    print("\n=== Not on the website ===")
    for question in NOT_ON_SITE:
        results = top3(question)
        print(f"\n{question}")
        for score, chunk in results[:1]:
            print(f"  {score:.3f}  {chunk['url']}")

    print(f"\nChecked questions passed: {passed}/{checked}")


if __name__ == "__main__":
    main()
