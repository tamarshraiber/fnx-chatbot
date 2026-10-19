import Logo from "./Logo";
import SuggestedQuestions from "./SuggestedQuestions";
import "./Hero.css";

export default function Hero({ onPick, disabled, compact }) {
  return (
    <div className={`hero ${compact ? "hero--compact" : ""}`}>
      <div className="hero__mark" aria-hidden="true">
        <span className="hero__glow" />
        <Logo size={compact ? 56 : 80} />
      </div>
      <h1 className="hero__title">
        איך אפשר <span className="hero__accent">לעזור</span> היום?
      </h1>
      <p className="hero__lead">
        שאלו אותי על ביטוח רכב, דירה, בריאות, נסיעות ותביעות. התשובות מבוססות על תוכן אתר הפניקס.
      </p>
      <SuggestedQuestions onPick={onPick} disabled={disabled} />
    </div>
  );
}
