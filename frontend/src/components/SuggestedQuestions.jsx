import { CarIcon, HomeIcon, SupportIcon, TravelIcon } from "./Icons";
import "./SuggestedQuestions.css";

const QUESTIONS = [
  { topic: "רכב", Icon: CarIcon, text: "איך מגישים תביעה בביטוח רכב?" },
  { topic: "דירה", Icon: HomeIcon, text: "מה כולל ביטוח דירה?" },
  { topic: "נסיעות", Icon: TravelIcon, text: "מה כולל ביטוח נסיעות לחו״ל?" },
  { topic: "שירות", Icon: SupportIcon, text: "איך יוצרים קשר עם שירות הלקוחות?" },
];

export default function SuggestedQuestions({ onPick, disabled }) {
  return (
    <ul className="suggest" aria-label="שאלות מוצעות">
      {QUESTIONS.map(({ topic, Icon, text }, i) => (
        <li key={text} style={{ animationDelay: `${0.12 + i * 0.06}s` }}>
          <button type="button" className="suggest__card" disabled={disabled} onClick={() => onPick(text)}>
            <span className="suggest__topic"><Icon />{topic}</span>
            <span className="suggest__text">{text}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
