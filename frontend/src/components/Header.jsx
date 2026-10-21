import Logo from "./Logo";
import { CloseIcon, ExpandIcon, NewChatIcon, QualityIcon, ShrinkIcon } from "./Icons";
import "./Header.css";

export default function Header({ mode, hasMessages, onNewChat, onToggleMode, onClose }) {
  const widget = mode === "widget";
  return (
    <header className="header">
      <button type="button" className="header__home" onClick={onNewChat} title="חזרה למסך הראשי" aria-label="חזרה למסך הראשי">
        <Logo size={widget ? 32 : 40} />
        <span className="header__titles">
          <span className="header__name">הפניקס</span>
          <span className="header__sub">עוזר וירטואלי</span>
        </span>
      </button>
      <div className="header__actions">
        <a
          className={`header__link${widget ? " header__link--compact" : ""}`}
          href="#/stats"
          title="איכות ושקיפות"
          aria-label="איכות ושקיפות"
        >
          <QualityIcon />
          <span className="header__link-text">איכות ושקיפות</span>
        </a>
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
