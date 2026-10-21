"""End-to-end eval: ask every question of the eval set through the real chat service (retrieval + Gemini) and score it.

Per answerable question we check:   found = true, and the cited URL contains an expected page.
Per unanswerable question we check: found = false (the bot says "not on the website").
Every run is added to data/eval/e2e_history.json, so we can see whether a change made things better or worse.
It uses LLM calls (two per question), so a pause is made between questions.

Run:  python -m scripts.eval_e2e
      python -m scripts.eval_e2e --limit 5    (only the first 5 questions of each kind)
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.config import RELEVANCE_THRESHOLD, RERANK_ENABLED
from backend.services.chat_service import answer_question

EVAL_DIR = Path(__file__).resolve().parent.parent / "data" / "eval"
EVAL_FILE = EVAL_DIR / "eval_set.json"
HISTORY_FILE = EVAL_DIR / "e2e_history.json"
PAUSE_SECONDS = 4  # keeps us under the free-tier request limits


def ask(question: str) -> dict:
    try:
        answer = answer_question(question, [])
    except Exception as error:  # a failed call counts as a failed question, the run goes on
        return {"error": type(error).__name__, "found": None, "source_url": None, "answer": ""}
    return {"found": answer.found, "source_url": answer.source_url, "answer": answer.answer}


def main() -> None:
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    data = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    rows = []
    for kind in ("answerable", "unanswerable"):
        for item in data[kind][:limit]:
            result = ask(item["question"])
            if kind == "answerable":
                url = result["source_url"] or ""
                ok = bool(result["found"]) and any(part in url for part in item["expected"])
            else:
                ok = result["found"] is False
            rows.append({"kind": kind, "question": item["question"], "ok": ok, **result})
            print(f"[{'OK ' if ok else 'BAD'}] {kind[:6]}: {item['question']} -> {result['source_url']}")
            time.sleep(PAUSE_SECONDS)

    def count(kind: str, ok: bool | None = None) -> int:
        return sum(1 for row in rows if row["kind"] == kind and (ok is None or row["ok"] == ok))

    summary = {
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cutoff": RELEVANCE_THRESHOLD,
        "rerank": RERANK_ENABLED,
        "answerable_correct": f"{count('answerable', True)}/{count('answerable')}",
        "unanswerable_rejected": f"{count('unanswerable', True)}/{count('unanswerable')}",
        "errors": sum(1 for row in rows if row.get("error")),
    }
    print("\n===== SUMMARY =====")
    for key, value in summary.items():
        print(f"{key}: {value}")

    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8")) if HISTORY_FILE.exists() else []
    history.append({**summary, "rows": rows})
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved to {HISTORY_FILE}")


if __name__ == "__main__":
    main()
