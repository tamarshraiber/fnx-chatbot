import { useEffect, useRef } from "react";
import Message from "./Message";
import TypingIndicator from "./TypingIndicator";
import "./MessageList.css";

export default function MessageList({ messages, loading }) {
  const endRef = useRef(null);

  const streaming = messages[messages.length - 1]?.streaming === true; // the answer is being written right now

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Smooth scrolling on every new word would lag, so it jumps while streaming.
    endRef.current?.scrollIntoView({ behavior: reduce || streaming ? "auto" : "smooth", block: "end" });
  }, [messages, loading, streaming]);

  return (
    <div className="messages" role="log" aria-live="polite" aria-label="השיחה">
      {messages.map((m) => <Message key={m.id} message={m} />)}
      {loading && !streaming && <TypingIndicator />}
      <div ref={endRef} />
    </div>
  );
}
