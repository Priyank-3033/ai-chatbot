import { useEffect, useMemo, useRef, useState } from "react";

export default function ChatInput({
  onSend,
  isLoading,
  placeholder,
  focusSignal,
}) {
  const [draft, setDraft] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const fileInputRef = useRef(null);
  const recognitionRef = useRef(null);
  const textAreaRef = useRef(null);

  const speechSupported = useMemo(() => {
    return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition);
  }, []);

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
    if (!draft.trim() && attachments.length === 0) return;
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
    <form className="composer-wrap" onSubmit={handleSubmit}>
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
    </form>
  );
}
