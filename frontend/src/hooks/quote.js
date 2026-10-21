/** The longest piece of an answer that can be quoted. The whole question, quote included, may be 500 characters. */
export const QUOTE_MAX = 200;

/** Shorten a selected text to the quote limit (with "…" if it was cut). */
export function shortenQuote(text) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  return clean.length > QUOTE_MAX ? `${clean.slice(0, QUOTE_MAX - 1).trimEnd()}…` : clean;
}

/** What goes before the person's own question when they ask about a quoted piece of an answer. */
export function quotePrefix(quote) {
  return quote ? `בהקשר לקטע מהתשובה: «${quote}». ` : "";
}

/** The full question the server receives. */
export function composeQuestion(question, quote) {
  return `${quotePrefix(quote)}${question}`;
}
