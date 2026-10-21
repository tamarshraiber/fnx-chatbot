import { useState } from "react";
import Header from "./Header";
import Hero from "./Hero";
import MessageList from "./MessageList";
import ErrorBanner from "./ErrorBanner";
import ChatInput from "./ChatInput";
import SelectionAsk from "./SelectionAsk";
import "./ChatWindow.css";

/** The whole chat. `mode` is "full" (whole page) or "widget" (small floating window). */
export default function ChatWindow({ mode, chat, onToggleMode, onClose }) {
  const { messages, loading, error, send, retry, reset } = chat;
  const empty = messages.length === 0 && !loading;
  const [quote, setQuote] = useState(""); // a piece of an earlier answer that the next question is about

  return (
    <section className={`chat chat--${mode}`} aria-label="צ'אט עם העוזר הווירטואלי של הפניקס">
      {/* first stop for keyboard and screen-reader users: jump over the header straight to the question box */}
      <button type="button" className="skip-link" onClick={() => document.getElementById("question")?.focus()}>
        דילוג לתיבת השאלה
      </button>
      <Header
        mode={mode}
        hasMessages={messages.length > 0}
        onNewChat={() => { setQuote(""); reset(); }}
        onToggleMode={onToggleMode}
        onClose={onClose}
      />
      <div className="chat__body">
        {empty ? (
          <Hero onPick={send} disabled={loading} compact={mode === "widget"} />
        ) : (
          <MessageList messages={messages} loading={loading} />
        )}
      </div>
      <div className="chat__footer">
        {error && <ErrorBanner error={error} onRetry={retry} />}
        <ChatInput
          onSend={(text) => { send(text, quote); setQuote(""); }}
          loading={loading}
          quote={quote}
          onClearQuote={() => setQuote("")}
        />
      </div>
      <SelectionAsk onAsk={setQuote} />
    </section>
  );
}
