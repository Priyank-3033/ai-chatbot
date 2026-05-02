import ReactMarkdown from "react-markdown";

function CodeBlock({ inline, children }) {
  const content = String(children || "").replace(/\n$/, "");

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(content);
    } catch {
      // ignore clipboard failures
    }
  }

  if (inline) {
    return <code>{children}</code>;
  }

  return (
    <div className="markdown-code-shell">
      <button type="button" className="markdown-copy-button" onClick={handleCopy}>
        Copy
      </button>
      <pre className="markdown-code-block">
        <code>{children}</code>
      </pre>
    </div>
  );
}

function formatMessageTime(value) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleTimeString("en-IN", {
    hour: "numeric",
    minute: "2-digit",
  });
}

const markdownComponents = {
  p({ children }) {
    return <p className="markdown-paragraph">{children}</p>;
  },
  ul({ children }) {
    return <ul className="markdown-list">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="markdown-list markdown-list-ordered">{children}</ol>;
  },
  li({ children }) {
    return <li>{children}</li>;
  },
  a({ href, children }) {
    return (
      <a href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    );
  },
  code({ inline, children }) {
    return <CodeBlock inline={inline}>{children}</CodeBlock>;
  },
};

export default function MessageBubble({ message, role, assistantName }) {
  const resolvedRole = role || message.role;

  return (
    <div className={`message-row ${resolvedRole}`}>
      <div className={`message-content flat-message-shell ${resolvedRole === "user" ? "user-message-content" : "assistant-message-content"}`}>
        <div className="message-author">{resolvedRole === "assistant" ? assistantName : "You"}</div>
        <div className="message-text markdown-content">
          <ReactMarkdown components={markdownComponents}>{message.content || ""}</ReactMarkdown>
        </div>
        {message.created_at ? <div className={`message-timestamp ${resolvedRole === "user" ? "user" : ""}`}>{formatMessageTime(message.created_at)}</div> : null}
      </div>
    </div>
  );
}
