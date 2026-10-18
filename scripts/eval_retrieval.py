"""Run the eval set (data/eval/eval_set.json) against retrieval and print a report.
Uses only the local embedding model and Supabase. No Gemini calls.

Run:  python -m scripts.eval_retrieval
"""
import json
import sys
from pathlib import Path

from backend.config import RELEVANCE_THRESHOLD, TOP_K
from backend.repositories import vector_repository
from backend.services.embedding_service import embed_question

EVAL_FILE = Path(__file__).resolve().parent.parent / "data" / "eval" / "eval_set.json"


def search(question: str) -> list[dict]:
    return vector_repository.search(embed_question(question), top_k=TOP_K)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    data = json.loads(EVAL_FILE.read_text(encoding="utf-8"))

    print(f"Cutoff: {RELEVANCE_THRESHOLD}   Top K: {TOP_K}")

    # --- Answerable: we want a score above the cutoff AND the expected page in the top K.
    print("\n===== ANSWERABLE =====")
    answerable_scores = []
    kept = hits = 0
    for item in data["answerable"]:
        matches = search(item["question"])
        best = max((m["similarity"] for m in matches), default=0.0)
        hit = any(e in m["url"] for m in matches for e in item["expected"])
        answerable_scores.append(best)
        kept += best >= RELEVANCE_THRESHOLD
        hits += hit
        print(f"  {best:.3f} {'KEEP' if best >= RELEVANCE_THRESHOLD else 'drop'} "
              f"{'HIT ' if hit else 'MISS'} {item['question']}")
        if not hit and matches:
            print(f"        top url: {matches[0]['url']}")

    # --- Unanswerable: we want a score below the cutoff.
    print("\n===== UNANSWERABLE =====")
    unanswerable_scores = []
    rejected = 0
    for item in data["unanswerable"]:
        matches = search(item["question"])
        best = max((m["similarity"] for m in matches), default=0.0)
        unanswerable_scores.append(best)
        rejected += best < RELEVANCE_THRESHOLD
        tag = " (hard)" if item.get("hard") else ""
        print(f"  {best:.3f} {'ok  ' if best < RELEVANCE_THRESHOLD else 'LEAK'} {item['question']}{tag}")

    # --- Summary.
    n_a, n_u = len(answerable_scores), len(unanswerable_scores)
    print("\n===== SUMMARY =====")
    print(f"Answerable above cutoff:      {kept}/{n_a}")
    print(f"Expected page in top {TOP_K}:       {hits}/{n_a}")
    print(f"Unanswerable rejected:        {rejected}/{n_u}")
    low_a, high_u = min(answerable_scores), max(unanswerable_scores)
    print(f"Lowest answerable score:      {low_a:.3f}")
    print(f"Highest unanswerable score:   {high_u:.3f}")
    print(f"Gap (positive = clean split): {low_a - high_u:+.3f}")

    # --- Cutoff sweep: how many questions are handled correctly at each cutoff.
    print("\nCutoff sweep (correct = answerable kept + unanswerable rejected):")
    best_cut, best_correct = None, -1
    for i in range(780, 921, 5):
        cut = i / 1000
        correct = sum(s >= cut for s in answerable_scores) + sum(s < cut for s in unanswerable_scores)
        print(f"  {cut:.3f}  {correct}/{n_a + n_u}")
        if correct > best_correct:
            best_cut, best_correct = cut, correct
    print(f"Best cutoff in this range: {best_cut:.3f} ({best_correct}/{n_a + n_u})")


if __name__ == "__main__":
    main()
