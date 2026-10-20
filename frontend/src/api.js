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

/** The error shown for a failed request: 429/503 = busy, 422 = bad question, anything else = our fault. */
function errorForStatus(status, detail = "") {
  if (status === 429 || status === 503) {
    return new ChatError(detail || "השירות עמוס כרגע, נסו שוב בעוד כמה דקות.", true);
  }
  if (status === 422) {
    return new ChatError("לא ניתן לשלוח את השאלה. נסו לקצר אותה או לנסח מחדש.", false);
  }
  return new ChatError("משהו השתבש בצד שלנו. נסו שוב.", true);
}

/** Post the question to `path`. Returns the response if it is OK, otherwise throws a ChatError. */
async function post(path, question, history) {
  const body = {
    question,
    history: history.slice(-MAX_HISTORY_ITEMS).map((m) => ({
      role: m.role,
      content: m.content.slice(0, MAX_MESSAGE_CHARS),
    })),
  };

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    throw new ChatError("אין חיבור לשרת. בדקו את החיבור ונסו שוב.", true);
  }

  if (response.ok) return response;

  let detail = "";
  try {
    const data = await response.json();
    if (typeof data.detail === "string") detail = data.detail;
  } catch {
    // body was not JSON; use the fallback messages below
  }

  throw errorForStatus(response.status, detail);
}

/** Send one question plus the earlier messages. Returns { answer, source_url, source_title, found }. */
export async function sendChat(question, history) {
  const response = await post("/chat", question, history);
  return response.json();
}

/**
 * Like sendChat, but the answer arrives in pieces. `onDelta(text)` is called for every piece,
 * and the final { answer, source_url, source_title, found } is returned (it replaces the pieces).
 */
export async function streamChat(question, history, onDelta) {
  const response = await post("/chat/stream", question, history);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let final = null;

  const handle = (line) => {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    if (event.type === "delta") onDelta(event.text);
    else if (event.type === "final") final = event;
    else if (event.type === "error") throw errorForStatus(event.status);
  };

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // the last piece may be half a line
      lines.forEach(handle);
    }
    handle(buffer);
  } catch (e) {
    if (e instanceof ChatError) throw e;
    throw new ChatError("החיבור לשרת נותק באמצע התשובה. נסו שוב.", true);
  }

  if (!final) throw new ChatError("החיבור לשרת נותק באמצע התשובה. נסו שוב.", true);
  return final;
}
