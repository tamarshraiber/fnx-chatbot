import "./RichText.css";

const TOKEN = /(\*\*[^*]+\*\*|https?:\/\/[^\s<]+)/g;
const LIST_ITEM = /^\s*(?:([-*•])|(\d+[.)]))\s+(.*)$/;

/** Turn **bold** and links inside one line into React nodes. No raw HTML is ever inserted. */
function inline(text) {
  return text.split(TOKEN).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    if (/^https?:\/\//.test(part)) {
      const url = part.replace(/[.,;:!?)]+$/, "");
      const tail = part.slice(url.length);
      return (
        <span key={i}>
          <a href={url} target="_blank" rel="noopener noreferrer" dir="ltr">{url}</a>
          {tail}
        </span>
      );
    }
    return part;
  });
}

/** Split the answer into paragraphs and bullet / numbered lists. */
function toBlocks(text) {
  const blocks = [];
  for (const line of text.replace(/\r/g, "").split("\n")) {
    if (!line.trim()) {
      blocks.push(null);
      continue;
    }
    const item = line.match(LIST_ITEM);
    const last = blocks[blocks.length - 1];
    if (item) {
      const ordered = Boolean(item[2]);
      if (last && last.type === "list" && last.ordered === ordered) last.items.push(item[3]);
      else blocks.push({ type: "list", ordered, items: [item[3]] });
    } else if (last && last.type === "p") {
      last.lines.push(line);
    } else {
      blocks.push({ type: "p", lines: [line] });
    }
  }
  return blocks.filter(Boolean);
}

export default function RichText({ text }) {
  return (
    <div className="rich">
      {toBlocks(text).map((block, i) => {
        if (block.type === "list") {
          const Tag = block.ordered ? "ol" : "ul";
          return (
            <Tag key={i}>
              {block.items.map((item, j) => <li key={j} dir="auto">{inline(item)}</li>)}
            </Tag>
          );
        }
        return (
          <p key={i} dir="auto">
            {block.lines.map((line, j) => (
              <span key={j}>{j > 0 && <br />}{inline(line)}</span>
            ))}
          </p>
        );
      })}
    </div>
  );
}
