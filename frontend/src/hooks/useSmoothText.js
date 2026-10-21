import { useEffect, useRef, useState } from "react";
import { prefersReducedMotion } from "./reducedMotion";

const BASE_CHARS_PER_SECOND = 45; // calm speed when we are keeping up with the server
const EXTRA_PER_BACKLOG_CHAR = 3; // speed up a little for every character we are behind
const MAX_CHARS_PER_SECOND = 400; // never faster than this, even for a long backlog

/**
 * Reveals `target` gradually instead of all at once, so streamed text flows instead of jumping.
 * Returns { text, done }: the part to show now, and whether all of `target` is shown.
 * With animate=false (an old message) or "reduce motion" on, the whole text is shown at once.
 */
export function useSmoothText(target, animate) {
  const position = useRef(animate ? 0 : target.length); // how many characters are shown (can be fractional)
  const [, setShown] = useState(position.current); // only used to ask React for a new render

  useEffect(() => {
    if (!animate || prefersReducedMotion()) {
      position.current = target.length;
      setShown(target.length);
      return undefined;
    }

    let last = performance.now();
    let frame = 0;
    const tick = (now) => {
      const seconds = Math.min((now - last) / 1000, 0.1); // a long pause (hidden tab) must not skip ahead
      last = now;
      position.current = Math.min(position.current, target.length);
      const backlog = target.length - position.current;
      const speed = Math.min(MAX_CHARS_PER_SECOND, BASE_CHARS_PER_SECOND + backlog * EXTRA_PER_BACKLOG_CHAR);
      position.current = Math.min(target.length, position.current + speed * seconds);
      setShown(Math.floor(position.current));
      if (position.current < target.length) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [target, animate]);

  const count = animate ? Math.min(Math.floor(position.current), target.length) : target.length;
  return { text: target.slice(0, count), done: count >= target.length };
}
