"""Run the eval set (data/eval/eval_set.json) against retrieval and print a report.

It compares two versions on the same questions:
  vector = plain vector search (top K)
  rerank = vector search (top RERANK_FETCH_K) re-scored by Cohere, then top K
The scores are saved to data/eval/scores_cache.json, so --cached can re-test cutoffs with no new calls.

Run:  python -m scripts.eval_retrieval              (vector + rerank; needs COHERE_API_KEY)
      python -m scripts.eval_retrieval --no-rerank  (vector only)
      python -m scripts.eval_retrieval --cached     (re-use the saved scores)
"""
import json
import sys
import time
from pathlib import Path

from backend.config import (
    RELEVANCE_THRESHOLD,
    RERANK_FETCH_K,
    RERANK_MODEL,
    RERANK_THRESHOLD,
    TOP_K,
)
from backend.repositories import vector_repository
from backend.services import rerank_service
from backend.services.embedding_service import embed_question

EVAL_DIR = Path(__file__).resolve().parent.parent / "data" / "eval"
EVAL_FILE = EVAL_DIR / "eval_set.json"
CACHE_FILE = EVAL_DIR / "scores_cache.json"
# The Cohere trial key allows about 10 rerank calls per minute.
RERANK_PAUSE_SECONDS = 6.5


def is_hit(urls: list[str], expected: list[str]) -> bool:
    return any(e in url for url in urls for e in expected)


def run_question(question: str, expected: list[str], with_rerank: bool) -> dict:
    """Search once and score the question with both versions."""
    candidates = vector_repository.search(embed_question(question), top_k=max(TOP_K, RERANK_FETCH_K))
    top = candidates[:TOP_K]
    row = {
        "vector_best": max((c["similarity"] for c in top), default=0.0),
        "vector_hit": is_hit([c["url"] for c in top], expected),
        "vector_top_url": top[0]["url"] if top else "",
    }
    if with_rerank:
        reranked = rerank_service.rerank(question, candidates, top_n=TOP_K)
        row["rerank_best"] = max((c["rerank_score"] for c in reranked), default=0.0)
        row["rerank_hit"] = is_hit([c["url"] for c in reranked], expected)
        row["rerank_top_url"] = reranked[0]["url"] if reranked else ""
        time.sleep(RERANK_PAUSE_SECONDS)
    return row


def collect(data: dict, with_rerank: bool) -> dict:
    results = {"answerable": [], "unanswerable": []}
    for kind in ("answerable", "unanswerable"):
        for item in data[kind]:
            print(f"  [{kind}] {item['question']}", flush=True)
            row = run_question(item["question"], item.get("expected", []), with_rerank)
            results[kind].append({"question": item["question"], "hard": item.get("hard", False), **row})
    return results


def report(results: dict, version: str, cutoff: float, sweep: range, divisor: int) -> None:
    """Print the per-question lines, the summary and the cutoff sweep for one version."""
    key = f"{version}_best"
    answerable, unanswerable = results["answerable"], results["unanswerable"]

    print(f"\n########## {version.upper()}  (cutoff {cutoff}) ##########")
    print("\n===== ANSWERABLE =====")
    for r in answerable:
        keep = r[key] >= cutoff
        hit = r[f"{version}_hit"]
        print(f"  {r[key]:.3f} {'KEEP' if keep else 'drop'} {'HIT ' if hit else 'MISS'} {r['question']}")
        if not hit:
            print(f"        top url: {r[f'{version}_top_url']}")
    print("\n===== UNANSWERABLE =====")
    for r in unanswerable:
        ok = r[key] < cutoff
        print(f"  {r[key]:.3f} {'ok  ' if ok else 'LEAK'} {r['question']}{' (hard)' if r['hard'] else ''}")

    a_scores = [r[key] for r in answerable]
    u_scores = [r[key] for r in unanswerable]
    print("\n===== SUMMARY =====")
    print(f"Answerable above cutoff:      {sum(s >= cutoff for s in a_scores)}/{len(a_scores)}")
    print(f"Expected page in top {TOP_K}:       {sum(r[f'{version}_hit'] for r in answerable)}/{len(answerable)}")
    print(f"Unanswerable rejected:        {sum(s < cutoff for s in u_scores)}/{len(u_scores)}")
    print(f"Lowest answerable score:      {min(a_scores):.3f}")
    print(f"Highest unanswerable score:   {max(u_scores):.3f}")
    print(f"Gap (positive = clean split): {min(a_scores) - max(u_scores):+.3f}")

    print("\nCutoff sweep (correct = answerable kept + unanswerable rejected):")
    best_cut, best_correct = None, -1
    for i in sweep:
        cut = i / divisor
        correct = sum(s >= cut for s in a_scores) + sum(s < cut for s in u_scores)
        print(f"  {cut:.3f}  {correct}/{len(a_scores) + len(u_scores)}")
        if correct > best_correct:
            best_cut, best_correct = cut, correct
    print(f"Best cutoff in this range: {best_cut:.3f} ({best_correct}/{len(a_scores) + len(u_scores)})")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    use_cache = "--cached" in sys.argv
    with_rerank = "--no-rerank" not in sys.argv

    if use_cache:
        results = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        with_rerank = "rerank_best" in results["answerable"][0]
    else:
        data = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
        print(f"Running {len(data['answerable']) + len(data['unanswerable'])} questions "
              f"(rerank {'on, ' + RERANK_MODEL if with_rerank else 'off'})...")
        results = collect(data, with_rerank)
        CACHE_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")

    report(results, "vector", RELEVANCE_THRESHOLD, range(780, 921, 5), 1000)
    if with_rerank:
        report(results, "rerank", RERANK_THRESHOLD, range(5, 100, 5), 100)


if __name__ == "__main__":
    main()
