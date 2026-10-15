import hashlib
import json
import re

from backend.ingestion import config

# The cookie banner starts with this text and ends with the word "סגירה" (close).
COOKIE_BANNER = re.compile(r"שימוש בקבצי Cookies.*?סגירה", re.DOTALL)
# Images: ![alt](url). Removed completely.
IMAGE_TAG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
# Links: [text](url "title"). We keep only the text.
LINK_TAG = re.compile(r"\[([^\]]*)\]\([^)]*\)")
# Footer blocks that are the same on every page. Everything after the first one is cut.
FOOTER_MARKERS = ["## כל הדרכים לדבר איתנו", "כניסה לפורטלים"]
HEADING_LINE = re.compile(r"^#{1,6}\s")


def clean_markdown(markdown: str) -> str:
    """Remove cookie banner, images, link URLs and the shared footer."""
    text = COOKIE_BANNER.sub("", markdown)
    text = IMAGE_TAG.sub("", text)
    text = LINK_TAG.sub(r"\1", text)

    for marker in FOOTER_MARKERS:
        position = text.find(marker)
        if position != -1:
            text = text[:position]

    # Remove spaces at line ends and collapse many blank lines into one.
    text = re.sub(r"[ \t​]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_sections(text: str) -> list[str]:
    """Cut the text before every heading line (#, ##, ...)."""
    sections: list[str] = []
    current: list[str] = []
    for line in text.split("\n"):
        if HEADING_LINE.match(line) and current:
            sections.append("\n".join(current).strip())
            current = []
        current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [section for section in sections if section]


def hard_split(text: str, size: int) -> list[str]:
    """Last resort for one very long line: cut at a space near the size limit."""
    parts = []
    while len(text) > size:
        cut = text.rfind(" ", 0, size)
        if cut <= 0:
            cut = size
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        parts.append(text)
    return parts


def split_long_section(section: str) -> list[str]:
    """Split a section longer than CHUNK_SIZE by lines, with a small overlap."""
    if len(section) <= config.CHUNK_SIZE:
        return [section]

    lines = []
    for line in section.split("\n"):
        lines.extend(hard_split(line, config.CHUNK_SIZE) if len(line) > config.CHUNK_SIZE else [line])

    pieces: list[str] = []
    current = ""
    for line in lines:
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > config.CHUNK_SIZE and current:
            pieces.append(current)
            # Start the next piece with the end of the previous one (the overlap).
            overlap = current[-config.CHUNK_OVERLAP:]
            current = f"{overlap}\n{line}"
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def merge_small_pieces(pieces: list[str]) -> list[str]:
    """Merge a short piece into the next one if the result still fits."""
    merged: list[str] = []
    for piece in pieces:
        if merged and len(merged[-1]) < config.MIN_CHUNK_SIZE and len(merged[-1]) + len(piece) + 1 <= config.CHUNK_SIZE:
            merged[-1] = f"{merged[-1]}\n{piece}"
        else:
            merged.append(piece)
    # A tiny last piece goes into the one before it.
    if len(merged) > 1 and len(merged[-1]) < config.MIN_CHUNK_SIZE:
        last = merged.pop()
        merged[-1] = f"{merged[-1]}\n{last}"
    return merged


def chunk_page(page: dict) -> list[dict]:
    """Turn one raw page into a list of chunks with title, url and date."""
    text = clean_markdown(page["markdown"])
    pieces = []
    for section in split_into_sections(text):
        pieces.extend(split_long_section(section))
    pieces = merge_small_pieces(pieces)

    url_id = hashlib.sha256(page["url"].encode("utf-8")).hexdigest()[:16]
    chunks = []
    for index, piece in enumerate(pieces):
        chunks.append(
            {
                "chunk_id": f"{url_id}-{index}",
                "chunk_index": index,
                "url": page["url"],
                "title": page["title"],
                "lastmod": page["lastmod"],
                # The title goes first so the embedding knows the topic of the chunk.
                "text": f"{page['title']}\n\n{piece}",
            }
        )
    return chunks


def main() -> None:
    config.CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks = []
    for path in sorted(config.RAW_DIR.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        chunks = chunk_page(page)
        print(f"{len(chunks)} chunks: {page['url']}")
        all_chunks.extend(chunks)

    output = config.CHUNKS_DIR / "chunks.json"
    output.write_text(json.dumps(all_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(all_chunks)} chunks saved to {output}")


if __name__ == "__main__":
    main()
