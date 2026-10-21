"""Fixes for Hebrew spelling slips that the language model has made in real answers.

The model writes new Hebrew every time, so a slip cannot be fixed in a file. This is a short list of slips we have
seen, each fixed only in the exact form it appeared. Add a line when a new one shows up. It is deliberately NOT a
general spell checker: a general rule (for example "a word never ends in a non-final letter") would damage real
words such as "קליפ".
"""
import re

_HEB = "א-ת"

# (what the model wrote, what it should be)
_FIXES = [
    # "מקיפ" instead of "מקיף" (comprehensive), also with a prefix such as ב, ה, ל, ו, מ, כ, ש. "מקיפה" and "מקיפים" are untouched.
    (re.compile(rf"(?<![{_HEB}])([ובלהמכש]{{0,2}})מקיפ(?![{_HEB}])"), r"\1מקיף"),
    # "מתקני סקה" instead of "מתקני הסקה" (heating installations).
    (re.compile(rf"(?<![{_HEB}])מתקני סקה(?![{_HEB}])"), "מתקני הסקה"),
]


def fix_spelling(text: str) -> str:
    for pattern, replacement in _FIXES:
        text = pattern.sub(replacement, text)
    return text
