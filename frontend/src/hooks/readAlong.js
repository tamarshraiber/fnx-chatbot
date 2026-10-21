const HIGHLIGHT_NAME = "read-along";

/** Can this browser mark text without changing the page (the CSS Custom Highlight API)? */
export function supportsHighlight() {
  return typeof CSS !== "undefined" && Boolean(CSS.highlights) && typeof window.Highlight === "function";
}

/**
 * Prepare an answer on the screen for reading aloud with a moving highlight.
 * Returns { text, rangeAt(charIndex, charLength) }:
 *  - text: what the voice should say. It is made of the text pieces on the screen, with a line break between
 *    paragraphs and list items, and web addresses blanked out (replaced by spaces) so they are not read.
 *  - rangeAt: the screen Range for the word the voice just started, from the position it reports.
 */
export function buildReadAlong(container) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const parts = []; // { node, start }: where each text piece begins inside `text`
  let text = "";
  let lastBlock = null;
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const block = node.parentElement?.closest("li, p") ?? null;
    if (parts.length && block !== lastBlock) text += "\n"; // a pause between paragraphs and list items
    lastBlock = block;
    parts.push({ node, start: text.length });
    text += node.parentElement?.closest("a") ? " ".repeat(node.data.length) : node.data;
  }

  const rangeAt = (charIndex, charLength) => {
    // the piece that holds this position (none if the voice points at a line break we added)
    const part = parts.find((p) => charIndex < p.start + p.node.data.length && charIndex + (charLength || 1) > p.start);
    if (!part) return null;
    const offset = Math.max(charIndex - part.start, 0);
    const length = charLength || (text.slice(charIndex).match(/^\S+/)?.[0].length ?? 0);
    if (!length) return null;
    const range = document.createRange();
    range.setStart(part.node, offset);
    range.setEnd(part.node, Math.min(offset + length, part.node.data.length));
    return range;
  };
  return { text, rangeAt };
}

/** Mark one range on the screen as "the word being read". null removes the mark. */
export function showWord(range) {
  if (!supportsHighlight()) return;
  if (range) CSS.highlights.set(HIGHLIGHT_NAME, new window.Highlight(range));
  else CSS.highlights.delete(HIGHLIGHT_NAME);
}

export function clearHighlight() {
  showWord(null);
}
