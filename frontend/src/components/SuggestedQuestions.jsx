import "./SuggestedQuestions.css";

const QUESTIONS = [
  { topic: "רכב", text: "איך מגישים תביעה בביטוח רכב?" },
  { topic: "דירה", text: "מה כולל ביטוח דירה?" },
  { topic: "נסיעות", text: "מה כולל ביטוח נסיעות לחו״ל?" },
  { topic: "בריאות", text: "מה ההבדל בין ביטוח בריאות פרטי לביטוח משלים?" },
  { topic: "שירות", text: "איך יוצרים קשר עם שירות הלקוחות?" },
];

export default function SuggestedQuestions({ onPick, disabled }) {
  return (
    <ul className="suggest" aria-label="שאלות מוצעות">
      {QUESTIONS.map((q, i) => (
        <li key={q.text} style={{ animationDelay: `${0.12 + i * 0.06}s` }}>
          <button type="button" className="suggest__card" disabled={disabled} onClick={() => onPick(q.text)}>
            <span className="suggest__topic">{q.topic}</span>
            <span className="suggest__text">{q.text}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
