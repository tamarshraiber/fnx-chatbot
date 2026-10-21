"""Known Hebrew spelling slips of the model are fixed in the final answer, and nothing else is touched."""
import pytest

from backend.models.schemas import LLMAnswer
from backend.services import generation_service as gen
from backend.utils.spelling import fix_spelling
from tests.helpers import make_chunk

URL = "https://www.fnx.co.il/a"


@pytest.mark.parametrize("wrong, right", [
    ("ביטוח רכב מקיפ", "ביטוח רכב מקיף"),
    ("ב\u05de\u05e7\u05d9\u05e4 ו\u05de\u05e7\u05d9\u05e4.", "ב\u05de\u05e7\u05d9\u05e3 ו\u05de\u05e7\u05d9\u05e3."),
    ("הביטוח מקיפ, והוא טוב", "הביטוח מקיף, והוא טוב"),
    ("בביטוח מקיפ", "בביטוח מקיף"),
    ("מתקני סקה ודוודים", "מתקני הסקה ודוודים"),
])
def test_known_slips_are_fixed(wrong, right):
    assert fix_spelling(wrong) == right


@pytest.mark.parametrize("fine", [
    "ביטוח רכב מקיף",
    "הכיסוי מקיפה את הרכב",
    "ביטוחים מקיפים",
    "מתקני הסקה",
    "קליפ",
    "",
])
def test_correct_text_is_not_changed(fine):
    assert fix_spelling(fine) == fine


def test_the_final_answer_is_fixed(monkeypatch):
    chunks = [make_chunk(url=URL, title="ביטוח | הפניקס")]
    monkeypatch.setattr(gen, "generate_json", lambda *a: LLMAnswer(answerable=True, answer="ביטוח רכב מקיפ", source_url=URL))
    assert gen.generate_answer("שאלה", chunks).answer == "ביטוח רכב מקיף"


def test_the_final_streamed_answer_is_fixed():
    chunks = [make_chunk(url=URL, title="ביטוח | הפניקס")]
    final = gen._finish_stream(f"ביטוח רכב מקיפ\nSOURCE: {URL}", chunks)
    assert final.answer == "ביטוח רכב מקיף" and final.source_url == URL
