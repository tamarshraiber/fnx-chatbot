import { useEffect, useRef, useState } from "react";
import { MAX_QUESTION_CHARS } from "../api";
import { MicIcon, SendIcon } from "./Icons";
import { quotePrefix } from "../hooks/quote";
import { useDictation } from "../hooks/useDictation";
import "./ChatInput.css";

export default function ChatInput({ onSend, loading, quote = "", onClearQuote }) {
  const [value, setValue] = useState("");
  const ref = useRef(null);
  const typedBefore = useRef(""); // what was already in the box when the recording started

  // The quote is part of the 500 characters the server accepts, so the box gets shorter when there is one.
  const limit = MAX_QUESTION_CHARS - quotePrefix(quote).length;
  const dictation = useDictation((said) => setValue(`${typedBefore.current}${typedBefore.current ? " " : ""}${said}`.slice(0, limit)));
  const toggleDictation = () => {
    if (dictation.listening) {
      dictation.stop();
    } else {
      typedBefore.current = value.trim();
      dictation.start();
    }
  };

  // A new quote means the person wants to ask about it: put the cursor in the box.
  useEffect(() => {
    if (quote) ref.current?.focus();
  }, [quote]);

  // Grow with the text, up to a limit.
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const submit = () => {
    if (!value.trim() || loading) return;
    dictation.stop();
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
      {quote && (
        <div className="input__quote">
          <span className="input__quote-text"><span className="sr-only">ציטוט מהתשובה: </span>«{quote}»</span>
          <button type="button" className="input__quote-clear" onClick={onClearQuote} aria-label="הסרת הציטוט">×</button>
        </div>
      )}
      <div className="input__box">
        <label htmlFor="question" className="sr-only">השאלה שלכם</label>
        <textarea
          id="question"
          ref={ref}
          rows={1}
          value={value}
          maxLength={limit}
          placeholder={quote ? "מה תרצו לשאול על הקטע?" : "כתבו כאן שאלה על ביטוח, תביעות או שירות…"}
          dir="auto"
          autoFocus
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
        />
        {value.length > limit - 100 && (
          <span className="input__count" dir="ltr">{value.length}/{limit}</span>
        )}
        {dictation.supported && (
          <button
            type="button"
            className={`input__mic${dictation.listening ? " input__mic--on" : ""}`}
            onClick={toggleDictation}
            aria-pressed={dictation.listening}
            aria-label={dictation.listening ? "עצירת ההקלטה" : "הקלטת שאלה בקול"}
            title={dictation.listening ? "עצירת ההקלטה" : "הקלטת שאלה בקול"}
          >
            <MicIcon />
          </button>
        )}
        <button type="submit" className="input__send" disabled={!canSend} aria-label="שליחה">
          <SendIcon />
        </button>
      </div>
      <p className="sr-only" role="status">{dictation.listening ? "מקשיבים… דברו עכשיו." : ""}</p>
      {dictation.error && <p className="input__error" role="alert">{dictation.error}</p>}
      <p className="input__note">
        התשובות מבוססות על תוכן אתר הפניקס ועשויות להכיל אי-דיוקים. לפרטים מחייבים יש לפנות לחברה.
      </p>
    </form>
  );
}
