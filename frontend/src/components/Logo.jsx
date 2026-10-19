import "./Logo.css";

/** Abstract phoenix mark: a rising flame over a pair of wing strokes. Drawn for this project. */
export default function Logo({ size = 40 }) {
  return (
    <svg className="logo" width={size} height={size} viewBox="0 0 48 48" role="img" aria-label="הפניקס">
      <defs>
        <linearGradient id="phx-flame" x1="12" y1="44" x2="36" y2="4" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#12285a" />
          <stop offset="0.6" stopColor="#1b3a78" />
          <stop offset="1" stopColor="#f26a21" />
        </linearGradient>
      </defs>
      <path d="M24 3c1 8 9 12 9 22a9 9 0 0 1-18 0c0-5 3-8 5-10 0 4 1 6 3 7-1-7 0-14 1-19Z" fill="url(#phx-flame)" />
      <path d="M8 30c4 8 12 13 16 13s12-5 16-13c-4 4-9 6-16 6S12 34 8 30Z" fill="url(#phx-flame)" opacity="0.55" />
      <circle cx="24" cy="26" r="3" fill="#fff" opacity="0.9" />
    </svg>
  );
}
