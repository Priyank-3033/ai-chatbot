import { useEffect, useRef } from "react";

import ChatInput from "./ChatInput";
import Loader from "./Loader";
import MessageBubble from "./MessageBubble";

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
  const feedRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

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
          <MessageBubble
            key={`${message.role}-${index}-${message.created_at || ""}`}
            message={message}
            assistantName={assistantName}
            active={Boolean(typingMessageKey && index === messages.length - 1)}
          />
        ))}

        {isLoading ? (
          <div className="message-row assistant">
            <div className="avatar">AI</div>
            <div className="message-content">
              <div className="message-author">{assistantName}</div>
              <Loader />
            </div>
          </div>
        ) : null}
        <div ref={endRef} />
      </div>

      <ChatInput
        onSend={onSend}
        isLoading={isLoading}
        placeholder={placeholder}
        memoryItems={memoryItems}
        memoryTrail={memoryTrail}
        focusSignal={focusSignal}
      />
    </section>
  );
}




