// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useRef } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import SpeakButton from "../components/SpeakButton";
import { buildReadAlong, supportsHighlight } from "./readAlong";

function Answer({ onUtterance }) {
  const ref = useRef(null);
  return (
    <>
      <div ref={ref} data-testid="answer">
        <p>שלום עולם</p>
        <ul><li>פריט אחד</li></ul>
        <p>ראו <a href="https://example.com/page">https://example.com/page</a> עכשיו</p>
      </div>
      <SpeakButton text="ignored" containerRef={ref} />
    </>
  );
}

let synth;
let spoken;

beforeEach(() => {
  spoken = [];
  synth = {
    speak: vi.fn((utterance) => spoken.push(utterance)),
    cancel: vi.fn(),
    getVoices: vi.fn().mockReturnValue([{ lang: "he-IL" }]),
  };
  window.speechSynthesis = synth;
  window.SpeechSynthesisUtterance = function Utterance(text) { this.text = text; };
  window.Highlight = class { constructor(...ranges) { this.ranges = ranges; } };
  globalThis.CSS = { highlights: new Map() };
});
afterEach(() => {
  cleanup();
  delete window.speechSynthesis;
  delete window.SpeechSynthesisUtterance;
  delete window.Highlight;
  delete globalThis.CSS;
});

describe("buildReadAlong", () => {
  const container = () => {
    const root = document.createElement("div");
    root.innerHTML = '<p>שלום עולם</p><ul><li>פריט אחד</li></ul><p>ראו <a href="https://x.co/a">https://x.co/a</a> עכשיו</p>';
    return root;
  };

  it("separates paragraphs and list items, and blanks out web addresses", () => {
    const { text } = buildReadAlong(container());
    expect(text.split("\n")).toHaveLength(3);
    expect(text).not.toContain("https");
    expect(text.length).toBe(container().textContent.length + 2); // only the two line breaks were added
  });

  it("finds the word the voice reports, as it is on the screen", () => {
    const { text, rangeAt } = buildReadAlong(container());
    expect(rangeAt(text.indexOf("עולם"), 4).toString()).toBe("עולם");
    expect(rangeAt(text.indexOf("אחד"), 3).toString()).toBe("אחד");
    expect(rangeAt(text.indexOf("עכשיו"), 5).toString()).toBe("עכשיו");
  });

  it("works out the word length when the voice does not report it", () => {
    const { text, rangeAt } = buildReadAlong(container());
    expect(rangeAt(text.indexOf("פריט"), undefined).toString()).toBe("פריט");
  });

  it("marks nothing when the voice points at a line break we added", () => {
    const { text, rangeAt } = buildReadAlong(container());
    expect(rangeAt(text.indexOf("\n"), 1)).toBeNull();
  });

  it("returns nothing for a position outside the text", () => {
    expect(buildReadAlong(container()).rangeAt(9999, 3)).toBeNull();
  });
});

describe("highlight while reading", () => {
  it("is available only when the browser has the highlight feature", () => {
    expect(supportsHighlight()).toBe(true);
    delete globalThis.CSS;
    expect(supportsHighlight()).toBe(false);
  });

  it("follows the word the voice starts, and goes away when the reading ends", () => {
    render(<Answer />);
    fireEvent.click(screen.getByRole("button", { name: "הקראת התשובה" }));
    const utterance = spoken[0];
    expect(utterance.text).not.toContain("https");

    act(() => utterance.onboundary({ name: "word", charIndex: utterance.text.indexOf("עולם"), charLength: 4 }));
    const highlight = CSS.highlights.get("read-along");
    expect(highlight.ranges[0].toString()).toBe("עולם");

    act(() => utterance.onend());
    expect(CSS.highlights.has("read-along")).toBe(false);
  });

  it("ignores sentence and other non-word signals", () => {
    render(<Answer />);
    fireEvent.click(screen.getByRole("button", { name: "הקראת התשובה" }));
    act(() => spoken[0].onboundary({ name: "sentence", charIndex: 0, charLength: 9 }));
    expect(CSS.highlights.has("read-along")).toBe(false);
  });

  it("clears the highlight when the reading is stopped", () => {
    render(<Answer />);
    fireEvent.click(screen.getByRole("button", { name: "הקראת התשובה" }));
    act(() => spoken[0].onboundary({ name: "word", charIndex: 0, charLength: 4 }));
    expect(CSS.highlights.has("read-along")).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "עצירת ההקראה" }));
    expect(CSS.highlights.has("read-along")).toBe(false);
  });
});
