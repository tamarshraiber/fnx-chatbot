import "./AccuracyRing.css";

const RADIUS = 52;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

/** The score as a whole percent (19 of 20 is 95). An empty or missing total counts as 0. */
export function percentOf(correct, total) {
  if (!total || total <= 0) return 0;
  return Math.round((Math.min(correct, total) / total) * 100);
}

/** A circle that fills up to the score. The fill animation is plain CSS, so it needs no script. */
export default function AccuracyRing({ correct, total, label, note, explain, index = 0 }) {
  const percent = percentOf(correct, total);
  const offset = CIRCUMFERENCE * (1 - percent / 100);
  return (
    <figure className="ring" style={{ "--i": index }}>
      <svg
        className="ring__svg"
        viewBox="0 0 120 120"
        role="img"
        aria-label={`${label}: ${correct} מתוך ${total}, ${percent} אחוז`}
      >
        <circle className="ring__track" cx="60" cy="60" r={RADIUS} />
        <circle
          className="ring__fill"
          cx="60"
          cy="60"
          r={RADIUS}
          strokeDasharray={CIRCUMFERENCE}
          style={{ "--ring-full": CIRCUMFERENCE, "--ring-offset": offset }}
        />
      </svg>
      <div className="ring__percent" dir="ltr">{percent}%</div>
      <figcaption className="ring__caption">
        <span className="ring__score" dir="ltr">{correct}/{total}</span>
        <span className="ring__label">{label}</span>
        {note && <span className="ring__note">{note}</span>}
        {explain && <span className="ring__explain">{explain}</span>}
      </figcaption>
    </figure>
  );
}
