import { useEffect, useMemo, useState } from "react";
import AdminPanel from "./components/AdminPanel";
import ChatWindow from "./components/ChatWindow";
import CommerceSidebar from "./components/CommerceSidebar";
import ProductDetailModal from "./components/ProductDetailModal";
import ProductStorefront from "./components/ProductStorefront";
import { useChat } from "./hooks/useChat";
import { API_BASE_URL, createApiClient } from "./services/apiClient";
import { useChatStore } from "./store/chatStore";

const TOKEN_KEY = "smart-chat-token-v1";
const MODE_KEY = "smart-chat-mode-v1";
const MODEL_KEY = "smart-chat-model-v1";
const PROVIDER_HINT_KEY = "smart-chat-provider-v1";
const THEME_KEY = "smart-chat-theme-v1";
const PROMPT_KEY = "smart-chat-custom-prompt-v4";
const PROMPT_TEMPLATES_KEY = "smart-chat-prompt-templates-v1";
const ACCURATE_MODE_KEY_PREFIX = "smart-chat-accurate-mode-v1";
const ORDER_FLOW = ["Placed", "Packed", "Shipped", "Out for Delivery", "Delivered"];
const HIDDEN_PRODUCT_NAMES = new Set(["Astra Forge 15", "Volt Tab Max"]);
const PRODUCT_PAGE_SIZE = 12;
const MODEL_OPTIONS = [
  { value: "gpt-4o-mini", label: "gpt-4o-mini", meta: "OpenAI · cheap + fast" },
  { value: "gpt-4o", label: "gpt-4o", meta: "OpenAI · powerful" },
  { value: "gemini-2.5-flash", label: "gemini-2.5-flash", meta: "Gemini · fast + smart" },
  { value: "gemini-2.5-pro", label: "gemini-2.5-pro", meta: "Gemini · strongest" },
];
const DEFAULT_GENERAL_PROMPT = `You are Smart AI, a powerful assistant that should feel natural, capable, trustworthy, and genuinely useful.

Main goal:
- Give the best helpful answer you can
- Be accurate, clear, practical, and direct
- Sound natural, not robotic

Core rules:
- Never invent facts, policies, or outcomes
- If you are unsure, clearly say "I don't know"
- Do not guess
- Ask one short clarification question only when truly needed
- Prefer usefulness and correctness over sounding formal
- Use any relevant conversation or document context carefully
- If the answer is not known, say "I don't know"

How to answer:
- Start with the answer
- Use simple language unless the user asks for something technical
- Be concise for simple questions and fuller for important ones
- Use bullets or short sections only when they actually help
- Do not force the same format every time
- For comparisons, recommend the best option first, then explain why
- For advice, give the practical next step

Special instructions:
- For coding: give complete working code
- For debugging: explain the likely issue and the cleanest fix
- For facts: be careful and precise
- For support: be calm, clear, and solution-focused`;
const DEFAULT_SUPPORT_PROMPT = `You are Smart AI in support mode, a reliable and thoughtful support assistant.

Your responsibilities:
- Provide correct, helpful, and clear answers
- Use only the provided context when available
- Do not guess or hallucinate information

Decision rules:
1. If answer is fully in context, answer confidently
2. If answer is partially in context, answer and mention the limitation
3. If answer is not in context, say: "I don’t have enough information to answer that accurately."
4. If the question is unclear, ask a short follow-up question

Behavior:
- Be polite, professional, and friendly
- Keep answers short and simple
- Stay within support-related topics only
- Accuracy is more important than completeness`;
const PROMPT_PRESETS = {
  accuracy: {
    label: "Accuracy",
    text: DEFAULT_GENERAL_PROMPT,
  },
  coding: {
    label: "Coding",
    text: "You are a strong coding assistant.\n- If the user asks for code, give complete working code first\n- Keep the code runnable and clean\n- After the code, explain only what is useful\n- For beginner questions, use simple examples\n- For bugs, explain the likely cause and then give the fix\n- Do not ask unnecessary follow-up questions for simple coding requests",
  },
  support: {
    label: "Support",
    text: "You are a highly accurate AI customer support assistant.\n- Answer only from the provided context when it is relevant\n- Do not guess or hallucinate\n- If the answer is not in context, say: \"I don’t have enough information to answer that accurately.\"\n- If the question is unclear, ask one short follow-up question\n- If the question is unrelated, say: \"I can only help with support-related questions.\"\n- Be polite, short, professional, friendly, and natural\n- Give the direct answer first, then one short next step if needed",
  },
  interview: {
    label: "Interview",
    text: "You are an interview preparation assistant.\n- Give strong interview-ready answers\n- Sound confident but natural\n- Use simple professional language\n- Give the best answer first\n- Include the key points the user should say\n- Keep answers practical, realistic, and easy to speak aloud",
  },
  teacher: {
    label: "Teacher",
    text: "You are a friendly teacher.\n- Explain in simple language\n- Break difficult topics into easy steps\n- Use examples\n- Keep the answer clear and beginner-friendly\n- Avoid unnecessary jargon\n- Start with the simplest explanation before going deeper",
  },
};

function loadPromptState() {
  const saved = window.localStorage.getItem(PROMPT_KEY);
  if (!saved) {
    return {
      general: DEFAULT_GENERAL_PROMPT,
      support: DEFAULT_SUPPORT_PROMPT,
    };
  }
  try {
    const parsed = JSON.parse(saved);
    return {
      general: typeof parsed.general === "string" && parsed.general.trim() ? parsed.general : DEFAULT_GENERAL_PROMPT,
      support: typeof parsed.support === "string" && parsed.support.trim() ? parsed.support : DEFAULT_SUPPORT_PROMPT,
    };
  } catch {
    return {
      general: DEFAULT_GENERAL_PROMPT,
      support: DEFAULT_SUPPORT_PROMPT,
    };
  }
}

function loadPromptTemplates() {
  const saved = window.localStorage.getItem(PROMPT_TEMPLATES_KEY);
  if (!saved) return [];
  try {
    const parsed = JSON.parse(saved);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item) => item && typeof item.name === "string" && typeof item.text === "string").slice(0, 12);
  } catch {
    return [];
  }
}

function getAccurateModeStorageKey(email) {
  return `${ACCURATE_MODE_KEY_PREFIX}:${String(email || "").toLowerCase()}`;
}

function loadAccurateMode(email) {
  if (!email) return false;
  return window.localStorage.getItem(getAccurateModeStorageKey(email)) === "true";
}

function saveAccurateMode(email, enabled) {
  if (!email) return;
  window.localStorage.setItem(getAccurateModeStorageKey(email), enabled ? "true" : "false");
}

const MODE_CONFIG = {
  general: {
    title: "Smart AI assistant",
    subtitle: "One AI that can help with shopping, ecommerce problems, support questions, and everyday real-life decisions.",
    starterPrompts: [
      "Best phone under 20000 for camera",
      "My order is delayed. What should I do?",
      "Help me plan a study schedule for exams",
      "I need to choose between two job offers",
    ],
  },
  support: {
    title: "Smart AI assistant",
    subtitle: "One AI that can help with shopping, ecommerce problems, support questions, and everyday real-life decisions.",
    starterPrompts: [
      "How do I reset my password?",
      "What is your refund policy?",
      "My login OTP is not working.",
      "Can I change my shipping address after ordering?",
    ],
  },
};

function evaluateSimpleMath(question) {
  const compact = question.replace(/\s+/g, "").replace(/x/gi, "*");
  if (!/^[\d.+\-*/()]+$/.test(compact)) return null;
  try {
    // eslint-disable-next-line no-new-func
    const result = Function(`"use strict"; return (${compact});`)();
    if (typeof result !== "number" || !Number.isFinite(result)) return null;
    return Number.isInteger(result) ? result : Number(result.toFixed(4));
  } catch {
    return null;
  }
}

function evaluatePercent(question) {
  const match = question.trim().toLowerCase().match(/^(\d+(?:\.\d+)?)%\s+of\s+(\d+(?:\.\d+)?)$/);
  if (!match) return null;
  const result = (Number(match[1]) / 100) * Number(match[2]);
  return Number.isInteger(result) ? result : Number(result.toFixed(4));
}

function evaluateSimpleConversion(question) {
  const lowered = question.trim().toLowerCase();
  const conversions = {
    "km:m": 1000,
    "m:cm": 100,
    "cm:mm": 10,
    "kg:g": 1000,
    "hour:minutes": 60,
    "hours:minutes": 60,
    "minute:seconds": 60,
    "minutes:seconds": 60,
  };
  const match = lowered.match(/^(\d+(?:\.\d+)?)\s*([a-z]+)\s+(?:to|in)\s+([a-z]+)$/);
  if (!match) return null;
  const factor = conversions[`${match[2]}:${match[3]}`];
  if (!factor) return null;
  const result = Number(match[1]) * factor;
  return {
    result: Number.isInteger(result) ? result : Number(result.toFixed(4)),
    unit: match[3],
    fromUnit: match[2],
    factor,
    value: Number(match[1]),
  };
}

function buildFallbackReply(question, mode) {
  const normalized = question.toLowerCase().trim();
  const mathResult = evaluateSimpleMath(question);
  if (mathResult !== null) {
    return `Short answer: ${mathResult}\n\nExplanation: I calculated \`${question}\`.\n\nSteps / Details:\n1. Read the numbers and operators\n2. Evaluate the expression\n3. Final result is ${mathResult}`;
  }
  const percentResult = evaluatePercent(question);
  if (percentResult !== null) {
    return `Short answer: ${percentResult}\n\nExplanation: I calculated \`${question}\` as percentage of a number.\n\nSteps / Details:\n1. Convert the percentage into a decimal\n2. Multiply by the value\n3. Final result is ${percentResult}`;
  }
  const conversionResult = evaluateSimpleConversion(question);
  if (conversionResult !== null) {
    return `Short answer: ${conversionResult.result} ${conversionResult.unit}\n\nExplanation: 1 ${conversionResult.fromUnit} = ${conversionResult.factor} ${conversionResult.unit}.\n\nSteps / Details:\n1. Start with ${conversionResult.value} ${conversionResult.fromUnit}\n2. Multiply by ${conversionResult.factor}\n3. Final result is ${conversionResult.result} ${conversionResult.unit}`;
  }
  if (mode === "general") {
    if (normalized.includes("phone") || normalized.includes("mobile") || normalized.includes("laptop") || normalized.includes("tablet")) {
      return "I can help with that. Tell me your budget and what matters most, like camera, gaming, battery, display, study, or work use, and I will suggest better options.";
    }
    if (normalized.includes("order") || normalized.includes("refund") || normalized.includes("shipping") || normalized.includes("delivery")) {
      return "I can help with ecommerce issues too. Tell me the exact problem, like delayed delivery, refund, address change, or order status, and I will guide you step by step.";
    }
    if (normalized.includes("study") || normalized.includes("exam")) {
      return "I can help you make that easier. Tell me your exam date and subjects, and I will help you build a simple study plan.";
    }
    if (normalized.includes("job") || normalized.includes("career") || normalized.includes("interview")) {
      return "I can help with that. Tell me the exact situation, like interview prep, resume help, or choosing between offers, and I will help you think it through clearly.";
    }
    if (normalized.includes("budget") || normalized.includes("money") || normalized.includes("save")) {
      return "I can help with budgeting too. If you share your monthly income and main expenses, I can help you make a simple plan.";
    }
    if (normalized.includes("should i") || normalized.includes("what should i do") || normalized.includes("problem") || normalized.includes("confused") || normalized.includes("stuck")) {
      return "Yes, I can help you solve that. Tell me the situation in one or two lines, and I will help you break it down, compare options, and decide the best next step.";
    }
    return "I can help with that. Give me a little more detail so I can answer more clearly and usefully.";
  }
  if (normalized.includes("refund") || normalized.includes("charged")) {
    return "Refunds for annual plans are usually available within 14 days of the latest charge when usage stays below the fair-use threshold.";
  }
  if (normalized.includes("password") || normalized.includes("login")) {
    return "Customers can use the Forgot Password link on the login screen. If they no longer have access to their email, the case should move to manual verification.";
  }
  if (normalized.includes("shipping") || normalized.includes("order") || normalized.includes("address")) {
    return "Orders can usually be changed only before they enter the packed state. After that, it should be handled as a post-order support request.";
  }
  return "I can help summarize the issue and suggest the next support step, but for disputes, ownership conflicts, or security incidents, a human support agent should review the case.";
}

function summarizeSession(detail) {
  const preview = [...detail.messages].reverse().find((message) => message.role === "user")?.content || detail.messages.at(-1)?.content || "Start a conversation";
  return { id: detail.id, title: detail.title, mode: detail.mode, updated_at: detail.updated_at, preview };
}

function extractMemoryItems(messages) {
  const labels = [];
  const recentUserMessages = messages.filter((message) => message.role === "user").slice(-8);
  const keywordMap = [
    ["Shopping", ["phone", "laptop", "tablet", "watch", "product", "buy", "budget"]],
    ["Support", ["refund", "order", "shipping", "delivery", "password", "otp", "account"]],
    ["Coding", ["code", "java", "python", "javascript", "html", "css", "dsa", "program"]],
    ["Study", ["study", "exam", "learn", "explain", "subject"]],
    ["Career", ["job", "career", "interview", "resume"]],
    ["Money", ["budget", "money", "save", "expense", "salary"]],
  ];

  recentUserMessages.forEach((message) => {
    const text = message.content.toLowerCase();
    keywordMap.forEach(([label, keywords]) => {
      if (keywords.some((keyword) => text.includes(keyword)) && !labels.includes(label)) {
        labels.push(label);
      }
    });
  });

  return labels.slice(0, 5);
}

function extractConversationMemory(messages) {
  const recentUserMessages = messages
    .filter((message) => message.role === "user")
    .slice(-3)
    .map((message) => message.content.trim())
    .filter(Boolean);

  return recentUserMessages.map((message) => (message.length > 40 ? `${message.slice(0, 40)}...` : message));
}

export default function App() {
  const [token, setToken] = useState(() => window.localStorage.getItem(TOKEN_KEY) || "");
  const [activeMode, setActiveMode] = useState(() => window.localStorage.getItem(MODE_KEY) || "general");
  const [theme, setTheme] = useState(() => window.localStorage.getItem(THEME_KEY) || "light");
  const [user, setUser] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activePanel, setActivePanel] = useState("chat");
  const [products, setProducts] = useState([]);
  const [productTotal, setProductTotal] = useState(0);
  const [productPage, setProductPage] = useState(1);
  const [wishlist, setWishlist] = useState({ items: [] });
  const [cart, setCart] = useState({ items: [], total_amount: 0 });
  const [orders, setOrders] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [adminStats, setAdminStats] = useState(null);
  const [adminChatLogs, setAdminChatLogs] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [productSearch, setProductSearch] = useState("");
  const [productSuggestions, setProductSuggestions] = useState([]);
  const [category, setCategory] = useState("all");
  const [checkoutForm, setCheckoutForm] = useState({
    full_name: "",
    phone: "",
    address_line: "",
    city: "",
    state: "",
    postal_code: "",
    payment_method: "Cash on Delivery",
    payment_provider: "SmartPay Demo",
    payment_reference: "",
  });
  const [authMode, setAuthMode] = useState("login");
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "" });
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [retryAction, setRetryAction] = useState(null);
  const [booting, setBooting] = useState(true);
  const [selectedModel, setSelectedModel] = useState(() => window.localStorage.getItem(MODEL_KEY) || "gpt-4o");
  const [promptState, setPromptState] = useState(() => loadPromptState());
  const [promptTemplates, setPromptTemplates] = useState(() => loadPromptTemplates());
  const [templateName, setTemplateName] = useState("");
  const [showAiSettings, setShowAiSettings] = useState(false);
  const [accurateModeEnabled, setAccurateModeEnabled] = useState(false);

  const modeConfig = MODE_CONFIG[activeMode];
  const messages = useChatStore((state) => state.messages);
  const setMessages = useChatStore((state) => state.setMessages);
  const sessions = useChatStore((state) => state.sessions);
  const setSessions = useChatStore((state) => state.setSessions);
  const activeSessionId = useChatStore((state) => state.activeSessionId);
  const setActiveSessionId = useChatStore((state) => state.setActiveSessionId);
  const isLoading = useChatStore((state) => state.isLoading);
  const setIsLoading = useChatStore((state) => state.setIsLoading);
  const typingMessageKey = useChatStore((state) => state.typingMessageKey);
  const setTypingMessageKey = useChatStore((state) => state.setTypingMessageKey);
  const clearChat = useChatStore((state) => state.clearChat);
  const sessionsForMode = useMemo(() => sessions.filter((session) => session.mode === "general"), [sessions]);
  const wishlistIds = useMemo(() => wishlist.items.map((item) => item.product_id), [wishlist]);
  const memoryItems = useMemo(() => extractMemoryItems(messages), [messages]);
  const memoryTrail = useMemo(() => extractConversationMemory(messages), [messages]);
  const activePrompt = promptState[activeMode] || "";
  const apiClient = useMemo(
    () =>
      createApiClient({
        getToken: () => token,
        onUnauthorized: () => {
          setToken("");
          setUser(null);
          setRetryAction(null);
        },
      }),
    [token],
  );

  useEffect(() => {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  }, [token]);

  useEffect(() => {
    window.localStorage.setItem(MODE_KEY, activeMode);
  }, [activeMode]);

  useEffect(() => {
    window.localStorage.setItem(MODEL_KEY, selectedModel);
    window.localStorage.setItem(PROVIDER_HINT_KEY, selectedModel.startsWith("gemini") ? "gemini" : "openai");
  }, [selectedModel]);

  useEffect(() => {
    window.localStorage.setItem(THEME_KEY, theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem(PROMPT_KEY, JSON.stringify(promptState));
  }, [promptState]);

  useEffect(() => {
    window.localStorage.setItem(PROMPT_TEMPLATES_KEY, JSON.stringify(promptTemplates));
  }, [promptTemplates]);

  useEffect(() => {
    setProductPage(1);
  }, [category, productSearch]);

  useEffect(() => {
    if (user?.email) {
      saveAccurateMode(user.email, accurateModeEnabled);
    }
  }, [user, accurateModeEnabled]);

  useEffect(() => {
    async function bootstrap() {
      if (!token) {
        setBooting(false);
        return;
      }
      try {
        const [meData, sessionData] = await Promise.all([
          apiClient.request("/api/auth/me", { token }),
          apiClient.request("/api/chat-sessions", { token }),
        ]);
        const shouldRestoreAccurateMode = loadAccurateMode(meData.email);
        setUser(meData);
        setAccurateModeEnabled(shouldRestoreAccurateMode);
        if (shouldRestoreAccurateMode) {
          setSelectedModel("gpt-4o");
          setPromptState((current) => ({
            ...current,
            general: current.general?.trim() ? current.general : DEFAULT_GENERAL_PROMPT,
            support: current.support?.trim() ? current.support : DEFAULT_SUPPORT_PROMPT,
          }));
        }
        setCheckoutForm((current) => ({ ...current, full_name: meData.name }));
        setSessions(sessionData);
        await Promise.all([fetchProducts(token), fetchWishlist(token), fetchCart(token), fetchOrders(token), fetchDocuments(token)]);
        if (meData.is_admin) {
          await fetchAdminInsights(token);
        }
        const preferred = sessionData.find((session) => session.mode === "general") || sessionData[0];
        if (preferred) {
          setActiveMode("general");
          await openSession(preferred.id, token, "general");
        } else {
          await createSession("general", token);
        }
      } catch {
        setToken("");
        setUser(null);
      } finally {
        setBooting(false);
      }
    }
    bootstrap();
  }, []);

  useEffect(() => {
    if (!token) return;
    const timer = window.setTimeout(() => {
      fetchProducts().catch(() => {});
    }, 300);
    return () => window.clearTimeout(timer);
  }, [token, category, productSearch, productPage]);

  useEffect(() => {
    if (!token || !productSearch.trim()) {
      setProductSuggestions([]);
      return;
    }
    const timer = window.setTimeout(async () => {
      try {
        const suggestions = await apiClient.request(`/api/products/autocomplete?q=${encodeURIComponent(productSearch.trim())}`);
        setProductSuggestions(suggestions);
      } catch {
        setProductSuggestions([]);
      }
    }, 180);
    return () => window.clearTimeout(timer);
  }, [token, productSearch]);

  async function fetchProducts(tokenOverride = token) {
    const params = new URLSearchParams();
    if (category !== "all") params.set("category", category);
    if (productSearch.trim()) params.set("search", productSearch.trim());
    params.set("page", String(productPage));
    params.set("page_size", String(PRODUCT_PAGE_SIZE));
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const data = await apiClient.request(`/api/products${suffix}`, { token: tokenOverride });
    const filteredData = data.items.filter((product) => !HIDDEN_PRODUCT_NAMES.has(product.name));
    setProducts(filteredData);
    setProductTotal(Math.max(0, data.total - [...data.items].filter((product) => HIDDEN_PRODUCT_NAMES.has(product.name)).length));
    return filteredData;
  }

  async function fetchWishlist(tokenOverride = token) {
    const data = await apiClient.request("/api/wishlist", { token: tokenOverride });
    setWishlist(data);
    return data;
  }

  async function fetchCart(tokenOverride = token) {
    const data = await apiClient.request("/api/cart", { token: tokenOverride });
    setCart(data);
    return data;
  }

  async function fetchOrders(tokenOverride = token) {
    const data = await apiClient.request("/api/orders", { token: tokenOverride });
    setOrders(data);
    return data;
  }

  async function fetchDocuments(tokenOverride = token) {
    const data = await apiClient.request("/api/documents", { token: tokenOverride });
    setDocuments(data);
    return data;
  }

  async function fetchAdminInsights(tokenOverride = token) {
    if (!user?.is_admin && !tokenOverride) return;
    const [stats, logs] = await Promise.all([
      apiClient.request("/api/admin/stats", { token: tokenOverride }),
      apiClient.request("/api/admin/chat-logs", { token: tokenOverride }),
    ]);
    setAdminStats(stats);
    setAdminChatLogs(logs);
  }

  async function refreshSessions(tokenOverride = token) {
    const sessionData = await apiClient.request("/api/chat-sessions", { token: tokenOverride });
    setSessions(sessionData);
    return sessionData;
  }

  async function openSession(sessionId, tokenOverride = token, nextMode = null) {
    const detail = await apiClient.request(`/api/chat-sessions/${sessionId}`, { token: tokenOverride });
    setActivePanel("chat");
    setActiveSessionId(detail.id);
    setMessages(detail.messages);
    setTypingMessageKey("");
    setActiveMode(nextMode || detail.mode);
    setSessions((current) => {
      const summary = summarizeSession(detail);
      const filtered = current.filter((session) => session.id !== detail.id);
      return [summary, ...filtered];
    });
    return detail;
  }

  async function createSession(mode = activeMode, tokenOverride = token) {
    const detail = await apiClient.request("/api/chat-sessions", { method: "POST", body: { mode }, token: tokenOverride });
    const summary = summarizeSession(detail);
    setSessions((current) => [summary, ...current.filter((session) => session.id !== detail.id)]);
    setActiveMode(mode);
    setActiveSessionId(detail.id);
    setMessages(detail.messages);
    setTypingMessageKey("");
    return detail;
  }

  async function handleDeleteSession(sessionId) {
    if (isLoading) return;
    setPageError("");
    setRetryAction(null);
    try {
      await apiClient.request(`/api/chat-sessions/${sessionId}`, { method: "DELETE" });
      const updatedSessions = await refreshSessions();
      if (activeSessionId === sessionId) {
        const nextSession = updatedSessions.find((session) => session.mode === "general");
        if (nextSession) {
          await openSession(nextSession.id, token, "general");
        } else {
          await createSession("general");
          await refreshSessions();
        }
      }
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to delete chat.");
    }
  }

  const { sendMessage } = useChat({
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
    setRetryAction,
    buildFallbackReply,
    setTypingMessageKey,
  });

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setAuthError("");
    try {
      const endpoint = authMode === "register" ? "/api/auth/register" : "/api/auth/login";
      const body = authMode === "register" ? authForm : { email: authForm.email, password: authForm.password };
      const data = await apiClient.request(endpoint, { method: "POST", body });
      const shouldRestoreAccurateMode = loadAccurateMode(data.user.email);
      setToken(data.token);
      setUser(data.user);
      setAccurateModeEnabled(shouldRestoreAccurateMode);
      if (shouldRestoreAccurateMode) {
        setSelectedModel("gpt-4o");
      }
      setCheckoutForm((current) => ({ ...current, full_name: data.user.name }));
      setAuthForm({ name: "", email: "", password: "" });
        await Promise.all([fetchProducts(data.token), fetchWishlist(data.token), fetchCart(data.token), fetchOrders(data.token), fetchDocuments(data.token)]);
        if (data.user.is_admin) {
          await fetchAdminInsights(data.token);
        }
      await createSession("general", data.token);
      await refreshSessions(data.token);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setBooting(false);
    }
  }

  function updatePromptForMode(mode, value) {
    setAccurateModeEnabled(false);
    setPromptState((current) => ({
      ...current,
      [mode]: value,
    }));
  }

  function applyPreset(presetKey) {
    const preset = PROMPT_PRESETS[presetKey];
    if (!preset) return;
    if (presetKey === "accuracy") {
      applyAccurateSmartAi();
      return;
    }
    updatePromptForMode(activeMode, preset.text);
  }

  function applyAccurateSmartAi() {
    setSelectedModel("gpt-4o");
    setAccurateModeEnabled(true);
    setPromptState((current) => ({
      ...current,
      general: DEFAULT_GENERAL_PROMPT,
      support: DEFAULT_SUPPORT_PROMPT,
    }));
  }

  function saveCurrentPromptTemplate() {
    const name = templateName.trim();
    const text = activePrompt.trim();
    if (!name || !text) return;
    setPromptTemplates((current) => {
      const next = [{ name, text }, ...current.filter((item) => item.name.toLowerCase() !== name.toLowerCase())];
      return next.slice(0, 12);
    });
    setTemplateName("");
  }

  function applyTemplate(text) {
    setAccurateModeEnabled(false);
    updatePromptForMode(activeMode, text);
  }

  function handleModelChange(model) {
    setSelectedModel(model);
    if (model !== "gpt-4o") {
      setAccurateModeEnabled(false);
    }
  }

  function openFastApiStatus() {
    window.open(`${API_BASE_URL}/api/health`, "_blank", "noopener,noreferrer");
  }

  function openSqliteBackupView() {
    setActivePanel("chat");
    setShowAiSettings(false);
  }

  function openPaymentDemoView() {
    setActivePanel("store");
  }

  function openChatView() {
    setActivePanel("chat");
    setShowAiSettings(false);
  }

  function deleteTemplate(name) {
    setPromptTemplates((current) => current.filter((item) => item.name !== name));
  }

  async function handleAddToCart(productId) {
    try {
      setRetryAction(null);
      await apiClient.request("/api/cart/items", { method: "POST", body: { product_id: productId, quantity: 1 } });
      await fetchCart();
    } catch (error) {
      setRetryAction(() => () => handleAddToCart(productId));
      setPageError(error instanceof Error ? error.message : "Unable to add item to cart.");
    }
  }

  async function handleUpdateQty(productId, quantity) {
    try {
      setRetryAction(null);
      await apiClient.request(`/api/cart/items/${productId}`, { method: "PUT", body: { product_id: productId, quantity } });
      await fetchCart();
    } catch (error) {
      setRetryAction(() => () => handleUpdateQty(productId, quantity));
      setPageError(error instanceof Error ? error.message : "Unable to update cart.");
    }
  }

  async function handleToggleWishlist(productId) {
    try {
      setRetryAction(null);
      const exists = wishlistIds.includes(productId);
      const method = exists ? "DELETE" : "POST";
      const data = await apiClient.request(`/api/wishlist/${productId}`, { method });
      setWishlist(data);
    } catch (error) {
      setRetryAction(() => () => handleToggleWishlist(productId));
      setPageError(error instanceof Error ? error.message : "Unable to update wishlist.");
    }
  }

  async function handleCheckout() {
    if (isLoading || cart.items.length === 0) return;
    setIsLoading(true);
    setPageError("");
    setRetryAction(null);
    try {
      await apiClient.request("/api/orders/checkout", { method: "POST", body: checkoutForm });
      await Promise.all([fetchCart(), fetchOrders()]);
      setCheckoutForm((current) => ({
        ...current,
        address_line: "",
        city: "",
        state: "",
        postal_code: "",
        phone: "",
        payment_reference: "",
      }));
    } catch (error) {
      setRetryAction(() => () => handleCheckout());
      setPageError(error instanceof Error ? error.message : "Checkout failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function openProductDetail(productId) {
    try {
      setRetryAction(null);
      const data = await apiClient.request(`/api/products/${productId}`);
      setSelectedProduct(data);
    } catch (error) {
      setRetryAction(() => () => openProductDetail(productId));
      setPageError(error instanceof Error ? error.message : "Unable to load product details.");
    }
  }

  async function handleSaveProduct(payload, isEditing) {
    const path = isEditing ? `/api/admin/products/${payload.id}` : "/api/admin/products";
    const method = isEditing ? "PUT" : "POST";
    await apiClient.request(path, { method, body: payload });
    await fetchProducts();
  }

  async function handleDeleteProduct(productId) {
    try {
      setRetryAction(null);
      await apiClient.request(`/api/admin/products/${productId}`, { method: "DELETE" });
      if (selectedProduct?.id === productId) setSelectedProduct(null);
      await fetchProducts();
    } catch (error) {
      setRetryAction(() => () => handleDeleteProduct(productId));
      setPageError(error instanceof Error ? error.message : "Unable to delete product.");
    }
  }

  async function handleAdvanceOrder(orderId, currentStatus) {
    const index = ORDER_FLOW.indexOf(currentStatus);
    if (index === -1 || index === ORDER_FLOW.length - 1) return;
    try {
      setRetryAction(null);
      await apiClient.request(`/api/admin/orders/${orderId}/status`, { method: "PUT", body: { status: ORDER_FLOW[index + 1] } });
      await fetchOrders();
    } catch (error) {
      setRetryAction(() => () => handleAdvanceOrder(orderId, currentStatus));
      setPageError(error instanceof Error ? error.message : "Unable to update tracking.");
    }
  }

  async function startNewChat(nextMode = activeMode) {
    if (isLoading) return;
    setActivePanel("chat");
    await createSession(nextMode);
    await refreshSessions();
  }

  async function switchMode(mode) {
    if (mode === activeMode || isLoading) return;
    setActiveMode(mode);
    const existing = sessions.find((session) => session.mode === mode);
    if (existing) {
      await openSession(existing.id, token, mode);
      return;
    }
    await createSession(mode);
    await refreshSessions();
  }

  function logout() {
    if (isLoading) return;
    setToken("");
    setUser(null);
    setRetryAction(null);
    setAccurateModeEnabled(false);
    setSessions([]);
    clearChat();
    setProducts([]);
    setWishlist({ items: [] });
    setCart({ items: [], total_amount: 0 });
    setOrders([]);
    setSelectedProduct(null);
    setActiveSessionId(null);
    setAuthError("");
    setPageError("");
  }

  if (booting) {
    return <main className="login-shell"><section className="login-layout"><section className="login-card loading-card"><div className="login-badge">AI</div><h2>Loading Smart Commerce...</h2></section></section></main>;
  }

  if (!user) {
    return (
      <main className={`login-shell ${theme === "dark" ? "theme-dark" : ""}`}>
        <section className="login-layout">
          <div className="login-showcase">
            <div className="login-showcase-top">
              <div className="login-badge">AI</div>
              <button type="button" className="theme-toggle" onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")}>
                {theme === "dark" ? "Light" : "Dark"}
              </button>
            </div>
            <p className="eyebrow">Welcome Back</p>
            <h1>Open your AI ecommerce workspace with backend backup built in.</h1>
            <p className="login-copy">Sign in with email and password, browse products, manage wishlist, cart and orders, keep chats saved in the backend database, and use one AI for ecommerce help plus everyday problem solving.</p>
            <div className="login-showcase-rail">
              <span className="login-showcase-chip">AI chat + memory</span>
              <span className="login-showcase-chip">Store + orders</span>
              <span className="login-showcase-chip">PDF-aware answers</span>
              <span className="login-showcase-chip">Live backend sync</span>
            </div>
            <div className="login-feature-grid">
              <article className="login-feature-card"><strong>Storefront</strong><p>Browse products, open full detail views, add to wishlist, and place orders.</p></article>
              <article className="login-feature-card"><strong>Server Backup</strong><p>Chats, wishlist, cart, and orders are backed by the FastAPI app and SQLite database.</p></article>
              <article className="login-feature-card"><strong>AI Problem Solving</strong><p>Ask for shopping help, order support, everyday decisions, writing help, and practical guidance.</p></article>
            </div>
          </div>
          <section className="login-card">
            <div className="auth-switch">
              <button className={`auth-tab ${authMode === "login" ? "active" : ""}`} onClick={() => setAuthMode("login")} type="button">Sign in</button>
              <button className={`auth-tab ${authMode === "register" ? "active" : ""}`} onClick={() => setAuthMode("register")} type="button">Create account</button>
            </div>
            <p className="eyebrow">Secure Access</p>
            <h2>{authMode === "login" ? "Sign in to Smart Commerce" : "Create your Smart Commerce account"}</h2>
            <p className="login-form-copy">{authMode === "login" ? "Enter your email and password to restore your saved chats, wishlist, cart, and orders." : "Create an account to save your chat history and shopping data in the backend database."}</p>
            <form className="login-form" onSubmit={handleAuthSubmit}>
              {authMode === "register" ? <label>Name<input type="text" value={authForm.name} onChange={(event) => setAuthForm((current) => ({ ...current, name: event.target.value }))} placeholder="Your name" /></label> : null}
              <label>Email<input type="email" value={authForm.email} onChange={(event) => setAuthForm((current) => ({ ...current, email: event.target.value }))} placeholder="you@example.com" /></label>
              <label>Password<input type="password" value={authForm.password} onChange={(event) => setAuthForm((current) => ({ ...current, password: event.target.value }))} placeholder="Enter password" /></label>
              {authError ? <p className="auth-error">{authError}</p> : null}
              <button type="submit" className="login-button">{authMode === "login" ? "Continue to store" : "Create account"}</button>
            </form>
          </section>
        </section>
      </main>
    );
  }

  return (
    <div className={`app-shell commerce-shell ${sidebarCollapsed ? "sidebar-collapsed" : ""} ${theme === "dark" ? "theme-dark" : ""}`}>
      <aside className={`sidebar ${sidebarCollapsed ? "collapsed" : ""}`}>
        <button
          type="button"
          className="sidebar-collapse-button"
          onClick={() => setSidebarCollapsed((current) => !current)}
          aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? "»" : "«"}
        </button>
        <button className="new-chat-button" onClick={() => startNewChat()} title="New chat">
          {sidebarCollapsed ? "+" : "New chat"}
        </button>
        <div className="sidebar-section">
          {sidebarCollapsed ? null : <p className="sidebar-label">Workspace</p>}
          <button className={`history-item ${activePanel === "chat" ? "active" : ""}`} onClick={() => setActivePanel("chat")} title="Smart Chat">
            {sidebarCollapsed ? "Chat" : "Smart Chat"}
          </button>
          <button className={`history-item ${activePanel === "store" ? "active" : ""}`} onClick={() => setActivePanel("store")} title="Store & Orders">
            {sidebarCollapsed ? "Store" : "Store & Orders"}
          </button>
        </div>
        {sidebarCollapsed ? null : (
          <div className="sidebar-section profile-card">
            <p className="sidebar-label">Signed In</p>
            <strong>{user.name}</strong>
            <p className="profile-email">{user.email}</p>
            {user.is_admin ? <p className="admin-chip">Admin access enabled</p> : null}
            <button className="logout-button" onClick={logout}>Log out</button>
          </div>
        )}
        {sidebarCollapsed ? null : (
          <div className="sidebar-section">
            <p className="sidebar-label">Saved AI Chats</p>
            <div className="session-list">
              {sessionsForMode.map((session) => (
                <article key={session.id} className={`session-card ${session.id === activeSessionId ? "active" : ""}`}>
                  <button className="session-item" onClick={() => openSession(session.id, token, "general")}>
                    <strong>{session.title}</strong><span>{session.preview}</span>
                  </button>
                  <button className="session-delete-button" type="button" onClick={() => handleDeleteSession(session.id)}>
                    Delete
                  </button>
                </article>
              ))}
            </div>
          </div>
        )}
        {sidebarCollapsed ? null : <div className="sidebar-footer"><div className="product-badge">AI</div><div><strong>Smart AI</strong><p>One assistant for shopping, support, and real-life help</p></div></div>}
      </aside>

        <main className="main-panel">
          <header className="topbar">
            <div className="topbar-copy">
              <p className="eyebrow">Single AI Workspace</p>
              <h1>{activePanel === "chat" ? "Smart AI assistant" : "Store and orders"}</h1>
            <p className="topbar-subtitle">
              {activePanel === "chat"
                ? "Ask one AI for shopping advice, ecommerce problem solving, support help, and everyday real-life questions."
                : "Browse products, save wishlist items, place orders, and track shipments from one shopping workspace."}
            </p>
            {pageError ? (
              <div className="page-error-toast" role="alert">
                <div>
                  <strong>Something went wrong</strong>
                  <p>{pageError}</p>
                </div>
                <div className="page-error-actions">
                  {retryAction ? (
                    <button
                      type="button"
                      className="page-error-retry"
                      onClick={() => {
                        setPageError("");
                        const action = retryAction;
                        setRetryAction(null);
                        action?.();
                      }}
                    >
                      Retry
                    </button>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => {
                      setPageError("");
                      setRetryAction(null);
                    }}
                    aria-label="Dismiss error"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            ) : null}
            {activePanel === "chat" ? (
              <>
                <div className="ai-settings-toggle-row">
                  <span className="summary-chip">{selectedModel}</span>
                  <button
                    type="button"
                    className={`ai-settings-toggle ${showAiSettings ? "active" : ""}`}
                    onClick={() => setShowAiSettings((current) => !current)}
                  >
                    {showAiSettings ? "Hide settings" : "AI settings"}
                  </button>
                  {accurateModeEnabled ? <span className="summary-chip summary-chip-accent">Accuracy mode</span> : null}
                  <button type="button" className="accurate-ai-button compact" onClick={applyAccurateSmartAi}>
                    Accurate mode
                  </button>
                </div>
                {showAiSettings ? (
                  <div className="ai-settings-panel">
                    <div className="ai-model-row">
                      {MODEL_OPTIONS.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          className={`model-chip ${selectedModel === option.value ? "active" : ""}`}
                          onClick={() => handleModelChange(option.value)}
                        >
                          <strong>{option.label}</strong>
                          <span>{option.meta}</span>
                        </button>
                      ))}
                    </div>
                    <div className="preset-row">
                      {Object.entries(PROMPT_PRESETS).map(([key, preset]) => (
                        <button key={key} type="button" className="preset-chip" onClick={() => applyPreset(key)}>
                          {preset.label}
                        </button>
                      ))}
                    </div>
                    <label className="prompt-editor">
                      <span>Prompt for {activeMode === "general" ? "general mode" : "support mode"}</span>
                      <textarea
                        value={activePrompt}
                        onChange={(event) => updatePromptForMode(activeMode, event.target.value)}
                        placeholder={"Example:\n- Give short, clear answers\n- Use simple language\n- If coding, give full working code\n- Be helpful and friendly"}
                        rows="4"
                      />
                    </label>
                    <div className="template-save-row">
                      <input
                        type="text"
                        value={templateName}
                        onChange={(event) => setTemplateName(event.target.value)}
                        placeholder="Template name"
                      />
                      <button type="button" className="template-save-button" onClick={saveCurrentPromptTemplate}>
                        Save template
                      </button>
                    </div>
                    {promptTemplates.length ? (
                      <div className="template-list">
                        {promptTemplates.map((template) => (
                          <article key={template.name} className="template-card">
                            <button type="button" className="template-apply" onClick={() => applyTemplate(template.text)}>
                              <strong>{template.name}</strong>
                              <span>{template.text}</span>
                            </button>
                            <button type="button" className="template-delete" onClick={() => deleteTemplate(template.name)}>
                              Delete
                            </button>
                          </article>
                        ))}
                      </div>
                    ) : null}
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
          <div className="topbar-view-tabs">
            <button
              type="button"
              className="topbar-view-tab theme-toggle-tab"
              onClick={() => setTheme((current) => current === "dark" ? "light" : "dark")}
            >
              {theme === "dark" ? "Light" : "Dark"}
            </button>
            <button
              type="button"
              className={`topbar-view-tab ${activePanel === "chat" ? "active" : ""}`}
              onClick={() => setActivePanel("chat")}
            >
              Chat
            </button>
            <button
              type="button"
              className={`topbar-view-tab ${activePanel === "store" ? "active" : ""}`}
              onClick={() => setActivePanel("store")}
            >
              Store
            </button>
          </div>
        </header>

        {activePanel === "chat" ? (
          <ChatWindow
            messages={messages}
            onSend={sendMessage}
            isLoading={isLoading}
            starterPrompts={modeConfig.starterPrompts}
            assistantName="Smart AI"
            activeMode={activeMode}
            placeholder="Ask about products, ecommerce issues, support, life decisions, study, career, or everyday questions..."
            emptyDescription="Use one AI for product recommendations, order help, support guidance, study plans, decisions, and everyday problem solving."
            memoryItems={memoryItems}
            memoryTrail={memoryTrail}
            typingMessageKey={typingMessageKey}
            focusSignal={`${activePanel}-${activeSessionId}-${messages.length}-${showAiSettings ? "settings" : "chat"}`}
          />
        ) : (
          <div className="commerce-layout">
            <div className="commerce-main">
              <>
                <ProductStorefront
                  products={products}
                  productTotal={productTotal}
                  productPage={productPage}
                  onPageChange={setProductPage}
                  pageSize={PRODUCT_PAGE_SIZE}
                  productSearch={productSearch}
                  setProductSearch={setProductSearch}
                  productSuggestions={productSuggestions}
                  category={category}
                  setCategory={setCategory}
                  onAsk={sendMessage}
                  onAddToCart={handleAddToCart}
                  onViewDetails={openProductDetail}
                  onToggleWishlist={handleToggleWishlist}
                  wishlistIds={wishlistIds}
                />
                {user.is_admin ? (
                  <AdminPanel
                    products={products}
                    stats={adminStats}
                    chatLogs={adminChatLogs}
                    documents={documents}
                    onSave={handleSaveProduct}
                    onDelete={handleDeleteProduct}
                    busy={isLoading}
                  />
                ) : null}
              </>
            </div>
            <CommerceSidebar
              cart={cart}
              wishlist={wishlist}
              orders={orders}
              checkoutForm={checkoutForm}
              setCheckoutForm={setCheckoutForm}
              onCheckout={handleCheckout}
              onUpdateQty={handleUpdateQty}
              onToggleWishlist={handleToggleWishlist}
              onViewDetails={openProductDetail}
              onAdvanceOrder={handleAdvanceOrder}
              loading={isLoading}
              isAdmin={user.is_admin}
            />
          </div>
        )}
      </main>

      <ProductDetailModal
        product={selectedProduct}
        inWishlist={selectedProduct ? wishlistIds.includes(selectedProduct.id) : false}
        onClose={() => setSelectedProduct(null)}
        onAddToCart={handleAddToCart}
        onToggleWishlist={handleToggleWishlist}
        onAsk={sendMessage}
      />
    </div>
  );
}
