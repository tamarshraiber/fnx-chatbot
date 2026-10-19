const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

export const MAX_QUESTION_CHARS = 500; // same limit as the backend
const MAX_HISTORY_ITEMS = 20;
const MAX_MESSAGE_CHARS = 2000;

/** An error with a Hebrew message that is safe to show, and a flag saying if retrying makes sense. */
export class ChatError extends Error {
  constructor(message, canRetry) {
    super(message);
    this.canRetry = canRetry;
  }
}

/** Send one question plus the earlier messages. Returns { answer, source_url, source_title, found }. */
export async function sendChat(question, history) {
  const body = {
    question,
    history: history.slice(-MAX_HISTORY_ITEMS).map((m) => ({
      role: m.role,
      content: m.content.slice(0, MAX_MESSAGE_CHARS),
    })),
  };

  let response;
  try {
    response = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ChatError("אין חיבור לשרת. בדקו את החיבור ונסו שוב.", true);
  }

  if (response.ok) return response.json();

  let detail = "";
  try {
    const data = await response.json();
    if (typeof data.detail === "string") detail = data.detail;
  } catch {
    // body was not JSON; use the fallback messages below
  }

  if (response.status === 429 || response.status === 503) {
    throw new ChatError(detail || "השירות עמוס כרגע, נסו שוב בעוד כמה דקות.", true);
  }
  if (response.status === 422) {
    throw new ChatError("לא ניתן לשלוח את השאלה. נסו לקצר אותה או לנסח מחדש.", false);
  }
  throw new ChatError("משהו השתבש בצד שלנו. נסו שוב.", true);
}
