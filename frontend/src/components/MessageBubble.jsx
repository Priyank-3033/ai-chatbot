function formatMessageTime(value) {
  if (!value) return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return parsed.toLocaleTimeString("en-IN", {
    hour: "numeric",
    minute: "2-digit",
  });
}

function renderInline(text, keyPrefix) {
  const nodes = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let lastIndex = 0;
  let matchIndex = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      nodes.push(<strong key={`${keyPrefix}-strong-${matchIndex}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`") && token.endsWith("`")) {
      nodes.push(<code key={`${keyPrefix}-code-${matchIndex}`}>{token.slice(1, -1)}</code>);
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        nodes.push(
          <a key={`${keyPrefix}-link-${matchIndex}`} href={linkMatch[2]} target="_blank" rel="noreferrer">
            {linkMatch[1]}
          </a>,
        );
      } else {
        nodes.push(token);
      }
    }
    lastIndex = pattern.lastIndex;
    matchIndex += 1;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function renderMarkdown(content) {
  const blocks = [];
  const pattern = /```(\w+)?\n?([\s\S]*?)```/g;
  let lastIndex = 0;
  let codeIndex = 0;
  let match;

  function pushPlainBlock(text, prefix) {
    text
      .split(/\n{2,}/)
      .map((chunk) => chunk.trim())
      .filter(Boolean)
      .forEach((chunk, blockIndex) => {
        const lines = chunk.split("\n");
        if (lines.every((line) => /^- /.test(line.trim()))) {
          blocks.push(
            <ul key={`${prefix}-ul-${blockIndex}`}>
              {lines.map((line, lineIndex) => (
                <li key={`${prefix}-li-${blockIndex}-${lineIndex}`}>{renderInline(line.replace(/^- /, ""), `${prefix}-li-inline-${lineIndex}`)}</li>
              ))}
            </ul>,
          );
          return;
        }

        if (lines.every((line) => /^\d+\.\s/.test(line.trim()))) {
          blocks.push(
            <ol key={`${prefix}-ol-${blockIndex}`}>
              {lines.map((line, lineIndex) => (
                <li key={`${prefix}-oli-${blockIndex}-${lineIndex}`}>{renderInline(line.replace(/^\d+\.\s/, ""), `${prefix}-oli-inline-${lineIndex}`)}</li>
              ))}
            </ol>,
          );
          return;
        }

        blocks.push(
          <p key={`${prefix}-p-${blockIndex}`}>
            {lines.map((line, lineIndex) => (
              <span key={`${prefix}-line-${blockIndex}-${lineIndex}`}>
                {renderInline(line, `${prefix}-inline-${lineIndex}`)}
                {lineIndex < lines.length - 1 ? <br /> : null}
              </span>
            ))}
          </p>,
        );
      });
  }

  while ((match = pattern.exec(content)) !== null) {
    if (match.index > lastIndex) {
      pushPlainBlock(content.slice(lastIndex, match.index), `plain-${codeIndex}`);
    }
    blocks.push(
      <pre key={`code-${codeIndex}`} className="markdown-code-block">
        <code>{match[2].trim()}</code>
      </pre>,
    );
    lastIndex = pattern.lastIndex;
    codeIndex += 1;
  }

  if (lastIndex < content.length) {
    pushPlainBlock(content.slice(lastIndex), `tail-${codeIndex}`);
  }

  return blocks;
}

export default function MessageBubble({ message, role, assistantName }) {
  const resolvedRole = role || message.role;

  return (
    <div className={`message-row ${resolvedRole}`}>
      {resolvedRole === "assistant" ? (
        <>
          <div className="avatar">AI</div>
          <div className="message-content">
            <div className="message-author">{assistantName}</div>
            <div className="message-text markdown-content">{renderMarkdown(message.content)}</div>
            {message.created_at ? <div className="message-timestamp">{formatMessageTime(message.created_at)}</div> : null}
          </div>
        </>
      ) : (
        <>
          <div className="message-content user-message-content">
            <div className="message-author">You</div>
            <div className="message-text markdown-content">{renderMarkdown(message.content)}</div>
            {message.created_at ? <div className="message-timestamp user">{formatMessageTime(message.created_at)}</div> : null}
          </div>
          <div className="avatar">You</div>
        </>
      )}
    </div>
  );
}
