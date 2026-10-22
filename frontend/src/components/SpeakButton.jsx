import { useCallback, useEffect, useRef } from "react";
import { SpeakerIcon, StopIcon } from "./Icons";
import { buildReadAlong, clearHighlight, showWord, supportsHighlight } from "../hooks/readAlong";
import { speechSupported, useSpeech } from "../hooks/useSpeech";

/**
 * "Read the answer aloud" button. With autoPlay the answer is also read once, as soon as the button appears
 * (the accessibility menu has an "auto-read" switch for that).
 */
export default function SpeakButton({ text, containerRef, autoPlay = false }) {
  const { speaking, noHebrewVoice, speak, stop } = useSpeech();
  const autoPlayed = useRef(false);

  // Read the answer as it is on the screen and highlight each word when the voice reports it.
  // Without the screen element, or in a browser that cannot highlight, it reads the plain text.
  const play = useCallback(() => {
    const container = containerRef?.current;
    if (container && supportsHighlight()) {
      const along = buildReadAlong(container);
      speak(along.text, (index, length) => showWord(along.rangeAt(index, length)));
    } else {
      speak(text);
    }
  }, [containerRef, speak, text]);

  // The start waits one tick. In development, React sets up and cleans up every component twice, and the cleanup
  // in useSpeech cancels speech: without the wait, the first start would be cancelled and never repeated.
  useEffect(() => {
    if (!autoPlay || autoPlayed.current) return undefined;
    const timer = setTimeout(() => {
      autoPlayed.current = true;
      play();
    }, 0);
    return () => clearTimeout(timer);
  }, [autoPlay, play]);

  useEffect(() => {
    if (!speaking) clearHighlight(); // stopped, finished or replaced by another text
  }, [speaking]);
  useEffect(() => clearHighlight, []);

  if (!speechSupported()) return null; // this browser cannot speak: show no button at all

  return (
    <>
      <button
        type="button"
        className="copy"
        onClick={() => (speaking ? stop() : play())}
        aria-pressed={speaking}
        aria-label={speaking ? "עצירת ההקראה" : "הקראת התשובה"}
      >
        {speaking ? <StopIcon /> : <SpeakerIcon />}
        <span>{speaking ? "עצירה" : "הקראה"}</span>
      </button>
      {noHebrewVoice && (
        <span className="answer__voice-note" role="status">
          לא נמצא קול בעברית במכשיר, ההקראה עלולה להישמע לא ברור.
        </span>
      )}
    </>
  );
}
