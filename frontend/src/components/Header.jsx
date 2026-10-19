import Logo from "./Logo";
import { CloseIcon, ExpandIcon, NewChatIcon, ShrinkIcon } from "./Icons";
import "./Header.css";

export default function Header({ mode, hasMessages, onNewChat, onToggleMode, onClose }) {
  const widget = mode === "widget";
  return (
    <header className="header">
      <Logo size={widget ? 32 : 40} />
      <div className="header__titles">
        <div className="header__name">הפניקס</div>
        <div className="header__sub">עוזר וירטואלי</div>
      </div>
      <div className="header__actions">
        {hasMessages && (
          <button type="button" className="icon-btn" onClick={onNewChat} title="שיחה חדשה" aria-label="שיחה חדשה">
            <NewChatIcon />
          </button>
        )}
        <button
          type="button"
          className="icon-btn"
          onClick={onToggleMode}
          title={widget ? "תצוגה מלאה" : "תצוגה מוקטנת"}
          aria-label={widget ? "מעבר לתצוגה מלאה" : "מעבר לתצוגה מוקטנת"}
        >
          {widget ? <ExpandIcon /> : <ShrinkIcon />}
        </button>
        {widget && (
          <button type="button" className="icon-btn" onClick={onClose} title="סגירה" aria-label="סגירת הצ'אט">
            <CloseIcon />
          </button>
        )}
      </div>
    </header>
  );
}
