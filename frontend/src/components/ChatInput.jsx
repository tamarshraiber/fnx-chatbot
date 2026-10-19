import { useEffect, useRef, useState } from "react";
import { MAX_QUESTION_CHARS } from "../api";
import { SendIcon } from "./Icons";
import "./ChatInput.css";

export default function ChatInput({ onSend, loading }) {
  const [value, setValue] = useState("");
  const ref = useRef(null);

  // Grow with the text, up to a limit.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const submit = () => {
    if (!value.trim() || loading) return;
    onSend(value);
    setValue("");
  };

  const onKeyDown = (e) => {
    // isComposing: do not send while a keyboard (IME) is still building a word
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  const canSend = value.trim().length > 0 && !loading;

  return (
    <form className="input" onSubmit={(e) => { e.preventDefault(); submit(); }}>
      <div className="input__box">
        <label htmlFor="question" className="sr-only">השאלה שלכם</label>
        <textarea
          id="question"
          ref={ref}
          rows={1}
          value={value}
          maxLength={MAX_QUESTION_CHARS}
          placeholder="כתבו כאן שאלה על ביטוח, תביעות או שירות…"
          dir="auto"
          autoFocus
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
        />
        {value.length > MAX_QUESTION_CHARS - 100 && (
          <span className="input__count" dir="ltr">{value.length}/{MAX_QUESTION_CHARS}</span>
        )}
        <button type="submit" className="input__send" disabled={!canSend} aria-label="שליחה">
          <SendIcon />
        </button>
      </div>
      <p className="input__note">
        התשובות מבוססות על תוכן אתר הפניקס ועשויות להכיל אי-דיוקים. לפרטים מחייבים יש לפנות לחברה.
      </p>
    </form>
  );
}
