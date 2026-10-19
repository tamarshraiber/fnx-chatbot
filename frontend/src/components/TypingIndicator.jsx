import Logo from "./Logo";
import "./TypingIndicator.css";

export default function TypingIndicator() {
  return (
    <div className="msg msg--bot" role="status" aria-label="העוזר כותב תשובה">
      <Logo size={32} />
      <div className="typing">
        <span /><span /><span />
      </div>
    </div>
  );
}
