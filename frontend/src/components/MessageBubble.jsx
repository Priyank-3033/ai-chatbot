import ReactMarkdown from "react-markdown";

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
    if (inline) {
      return <code>{children}</code>;
    }
    return (
      <pre className="markdown-code-block">
        <code>{children}</code>
      </pre>
    );
  },
};

export default function MessageBubble({ message, role, assistantName }) {
  const resolvedRole = role || message.role;

  return (
    <div className={`message-row ${resolvedRole}`}>
      {resolvedRole === "assistant" ? (
        <>
          <div className="avatar">AI</div>
          <div className="message-content">
            <div className="message-author">{assistantName}</div>
            <div className="message-text markdown-content">
              <ReactMarkdown components={markdownComponents}>{message.content || ""}</ReactMarkdown>
            </div>
            {message.created_at ? <div className="message-timestamp">{formatMessageTime(message.created_at)}</div> : null}
          </div>
        </>
      ) : (
        <>
          <div className="message-content user-message-content">
            <div className="message-author">You</div>
            <div className="message-text markdown-content">
              <ReactMarkdown components={markdownComponents}>{message.content || ""}</ReactMarkdown>
            </div>
            {message.created_at ? <div className="message-timestamp user">{formatMessageTime(message.created_at)}</div> : null}
          </div>
          <div className="avatar">You</div>
        </>
      )}
    </div>
  );
}
