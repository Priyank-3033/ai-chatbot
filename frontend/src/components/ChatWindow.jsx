import { useEffect, useMemo, useRef, useState } from "react";

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

function AnimatedAssistantMessage({ content, active }) {
  const [visible, setVisible] = useState(active ? "" : content);

  useEffect(() => {
    if (!active) {
      setVisible(content);
      return;
    }

    setVisible("");
    let frame = 0;
    const step = Math.max(2, Math.ceil(content.length / 60));
    const timer = window.setInterval(() => {
      frame += step;
      const nextValue = content.slice(0, frame);
      setVisible(nextValue);
      if (frame >= content.length) {
        window.clearInterval(timer);
      }
    }, 14);

    return () => window.clearInterval(timer);
  }, [content, active]);

  return <div className="message-text markdown-content">{renderMarkdown(visible)}</div>;
}

export default function ChatWindow({
  messages,
  onSend,
  isLoading,
  starterPrompts,
  assistantName,
  placeholder,
  emptyDescription,
  memoryItems = [],
  memoryTrail = [],
  typingMessageKey = "",
  focusSignal = "",
}) {
  const [draft, setDraft] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const feedRef = useRef(null);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);
  const textAreaRef = useRef(null);

  const speechSupported = useMemo(() => {
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  }, []);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  useEffect(() => {
    if (!textAreaRef.current) return;
    textAreaRef.current.style.height = "0px";
    textAreaRef.current.style.height = `${Math.min(textAreaRef.current.scrollHeight, 180)}px`;
  }, [draft]);

  useEffect(() => {
    if (!textAreaRef.current) return;
    const frame = window.requestAnimationFrame(() => {
      textAreaRef.current?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [focusSignal]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  function submitDraft() {
    if (!draft.trim() && attachments.length === 0) {
      return;
    }
    onSend({ text: draft, attachments });
    setDraft("");
    setAttachments([]);
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitDraft();
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submitDraft();
    }
  }

  async function handleFileChange(event) {
    const nextFiles = Array.from(event.target.files || []);
    if (nextFiles.length === 0) return;

    const parsedFiles = await Promise.all(
      nextFiles.map(
        (file) =>
          new Promise((resolve) => {
            const textLike = /text|json|javascript|typescript|xml/.test(file.type) || /\.(txt|md|js|jsx|ts|tsx|json|py|java|html|css|csv)$/i.test(file.name);
            if (!textLike) {
              resolve({
                name: file.name,
                type: file.type || "file",
                kind: file.type.startsWith("image/") ? "image" : "file",
                size: file.size,
                preview: "",
                rawFile: file,
              });
              return;
            }

            const reader = new FileReader();
            reader.onload = () => {
              resolve({
                name: file.name,
                type: file.type || "text/plain",
                kind: "text",
                size: file.size,
                preview: String(reader.result || "").slice(0, 1400),
                rawFile: file,
              });
            };
            reader.onerror = () => {
              resolve({
                name: file.name,
                type: file.type || "file",
                kind: "file",
                size: file.size,
                preview: "",
                rawFile: file,
              });
            };
            reader.readAsText(file);
          }),
      ),
    );

    setAttachments((current) => [...current, ...parsedFiles]);
    event.target.value = "";
  }

  function removeAttachment(name) {
    setAttachments((current) => current.filter((attachment) => attachment.name !== name));
  }

  function toggleVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.interimResults = true;
    recognition.continuous = false;
    const baseDraft = draft ? `${draft.trim()} ` : "";

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map((result) => result[0]?.transcript || "")
        .join(" ")
        .trim();
      setDraft(`${baseDraft}${transcript}`.trim());
    };

    recognition.onend = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognition.onerror = () => {
      setIsListening(false);
      recognitionRef.current = null;
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }

  return (
    <section className="chat-layout">
      <div className="message-feed" ref={feedRef}>
        {messages.length === 1 ? (
          <div className="empty-state">
            <div className="hero-orb">AI</div>
            <h2>How can I help you today?</h2>
            <p>{emptyDescription}</p>
            {memoryItems.length ? (
              <div className="memory-strip">
                <span className="memory-label">Memory</span>
                {memoryItems.map((item) => (
                  <span key={item} className="memory-chip">
                    {item}
                  </span>
                ))}
              </div>
            ) : null}
            <div className="prompt-grid">
              {starterPrompts.map((prompt) => (
                <button key={prompt} className="prompt-card" onClick={() => onSend(prompt)}>
                  <span className="prompt-title">{prompt}</span>
                  <span className="prompt-meta">Try this prompt</span>
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`message-row ${message.role}`}>
            {message.role === "assistant" ? (
              <>
                <div className="avatar">AI</div>
                <div className="message-content">
                  <div className="message-author">{assistantName}</div>
                  <AnimatedAssistantMessage content={message.content} active={typingMessageKey && index === messages.length - 1} />
                </div>
              </>
            ) : (
              <>
                <div className="message-content user-message-content">
                  <div className="message-author">You</div>
                  <div className="message-text markdown-content">{renderMarkdown(message.content)}</div>
                </div>
                <div className="avatar">You</div>
              </>
            )}
          </div>
        ))}

        {isLoading ? (
          <div className="message-row assistant">
            <div className="avatar">AI</div>
            <div className="message-content">
              <div className="message-author">{assistantName}</div>
              <div className="typing-indicator">
                <span />
                <span />
                <span />
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <form className="composer-wrap" onSubmit={handleSubmit}>
        {memoryItems.length ? (
          <div className="memory-row">
            <span className="memory-label">Memory active</span>
            {memoryItems.map((item) => (
              <span key={`memory-${item}`} className="memory-chip">
                {item}
              </span>
            ))}
          </div>
        ) : null}
        {memoryTrail.length ? (
          <div className="memory-row memory-trail-row">
            <span className="memory-label">Recent context</span>
            {memoryTrail.map((item, index) => (
              <span key={`trail-${index}`} className="memory-chip memory-trail-chip">
                {item}
              </span>
            ))}
          </div>
        ) : null}
        {attachments.length ? (
          <div className="attachment-row">
            {attachments.map((attachment) => (
              <div key={attachment.name} className="attachment-chip">
                <span>{attachment.name}</span>
                <button type="button" onClick={() => removeAttachment(attachment.name)}>
                  x
                </button>
              </div>
            ))}
          </div>
        ) : null}
        <div className="composer-box">
          <div className="composer-glow" />
          <textarea
            ref={textAreaRef}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows="1"
          />
          <div className="composer-actions">
            <input ref={fileInputRef} type="file" className="file-input" multiple onChange={handleFileChange} />
            <button type="button" className="composer-icon-button secondary" onClick={() => fileInputRef.current?.click()}>
              +
            </button>
            <button type="button" className={`composer-icon-button secondary ${isListening ? "active" : ""}`} onClick={toggleVoiceInput} disabled={!speechSupported}>
              {isListening ? "On" : "Mic"}
            </button>
            <button type="submit" disabled={isLoading || (!draft.trim() && attachments.length === 0)}>
            Ask
            </button>
          </div>
        </div>
        <p className="composer-note">
          Responses can come from the FastAPI backend or a local fallback when the backend is offline.
        </p>
      </form>
    </section>
  );
}

