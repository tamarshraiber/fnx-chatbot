import { useEffect, useState } from "react";
import { shortenQuote } from "../hooks/quote";
import "./SelectionAsk.css";

/** The selected text, if it lies inside ONE answer of the bot, with the place of the selection on the screen. */
export function selectedAnswerText() {
  const selection = window.getSelection?.();
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null;
  const range = selection.getRangeAt(0);
  const node = range.commonAncestorContainer;
  const host = (node.nodeType === 1 ? node : node.parentElement)?.closest(".answer .rich");
  if (!host) return null; // not in an answer, or it stretches over more than one answer
  const text = shortenQuote(selection.toString());
  if (text.length < 2) return null;
  return { text, rect: range.getBoundingClientRect() };
}

/**
 * A small floating button next to the text the person selected in an answer: "ask about this".
 * Clicking it hands the (shortened) text to onAsk, which shows it as a quote above the question box.
 */
export default function SelectionAsk({ onAsk }) {
  const [pick, setPick] = useState(null); // { text, top, left } or null

  useEffect(() => {
    let frame = 0;
    const refresh = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(() => {
        const found = selectedAnswerText();
        if (!found) return setPick(null);
        const { rect } = found;
        const below = rect.bottom + 8;
        const top = below + 44 > window.innerHeight ? Math.max(rect.top - 48, 8) : below; // above if there is no room below
        const left = Math.min(Math.max(rect.left + rect.width / 2, 70), window.innerWidth - 70);
        return setPick({ text: found.text, top, left });
      });
    };
    document.addEventListener("selectionchange", refresh);
    window.addEventListener("scroll", refresh, true);
    window.addEventListener("resize", refresh);
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("selectionchange", refresh);
      window.removeEventListener("scroll", refresh, true);
      window.removeEventListener("resize", refresh);
    };
  }, []);

  if (!pick) return null;
  return (
    <button
      type="button"
      className="ask-selection"
      style={{ top: pick.top, left: pick.left }}
      onMouseDown={(event) => event.preventDefault()} // keep the selection while clicking
      onClick={() => {
        onAsk(pick.text);
        window.getSelection()?.removeAllRanges();
        setPick(null);
      }}
    >
      שאלו על זה
    </button>
  );
}
