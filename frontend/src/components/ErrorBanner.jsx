import { RetryIcon } from "./Icons";
import "./ErrorBanner.css";

export default function ErrorBanner({ error, onRetry }) {
  return (
    <div className="error" role="alert">
      <span className="error__text">{error.message}</span>
      {error.canRetry && (
        <button type="button" className="error__retry" onClick={onRetry}>
          <RetryIcon />
          נסו שוב
        </button>
      )}
    </div>
  );
}
