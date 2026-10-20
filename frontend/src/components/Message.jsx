import { useEffect, useRef, useState } from "react";
import Logo from "./Logo";
import RichText from "./RichText";
import SourceCard from "./SourceCard";
import { CheckIcon, CopyIcon } from "./Icons";
import { useSmoothText } from "../hooks/useSmoothText";
import "./Message.css";

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

export default function Message({ message }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef(null);
  useEffect(() => () => clearTimeout(timer.current), []);

  // Only a message that was streamed in front of the user is animated. Restored messages appear at once.
  const animated = useRef(message.streaming === true);
  if (message.streaming) animated.current = true;
  const { text, done } = useSmoothText(message.content, animated.current);
  const writing = message.streaming === true || !done; // still receiving or still revealing words
  const appear = animated.current ? "fade-in" : undefined;

  if (message.role === "user") {
    return (
      <div className="msg msg--user">
        <div className="bubble" dir="auto">{message.content}</div>
      </div>
    );
  }

  const handleCopy = async () => {
    if (await copyText(message.content)) {
      setCopied(true);
      clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className={`msg msg--bot ${animated.current ? "msg--soft" : ""}`}>
      <Logo size={32} />
      <div className={`answer ${message.found ? "" : "answer--notfound"} ${writing ? "answer--writing" : ""}`}>
        <RichText text={text} />
        {!writing && (
          <div className={appear}>
            {message.found && message.sourceUrl && <SourceCard url={message.sourceUrl} title={message.sourceTitle} />}
            {!message.found && (
              <p className="answer__hint">אפשר לנסח את השאלה אחרת, או לשאול על נושא אחר באתר הפניקס.</p>
            )}
            <div className="answer__actions">
              <button type="button" className="copy" onClick={handleCopy} aria-label="העתקת התשובה">
                {copied ? <CheckIcon /> : <CopyIcon />}
                <span aria-live="polite">{copied ? "הועתק" : "העתקה"}</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
