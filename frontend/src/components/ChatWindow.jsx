import { useEffect, useRef, useState } from "react";

export default function ChatWindow({
  messages,
  onSend,
  isLoading,
  starterPrompts,
  assistantName,
  placeholder,
  emptyDescription,
}) {
  const [draft, setDraft] = useState("");
  const feedRef = useRef(null);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  function handleSubmit(event) {
    event.preventDefault();
    if (!draft.trim()) {
      return;
    }
    onSend(draft);
    setDraft("");
  }

  return (
    <section className="chat-layout">
      <div className="message-feed" ref={feedRef}>
        {messages.length === 1 ? (
          <div className="empty-state">
            <div className="hero-orb">AI</div>
            <h2>How can I help you today?</h2>
            <p>{emptyDescription}</p>
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
                  <div className="message-text">{message.content}</div>
                </div>
              </>
            ) : (
              <>
                <div className="message-content user-message-content">
                  <div className="message-author">You</div>
                  <div className="message-text">{message.content}</div>
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
        <div className="composer-box">
          <div className="composer-glow" />
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={placeholder}
            rows="1"
          />
          <button type="submit" disabled={isLoading || !draft.trim()}>
            Ask
          </button>
        </div>
        <p className="composer-note">
          Responses can come from the FastAPI backend or a local fallback when the backend is offline.
        </p>
      </form>
    </section>
  );
}
