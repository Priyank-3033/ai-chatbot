import { create } from "zustand";

export const useChatStore = create((set) => ({
  messages: [],
  isLoading: false,
  typingMessageKey: "",
  setMessages: (messages) => set({ messages }),
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),
  setIsLoading: (value) => set({ isLoading: value }),
  setTypingMessageKey: (value) => set({ typingMessageKey: value }),
  clearChat: () =>
    set({
      messages: [],
      isLoading: false,
      typingMessageKey: "",
    }),
}));
