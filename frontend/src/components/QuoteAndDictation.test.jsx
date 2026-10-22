// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ChatInput from "./ChatInput";
import SelectionAsk from "./SelectionAsk";
import { composeQuestion, QUOTE_MAX, quotePrefix, shortenQuote } from "../hooks/quote";
import { useChat } from "../hooks/useChat";

vi.mock("../api", async (importOriginal) => ({ ...(await importOriginal()), streamChat: vi.fn() }));
const { streamChat, MAX_QUESTION_CHARS } = await import("../api");

const ANSWER = { answer: "תשובה", source_url: null, source_title: null, found: true };

let recognition;

beforeEach(() => {
  streamChat.mockReset();
  sessionStorage.clear();
  recognition = null;
  // jsdom cannot measure text; real browsers can. A fixed place is enough to test the button.
  Range.prototype.getBoundingClientRect = () => ({ top: 100, bottom: 120, left: 200, right: 300, width: 100, height: 20 });
  window.webkitSpeechRecognition = function Recognition() {
    recognition = this;
    this.start = vi.fn();
    this.stop = vi.fn(() => this.onend?.());
    this.abort = vi.fn();
  };
});
afterEach(() => {
  cleanup();
  delete window.webkitSpeechRecognition;
  window.getSelection().removeAllRanges();
});

describe("quote helpers", () => {
  it("shortens a long selection and adds a mark", () => {
    const long = "מילה ".repeat(100);
    const quote = shortenQuote(long);
    expect(quote.length).toBeLessThanOrEqual(QUOTE_MAX);
    expect(quote.endsWith("…")).toBe(true);
    expect(shortenQuote("  קצר \n  וטוב ")).toBe("קצר וטוב");
  });

  it("puts the quote before the question, and leaves a question without a quote alone", () => {
    expect(composeQuestion("מה זה אומר?", "ביטוח חובה")).toBe("בהקשר לקטע מהתשובה: «ביטוח חובה». מה זה אומר?");
    expect(composeQuestion("מה זה אומר?", "")).toBe("מה זה אומר?");
    expect(quotePrefix(undefined)).toBe("");
  });
});

describe("asking about a quote", () => {
  it("sends the quote with the question, shows them apart, and keeps the quote in the history", async () => {
    streamChat.mockResolvedValue(ANSWER);
    const { result } = renderHook(() => useChat());
    act(() => result.current.reset());

    await act(async () => result.current.send("מה זה אומר?", "ביטוח חובה"));
    expect(streamChat.mock.calls[0][0]).toBe("בהקשר לקטע מהתשובה: «ביטוח חובה». מה זה אומר?");
    expect(result.current.messages[0]).toMatchObject({ role: "user", content: "מה זה אומר?", quote: "ביטוח חובה" });

    await act(async () => result.current.send("ועוד שאלה"));
    const history = streamChat.mock.calls[1][1];
    expect(history[0].content).toBe("בהקשר לקטע מהתשובה: «ביטוח חובה». מה זה אומר?");
    expect(streamChat.mock.calls[1][0]).toBe("ועוד שאלה");
  });

  it("shows the quote above the box, shortens the room for the question, and can remove it", () => {
    const onClear = vi.fn();
    render(<ChatInput onSend={() => {}} loading={false} quote="ביטוח חובה" onClearQuote={onClear} />);
    expect(screen.getByText(/«ביטוח חובה»/)).toBeTruthy();
    const box = screen.getByLabelText("השאלה שלכם");
    expect(Number(box.getAttribute("maxlength"))).toBe(MAX_QUESTION_CHARS - quotePrefix("ביטוח חובה").length);
    fireEvent.click(screen.getByRole("button", { name: "הסרת הציטוט" }));
    expect(onClear).toHaveBeenCalled();
  });
});

describe("the ask-about-this button", () => {
  const select = (element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    document.dispatchEvent(new Event("selectionchange"));
  };

  it("appears for text selected inside an answer, and hands the text over", async () => {
    const onAsk = vi.fn();
    render(
      <>
        <div className="answer"><div className="rich"><p data-testid="p">ביטוח חובה הוא חובה על פי חוק</p></div></div>
        <SelectionAsk onAsk={onAsk} />
      </>,
    );
    select(screen.getByTestId("p"));
    const button = await screen.findByRole("button", { name: "שאלו על זה" });
    fireEvent.click(button);
    expect(onAsk).toHaveBeenCalledWith("ביטוח חובה הוא חובה על פי חוק");
    await waitFor(() => expect(screen.queryByRole("button", { name: "שאלו על זה" })).toBeNull());
  });

  it("does not appear for text outside an answer", async () => {
    render(
      <>
        <p data-testid="outside">טקסט רגיל בדף</p>
        <SelectionAsk onAsk={() => {}} />
      </>,
    );
    select(screen.getByTestId("outside"));
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.queryByRole("button", { name: "שאלו על זה" })).toBeNull();
  });
});

describe("dictation", () => {
  it("fills the question box with what is said, after the text that was already there", () => {
    render(<ChatInput onSend={() => {}} loading={false} />);
    const box = screen.getByLabelText("השאלה שלכם");
    fireEvent.change(box, { target: { value: "שלום" } });
    fireEvent.click(screen.getByRole("button", { name: "הקלטת שאלה בקול" }));
    expect(recognition.start).toHaveBeenCalled();
    expect(recognition.lang).toBe("he-IL");

    act(() => recognition.onresult({ results: [[{ transcript: "מה כולל" }], [{ transcript: " ביטוח" }]] }));
    expect(box.value).toBe("שלום מה כולל ביטוח");

    fireEvent.click(screen.getByRole("button", { name: "עצירת ההקלטה" }));
    expect(screen.getByRole("button", { name: "הקלטת שאלה בקול" })).toBeTruthy();
  });

  it("empties the box after sending, even if the recording delivers one more piece of text", () => {
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} loading={false} />);
    const box = screen.getByLabelText("השאלה שלכם");
    fireEvent.click(screen.getByRole("button", { name: "הקלטת שאלה בקול" }));
    const late = recognition.onresult; // what the browser would still call after the send
    act(() => late({ results: [[{ transcript: "מה כולל ביטוח" }]] }));
    expect(box.value).toBe("מה כולל ביטוח");

    fireEvent.click(screen.getByRole("button", { name: "שליחה" }));
    expect(onSend).toHaveBeenCalledWith("מה כולל ביטוח");
    expect(box.value).toBe("");
    expect(recognition.abort).toHaveBeenCalled();
    expect(recognition.onresult).toBeNull(); // a late piece of text is ignored
    expect(screen.getByRole("button", { name: "הקלטת שאלה בקול" })).toBeTruthy();
  });

  it("explains in Hebrew when the microphone is not allowed", () => {
    render(<ChatInput onSend={() => {}} loading={false} />);
    fireEvent.click(screen.getByRole("button", { name: "הקלטת שאלה בקול" }));
    act(() => recognition.onerror({ error: "not-allowed" }));
    expect(screen.getByRole("alert").textContent).toContain("אין הרשאה למיקרופון");
  });

  it("shows no microphone button in a browser that cannot recognise speech", () => {
    delete window.webkitSpeechRecognition;
    render(<ChatInput onSend={() => {}} loading={false} />);
    expect(screen.queryByRole("button", { name: "הקלטת שאלה בקול" })).toBeNull();
  });
});
