import Header from "./Header";
import Hero from "./Hero";
import MessageList from "./MessageList";
import ErrorBanner from "./ErrorBanner";
import ChatInput from "./ChatInput";
import "./ChatWindow.css";

/** The whole chat. `mode` is "full" (whole page) or "widget" (small floating window). */
export default function ChatWindow({ mode, chat, onToggleMode, onClose }) {
  const { messages, loading, error, send, retry, reset } = chat;
  const empty = messages.length === 0 && !loading;

  return (
    <section className={`chat chat--${mode}`} aria-label="צ'אט עם העוזר הווירטואלי של הפניקס">
      <Header
        mode={mode}
        hasMessages={messages.length > 0}
        onNewChat={reset}
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
        <ChatInput onSend={send} loading={loading} />
      </div>
    </section>
  );
}
