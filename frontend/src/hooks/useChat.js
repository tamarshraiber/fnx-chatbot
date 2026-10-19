import { useCallback, useRef, useState } from "react";
import { ChatError, sendChat } from "../api";

let nextId = 1;

/** Holds the conversation: messages, loading flag and the last error. History lives only in memory. */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null); // { message, canRetry }
  const lastRequest = useRef(null);
  const messagesRef = useRef([]);
  const session = useRef(0); // bumped on reset, so a late reply from the old conversation is dropped

  const update = (next) => {
    messagesRef.current = next;
    setMessages(next);
  };

  const run = useCallback(async (question, history) => {
    const mySession = session.current;
    setLoading(true);
    setError(null);
    lastRequest.current = { question, history };
    try {
      const result = await sendChat(question, history);
      if (mySession !== session.current) return;
      update([
        ...messagesRef.current,
        {
          id: nextId++,
          role: "assistant",
          content: result.answer,
          sourceUrl: result.source_url,
          found: result.found,
        },
      ]);
    } catch (e) {
      if (mySession !== session.current) return;
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
