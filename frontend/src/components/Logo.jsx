import { useId } from "react";
import "./Logo.css";

/** Profile icon: a soft navy circle with a fire-colored Hebrew letter ה (He). */
export default function Logo({ size = 40 }) {
  const id = useId(); // gradient ids must be unique, since the logo appears several times on one page
  const navy = `${id}-navy`;
  const fire = `${id}-fire`;
  return (
    <svg className="logo" width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="הפניקס">
      <defs>
        <linearGradient id={navy} x1="0" y1="1" x2="0" y2="0">
          <stop offset="0" stopColor="#0b1b3b" />
          <stop offset="1" stopColor="#1f4a9c" />
        </linearGradient>
        <linearGradient id={fire} gradientUnits="userSpaceOnUse" x1="0" y1="44" x2="0" y2="20">
          <stop offset="0" stopColor="#f58a4b" />
          <stop offset="1" stopColor="#ffc89a" />
        </linearGradient>
      </defs>
      {/* round background with a faint ring */}
      <circle cx="32" cy="32" r="31" fill={`url(#${navy})`} />
      <circle cx="32" cy="32" r="30" fill="none" stroke="#f58a4b" strokeOpacity="0.35" strokeWidth="1" />
      {/* the letter He, sitting on the baseline. On screen it looked too low at y=44, so it is moved up */}
      <text
        x="32"
        y="41"
        textAnchor="middle"
        fontFamily="'Arial Hebrew', Arial, 'Segoe UI', sans-serif"
        fontSize="34"
        fontWeight="700"
        fill={`url(#${fire})`}
      >
        ה
      </text>
    </svg>
  );
}
