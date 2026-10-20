import { useCallback, useRef, useState } from "react";
import { ChatError, streamChat } from "../api";

const STORAGE_KEY = "phoenix-chat-messages";

/** Read the saved conversation. sessionStorage survives a page refresh but is erased when the tab is closed. */
function loadSaved() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(STORAGE_KEY));
    return Array.isArray(saved) ? saved : [];
  } catch {
    return []; // storage blocked or data broken: start empty
  }
}

function save(messages) {
  try {
    if (messages.length) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // storage blocked or full: the chat still works, it just will not survive a refresh
  }
}

const initialMessages = loadSaved();
let nextId = initialMessages.reduce((max, m) => Math.max(max, Number(m.id) || 0), 0) + 1; // continue after the saved ids

/** Holds the conversation: messages, loading flag and the last error. Messages are also kept in sessionStorage. */
export function useChat() {
  const [messages, setMessages] = useState(initialMessages);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null); // { message, canRetry }
  const lastRequest = useRef(null);
  const messagesRef = useRef(initialMessages);
  const session = useRef(0); // bumped on reset, so a late reply from the old conversation is dropped

  const update = (next) => {
    messagesRef.current = next;
    setMessages(next);
    save(next);
  };

  const run = useCallback(async (question, history) => {
    const mySession = session.current;
    setLoading(true);
    setError(null);
    lastRequest.current = { question, history };
    let id = null; // id of the assistant message, once the first words arrive
    const withoutMine = () => messagesRef.current.filter((m) => m.id !== id);
    try {
      let text = "";
      const result = await streamChat(question, history, (delta) => {
        if (mySession !== session.current) return;
        text += delta;
        id ??= nextId++;
        // Show the words as they arrive. Not saved yet: the finished message is saved below.
        const next = [...withoutMine(), { id, role: "assistant", content: text, found: true, streaming: true }];
        messagesRef.current = next;
        setMessages(next);
      });
      if (mySession !== session.current) return;
      id ??= nextId++;
      update([
        ...withoutMine(),
        {
          id,
          role: "assistant",
          content: result.answer,
          sourceUrl: result.source_url,
          sourceTitle: result.source_title,
          found: result.found,
        },
      ]);
    } catch (e) {
      if (mySession !== session.current) return;
      if (id !== null) update(withoutMine()); // drop the half-written answer
      const known = e instanceof ChatError;
      setError({
        message: known ? e.message : "משהו השתבש. נסו שוב.",
        canRetry: known ? e.canRetry : true,
      });
    } finally {
      if (mySession === session.current) setLoading(false);
    }
  }, []);

  const send = useCallback(
    (text) => {
      const question = text.trim();
      if (!question || loading) return;
      const history = messagesRef.current.map(({ role, content }) => ({ role, content }));
      update([...messagesRef.current, { id: nextId++, role: "user", content: question }]);
      run(question, history);
    },
    [loading, run],
  );

  const retry = useCallback(() => {
    if (lastRequest.current && !loading) run(lastRequest.current.question, lastRequest.current.history);
  }, [loading, run]);

  const reset = useCallback(() => {
    session.current += 1;
    update([]);
    setError(null);
    setLoading(false);
  }, []);

  return { messages, loading, error, send, retry, reset };
}
