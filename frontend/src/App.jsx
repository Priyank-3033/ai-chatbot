import { useEffect, useMemo, useState } from "react";
import AdminPanel from "./components/AdminPanel";
import ChatWindow from "./components/ChatWindow";
import CommerceSidebar from "./components/CommerceSidebar";
import ProductDetailModal from "./components/ProductDetailModal";
import ProductStorefront from "./components/ProductStorefront";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const TOKEN_KEY = "smart-chat-token-v1";
const MODE_KEY = "smart-chat-mode-v1";
const ORDER_FLOW = ["Placed", "Packed", "Shipped", "Out for Delivery", "Delivered"];

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

function buildSourceText(sources, mode) {
  if (!sources || sources.length === 0) return "";
  const heading = mode === "support" ? "Sources" : "Suggestions";
  return `\n\n${heading}:\n${sources.map((source) => `- ${source.title}: ${source.snippet}`).join("\n")}`;
}

function buildFallbackReply(question, mode) {
  const normalized = question.toLowerCase().trim();
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

export default function App() {
  const [token, setToken] = useState(() => window.localStorage.getItem(TOKEN_KEY) || "");
  const [activeMode, setActiveMode] = useState(() => window.localStorage.getItem(MODE_KEY) || "general");
  const [user, setUser] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [activePanel, setActivePanel] = useState("chat");
  const [products, setProducts] = useState([]);
  const [wishlist, setWishlist] = useState({ items: [] });
  const [cart, setCart] = useState({ items: [], total_amount: 0 });
  const [orders, setOrders] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [productSearch, setProductSearch] = useState("");
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
  const [isLoading, setIsLoading] = useState(false);
  const [booting, setBooting] = useState(true);

  const modeConfig = MODE_CONFIG[activeMode];
  const sessionsForMode = useMemo(() => sessions.filter((session) => session.mode === "general"), [sessions]);
  const wishlistIds = useMemo(() => wishlist.items.map((item) => item.product_id), [wishlist]);

  useEffect(() => {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  }, [token]);

  useEffect(() => {
    window.localStorage.setItem(MODE_KEY, activeMode);
  }, [activeMode]);

  useEffect(() => {
    async function bootstrap() {
      if (!token) {
        setBooting(false);
        return;
      }
      try {
        const [meData, sessionData] = await Promise.all([
          apiFetch("/api/auth/me", { token }),
          apiFetch("/api/chat-sessions", { token }),
        ]);
        setUser(meData);
        setCheckoutForm((current) => ({ ...current, full_name: meData.name }));
        setSessions(sessionData);
        await Promise.all([fetchProducts(token), fetchWishlist(token), fetchCart(token), fetchOrders(token)]);
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
    fetchProducts().catch(() => {});
  }, [token, category, productSearch]);

  async function apiFetch(path, { method = "GET", body, token: tokenOverride } = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(tokenOverride || token ? { Authorization: `Bearer ${tokenOverride || token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      let detail = "Request failed.";
      try {
        const errorData = await response.json();
        if (errorData?.detail) detail = errorData.detail;
      } catch {
        // noop
      }
      throw new Error(detail);
    }
    return response.json();
  }

  async function fetchProducts(tokenOverride = token) {
    const params = new URLSearchParams();
    if (category !== "all") params.set("category", category);
    if (productSearch.trim()) params.set("search", productSearch.trim());
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const data = await apiFetch(`/api/products${suffix}`, { token: tokenOverride });
    setProducts(data);
    return data;
  }

  async function fetchWishlist(tokenOverride = token) {
    const data = await apiFetch("/api/wishlist", { token: tokenOverride });
    setWishlist(data);
    return data;
  }

  async function fetchCart(tokenOverride = token) {
    const data = await apiFetch("/api/cart", { token: tokenOverride });
    setCart(data);
    return data;
  }

  async function fetchOrders(tokenOverride = token) {
    const data = await apiFetch("/api/orders", { token: tokenOverride });
    setOrders(data);
    return data;
  }

  async function refreshSessions(tokenOverride = token) {
    const sessionData = await apiFetch("/api/chat-sessions", { token: tokenOverride });
    setSessions(sessionData);
    return sessionData;
  }

  async function openSession(sessionId, tokenOverride = token, nextMode = null) {
    const detail = await apiFetch(`/api/chat-sessions/${sessionId}`, { token: tokenOverride });
    setActivePanel("chat");
    setActiveSessionId(detail.id);
    setMessages(detail.messages);
    setActiveMode(nextMode || detail.mode);
    setSessions((current) => {
      const summary = summarizeSession(detail);
      const filtered = current.filter((session) => session.id !== detail.id);
      return [summary, ...filtered];
    });
    return detail;
  }

  async function createSession(mode = activeMode, tokenOverride = token) {
    const detail = await apiFetch("/api/chat-sessions", { method: "POST", body: { mode }, token: tokenOverride });
    const summary = summarizeSession(detail);
    setSessions((current) => [summary, ...current.filter((session) => session.id !== detail.id)]);
    setActiveMode(mode);
    setActiveSessionId(detail.id);
    setMessages(detail.messages);
    return detail;
  }

  async function handleDeleteSession(sessionId) {
    if (isLoading) return;
    setPageError("");
    try {
      await apiFetch(`/api/chat-sessions/${sessionId}`, { method: "DELETE" });
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

  async function handleAuthSubmit(event) {
    event.preventDefault();
    setAuthError("");
    try {
      const endpoint = authMode === "register" ? "/api/auth/register" : "/api/auth/login";
      const body = authMode === "register" ? authForm : { email: authForm.email, password: authForm.password };
      const data = await apiFetch(endpoint, { method: "POST", body });
      setToken(data.token);
      setUser(data.user);
      setCheckoutForm((current) => ({ ...current, full_name: data.user.name }));
      setAuthForm({ name: "", email: "", password: "" });
      await Promise.all([fetchProducts(data.token), fetchWishlist(data.token), fetchCart(data.token), fetchOrders(data.token)]);
      await createSession("general", data.token);
      await refreshSessions(data.token);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setBooting(false);
    }
  }

  async function sendMessage(input) {
    const question = input.trim();
    if (!question || isLoading || !activeSessionId) return;
    setActivePanel("chat");
    const optimisticMessages = [...messages, { role: "user", content: question }];
    setMessages(optimisticMessages);
    setIsLoading(true);
    setPageError("");
    try {
      const data = await apiFetch("/api/chat", {
        method: "POST",
        body: { question, history: messages.map((message) => ({ role: message.role, content: message.content })), mode: activeMode, session_id: activeSessionId },
      });
      const detail = await openSession(data.session_id, token, activeMode);
      setMessages(detail.messages.map((message, index) => index === detail.messages.length - 1 && message.role === "assistant" ? { ...message, content: `${message.content}${buildSourceText(data.sources, activeMode)}` } : message));
      await refreshSessions();
    } catch (error) {
      const note = error instanceof Error ? error.message : "The backend request failed.";
      setMessages([...optimisticMessages, { role: "assistant", content: `${buildFallbackReply(question, activeMode)}\n\nNote: ${note}` }]);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAddToCart(productId) {
    try {
      await apiFetch("/api/cart/items", { method: "POST", body: { product_id: productId, quantity: 1 } });
      await fetchCart();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to add item to cart.");
    }
  }

  async function handleUpdateQty(productId, quantity) {
    try {
      await apiFetch(`/api/cart/items/${productId}`, { method: "PUT", body: { product_id: productId, quantity } });
      await fetchCart();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to update cart.");
    }
  }

  async function handleToggleWishlist(productId) {
    try {
      const exists = wishlistIds.includes(productId);
      const method = exists ? "DELETE" : "POST";
      const data = await apiFetch(`/api/wishlist/${productId}`, { method });
      setWishlist(data);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to update wishlist.");
    }
  }

  async function handleCheckout() {
    if (isLoading || cart.items.length === 0) return;
    setIsLoading(true);
    setPageError("");
    try {
      await apiFetch("/api/orders/checkout", { method: "POST", body: checkoutForm });
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
      setPageError(error instanceof Error ? error.message : "Checkout failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function openProductDetail(productId) {
    try {
      const data = await apiFetch(`/api/products/${productId}`);
      setSelectedProduct(data);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to load product details.");
    }
  }

  async function handleSaveProduct(payload, isEditing) {
    const path = isEditing ? `/api/admin/products/${payload.id}` : "/api/admin/products";
    const method = isEditing ? "PUT" : "POST";
    await apiFetch(path, { method, body: payload });
    await fetchProducts();
  }

  async function handleDeleteProduct(productId) {
    try {
      await apiFetch(`/api/admin/products/${productId}`, { method: "DELETE" });
      if (selectedProduct?.id === productId) setSelectedProduct(null);
      await fetchProducts();
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Unable to delete product.");
    }
  }

  async function handleAdvanceOrder(orderId, currentStatus) {
    const index = ORDER_FLOW.indexOf(currentStatus);
    if (index === -1 || index === ORDER_FLOW.length - 1) return;
    try {
      await apiFetch(`/api/admin/orders/${orderId}/status`, { method: "PUT", body: { status: ORDER_FLOW[index + 1] } });
      await fetchOrders();
    } catch (error) {
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
    setSessions([]);
    setMessages([]);
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
      <main className="login-shell">
        <section className="login-layout">
          <div className="login-showcase">
            <div className="login-badge">AI</div>
            <p className="eyebrow">Welcome Back</p>
            <h1>Open your AI ecommerce workspace with backend backup built in.</h1>
          <p className="login-copy">Sign in with email and password, browse products, manage wishlist, cart and orders, keep chats saved in the backend database, and use one AI for ecommerce help plus everyday problem solving.</p>
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
    <div className="app-shell commerce-shell">
      <aside className="sidebar">
        <button className="new-chat-button" onClick={() => startNewChat()}>New chat</button>
        <div className="sidebar-section">
          <p className="sidebar-label">Workspace</p>
          <button className={`history-item ${activePanel === "chat" ? "active" : ""}`} onClick={() => setActivePanel("chat")}>Smart Chat</button>
          <button className={`history-item ${activePanel === "store" ? "active" : ""}`} onClick={() => setActivePanel("store")}>Store & Orders</button>
        </div>
        <div className="sidebar-section profile-card">
          <p className="sidebar-label">Signed In</p>
          <strong>{user.name}</strong>
          <p className="profile-email">{user.email}</p>
          {user.is_admin ? <p className="admin-chip">Admin access enabled</p> : null}
          <button className="logout-button" onClick={logout}>Log out</button>
        </div>
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
        <div className="sidebar-footer"><div className="product-badge">AI</div><div><strong>Smart AI</strong><p>One assistant for shopping, support, and real-life help</p></div></div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-copy">
            <p className="eyebrow">Single AI Workspace</p>
            <h1>{activePanel === "chat" ? "Smart AI assistant" : "Store and orders"}</h1>
            <p className="topbar-subtitle">
              {activePanel === "chat"
                ? "Ask one AI for shopping advice, ecommerce problem solving, support help, and everyday real-life questions."
                : "Browse products, open detail pages, save wishlist items, place orders, and track shipments."}
            </p>
            {pageError ? <p className="page-error">{pageError}</p> : null}
          </div>
          <div className="topbar-badges">
            <span className="topbar-badge">FastAPI</span>
            <span className="topbar-badge">SQLite Backup</span>
            <span className="topbar-badge">Payment Demo</span>
            <span className="topbar-badge accent">{activePanel === "chat" ? "Chat View" : "Store View"}</span>
          </div>
        </header>

        {activePanel === "chat" ? (
          <ChatWindow
            messages={messages}
            onSend={sendMessage}
            isLoading={isLoading}
            starterPrompts={modeConfig.starterPrompts}
            assistantName="Smart AI"
            placeholder="Ask about products, ecommerce issues, support, life decisions, study, career, or everyday questions..."
            emptyDescription="Use one AI for product recommendations, order help, support guidance, study plans, decisions, and everyday problem solving."
          />
        ) : (
          <div className="commerce-layout">
            <div className="commerce-main">
              <>
                <ProductStorefront
                  products={products}
                  productSearch={productSearch}
                  setProductSearch={setProductSearch}
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
