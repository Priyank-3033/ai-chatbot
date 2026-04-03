import { create } from "zustand";

export const useChatStore = create((set) => ({
  messages: [],
  sessions: [],
  activeSessionId: null,
  isLoading: false,
  typingMessageKey: "",
  setMessages: (messages) =>
    set((state) => ({
      messages: typeof messages === "function" ? messages(state.messages) : messages,
    })),
  setSessions: (sessions) =>
    set((state) => ({
      sessions: typeof sessions === "function" ? sessions(state.sessions) : sessions,
    })),
  setActiveSessionId: (activeSessionId) =>
    set((state) => ({
      activeSessionId: typeof activeSessionId === "function" ? activeSessionId(state.activeSessionId) : activeSessionId,
    })),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  setIsLoading: (value) => set({ isLoading: value }),
  setTypingMessageKey: (value) => set({ typingMessageKey: value }),
  clearChat: () =>
    set({
      messages: [],
      sessions: [],
      activeSessionId: null,
      isLoading: false,
      typingMessageKey: "",
    }),
}));
