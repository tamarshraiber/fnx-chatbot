import { ExternalIcon } from "./Icons";
import "./SourceCard.css";

/** Show the page address in a readable way: domain, plus the decoded path. */
function describe(url) {
  try {
    const u = new URL(url);
    let path = u.pathname.replace(/\/$/, "");
    try {
      path = decodeURIComponent(path);
    } catch {
      // keep the raw path
    }
    return { host: u.hostname.replace(/^www\./, ""), path };
  } catch {
    return { host: url, path: "" };
  }
}

/** The link text is the page title. Without a title, we fall back to the readable address. */
export default function SourceCard({ url, title }) {
  const { host, path } = describe(url);
  return (
    <a className="source" href={url} target="_blank" rel="noopener noreferrer">
      <span className="source__label">מקור באתר</span>
      {title ? (
        <span className="source__url source__url--title" dir="auto">{title}</span>
      ) : (
        <span className="source__url" dir="ltr">{host}{path}</span>
      )}
      <span className="source__arrow"><ExternalIcon /></span>
    </a>
  );
}
