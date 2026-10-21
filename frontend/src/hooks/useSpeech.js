import { useCallback, useEffect, useRef, useState } from "react";

export function speechSupported() {
  return typeof window !== "undefined" && "speechSynthesis" in window && typeof window.SpeechSynthesisUtterance === "function";
}

/** The text as it should be spoken: no markdown marks, bullets or web addresses, which sound strange read aloud. */
export function cleanForSpeech(text) {
  return String(text || "")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/[*_`#>]+/g, "")
    .replace(/^\s*[•\-–]\s+/gm, "")
    .replace(/\s+/g, " ")
    .trim();
}

/** A Hebrew voice from the device, if there is one. */
export function pickHebrewVoice(voices) {
  const hebrew = (voice) => /^(he|iw)\b/i.test(voice.lang || "");
  return voices.find(hebrew) || null;
}

/**
 * Read text aloud with the browser's own voice (no server, no cost).
 * Returns { supported, speaking, noHebrewVoice, speak(text, onWord), stop() }; onWord(charIndex, charLength) is called for each word. Only one text is read at a time.
 */
export function useSpeech() {
  const supported = speechSupported();
  const [speaking, setSpeaking] = useState(false);
  const [noHebrewVoice, setNoHebrewVoice] = useState(false);
  const current = useRef(null); // the utterance that is being read now

  const stop = useCallback(() => {
    if (!supported) return;
    current.current = null;
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  const speak = useCallback(
    (text, onWord) => {
      if (!supported) return;
      // With onWord the caller has already prepared the exact text, so word positions must not shift: say it as it is.
      const spoken = onWord ? text : cleanForSpeech(text);
      if (!spoken || !spoken.trim()) return;
      const synth = window.speechSynthesis;
      const utterance = new window.SpeechSynthesisUtterance(spoken);
      utterance.lang = "he-IL";
      const voices = synth.getVoices();
      const voice = pickHebrewVoice(voices);
      if (voice) utterance.voice = voice;
      setNoHebrewVoice(voices.length > 0 && !voice); // an empty list usually means "not loaded yet", not "no voice"
      const finished = () => {
        if (current.current === utterance) setSpeaking(false); // ignore the end of an older text we replaced
      };
      utterance.onend = finished;
      utterance.onerror = finished;
      // The voice reports every word it starts (not all voices do). Words of an older text are ignored.
      utterance.onboundary = (event) => {
        if (onWord && current.current === utterance && (!event.name || event.name === "word")) {
          onWord(event.charIndex, event.charLength);
        }
      };
      synth.cancel(); // stop whatever was being read
      current.current = utterance;
      setSpeaking(true);
      synth.speak(utterance);
    },
    [supported],
  );

  useEffect(() => () => {
    if (current.current) window.speechSynthesis.cancel(); // leaving the page or removing the message
  }, []);

  return { supported, speaking, noHebrewVoice, speak, stop };
}
