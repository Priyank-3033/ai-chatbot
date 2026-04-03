import { WS_BASE_URL } from "../services/apiClient";

function buildAttachmentContext(attachments) {
  if (!attachments?.length) return "";
  const lines = attachments.map((attachment) => {
    const intro = `- ${attachment.name} (${attachment.kind || attachment.type || "file"})`;
    if (attachment.preview) {
      return `${intro}\nPreview:\n\`\`\`\n${attachment.preview}\n\`\`\``;
    }
    return intro;
  });
  return `\n\nAttached files:\n${lines.join("\n")}`;
}

function buildSourceText(sources, mode) {
  if (!sources || sources.length === 0 || mode !== "support") return "";
  return `\n\nSources:\n${sources.map((source) => `- ${source.title}: ${source.snippet}`).join("\n")}`;
}

function sendMessageRealtime({
  token,
  activeMode,
  activeSessionId,
  selectedModel,
  activePrompt,
  optimisticMessages,
  question,
  history,
  setMessages,
}) {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(`${WS_BASE_URL}/ws/chat?token=${encodeURIComponent(token)}`);
    let receivedStart = false;
    let streamedContent = "";
    let responseSessionId = activeSessionId;

    socket.onopen = () => {
      socket.send(
        JSON.stringify({
          question,
          mode: activeMode,
          session_id: activeSessionId,
          history,
          model: selectedModel,
          custom_prompt: activePrompt.trim() || null,
        }),
      );
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "start") {
        receivedStart = true;
        responseSessionId = data.session_id || responseSessionId;
        setMessages(optimisticMessages);
        return;
      }
      if (data.type === "chunk") {
        streamedContent += data.content || "";
        setMessages((current) => {
          const next = [...current];
          if (!next.length || next[next.length - 1].role !== "assistant") {
            next.push({ role: "assistant", content: streamedContent });
          } else {
            next[next.length - 1] = { ...next[next.length - 1], content: streamedContent };
          }
          return next;
        });
        return;
      }
      if (data.type === "done") {
        socket.close();
        resolve({
          sessionId: responseSessionId,
          content: `${data.content || streamedContent}${buildSourceText(data.sources, activeMode)}`,
        });
        return;
      }
      if (data.type === "error") {
        socket.close();
        reject(new Error(data.message || "Realtime chat failed."));
      }
    };

    socket.onerror = () => {
      if (!receivedStart) {
        reject(new Error("Realtime chat unavailable."));
      }
    };

    socket.onclose = () => {
      if (!receivedStart && streamedContent.length === 0) {
        reject(new Error("Realtime chat unavailable."));
      }
    };
  });
}

export function useChat({
  apiClient,
  token,
  activeMode,
  activeSessionId,
  activePrompt,
  selectedModel,
  isLoading,
  setIsLoading,
  messages,
  setMessages,
  openSession,
  refreshSessions,
  fetchDocuments,
  setActivePanel,
  setShowAiSettings,
  setPageError,
  buildFallbackReply,
  setTypingMessageKey,
}) {
  async function sendMessage(input) {
    const payload = typeof input === "string" ? { text: input, attachments: [] } : input || {};
    const question = (payload.text || "").trim();
    const attachments = payload.attachments || [];
    const uploadableAttachments = attachments.filter((attachment) => attachment.rawFile);

    if (uploadableAttachments.length) {
      try {
        await Promise.all(
          uploadableAttachments.map((attachment) => {
            const formData = new FormData();
            formData.append("file", attachment.rawFile);
            return apiClient.formRequest("/api/documents", formData);
          }),
        );
        await fetchDocuments();
      } catch (error) {
        setPageError(error instanceof Error ? error.message : "Unable to upload file.");
      }
    }

    const attachmentContext = buildAttachmentContext(attachments);
    const visibleQuestion = question || (attachments.length ? "Please check the attached file and help me with it." : "");
    const composedQuestion = `${visibleQuestion}${attachmentContext}`.trim();
    if (!composedQuestion || isLoading || !activeSessionId) return;

    setActivePanel("chat");
    setShowAiSettings(false);
    const optimisticMessages = [...messages, { role: "user", content: composedQuestion }];
    setMessages(optimisticMessages);
    setIsLoading(true);
    setPageError("");

    try {
      try {
        const wsData = await sendMessageRealtime({
          token,
          activeMode,
          activeSessionId,
          selectedModel,
          activePrompt,
          optimisticMessages: [...optimisticMessages, { role: "assistant", content: "" }],
          question: composedQuestion,
          history: messages.map((message) => ({ role: message.role, content: message.content })),
          setMessages,
        });
        const detail = await openSession(wsData.sessionId, token, activeMode);
        const nextMessages = detail.messages.map((message, index) =>
          index === detail.messages.length - 1 && message.role === "assistant"
            ? { ...message, content: wsData.content }
            : message,
        );
        setMessages(nextMessages);
        await refreshSessions();
      } catch {
        const data = await apiClient.request("/api/chat", {
          method: "POST",
          body: {
            question: composedQuestion,
            history: messages.map((message) => ({ role: message.role, content: message.content })),
            mode: activeMode,
            session_id: activeSessionId,
            model: selectedModel,
            custom_prompt: activePrompt.trim() || null,
          },
        });
        const detail = await openSession(data.session_id, token, activeMode);
        const nextMessages = detail.messages.map((message, index) =>
          index === detail.messages.length - 1 && message.role === "assistant"
            ? { ...message, content: `${message.content}${buildSourceText(data.sources, activeMode)}` }
            : message,
        );
        setMessages(nextMessages);
        const lastAssistant = [...nextMessages].reverse().find((message) => message.role === "assistant");
        setTypingMessageKey(lastAssistant ? `${detail.id}-${lastAssistant.content.length}-${Date.now()}` : "");
        await refreshSessions();
      }
    } catch {
      const fallbackContent = buildFallbackReply(visibleQuestion, activeMode);
      setMessages([...optimisticMessages, { role: "assistant", content: fallbackContent }]);
      setTypingMessageKey(`fallback-${Date.now()}-${fallbackContent.length}`);
    } finally {
      setIsLoading(false);
    }
  }

  return {
    sendMessage,
  };
}
