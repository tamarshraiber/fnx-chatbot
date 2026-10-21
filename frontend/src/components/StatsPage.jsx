import { useEffect, useState } from "react";
import Logo from "./Logo";
import { fetchStats } from "../api";
import "./StatsPage.css";

function formatDate(value) {
  if (!value) return "לא ידוע";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "לא ידוע" : date.toLocaleDateString("he-IL");
}

function Card({ value, label, note }) {
  return (
    <div className="stats__card">
      <div className="stats__value" dir="ltr">{value ?? "-"}</div>
      <div className="stats__label">{label}</div>
      {note && <div className="stats__note">{note}</div>}
    </div>
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
  return (
    <main className="stats">
      <header className="stats__header">
        <Logo size={40} />
        <div>
          <h1>איכות ושקיפות</h1>
          <p>נתונים כלליים בלבד. אין כאן שאלות או מידע על משתמשים.</p>
        </div>
        <a className="stats__back" href="#/">חזרה לצ'אט</a>
      </header>

      {failed && <p className="stats__error">לא הצלחנו לטעון את הנתונים. נסו שוב בעוד רגע.</p>}
      {!stats && !failed && <p className="stats__loading">טוען נתונים...</p>}

      {stats && (
        <>
          <section className="stats__grid" aria-label="המידע שהצ'אט מכיר">
            <Card value={stats.pages} label="עמודים מאתר הפניקס" />
            <Card value={stats.chunks} label="קטעי טקסט במאגר" />
            <Card value={formatDate(stats.last_refresh)} label="עדכון אחרון של המידע" />
          </section>

          {scores && (
            <section className="stats__grid" aria-label="תוצאות בדיקה">
              <Card
                value={`${scores.answerable_correct}/${scores.answerable_total}`}
                label="שאלות עם תשובה באתר: נענו נכון"
                note="התשובה מצביעה על העמוד הנכון"
              />
              <Card
                value={`${scores.unanswerable_rejected}/${scores.unanswerable_total}`}
                label="שאלות בלי תשובה באתר: נדחו נכון"
                note="הצ'אט אומר שהמידע לא באתר"
              />
              <Card
                value={`${scores.retrieval_top5}/${scores.retrieval_total}`}
                label="העמוד הנכון נמצא בחמש התוצאות הראשונות"
              />
            </section>
          )}

          <p className="stats__foot">
            הבדיקה נעשתה ב-{scores ? scores.date : "-"} על 30 שאלות קבועות. זו אינדיקציה ולא הבטחה: בדיקה על
            מספר קטן של שאלות.
          </p>
        </>
      )}
    </main>
  );
}
