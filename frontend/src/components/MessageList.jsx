import { useEffect, useRef } from "react";
import Message from "./Message";
import TypingIndicator from "./TypingIndicator";
import "./MessageList.css";

export default function MessageList({ messages, loading }) {
  const endRef = useRef(null);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    endRef.current?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "end" });
  }, [messages, loading]);

  return (
    <div className="messages" role="log" aria-live="polite" aria-label="השיחה">
      {messages.map((m) => <Message key={m.id} message={m} />)}
      {loading && <TypingIndicator />}
      <div ref={endRef} />
    </div>
  );
}
