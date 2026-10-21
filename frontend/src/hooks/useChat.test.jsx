// @vitest-environment jsdom
import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ChatError } from "../api";
import { useChat } from "./useChat";

vi.mock("../api", async (importOriginal) => ({ ...(await importOriginal()), streamChat: vi.fn() }));
const { streamChat } = await import("../api");

const ANSWER = { answer: "תשובה", source_url: "https://www.fnx.co.il/a", source_title: "כותרת", found: true };

beforeEach(() => {
  streamChat.mockReset();
  sessionStorage.clear();
});

/** Render the hook and start from an empty conversation. */
function setup() {
  const hook = renderHook(() => useChat());
  act(() => hook.result.current.reset());
  return hook;
}

describe("sending", () => {
  it("adds the question, then the answer with its source", async () => {
    streamChat.mockResolvedValue(ANSWER);
    const { result } = setup();
    act(() => result.current.send("  שלום  "));
    expect(result.current.messages).toMatchObject([{ role: "user", content: "שלום" }]); // trimmed
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.messages).toMatchObject([
      { role: "user", content: "שלום" },
      { role: "assistant", content: "תשובה", sourceUrl: ANSWER.source_url, sourceTitle: "כותרת", found: true },
    ]);
    expect(result.current.error).toBeNull();
  });

  it("ignores an empty or spaces-only question", () => {
    const { result } = setup();
    act(() => result.current.send("   "));
    expect(result.current.messages).toEqual([]);
    expect(streamChat).not.toHaveBeenCalled();
  });

  it("ignores a second question while the first is still loading", async () => {
    let finish;
    streamChat.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    const { result } = setup();
    act(() => result.current.send("ראשונה"));
    act(() => result.current.send("שנייה"));
    expect(streamChat).toHaveBeenCalledTimes(1);
    await act(async () => finish(ANSWER));
    expect(result.current.messages).toHaveLength(2);
  });

  it("sends the earlier messages, without the new question and without extra fields", async () => {
    streamChat.mockResolvedValue(ANSWER);
    const { result } = setup();
    act(() => result.current.send("ראשונה"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.send("שנייה"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(streamChat.mock.calls[0][1]).toEqual([]);
    expect(streamChat.mock.calls[1][0]).toBe("שנייה");
    expect(streamChat.mock.calls[1][1]).toEqual([
      { role: "user", content: "ראשונה" },
      { role: "assistant", content: "תשובה" },
    ]);
  });

  it("shows the words as they arrive, then replaces them with the final answer", async () => {
    let onDelta;
    let finish;
    streamChat.mockImplementation((question, history, callback) => {
      onDelta = callback;
      return new Promise((resolve) => (finish = resolve));
    });
    const { result } = setup();
    act(() => result.current.send("שלום"));

    act(() => onDelta("תש"));
    act(() => onDelta("ובה"));
    expect(result.current.messages.at(-1)).toMatchObject({ role: "assistant", content: "תשובה", streaming: true });
    expect(result.current.messages).toHaveLength(2); // one message that grows, not many

    await act(async () => finish({ ...ANSWER, answer: "תשובה סופית" }));
    expect(result.current.messages.at(-1)).toMatchObject({ content: "תשובה סופית", sourceTitle: "כותרת" });
    expect(result.current.messages.at(-1).streaming).toBeUndefined();
    expect(result.current.messages).toHaveLength(2);
  });
});

describe("saving", () => {
  it("keeps the finished conversation in sessionStorage and removes it on reset", async () => {
    streamChat.mockResolvedValue(ANSWER);
    const { result } = setup();
    act(() => result.current.send("שלום"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(JSON.parse(sessionStorage.getItem("phoenix-chat-messages"))).toHaveLength(2);
    act(() => result.current.reset());
    expect(sessionStorage.getItem("phoenix-chat-messages")).toBeNull();
  });

  it("does not save a half-written answer", async () => {
    let onDelta;
    streamChat.mockImplementation((question, history, callback) => {
      onDelta = callback;
      return new Promise(() => {});
    });
    const { result } = setup();
    act(() => result.current.send("שלום"));
    act(() => onDelta("חצי"));
    const saved = JSON.parse(sessionStorage.getItem("phoenix-chat-messages"));
    expect(saved).toHaveLength(1);
    expect(saved[0].role).toBe("user");
  });
});

describe("errors", () => {
  it("shows the error, keeps the question, and can retry", async () => {
    streamChat.mockRejectedValueOnce(new ChatError("השירות עמוס", true)).mockResolvedValueOnce(ANSWER);
    const { result } = setup();
    act(() => result.current.send("שלום"));
    await waitFor(() => expect(result.current.error).toEqual({ message: "השירות עמוס", canRetry: true }));
    expect(result.current.messages).toMatchObject([{ role: "user" }]);
    expect(result.current.loading).toBe(false);

    act(() => result.current.retry());
    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.error).toBeNull();
    expect(streamChat.mock.calls[1][0]).toBe("שלום");
    expect(streamChat.mock.calls[1][1]).toEqual([]); // the question is not added to its own history
    expect(result.current.messages.filter((m) => m.role === "user")).toHaveLength(1); // and not shown twice
  });

  it("drops a half-written answer when the connection fails", async () => {
    streamChat.mockImplementation(async (question, history, onDelta) => {
      onDelta("חצי");
      throw new ChatError("החיבור נותק", true);
    });
    const { result } = setup();
    act(() => result.current.send("שלום"));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.messages).toMatchObject([{ role: "user" }]);
  });

  it("shows a general Hebrew message for an unexpected error", async () => {
    streamChat.mockRejectedValue(new Error("boom"));
    const { result } = setup();
    act(() => result.current.send("שלום"));
    await waitFor(() => expect(result.current.error).toEqual({ message: "משהו השתבש. נסו שוב.", canRetry: true }));
  });

  it("passes on canRetry=false for a question the server rejected", async () => {
    streamChat.mockRejectedValue(new ChatError("לא ניתן לשלוח", false));
    const { result } = setup();
    act(() => result.current.send("שלום"));
    await waitFor(() => expect(result.current.error?.canRetry).toBe(false));
  });
});

describe("reset", () => {
  it("clears the conversation and the error", async () => {
    streamChat.mockRejectedValue(new ChatError("עמוס", true));
    const { result } = setup();
    act(() => result.current.send("שלום"));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    act(() => result.current.reset());
    expect(result.current.messages).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it("drops a late reply that belongs to the old conversation", async () => {
    let finish;
    streamChat.mockReturnValue(new Promise((resolve) => (finish = resolve)));
    const { result } = setup();
    act(() => result.current.send("שלום"));
    act(() => result.current.reset());
    expect(result.current.loading).toBe(false);
    await act(async () => finish(ANSWER));
    expect(result.current.messages).toEqual([]);
  });
});
