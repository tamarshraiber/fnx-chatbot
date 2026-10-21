import { useEffect, useState } from "react";
import Logo from "./Logo";
import { ChatIcon } from "./Icons";
import AccuracyRing, { percentOf } from "./AccuracyRing";
import { fetchStats } from "../api";
import { useCountUp } from "../hooks/useCountUp";
import "./StatsPage.css";

function formatDate(value) {
  if (!value) return "לא ידוע";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "לא ידוע" : date.toLocaleDateString("he-IL");
}

/** A number that counts up to its value. Anything that is not a number is shown as it is. */
function AnimatedValue({ value }) {
  const shown = useCountUp(value);
  return typeof shown === "number" ? shown.toLocaleString("he-IL") : shown ?? "-";
}

function Card({ value, label, note, index = 0 }) {
  return (
    <div className="stats__card" style={{ "--i": index }}>
      <div className="stats__value" dir="ltr"><AnimatedValue value={value} /></div>
      <div className="stats__label">{label}</div>
      {note && <div className="stats__note">{note}</div>}
    </div>
  );
}

/** Grey placeholder cards with a soft shimmer, in the same places as the real ones. */
function Skeleton() {
  return (
    <div className="stats__skeleton" role="status" aria-label="טוען נתונים">
      <div className="stats__grid">
        {[0, 1, 2].map((n) => (
          <div className="stats__card stats__card--skeleton" key={n}>
            <div className="skeleton skeleton--value" />
            <div className="skeleton skeleton--line" />
          </div>
        ))}
      </div>
      <div className="stats__grid">
        {[0, 1, 2].map((n) => (
          <div className="stats__card stats__card--skeleton stats__card--ring" key={n}>
            <div className="skeleton skeleton--circle" />
            <div className="skeleton skeleton--line" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** Horizontal bars, one per test, so the weakest one is easy to see. */
function Comparison({ rows }) {
  const lowest = Math.min(...rows.map((row) => row.percent));
  return (
    <section className="stats__panel" aria-label="השוואת תוצאות הבדיקה">
      <h2>השוואה בין הבדיקות</h2>
      {rows.map((row, index) => (
        <div className="bar" key={row.label} style={{ "--i": index }}>
          <div className="bar__head">
            <span>{row.label}</span>
            <span dir="ltr">{row.percent}%</span>
          </div>
          <div className="bar__track">
            <div
              className={`bar__fill${row.percent === lowest && lowest < 100 ? " bar__fill--weak" : ""}`}
              style={{ width: `${row.percent}%` }}
            />
          </div>
        </div>
      ))}
      <p className="stats__explain">
        כל פס הוא אחוז ההצלחה בבדיקה אחת. הפס הכתום הוא הנקודה החלשה ביותר כרגע, ושם יש עוד מקום לשיפור.
      </p>
    </section>
  );
}

/** Public page with totals only: how much the bot knows and how well it did on our test questions. */
export default function StatsPage() {
  const [stats, setStats] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchStats()
      .then((data) => !cancelled && setStats(data))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, []);

  const scores = stats?.eval;
  const perPage = stats?.pages && stats?.chunks ? (stats.chunks / stats.pages).toFixed(1) : null;
  const rows = scores
    ? [
        { label: "שאלות עם תשובה באתר: נענו נכון", percent: percentOf(scores.answerable_correct, scores.answerable_total) },
        { label: "שאלות בלי תשובה באתר: נדחו נכון", percent: percentOf(scores.unanswerable_rejected, scores.unanswerable_total) },
        { label: "העמוד הנכון בחמש התוצאות הראשונות", percent: percentOf(scores.retrieval_top5, scores.retrieval_total) },
      ]
    : [];

  return (
    <main className="stats">
      <header className="stats__header">
        <Logo size={40} />
        <div>
          <h1>מדד האמינות</h1>
          <p>נתונים כלליים בלבד. אין כאן שאלות או מידע על משתמשים.</p>
        </div>
        <a className="stats__back" href="#/"><ChatIcon />חזרה לצ'אט</a>
      </header>

      {failed && <p className="stats__error">לא הצלחנו לטעון את הנתונים. נסו שוב בעוד רגע.</p>}
      {!stats && !failed && <Skeleton />}

      {stats && (
        <>
          <section className="stats__grid" aria-label="המידע שהצ'אט מכיר">
            <Card index={0} value={stats.pages} label="עמודים מאתר הפניקס" />
            <Card
              index={1}
              value={stats.chunks}
              label="קטעי טקסט במאגר"
              note={perPage ? `כ-${perPage} קטעים לכל עמוד` : undefined}
            />
            <Card index={2} value={formatDate(stats.last_refresh)} label="עדכון אחרון של המידע" />
          </section>

          {scores && (
            <>
              <section className="stats__grid" aria-label="תוצאות בדיקה">
                <AccuracyRing
                  index={3}
                  correct={scores.answerable_correct}
                  total={scores.answerable_total}
                  label="שאלות עם תשובה באתר: נענו נכון"
                  note="התשובה מצביעה על העמוד הנכון"
                  explain={`מתוך ${scores.answerable_total} שאלות שהתשובה להן באתר, כמה נענו נכון ופנו לעמוד הנכון.`}
                />
                <AccuracyRing
                  index={4}
                  correct={scores.unanswerable_rejected}
                  total={scores.unanswerable_total}
                  label="שאלות בלי תשובה באתר: נדחו נכון"
                  note="הצ'אט אומר שהמידע לא באתר"
                  explain={`מתוך ${scores.unanswerable_total} שאלות שאין להן תשובה באתר, כמה נדחו נכון: הצ'אט אמר שהמידע לא באתר ולא המציא תשובה.`}
                />
                <AccuracyRing
                  index={5}
                  correct={scores.retrieval_top5}
                  total={scores.retrieval_total}
                  label="העמוד הנכון נמצא בחמש התוצאות הראשונות"
                  explain={`בכמה מ-${scores.retrieval_total} השאלות העמוד הנכון הופיע בחמש התוצאות הראשונות של החיפוש, עוד לפני כתיבת התשובה.`}
                />
              </section>
              <Comparison rows={rows} />
            </>
          )}

          <p className="stats__foot">
            הבדיקה נעשתה ב-{scores ? scores.date : "-"} על {scores ? scores.answerable_total + scores.unanswerable_total : "-"} שאלות
            קבועות. זו אינדיקציה ולא הבטחה: בדיקה על מספר קטן של שאלות.
          </p>
        </>
      )}
      <p className="stats__foot"><a href="#/accessibility">הצהרת נגישות</a></p>
    </main>
  );
}
