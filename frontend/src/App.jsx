import { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import Logo from "./components/Logo";
import StatsPage from "./components/StatsPage";
import { ChatIcon, CloseIcon } from "./components/Icons";
import { wakeServer } from "./api";
import { useChat } from "./hooks/useChat";
import "./App.css";

const isStatsAddress = () => window.location.hash === "#/stats";

export default function App() {
  const chat = useChat(); // lives here, so the conversation survives switching views
  const [mode, setMode] = useState("full"); // "full" | "widget"
  const [open, setOpen] = useState(true); // widget only: is the window open?
  const [statsPage, setStatsPage] = useState(isStatsAddress); // the public quality page, at the address #/stats

  // A free server sleeps when unused. Waking it now means the first question does not wait for it.
  useEffect(() => {
    wakeServer();
  }, []);

  useEffect(() => {
    const onChange = () => setStatsPage(isStatsAddress());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const toggleMode = () => {
    setMode((m) => (m === "full" ? "widget" : "full"));
    setOpen(true);
  };

  if (statsPage) return <StatsPage />;

  if (mode === "full") {
    return <ChatWindow mode="full" chat={chat} onToggleMode={toggleMode} />;
  }

  return (
    <div className="stage">
      <div className="stage__intro">
        <Logo size={64} />
        <h1>העוזר הווירטואלי של הפניקס</h1>
        <p>תצוגה מוקטנת: החלון הצף נמצא בפינה.</p>
        <button type="button" className="stage__full" onClick={toggleMode}>מעבר לתצוגה מלאה</button>
      </div>
      {open && <ChatWindow mode="widget" chat={chat} onToggleMode={toggleMode} onClose={() => setOpen(false)} />}
      <button
        type="button"
        className="launcher"
        onClick={() => setOpen((o) => !o)}
        aria-label={open ? "סגירת הצ'אט" : "פתיחת הצ'אט"}
        aria-expanded={open}
      >
        {open ? <CloseIcon /> : <ChatIcon />}
      </button>
    </div>
  );
}
