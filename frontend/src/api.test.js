import { afterEach, describe, expect, it, vi } from "vitest";
import { ChatError, sendChat, streamChat } from "./api";

const FINAL = { type: "final", answer: "תשובה", source_url: "https://www.fnx.co.il/a", source_title: "כותרת", found: true };

afterEach(() => vi.unstubAllGlobals());

/** Replace fetch by a fake that returns `response` (or throws). Returns the fake so calls can be checked. */
function fakeFetch(response) {
  const fake = vi.fn(async () => {
    if (response instanceof Error) throw response;
    return response;
  });
  vi.stubGlobal("fetch", fake);
  return fake;
}

/** A streaming response made of the given text pieces (each piece is one network chunk). */
function streamResponse(...pieces) {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    start(controller) {
      pieces.forEach((piece) => controller.enqueue(encoder.encode(piece)));
      controller.close();
    },
  });
  return new Response(body, { status: 200 });
}

const line = (event) => JSON.stringify(event) + "\n";

describe("streamChat", () => {
  it("calls onDelta for each piece and returns the final answer", async () => {
    fakeFetch(streamResponse(line({ type: "delta", text: "תש" }), line({ type: "delta", text: "ובה" }), line(FINAL)));
    const deltas = [];
    const result = await streamChat("שלום", [], (text) => deltas.push(text));
    expect(deltas).toEqual(["תש", "ובה"]);
    expect(result).toMatchObject({ answer: "תשובה", found: true, source_title: "כותרת" });
  });

  it("handles a line that is split across network chunks", async () => {
    const full = line({ type: "delta", text: "שלום" }) + line(FINAL);
    fakeFetch(streamResponse(full.slice(0, 10), full.slice(10, 30), full.slice(30)));
    const deltas = [];
    const result = await streamChat("שלום", [], (text) => deltas.push(text));
    expect(deltas).toEqual(["שלום"]);
    expect(result.answer).toBe("תשובה");
  });

  it("handles a Hebrew letter split between two chunks", async () => {
    const bytes = new TextEncoder().encode(line({ type: "delta", text: "שלום" }) + line(FINAL));
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(bytes.slice(0, 33)); // 33 cuts the middle of a two-byte letter
        controller.enqueue(bytes.slice(33));
        controller.close();
      },
    });
    fakeFetch(new Response(body, { status: 200 }));
    const deltas = [];
    await streamChat("שלום", [], (text) => deltas.push(text));
    expect(deltas).toEqual(["שלום"]);
  });

  it("accepts a final line with no newline at the end", async () => {
    fakeFetch(streamResponse(JSON.stringify(FINAL)));
    expect((await streamChat("שלום", [], () => {})).answer).toBe("תשובה");
  });

  it("ignores blank lines", async () => {
    fakeFetch(streamResponse("\n\n" + line(FINAL) + "\n"));
    expect((await streamChat("שלום", [], () => {})).found).toBe(true);
  });

  it("turns an error event into a ChatError (503 = busy, can retry)", async () => {
    fakeFetch(streamResponse(line({ type: "delta", text: "תש" }), line({ type: "error", status: 503 })));
    await expect(streamChat("שלום", [], () => {})).rejects.toMatchObject({ canRetry: true, message: expect.stringContaining("עמוס") });
  });

  it("fails clearly when the connection ends before the final event", async () => {
    fakeFetch(streamResponse(line({ type: "delta", text: "תש" })));
    const error = await streamChat("שלום", [], () => {}).catch((e) => e);
    expect(error).toBeInstanceOf(ChatError);
    expect(error.canRetry).toBe(true);
  });

  it("fails clearly when a line is not valid JSON", async () => {
    fakeFetch(streamResponse("this is not json\n"));
    const error = await streamChat("שלום", [], () => {}).catch((e) => e);
    expect(error).toBeInstanceOf(ChatError);
  });
});

describe("request", () => {
  it("posts the question and the history as JSON", async () => {
    const fake = fakeFetch(streamResponse(line(FINAL)));
    await streamChat("שאלה", [{ role: "user", content: "קודם" }], () => {});
    const [url, options] = fake.mock.calls[0];
    expect(url).toMatch(/\/chat\/stream$/);
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ question: "שאלה", history: [{ role: "user", content: "קודם" }] });
  });

  it("sends only the last 20 messages, each cut to 2000 characters, and only role and content", async () => {
    const fake = fakeFetch(streamResponse(line(FINAL)));
    const history = Array.from({ length: 25 }, (_, i) => ({ id: i, role: "user", content: `${i}`.padEnd(3000, "x"), found: true }));
    await streamChat("שאלה", history, () => {});
    const sent = JSON.parse(fake.mock.calls[0][1].body).history;
    expect(sent).toHaveLength(20);
    expect(sent[0].content.startsWith("5xx")).toBe(true); // messages 0-4 were dropped
    expect(sent.every((m) => m.content.length === 2000 && Object.keys(m).sort().join() === "content,role")).toBe(true);
  });
});

describe("errors", () => {
  const failing = (status, body) => new Response(body === undefined ? "oops" : JSON.stringify(body), { status });

  it.each([
    [429, true],
    [503, true],
    [500, true],
    [422, false],
  ])("status %i gives a ChatError with canRetry=%s", async (status, canRetry) => {
    fakeFetch(failing(status));
    const error = await sendChat("שלום", []).catch((e) => e);
    expect(error).toBeInstanceOf(ChatError);
    expect(error.canRetry).toBe(canRetry);
  });

  it("shows the message the server sent", async () => {
    fakeFetch(failing(429, { detail: "יותר מדי בקשות. נסו שוב בעוד דקה." }));
    await expect(sendChat("שלום", [])).rejects.toThrow("יותר מדי בקשות. נסו שוב בעוד דקה.");
  });

  it("never shows a technical detail for a 500", async () => {
    fakeFetch(failing(500, { detail: "Traceback: secret" }));
    const error = await sendChat("שלום", []).catch((e) => e);
    expect(error.message).not.toContain("secret");
  });

  it("gives a connection message when the server cannot be reached", async () => {
    fakeFetch(new TypeError("Failed to fetch"));
    const error = await sendChat("שלום", []).catch((e) => e);
    expect(error).toBeInstanceOf(ChatError);
    expect(error.canRetry).toBe(true);
    expect(error.message).toContain("חיבור");
  });
});

describe("sendChat", () => {
  it("returns the JSON answer", async () => {
    fakeFetch(new Response(JSON.stringify({ answer: "תשובה", found: true }), { status: 200 }));
    expect(await sendChat("שלום", [])).toEqual({ answer: "תשובה", found: true });
  });
});
