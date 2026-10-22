import { useCallback, useEffect, useRef, useState } from "react";

const recognitionClass = () => (typeof window === "undefined" ? null : window.SpeechRecognition || window.webkitSpeechRecognition || null);

export function dictationSupported() {
  return Boolean(recognitionClass());
}

/** Short Hebrew text for each reason the browser gives when listening fails. */
export function dictationErrorMessage(code) {
  switch (code) {
    case "not-allowed":
    case "service-not-allowed":
      return "אין הרשאה למיקרופון. אפשרו גישה למיקרופון בהגדרות הדפדפן.";
    case "no-speech":
      return "לא שמענו כלום. נסו שוב.";
    case "audio-capture":
      return "לא נמצא מיקרופון במכשיר.";
    case "network":
      return "אין חיבור לשירות זיהוי הדיבור.";
    default:
      return "ההקלטה נעצרה. נסו שוב.";
  }
}

/**
 * Turn speech into text with the browser's own recognition (Hebrew). No server of ours is involved.
 * onText(text) is called while the person talks, with everything said in this recording so far.
 * Returns { supported, listening, error, start(), stop(), cancel() }.
 */
export function useDictation(onText) {
  const supported = dictationSupported();
  const [listening, setListening] = useState(false);
  const [error, setError] = useState(null);
  const recognition = useRef(null);
  const onTextRef = useRef(onText);
  onTextRef.current = onText; // always the newest function, without restarting the recording

  const stop = useCallback(() => {
    recognition.current?.stop();
  }, []);

  // stop() lets the browser deliver one last piece of text after it. cancel() throws that away: used when the question is sent.
  const cancel = useCallback(() => {
    const rec = recognition.current;
    if (!rec) return;
    rec.onresult = null;
    rec.onerror = null;
    recognition.current = null;
    setListening(false);
    rec.abort?.();
  }, []);

  const start = useCallback(() => {
    const Recognition = recognitionClass();
    if (!Recognition || recognition.current) return;
    const rec = new Recognition();
    rec.lang = "he-IL";
    rec.interimResults = true; // show words while they are being said
    rec.continuous = false; // one sentence or question per recording
    rec.onresult = (event) => {
      let said = "";
      for (let i = 0; i < event.results.length; i++) said += event.results[i][0].transcript;
      onTextRef.current(said.trim());
    };
    rec.onerror = (event) => setError(dictationErrorMessage(event.error));
    rec.onend = () => {
      recognition.current = null;
      setListening(false);
    };
    recognition.current = rec;
    setError(null);
    setListening(true);
    try {
      rec.start();
    } catch {
      recognition.current = null;
      setListening(false);
      setError(dictationErrorMessage());
    }
  }, []);

  useEffect(() => () => recognition.current?.abort?.(), []);

  return { supported, listening, error, start, stop, cancel };
}
