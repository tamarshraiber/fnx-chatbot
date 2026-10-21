"""Make DEMO.md: real questions asked to the real chatbot, with the answers and sources it gave today.

Run:  python -m scripts.make_demo
It uses LLM calls (two per question), so a pause is made between questions.
"""
import json
import time
from datetime import date
from pathlib import Path

from backend.services.chat_service import answer_question

ROOT = Path(__file__).resolve().parent.parent
EVAL_FILE = ROOT / "data" / "eval" / "eval_set.json"
DEMO_FILE = ROOT / "DEMO.md"
UNANSWERABLE_COUNT = 6
PAUSE_SECONDS = 4  # keeps us under the free-tier request limits


def ask(question: str) -> str:
    try:
        answer = answer_question(question, [])
    except Exception as error:  # a failed call is written in the file, the run goes on
        return f"**(error: {type(error).__name__})**"
    text = answer.answer.strip().replace("\n", "\n> ")
    source = f"\n>\n> מקור: [{answer.source_title or answer.source_url}]({answer.source_url})" if answer.source_url else ""
    return f"> {text}{source}"


def main() -> None:
    data = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    sections = [
        ("שאלות שהתשובה עליהן נמצאת באתר", data["answerable"]),
        ("שאלות שהתשובה עליהן לא באתר (הצ'אט אמור לומר שהמידע לא באתר)", data["unanswerable"][:UNANSWERABLE_COUNT]),
    ]
    lines = [
        "# הדגמה: שאלות ותשובות אמיתיות של הצ'אט",
        "",
        f"נוצר ב-{date.today().isoformat()} על ידי `python -m scripts.make_demo`. כל תשובה נוצרה על ידי הצ'אט, "
        "בלי עריכה. התשובות עשויות להשתנות מעט בין הרצות.",
        "",
    ]
    number = 0
    for title, items in sections:
        lines += [f"## {title}", ""]
        for item in items:
            number += 1
            print(f"{number}. {item['question']}")
            lines += [f"### {number}. {item['question']}", "", ask(item["question"]), ""]
            time.sleep(PAUSE_SECONDS)
    DEMO_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved to {DEMO_FILE}")


if __name__ == "__main__":
    main()
