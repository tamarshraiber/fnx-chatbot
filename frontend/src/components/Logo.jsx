import { useId } from "react";
import "./Logo.css";

/**
 * Two speech bubbles that merge into one symbol: a navy one behind, an orange one in front, and a lighter
 * shape where they overlap. A small sparkle in the orange bubble hints at "smart". With thinking=true the
 * sparkle twinkles (used while the bot is writing an answer).
 */
export default function Logo({ size = 40, thinking = false }) {
  const id = useId(); // gradient and clip ids must be unique, since the logo appears several times on one page
  const navy = `${id}-navy`;
  const fire = `${id}-fire`;
  const back = `${id}-back`;
  return (
    <svg
      className={`logo${thinking ? " logo--thinking" : ""}`}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      role="img"
      aria-label="עוזר וירטואלי"
    >
      <defs>
        <linearGradient id={navy} x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#1b3a78" />
          <stop offset="1" stopColor="#2f66c8" />
        </linearGradient>
        <linearGradient id={fire} x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#f26a21" />
          <stop offset="1" stopColor="#ff8a4c" />
        </linearGradient>
        <clipPath id={back}>
          <rect x="5" y="7" width="35" height="29" rx="10" />
        </clipPath>
      </defs>
      {/* back bubble (navy), tail at the bottom left */}
      <path d="M12 35 L10 46 L22 35 Z" fill={`url(#${navy})`} />
      <rect x="5" y="7" width="35" height="29" rx="10" fill={`url(#${navy})`} stroke="#ffffff" strokeOpacity="0.22" strokeWidth="1" />
      {/* front bubble (orange), tail at the bottom right */}
      <path d="M51 49 L55 59 L43 49 Z" fill={`url(#${fire})`} />
      <rect x="22" y="21" width="37" height="29" rx="10" fill={`url(#${fire})`} />
      {/* where the two bubbles meet: the lighter overlap that joins them into one symbol */}
      <g clipPath={`url(#${back})`}>
        <rect x="22" y="21" width="37" height="29" rx="10" fill="#ffe3d0" fillOpacity="0.92" />
      </g>
      {/* the sparkle and its dot: the "AI" hint */}
      <path
        className="logo__spark"
        d="M48 29 Q48 35.5 54.5 35.5 Q48 35.5 48 42 Q48 35.5 41.5 35.5 Q48 35.5 48 29 Z"
        fill="#ffffff"
      />
      <circle className="logo__dot" cx="54.5" cy="28.5" r="1.7" fill="#ffffff" />
    </svg>
  );
}
