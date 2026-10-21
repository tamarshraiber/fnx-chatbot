def make_chunk(url="https://www.fnx.co.il/a", title="כותרת | הפניקס", text="טקסט", **extra) -> dict:
    """A retrieved chunk, the same shape that the vector repository returns."""
    return {"url": url, "title": title, "text": text, "chunk_id": "abc-0", "similarity": 0.9, **extra}
